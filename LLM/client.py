import os

from LLM.base import LLMDecisionRecord, ProviderError
from LLM.config import load_env, normalize_provider_name
from LLM.logger import ExperimentLogger
from LLM.parser import parse_json_response, validate_build_response, validate_start_response
from LLM.prompts import PromptBuilder
from LLM.providers import build_provider


class CatanLLMClient:
    def __init__(self, provider_name=None, model_name=None, prompt_name=None, timeout_seconds=20, logger=None):
        load_env()
        self.provider_name = normalize_provider_name(provider_name or os.getenv("CATAN_LLM_PROVIDER", "mock"))
        self.model_name = model_name or os.getenv("CATAN_LLM_MODEL", "mock-rule")
        self.prompt_name = prompt_name or os.getenv("CATAN_LLM_PROMPT", "strict_json")
        self.provider = build_provider(self.provider_name, self.model_name, timeout_seconds=timeout_seconds)
        self.prompt_builder = PromptBuilder(self.prompt_name)
        self.logger = logger or ExperimentLogger(os.getenv("CATAN_LLM_LOG_PATH"))

    def decide(self, decision_type, game_state, candidate_actions, fallback_hint=None):
        prompt = self.prompt_builder.build(decision_type, game_state, candidate_actions)
        record = LLMDecisionRecord(
            provider=self.provider.provider_name,
            model=self.provider.model_name,
            prompt_name=self.prompt_name,
            decision_type=decision_type,
            metadata={"candidate_actions": candidate_actions},
        )

        try:
            response = self.provider.generate(prompt, fallback_hint=fallback_hint)
            record.raw_response = response.get("text")
            record.latency_ms = response.get("latency_ms")
            record.prompt_tokens = response.get("prompt_tokens")
            record.completion_tokens = response.get("completion_tokens")
            parsed = parse_json_response(record.raw_response)

            if decision_type == "on_game_start":
                record.parsed_response = validate_start_response(parsed)
            elif decision_type == "on_build_phase":
                record.parsed_response = validate_build_response(parsed)
            else:
                record.parsed_response = parsed
        except (ProviderError, ValueError, KeyError) as exc:
            record.used_fallback = True
            record.fallback_reason = str(exc)

        self.logger.log(record.to_dict())
        return record
