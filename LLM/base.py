import json
from dataclasses import dataclass, field


@dataclass
class LLMDecisionRecord:
    provider: str
    model: str
    prompt_name: str
    decision_type: str
    raw_response: str | None = None
    parsed_response: dict | None = None
    latency_ms: float | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    used_fallback: bool = False
    fallback_reason: str | None = None
    metadata: dict = field(default_factory=dict)

    def to_dict(self):
        return {
            "provider": self.provider,
            "model": self.model,
            "prompt_name": self.prompt_name,
            "decision_type": self.decision_type,
            "raw_response": self.raw_response,
            "parsed_response": self.parsed_response,
            "latency_ms": self.latency_ms,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "used_fallback": self.used_fallback,
            "fallback_reason": self.fallback_reason,
            "metadata": self.metadata,
        }


class LLMProvider:
    provider_name = "base"

    def __init__(self, model_name="unknown", timeout_seconds=20):
        self.model_name = model_name
        self.timeout_seconds = timeout_seconds

    def generate(self, prompt, **kwargs):
        raise NotImplementedError


class ProviderError(RuntimeError):
    pass


def safe_json_dumps(data):
    return json.dumps(data, ensure_ascii=True, sort_keys=True)
