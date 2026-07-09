import json
import re
from typing import Any

import litellm
import structlog

from app.adapters.base import (
    EvaluationAdapter,
    JudgeConfigParams,
    Message,
    Score,
    ToolCall,
)
from app.services.provider_utils import get_litellm_client

logger = structlog.get_logger()


class LiteLLMJudgeAdapter(EvaluationAdapter):
    """Direct LLM-as-judge adapter using LiteLLM for model access."""

    DEFAULT_PROMPT_TEMPLATE = """You are evaluating the quality of an AI assistant's response.

Question: {question}
Expected Answer: {expected_answer}
Actual Answer: {actual_answer}

Score the response on a scale of 0.0 to 1.0 for correctness.
A score of 1.0 means the actual answer is fully correct and complete.
A score of 0.0 means the actual answer is completely wrong.

Respond with ONLY a JSON object: {{"score": <float>, "reasoning": "<explanation>"}}"""

    RAG_METRICS_PROMPT_TEMPLATE = """\
You are evaluating the quality of a Retrieval-Augmented Generation (RAG) response.

## Question
{question}

## Expected Answer
{expected_answer}

## Actual Answer
{actual_answer}

## Retrieved Context Chunks
{formatted_chunks}

## Evaluation Rubric

Score each dimension on a scale of 0.0 to 1.0:

1. **context_precision** (0.0-1.0): Are the retrieved chunks relevant to the question? \
A score of 1.0 means every chunk is highly relevant and useful for answering the question.
2. **context_recall** (0.0-1.0): Do the retrieved chunks cover the information needed to answer \
the question completely? A score of 1.0 means the chunks contain all the necessary information. \
{context_recall_instruction}
3. **faithfulness** (0.0-1.0): Is the answer grounded in the retrieved chunks without hallucination? \
A score of 1.0 means every claim in the answer is supported by the chunks.
4. **answer_relevance** (0.0-1.0): Does the answer directly address the question? \
A score of 1.0 means the answer fully and precisely addresses what was asked.

Respond with ONLY a JSON object:
{{"context_precision": <float>, "context_recall": <float>, "faithfulness": <float>, \
"answer_relevance": <float>, "reasoning": "<explanation>"}}"""

    _RAG_DIMENSIONS = ("context_precision", "context_recall", "faithfulness", "answer_relevance")

    CONVERSATION_PROMPT_TEMPLATE = """\
You are evaluating the quality of a multi-turn conversation between a user and an AI assistant.

## Conversation Transcript
{transcript}

## Evaluation Rubric

Score each dimension on a scale of 0.0 to 1.0:

1. **relevance** (0.0-1.0): How relevant are the agent's responses to the user's questions? \
A score of 1.0 means every response directly addresses the user's needs.
2. **tool_use_accuracy** (0.0-1.0): Were tools used appropriately and correctly? \
A score of 1.0 means tools were used exactly when needed with correct arguments. \
If no tools were available or needed, score based on whether the agent correctly \
refrained from using them (0.5 if neutral).
3. **resolution** (0.0-1.0): Did the agent successfully resolve the user's issue? \
A score of 1.0 means the issue was fully resolved.
4. **response_quality** (0.0-1.0): Quality of communication, clarity, and helpfulness. \
A score of 1.0 means responses are clear, well-structured, and helpful.

Respond with ONLY a JSON object:
{{"relevance": <float>, "tool_use_accuracy": <float>, "resolution": <float>, \
"response_quality": <float>, "overall": <float>, "reasoning": "<explanation>"}}"""

    _CONVERSATION_DIMENSIONS = ("relevance", "tool_use_accuracy", "resolution", "response_quality")

    DIMENSION_QA_PROMPT_TEMPLATE = """\
You are evaluating the quality of an AI assistant's response.

## Question
{question}

## Expected Answer
{expected_answer}

## Actual Answer
{actual_answer}

## Scoring Rubric

Score each dimension on a scale of 0.0 to 1.0:

{dimensions_section}

Respond with ONLY a JSON object:
{{{response_schema}, "reasoning": "<brief explanation>"}}\
"""

    @classmethod
    def get_config_schema(cls) -> dict[str, Any]:
        """Return JSON Schema for configurable fields of the LiteLLM judge adapter."""
        return {
            "type": "object",
            "properties": {
                "model": {
                    "type": "string",
                    "description": "LiteLLM model identifier for the judge (e.g. 'gpt-4.1', 'ollama/llama3.2:3b').",
                },
                "temperature": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 2.0,
                    "default": 0.0,
                    "description": "Sampling temperature for the judge LLM.",
                },
                "pass_threshold": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "default": 0.7,
                    "description": "Minimum score to consider an evaluation as passed.",
                },
                "prompt_template": {
                    "type": "string",
                    "description": (
                        "Custom prompt template for the judge."
                        " Supports {question}, {expected_answer}, {actual_answer} placeholders."
                    ),
                },
                "dimensions": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Custom scoring dimensions with weights.",
                },
            },
        }

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        api_base: str | None = None,
        max_concurrency: int = 10,
        extra_params: dict | None = None,
        proxy: str | None = None,
        ssl_cert_path: str | None = None,
        ssl_client_key: str | None = None,
    ):
        super().__init__(max_concurrency=max_concurrency)
        self.model = model
        self.api_key = api_key
        self.api_base = api_base
        self.extra_params = extra_params or {}
        self.proxy = proxy
        self.ssl_cert_path = ssl_cert_path
        self.ssl_client_key = ssl_client_key

    _CODE_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*\n?(.*?)\n?\s*```\s*$", re.DOTALL)

    @staticmethod
    def _parse_json_lenient(content: str) -> dict | None:
        """Parse JSON from LLM output, stripping markdown code fences if present."""
        content = content.strip()
        try:
            return json.loads(content)
        except (json.JSONDecodeError, TypeError):
            pass

        m = LiteLLMJudgeAdapter._CODE_FENCE_RE.match(content)
        if m:
            try:
                return json.loads(m.group(1).strip())
            except (json.JSONDecodeError, TypeError):
                pass

        return None

    async def _ask_judge(
        self,
        prompt: str,
        judge_config: JudgeConfigParams | None,
        mode: str,
        retries: int = 1,
    ) -> dict | None:
        """Build kwargs, call litellm, parse JSON response.

        Retries once on parse failure. Strips markdown code fences before
        parsing. Returns the parsed dict, or None on persistent failure.
        """
        model = (judge_config.model if judge_config else None) or self.model
        temperature = judge_config.temperature if judge_config and judge_config.temperature is not None else 0.0

        kwargs: dict = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        }
        if self.api_key:
            kwargs["api_key"] = self.api_key
        if self.api_base:
            kwargs["api_base"] = self.api_base
        for k, v in self.extra_params.items():
            if k not in kwargs:
                kwargs[k] = v

        client = get_litellm_client(
            self.proxy,
            self.ssl_cert_path,
            self.ssl_client_key,
            self.api_key,
            self.api_base,
        )
        if client is not None:
            kwargs["client"] = client

        for attempt in range(1 + retries):
            try:
                response = await litellm.acompletion(**kwargs)
            except Exception as exc:
                logger.warning("judge.api_error", error=str(exc), mode=mode, attempt=attempt + 1)
                if attempt < retries:
                    continue
                return None

            content = response.choices[0].message.content
            if content is None:
                logger.warning("judge.empty_response", mode=mode, attempt=attempt + 1)
                if attempt < retries:
                    continue
                return None

            parsed = self._parse_json_lenient(content)
            if parsed is not None:
                return parsed

            logger.warning("judge.parse_failed", raw_content=content[:500], mode=mode, attempt=attempt + 1)

        return None

    @staticmethod
    def _build_dimensions_prompt(dimensions: list[dict]) -> tuple[str, list[str]]:
        """Build the scoring rubric section and response schema from rubric dimensions.

        When a dimension carries a non-empty ``criteria`` list, criteria
        sub-items are appended below the dimension line so the judge LLM
        can evaluate each criterion individually.

        Returns (dimensions_section, response_schema, dimension_names).
        """
        lines = []
        names = []
        for i, dim in enumerate(dimensions, 1):
            name = dim.get("name", f"dimension_{i}")
            desc = dim.get("description", "")
            weight = dim.get("weight", 1.0)
            lines.append(f"{i}. **{name}** (0.0-1.0, weight={weight}): {desc}")
            names.append(name)

            criteria = dim.get("criteria") or []
            if criteria:
                lines.append("   Criteria:")
                for crit in criteria:
                    crit_name = crit.get("name", "unnamed")
                    crit_text = crit.get("criterion", "")
                    crit_weight = crit.get("weight", 1.0)
                    lines.append(f"   - {crit_name} (weight {crit_weight}): {crit_text}")

        section = "\n".join(lines)
        schema = ", ".join(f'"{n}": <float>' for n in names)
        return section, schema, names

    async def evaluate_qa(
        self,
        question: str,
        expected_answer: str,
        actual_answer: str,
        judge_config: JudgeConfigParams,
    ) -> Score:
        """Score a single Q&A pair using an LLM judge.

        When judge_config.dimensions is non-empty (from a rubric), scores each
        dimension individually and aggregates by weight. Otherwise uses the
        single-score default prompt.
        """
        async with self._semaphore:
            dimensions = judge_config.dimensions
            if dimensions:
                return await self._evaluate_qa_with_dimensions(
                    question, expected_answer, actual_answer, judge_config, dimensions
                )

            prompt_template = judge_config.prompt_template or self.DEFAULT_PROMPT_TEMPLATE
            prompt = prompt_template.format(
                question=question,
                expected_answer=expected_answer,
                actual_answer=actual_answer,
            )
            result = await self._ask_judge(prompt, judge_config, "qa")
            if result is None:
                return Score(value=0.0, passed=False, reasoning="LLM returned empty or unparseable response")
            score_value = float(result.get("score", 0.0))
            reasoning = result.get("reasoning", "")
            passed = score_value >= (judge_config.pass_threshold or 0.7)
            return Score(value=score_value, passed=passed, reasoning=reasoning)

    async def _evaluate_qa_with_dimensions(
        self,
        question: str,
        expected_answer: str,
        actual_answer: str,
        judge_config: JudgeConfigParams,
        dimensions: list[dict],
    ) -> Score:
        """Score a Q&A pair using per-dimension rubric scoring."""
        dimensions_section, response_schema, _dim_names = self._build_dimensions_prompt(dimensions)

        if judge_config.prompt_template:
            prompt = judge_config.prompt_template.format(
                question=question,
                expected_answer=expected_answer,
                actual_answer=actual_answer,
            )
        else:
            prompt = self.DIMENSION_QA_PROMPT_TEMPLATE.format(
                question=question,
                expected_answer=expected_answer,
                actual_answer=actual_answer,
                dimensions_section=dimensions_section,
                response_schema=response_schema,
            )

        result = await self._ask_judge(prompt, judge_config, "qa")
        if result is None:
            return Score(value=0.0, passed=False, reasoning="LLM returned empty or unparseable response")

        breakdown: dict[str, float] = {}
        for dim in dimensions:
            name = dim.get("name", "")
            breakdown[name] = float(result.get(name, 0.0))

        total_weight = sum(float(d.get("weight", 1.0)) for d in dimensions)
        if total_weight > 0:
            weighted_sum = sum(breakdown.get(d.get("name", ""), 0.0) * float(d.get("weight", 1.0)) for d in dimensions)
            overall = weighted_sum / total_weight
        else:
            overall = sum(breakdown.values()) / max(len(breakdown), 1)

        reasoning = result.get("reasoning", "")
        passed = overall >= (judge_config.pass_threshold or 0.7)
        return Score(value=overall, passed=passed, reasoning=reasoning, breakdown=breakdown)

    @staticmethod
    def _format_chunks(chunks: list[str], max_chunks: int = 20) -> str:
        """Format context chunks for the RAG judge prompt.

        If the list exceeds *max_chunks*, only the first *max_chunks* are
        included, with a notice about the omitted remainder.
        """
        if not chunks:
            return ""

        if len(chunks) > max_chunks:
            included = chunks[:max_chunks]
            omitted = len(chunks) - max_chunks
            parts = [f"[Chunk {i + 1}] {chunk}" for i, chunk in enumerate(included)]
            parts.append(f"... {omitted} additional chunks omitted ...")
        else:
            parts = [f"[Chunk {i + 1}] {chunk}" for i, chunk in enumerate(chunks)]

        return "\n".join(parts)

    @staticmethod
    def _format_conversation(messages: list[Message], tool_calls: list[ToolCall], max_messages: int = 50) -> str:
        """Format a conversation transcript for the judge prompt.

        If the conversation exceeds *max_messages*, the first 5 and last
        (max_messages - 5) messages are kept, with an omission notice in
        between.
        """
        if len(messages) > max_messages:
            head = messages[:5]
            tail = messages[-(max_messages - 5) :]
            omitted = len(messages) - max_messages
            parts: list[str] = []
            for msg in head:
                parts.append(f"[{msg.role}] {msg.content}")
            parts.append(f"... {omitted} messages omitted ...")
            for msg in tail:
                parts.append(f"[{msg.role}] {msg.content}")
        else:
            parts = [f"[{msg.role}] {msg.content}" for msg in messages]

        if tool_calls:
            parts.append("")
            parts.append("## Tool Calls")
            for tc in tool_calls:
                args_str = json.dumps(tc.arguments) if tc.arguments else ""
                duration = f" ({tc.duration_ms}ms)" if tc.duration_ms is not None else ""
                result = tc.result or ""
                parts.append(f"  > Tool: {tc.tool_name}({args_str}) -> {result}{duration}")

        return "\n".join(parts)

    async def evaluate_conversation(
        self,
        messages: list[Message],
        tool_calls: list[ToolCall],
        judge_config: JudgeConfigParams,
    ) -> Score:
        """Score a multi-turn conversation with tool calls."""
        if not messages:
            return Score(value=0.5, passed=False, reasoning="Empty conversation")

        async with self._semaphore:
            transcript = self._format_conversation(messages, tool_calls)
            prompt = self.CONVERSATION_PROMPT_TEMPLATE.format(transcript=transcript)
            result = await self._ask_judge(prompt, judge_config, "conversation")
            if result is None:
                return Score(value=0.0, passed=False, reasoning="LLM returned empty or unparseable response")

            breakdown = {dim: float(result.get(dim, 0.0)) for dim in self._CONVERSATION_DIMENSIONS}
            overall = sum(breakdown.values()) / len(self._CONVERSATION_DIMENSIONS)
            reasoning = result.get("reasoning", "")
            passed = overall >= (judge_config.pass_threshold or 0.7)

            return Score(value=overall, passed=passed, reasoning=reasoning, breakdown=breakdown)

    async def evaluate_rag(
        self,
        question: str,
        context_chunks: list[str],
        answer: str,
        expected_answer: str | None,
        metrics: list[str],
        judge_config: JudgeConfigParams | None = None,
    ) -> dict[str, Score]:
        """Score a RAG response with retrieved context using RAGAS-style metrics."""
        requested = set(metrics) if metrics else set(self._RAG_DIMENSIONS)
        threshold = (judge_config.pass_threshold if judge_config else None) or 0.7

        if not context_chunks and not answer:
            return {
                dim: Score(value=0.5, passed=False, reasoning="No context chunks or answer provided")
                for dim in self._RAG_DIMENSIONS
                if dim in requested
            }

        async with self._semaphore:
            formatted_chunks = self._format_chunks(context_chunks)
            context_recall_instruction = (
                "Score based on coverage relative to the expected answer."
                if expected_answer
                else "No expected answer provided; score 0.5 (neutral) for this dimension."
            )
            prompt = self.RAG_METRICS_PROMPT_TEMPLATE.format(
                question=question,
                expected_answer=expected_answer or "(not provided)",
                actual_answer=answer,
                formatted_chunks=formatted_chunks or "(no chunks retrieved)",
                context_recall_instruction=context_recall_instruction,
            )
            result = await self._ask_judge(prompt, judge_config, "rag")
            if result is None:
                return {
                    dim: Score(value=0.0, passed=False, reasoning="LLM returned empty or unparseable response")
                    for dim in self._RAG_DIMENSIONS
                    if dim in requested
                }

            reasoning = result.get("reasoning", "")
            scores: dict[str, Score] = {}
            for dim in self._RAG_DIMENSIONS:
                if dim not in requested:
                    continue
                if dim == "context_recall" and expected_answer is None:
                    scores[dim] = Score(
                        value=0.5,
                        passed=False,
                        reasoning="No expected answer provided; context_recall set to neutral",
                    )
                    continue
                score_value = float(result.get(dim, 0.0))
                scores[dim] = Score(
                    value=score_value,
                    passed=score_value >= threshold,
                    reasoning=reasoning,
                )
            return scores
