import json

import litellm

from app.adapters.base import (
    EvaluationAdapter,
    JudgeConfigParams,
    Message,
    Score,
    ToolCall,
)


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

    def __init__(self, model: str = "gpt-4.1", api_key: str | None = None, max_concurrency: int = 10):
        super().__init__(max_concurrency=max_concurrency)
        self.model = model
        self.api_key = api_key

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
            response = await litellm.acompletion(
                model=judge_config.model or self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=judge_config.temperature if judge_config.temperature is not None else 0.0,
                api_key=self.api_key,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content
            result = json.loads(content)
            score_value = float(result.get("score", 0.0))
            reasoning = result.get("reasoning", "")
            passed = score_value >= (judge_config.pass_threshold or 0.7)
            return Score(value=score_value, passed=passed, reasoning=reasoning)

    async def evaluate_conversation(
        self,
        messages: list[Message],
        tool_calls: list[ToolCall],
        judge_config: JudgeConfigParams,
    ) -> Score:
        """Score a multi-turn conversation (not yet implemented)."""
        raise NotImplementedError("Conversation evaluation not yet implemented in LiteLLM adapter")

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
        return mode in ("qa",)

    async def get_available_metrics(self) -> list[str]:
        """List metrics this adapter can compute."""
        return ["correctness"]
