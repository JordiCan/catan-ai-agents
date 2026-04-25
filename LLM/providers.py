import io
import json
import os
import time
from contextlib import redirect_stderr, redirect_stdout

from LLM.base import LLMProvider, ProviderError
from LLM.config import coalesce_env, normalize_provider_name


class MockProvider(LLMProvider):
    provider_name = "mock"

    def __init__(self, model_name="mock-rule", timeout_seconds=5):
        super().__init__(model_name=model_name, timeout_seconds=timeout_seconds)

    def generate(self, prompt, **kwargs):
        response = kwargs.get("mock_response")
        if response is None:
            response = kwargs.get("fallback_hint", {})
        if isinstance(response, dict):
            return {
                "text": json.dumps(response),
                "latency_ms": 0.0,
                "prompt_tokens": None,
                "completion_tokens": None,
            }
        return {"text": str(response), "latency_ms": 0.0, "prompt_tokens": None, "completion_tokens": None}


class LiteLLMProvider(LLMProvider):
    provider_name = "litellm"

    def __init__(self, provider_name, model_name=None, timeout_seconds=20):
        normalized = normalize_provider_name(provider_name)
        resolved_model = self._resolve_model_name(normalized, model_name)
        super().__init__(model_name=resolved_model, timeout_seconds=timeout_seconds)
        self.provider_name = normalized
        self.api_base = self._resolve_api_base(normalized)
        self.api_key = self._resolve_api_key(normalized)

    def _resolve_model_name(self, provider_name, model_name):
        if model_name:
            return model_name
        if provider_name == "poligpt":
            return "openai/poligpt"
        if provider_name == "ollama":
            return "ollama/llama3.1"
        if provider_name == "bedrock":
            return "bedrock/amazon.nova-micro-v1:0"
        return "mock-rule"

    def _resolve_api_base(self, provider_name):
        if provider_name == "poligpt":
            return coalesce_env("POLIGPT_API_BASE", default="https://api.poligpt.upv.es/")
        if provider_name == "ollama":
            return coalesce_env("OLLAMA_BASE_URL", default="http://localhost:11434")
        return None

    def _resolve_api_key(self, provider_name):
        if provider_name == "poligpt":
            return coalesce_env("POLIGPT_KEY", "POLIGPT_API_KEY")
        if provider_name == "bedrock":
            return coalesce_env("AWS_BEARER_TOKEN_BEDROCK", "BEDROCK_KEY")
        return None

    def generate(self, prompt, **kwargs):
        try:
            from litellm import completion
        except ImportError as exc:
            raise ProviderError("litellm is required for non-mock LLM providers") from exc

        started = time.time()
        completion_kwargs = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": kwargs.get("temperature", 0),
            "timeout": self.timeout_seconds,
        }

        if self.provider_name == "poligpt":
            if not self.api_key:
                raise ProviderError("POLIGPT_KEY is not configured")
            completion_kwargs["api_base"] = self.api_base
            completion_kwargs["api_key"] = self.api_key

        if self.provider_name == "ollama":
            completion_kwargs["api_base"] = self.api_base

        if self.provider_name == "bedrock":
            if self.api_key:
                # Bedrock API keys are exposed through the standard bearer-token env var.
                os.environ.setdefault("AWS_BEARER_TOKEN_BEDROCK", self.api_key)
                completion_kwargs["api_key"] = self.api_key
            region_name = coalesce_env("AWS_DEFAULT_REGION", "AWS_REGION", default="eu-west-1")
            completion_kwargs["aws_region_name"] = region_name

        try:
            output_buffer = io.StringIO()
            with redirect_stdout(output_buffer), redirect_stderr(output_buffer):
                response = completion(**completion_kwargs)
        except Exception as exc:
            raise ProviderError(f"{self.provider_name} request failed: {exc}") from exc

        usage = getattr(response, "usage", None)
        choices = getattr(response, "choices", []) or []
        text = ""
        if choices:
            message = getattr(choices[0], "message", None)
            if message is not None:
                text = getattr(message, "content", "") or ""

        prompt_tokens = getattr(usage, "prompt_tokens", None) if usage is not None else None
        completion_tokens = getattr(usage, "completion_tokens", None) if usage is not None else None

        return {
            "text": text,
            "latency_ms": (time.time() - started) * 1000,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
        }


def build_provider(provider_name, model_name, timeout_seconds=20):
    provider_name = normalize_provider_name(provider_name)
    if provider_name == "mock":
        return MockProvider(model_name=model_name or "mock-rule", timeout_seconds=timeout_seconds)
    if provider_name in {"poligpt", "ollama", "bedrock"}:
        return LiteLLMProvider(provider_name=provider_name, model_name=model_name, timeout_seconds=timeout_seconds)
    raise ProviderError(f"Unsupported provider: {provider_name}")
