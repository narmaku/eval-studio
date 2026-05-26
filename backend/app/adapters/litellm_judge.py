import json
import logging

import litellm

from app.adapters.base import (
    EvaluationAdapter,
    JudgeConfigParams,
    Message,
    Score,
    ToolCall,
)

logger = logging.getLogger(__name__)


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

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        api_base: str | None = None,
        max_concurrency: int = 10,
    ):
        super().__init__(max_concurrency=max_concurrency)
        self.model = model
        self.api_key = api_key
        self.api_base = api_base

    async def evaluate_qa(
        self,
        question: str,
        expected_answer: str,
        actual_answer: str,
        judge_config: JudgeConfigParams,
    ) -> Score:
        """Score a single Q&A pair using an LLM judge."""
        async with self._semaphore:
            prompt_template = judge_config.prompt_template or self.DEFAULT_PROMPT_TEMPLATE
            prompt = prompt_template.format(
                question=question,
                expected_answer=expected_answer,
                actual_answer=actual_answer,
            )
            kwargs: dict = {
                "model": judge_config.model or self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": judge_config.temperature if judge_config.temperature is not None else 0.0,
                "response_format": {"type": "json_object"},
            }
            if self.api_key:
                kwargs["api_key"] = self.api_key
            if self.api_base:
                kwargs["api_base"] = self.api_base
            response = await litellm.acompletion(**kwargs)
            content = response.choices[0].message.content
            if content is None:
                logger.warning("LLM returned empty content for Q&A evaluation")
                return Score(value=0.0, passed=False, reasoning="LLM returned empty response")
            try:
                result = json.loads(content)
            except (json.JSONDecodeError, TypeError) as exc:
                logger.error("Failed to parse LLM judge response: %s", exc, extra={"raw_content": content})
                return Score(value=0.0, passed=False, reasoning=f"Failed to parse judge response: {exc}")
            score_value = float(result.get("score", 0.0))
            reasoning = result.get("reasoning", "")
            passed = score_value >= (judge_config.pass_threshold or 0.7)
            return Score(value=score_value, passed=passed, reasoning=reasoning)

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

            kwargs: dict = {
                "model": judge_config.model or self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": judge_config.temperature if judge_config.temperature is not None else 0.0,
                "response_format": {"type": "json_object"},
            }
            if self.api_key:
                kwargs["api_key"] = self.api_key
            if self.api_base:
                kwargs["api_base"] = self.api_base

            response = await litellm.acompletion(**kwargs)
            content = response.choices[0].message.content

            if content is None:
                logger.warning("LLM returned empty content for conversation evaluation")
                return Score(value=0.0, passed=False, reasoning="LLM returned empty response")

            try:
                result = json.loads(content)
            except (json.JSONDecodeError, TypeError) as exc:
                logger.error("Failed to parse LLM judge response: %s", exc, extra={"raw_content": content})
                return Score(value=0.0, passed=False, reasoning=f"Failed to parse judge response: {exc}")

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
    ) -> dict[str, Score]:
        """Score a RAG response (not yet implemented)."""
        raise NotImplementedError("RAG evaluation not yet implemented in LiteLLM adapter")

    def supports_mode(self, mode: str) -> bool:
        """Check if this adapter supports a given evaluation mode."""
        return mode in ("qa", "agent")

    async def get_available_metrics(self) -> list[str]:
        """List metrics this adapter can compute."""
        return ["correctness", "relevance", "tool_use_accuracy", "resolution", "response_quality"]
