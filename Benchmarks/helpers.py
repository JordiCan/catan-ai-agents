import importlib
import os
import sys
from pathlib import Path


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)


POLIGPT_TEXT_MODELS = [
    "poligpt",
    "poligpt2",
    "qwen",
    "phi4",
    "gemma",
    "llama-mini",
]

POLIGPT_REASONING_MODELS = [
    "deepseek-reasoner-mini",
]

OLLAMA_TEXT_MODELS = [
    "llama3.2:3b",
    "gemma3:1b",
    "ministral-3:3b",
]

PROMPT_VARIANTS = ["direct_short", "strict_json", "guided_compact"]


def load_agent_class(path):
    module_name, class_name = path.rsplit(".", 1)
    module = importlib.import_module(module_name)
    return getattr(module, class_name)


def configured_agent_class(agent_class, params):
    if not params:
        return agent_class

    if isinstance(params, dict):
        class ConfiguredAgent(agent_class):
            def __init__(self, agent_id):
                super().__init__(agent_id, **params)
    elif isinstance(params, (list, tuple)):
        class ConfiguredAgent(agent_class):
            def __init__(self, agent_id):
                super().__init__(agent_id, *params)
    else:
        raise TypeError("params debe ser lista/tupla o dict")

    ConfiguredAgent.__name__ = f"{agent_class.__name__}Configured"
    return ConfiguredAgent


def agent_metadata(agent_class, params=None):
    params = params or {}
    return {
        "agent_name": getattr(agent_class, "__name__", str(agent_class)),
        "provider": params.get("provider_name", "heuristic"),
        "model": params.get("model_name", ""),
        "prompt": params.get("prompt_name", ""),
    }


def build_llm_params(provider_name, model_name, prompt_name="strict_json", log_path=None):
    params = {
        "provider_name": provider_name,
        "model_name": model_name,
        "prompt_name": prompt_name,
        "llm_enabled": True,
    }
    if log_path:
        params["log_path"] = log_path
    return params


def provider_model_name(provider_name, model_name):
    if provider_name == "poligpt" and not model_name.startswith("openai/"):
        return f"openai/{model_name}"
    if provider_name == "ollama" and not model_name.startswith("ollama/"):
        return f"ollama/{model_name}"
    return model_name


def make_log_path(provider_name, model_name, prompt_name):
    safe_model = model_name.replace("/", "_").replace(":", "_")
    return str(Path("artifacts") / f"{provider_name}_{safe_model}_{prompt_name}.jsonl")


def llm_targets(provider_name, models, prompts):
    targets = []
    for model_name in models:
        full_model_name = provider_model_name(provider_name, model_name)
        for prompt_name in prompts:
            targets.append(
                (
                    "Agents.HybridLLMAgent.HybridLLMAgent",
                    build_llm_params(
                        provider_name,
                        full_model_name,
                        prompt_name,
                        make_log_path(provider_name, model_name, prompt_name),
                    ),
                )
            )
    return targets


def benchmark_targets_from_env():
    target = os.getenv("BENCHMARK_TARGET", "heuristic").strip().lower()
    prompt_name = os.getenv("CATAN_LLM_PROMPT", "strict_json")
    log_path = os.getenv("CATAN_LLM_LOG_PATH")
    poligpt_models = [model.strip() for model in os.getenv("BENCHMARK_POLIGPT_MODELS", "poligpt").split(",") if model.strip()]
    recommended_poligpt_models = [model.strip() for model in os.getenv("BENCHMARK_POLIGPT_RECOMMENDED", ",".join(POLIGPT_TEXT_MODELS)).split(",") if model.strip()]
    reasoning_poligpt_models = [model.strip() for model in os.getenv("BENCHMARK_POLIGPT_REASONING", ",".join(POLIGPT_REASONING_MODELS)).split(",") if model.strip()]
    ollama_models = [model.strip() for model in os.getenv("BENCHMARK_OLLAMA_MODELS", os.getenv("CATAN_LLM_MODEL", OLLAMA_TEXT_MODELS[0])).split(",") if model.strip()]
    recommended_ollama_models = [model.strip() for model in os.getenv("BENCHMARK_OLLAMA_RECOMMENDED", ",".join(OLLAMA_TEXT_MODELS)).split(",") if model.strip()]
    prompt_variants = [prompt.strip() for prompt in os.getenv("BENCHMARK_PROMPTS", prompt_name).split(",") if prompt.strip()]

    targets = {
        "heuristic": [("Agents.HeuristicAgent.HeuristicAgent", None)],
        "mock": [("Agents.HybridLLMAgent.HybridLLMAgent", build_llm_params("mock", "mock-rule", prompt_name, log_path))],
        "poligpt": [("Agents.HybridLLMAgent.HybridLLMAgent", build_llm_params("poligpt", provider_model_name("poligpt", poligpt_models[0]), prompt_name, log_path or make_log_path("poligpt", poligpt_models[0], prompt_name)))],
        "poligpt-sweep": llm_targets("poligpt", poligpt_models, prompt_variants),
        "poligpt-recommended": llm_targets("poligpt", recommended_poligpt_models, prompt_variants),
        "poligpt-reasoning": llm_targets("poligpt", reasoning_poligpt_models, prompt_variants),
        "ollama": [("Agents.HybridLLMAgent.HybridLLMAgent", build_llm_params("ollama", provider_model_name("ollama", ollama_models[0]), prompt_name, log_path or make_log_path("ollama", ollama_models[0], prompt_name)))],
        "ollama-sweep": llm_targets("ollama", ollama_models, prompt_variants),
        "ollama-recommended": llm_targets("ollama", recommended_ollama_models, prompt_variants),
        "bedrock": [("Agents.HybridLLMAgent.HybridLLMAgent", build_llm_params("bedrock", os.getenv("CATAN_LLM_MODEL", "bedrock/anthropic.claude-3-haiku-20240307-v1:0"), prompt_name, log_path))],
        "baseline": [("Agents.AdrianHerasAgent.AdrianHerasAgent", None)],
        "all": [
            ("Agents.HeuristicAgent.HeuristicAgent", None),
            ("Agents.HybridLLMAgent.HybridLLMAgent", build_llm_params("mock", "mock-rule", prompt_name, log_path)),
            ("Agents.HybridLLMAgent.HybridLLMAgent", build_llm_params("poligpt", "openai/poligpt", prompt_name, log_path)),
            ("Agents.HybridLLMAgent.HybridLLMAgent", build_llm_params("ollama", os.getenv("CATAN_LLM_MODEL_OLLAMA", "ollama/llama3.1"), prompt_name, log_path)),
            ("Agents.HybridLLMAgent.HybridLLMAgent", build_llm_params("bedrock", os.getenv("CATAN_LLM_MODEL_BEDROCK", "bedrock/anthropic.claude-3-haiku-20240307-v1:0"), prompt_name, log_path)),
        ],
    }

    return targets.get(target, targets["heuristic"])
