import csv
import json
import os
import random
import sys
from pathlib import Path

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from Agents.RandomAgent import RandomAgent
from Benchmarks.helpers import (
    OLLAMA_TEXT_MODELS,
    POLIGPT_TEXT_MODELS,
    PROMPT_VARIANTS,
    agent_metadata,
    configured_agent_class,
    load_agent_class,
    llm_targets,
)
from LLM.config import load_env
from Managers.GameDirector import GameDirector


def summarize_match(game_trace, player_index):
    last_round = max(game_trace["game"].keys(), key=lambda round_name: int(round_name.split("_")[-1]))
    last_turn = max(
        game_trace["game"][last_round].keys(),
        key=lambda turn_name: int(turn_name.split("_")[-1].lstrip("P")),
    )
    victory_points = game_trace["game"][last_round][last_turn]["end_turn"]["victory_points"]
    agent_id = f"J{player_index}"
    winner = max(victory_points, key=lambda player: int(victory_points[player]))
    rank = 1 + sum(int(score) > int(victory_points[agent_id]) for score in victory_points.values())
    return {
        "victory": 1 if winner == agent_id else 0,
        "points": int(victory_points[agent_id]),
        "rank": rank,
    }


def evaluate_against_random(agent_path, params, matches, max_rounds, seed_base):
    agent_class = load_agent_class(agent_path)
    configured = configured_agent_class(agent_class, params)
    metadata = agent_metadata(agent_class, params)
    rows = []

    for position in range(4):
        for match_index in range(matches):
            random.seed(seed_base + position * 1000 + match_index)
            agents = [RandomAgent, RandomAgent, RandomAgent]
            agents.insert(position, configured)
            director = GameDirector(agents=agents, max_rounds=max_rounds, store_trace=False)
            trace = director.game_start(print_outcome=False)
            result = summarize_match(trace, position)
            result.update(metadata)
            result["position"] = position
            result["seed"] = seed_base + position * 1000 + match_index
            rows.append(result)

    return rows


def summarize_rows(rows):
    games = len(rows)
    wins = sum(row["victory"] for row in rows)
    points = sum(row["points"] for row in rows) / games if games else 0
    rank = sum(row["rank"] for row in rows) / games if games else 0
    first = rows[0] if rows else {}
    return {
        "provider": first.get("provider", ""),
        "model": first.get("model", ""),
        "prompt": first.get("prompt", ""),
        "games": games,
        "win_rate": wins / games if games else 0,
        "avg_points": points,
        "avg_rank": rank,
    }


def write_outputs(rows, output_prefix):
    output_prefix = Path(output_prefix)
    output_prefix.parent.mkdir(parents=True, exist_ok=True)
    detailed_path = output_prefix.with_suffix(".json")
    summary_path = output_prefix.with_name(output_prefix.name + "_summary.csv")

    detailed_path.write_text(json.dumps(rows, indent=2, ensure_ascii=True), encoding="utf-8")

    by_key = {}
    for row in rows:
        key = (row["provider"], row["model"], row["prompt"])
        by_key.setdefault(key, []).append(row)

    summaries = [summarize_rows(group) for group in by_key.values()]
    with summary_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["provider", "model", "prompt", "games", "win_rate", "avg_points", "avg_rank"])
        writer.writeheader()
        writer.writerows(summaries)

    return detailed_path, summary_path


def main():
    load_env()
    provider = os.getenv("MATRIX_PROVIDER", "poligpt").strip().lower()
    matches = int(os.getenv("MATRIX_MATCHES", "3"))
    max_rounds = int(os.getenv("MATRIX_MAX_ROUNDS", "150"))
    seed_base = int(os.getenv("MATRIX_SEED", "2026"))
    output_prefix = os.getenv("MATRIX_OUTPUT", "artifacts/llm_matrix")

    if provider == "poligpt":
        models = [model.strip() for model in os.getenv("MATRIX_MODELS", ",".join(POLIGPT_TEXT_MODELS)).split(",") if model.strip()]
    elif provider == "ollama":
        models = [model.strip() for model in os.getenv("MATRIX_MODELS", ",".join(OLLAMA_TEXT_MODELS)).split(",") if model.strip()]
    else:
        raise ValueError("MATRIX_PROVIDER must be poligpt or ollama")

    prompts = [prompt.strip() for prompt in os.getenv("MATRIX_PROMPTS", ",".join(PROMPT_VARIANTS)).split(",") if prompt.strip()]
    targets = llm_targets(provider, models, prompts)

    all_rows = []
    for agent_path, params in targets:
        rows = evaluate_against_random(agent_path, params, matches, max_rounds, seed_base)
        all_rows.extend(rows)

    detailed_path, summary_path = write_outputs(all_rows, output_prefix)
    print(f"Detailed results: {detailed_path}")
    print(f"Summary results: {summary_path}")


if __name__ == "__main__":
    main()
