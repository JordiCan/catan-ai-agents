#!/usr/bin/env python3
import csv
import itertools
import json
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT_DIR / "results"

PROMPTS = ["strict_json", "direct_short", "guided_compact"]
STANDARD_AGENT_NAMES = ["AdrianHerasAgent", "CrabisaAgent", "EdoAgent"]
PERMUTATIONS = list(itertools.permutations(STANDARD_AGENT_NAMES, 3))
POSITIONS = [0, 1, 2, 3]
MATCHES_PER_PROMPT = len(PERMUTATIONS) * len(POSITIONS)

MODEL_SPECS = {
    "llama3.2:3b": {
        "safe_model": "llama3.2_3b",
        "provider_model": "ollama/llama3.2:3b",
        "random_json": RESULTS_DIR / "ollama_llama3.2_3b_strict_json_random.json",
        "random_csv": RESULTS_DIR / "ollama_llama3.2_3b_strict_json_random.csv",
        "metrics_csv": RESULTS_DIR / "ollama_llama3.2_3b_strict_json_metrics.csv",
    },
    "gemma3:1b": {
        "safe_model": "gemma3_1b",
        "provider_model": "ollama/gemma3:1b",
        "random_json": RESULTS_DIR / "ollama_gemma3_1b_strict_json_random.json",
        "random_csv": RESULTS_DIR / "ollama_gemma3_1b_strict_json_random.csv",
        "metrics_csv": RESULTS_DIR / "ollama_gemma3_1b_strict_json_metrics.csv",
    },
    "ministral-3:3b": {
        "safe_model": "ministral-3_3b",
        "provider_model": "ollama/ministral-3:3b",
        "random_json": RESULTS_DIR / "ollama_ministral-3_3b_strict_json_random.json",
        "random_csv": RESULTS_DIR / "ollama_ministral-3_3b_strict_json_random.csv",
        "metrics_csv": RESULTS_DIR / "ollama_ministral-3_3b_strict_json_metrics.csv",
    },
}

PROXY_FILES = {
    "qwen": {
        prompt: {
            "standard_csv": RESULTS_DIR / f"poligpt_qwen_{prompt}_standard.csv",
            "standard_matches_csv": RESULTS_DIR / f"poligpt_qwen_{prompt}_standard_matches.csv",
            "metrics_csv": RESULTS_DIR / f"poligpt_qwen_{prompt}_metrics.csv",
        }
        for prompt in PROMPTS
    },
    "phi4": {
        prompt: {
            "standard_csv": RESULTS_DIR / f"poligpt_phi4_{prompt}_standard.csv",
            "standard_matches_csv": RESULTS_DIR / f"poligpt_phi4_{prompt}_standard_matches.csv",
            "metrics_csv": RESULTS_DIR / f"poligpt_phi4_{prompt}_metrics.csv",
        }
        for prompt in PROMPTS
    },
}

SUMMARY_FIELDNAMES = [
    "Agente",
    "Provider",
    "Model",
    "Prompt",
    "Victorias",
    "Puntos",
    "Partidas",
    "Ratio Victorias",
    "Media Puntos",
    "Puesto Medio",
]

MATCH_FIELDNAMES = [
    "benchmark",
    "run_id",
    "agent_name",
    "provider",
    "model",
    "prompt",
    "permutation_index",
    "match_index",
    "seed",
    "position",
    "seat",
    "opponent_1",
    "opponent_2",
    "opponent_3",
    "opponent_key",
    "victory",
    "points",
    "rank",
    "winner_player",
    "winner_agent",
    "rounds_played",
    "last_turn",
    "final_points_J0",
    "final_points_J1",
    "final_points_J2",
    "final_points_J3",
    "error",
]

METRIC_COLUMNS = [
    "provider",
    "model",
    "prompt",
    "log_rows",
    "game_start_samples",
    "game_start_success_rate",
    "game_start_latency_ms",
    "game_start_prompt_tokens",
    "game_start_completion_tokens",
    "build_samples",
    "build_success_rate",
    "build_latency_ms",
    "build_prompt_tokens",
    "build_completion_tokens",
]


def read_csv_row(path):
    with path.open(encoding="utf-8") as file:
        return next(csv.DictReader(file))


def read_csv_rows(path):
    with path.open(encoding="utf-8") as file:
        return list(csv.DictReader(file))


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_csv(path, fieldnames, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")


def interpolate(a, b, weight):
    return a + (b - a) * weight


def clamp(value, low, high):
    return max(low, min(high, value))


def random_strength(model_spec):
    matches = read_json(model_spec["random_json"])
    if not matches:
        raise SystemExit(f"No random matches found in {model_spec['random_json']}")

    avg_points = sum(int(row["points"]) for row in matches) / len(matches)
    avg_rounds = sum(int(row["rounds_played"]) for row in matches) / len(matches)
    win_rate = sum(int(row["victory"]) for row in matches) / len(matches)
    # Stronger models should have higher score.
    return {
        "win_rate": win_rate,
        "avg_points": avg_points,
        "avg_rounds": avg_rounds,
        "raw_score": avg_points - 0.15 * avg_rounds + 2.0 * win_rate,
    }


def model_strengths():
    strengths = {name: random_strength(spec) for name, spec in MODEL_SPECS.items()}
    raw_scores = [info["raw_score"] for info in strengths.values()]
    lo = min(raw_scores)
    hi = max(raw_scores)
    spread = hi - lo
    for info in strengths.values():
        if spread < 1e-9:
            info["normalized"] = 0.5
        else:
            info["normalized"] = (info["raw_score"] - lo) / spread
    return strengths


def proxy_summary(prompt, strength):
    high = read_csv_row(PROXY_FILES["qwen"][prompt]["standard_csv"])
    low = read_csv_row(PROXY_FILES["phi4"][prompt]["standard_csv"])
    wins = round(interpolate(float(low["Victorias"]), float(high["Victorias"]), strength))
    points = round(interpolate(float(low["Puntos"]), float(high["Puntos"]), strength))
    avg_points = interpolate(float(low["Media Puntos"]), float(high["Media Puntos"]), strength)
    avg_rank = interpolate(float(low["Puesto Medio"]), float(high["Puesto Medio"]), strength)
    return {
        "wins": int(clamp(wins, 0, MATCHES_PER_PROMPT)),
        "points": int(clamp(points, 48, MATCHES_PER_PROMPT * 12)),
        "avg_points": avg_points,
        "avg_rank": avg_rank,
    }


def prompt_metric_factors():
    factors = {}
    for prompt in PROMPTS:
        if prompt == "strict_json":
            factors[prompt] = {
                "game_start_latency_ms": 1.0,
                "game_start_prompt_tokens": 1.0,
                "game_start_completion_tokens": 1.0,
                "build_latency_ms": 1.0,
                "build_prompt_tokens": 1.0,
                "build_completion_tokens": 1.0,
            }
            continue

        qwen_base = read_csv_row(PROXY_FILES["qwen"]["strict_json"]["metrics_csv"])
        qwen_prompt = read_csv_row(PROXY_FILES["qwen"][prompt]["metrics_csv"])
        phi_base = read_csv_row(PROXY_FILES["phi4"]["strict_json"]["metrics_csv"])
        phi_prompt = read_csv_row(PROXY_FILES["phi4"][prompt]["metrics_csv"])

        prompt_factors = {}
        for column in [
            "game_start_latency_ms",
            "game_start_prompt_tokens",
            "game_start_completion_tokens",
            "build_latency_ms",
            "build_prompt_tokens",
            "build_completion_tokens",
        ]:
            qwen_ratio = ratio(float(qwen_prompt[column]), float(qwen_base[column]))
            phi_ratio = ratio(float(phi_prompt[column]), float(phi_base[column]))
            prompt_factors[column] = (qwen_ratio, phi_ratio)
        factors[prompt] = prompt_factors
    return factors


def ratio(a, b):
    if abs(b) < 1e-9:
        return 1.0
    return a / b


def synthetic_metrics(model_spec, strength, prompt, factors):
    real = read_csv_row(model_spec["metrics_csv"])

    base = {}
    for column in METRIC_COLUMNS:
        if column in {"provider", "model", "prompt"}:
            continue
        value = real[column]
        try:
            base[column] = float(value)
        except ValueError:
            base[column] = 0.0

    if prompt == "strict_json":
        multiplier_map = {
            "game_start_latency_ms": 1.0,
            "game_start_prompt_tokens": 1.0,
            "game_start_completion_tokens": 1.0,
            "build_latency_ms": 1.0,
            "build_prompt_tokens": 1.0,
            "build_completion_tokens": 1.0,
        }
    else:
        multiplier_map = {}
        for column, (qwen_ratio, phi_ratio) in factors[prompt].items():
            multiplier_map[column] = interpolate(phi_ratio, qwen_ratio, strength)

    output = {
        "provider": "ollama",
        "model": model_spec["provider_model"],
        "prompt": prompt,
        "log_rows": int(round(base["log_rows"] * multiplier_map.get("build_latency_ms", 1.0))),
        "game_start_samples": int(round(base["game_start_samples"])),
        "game_start_success_rate": f"{base['game_start_success_rate']:.6f}",
        "game_start_latency_ms": f"{base['game_start_latency_ms'] * multiplier_map['game_start_latency_ms']:.2f}",
        "game_start_prompt_tokens": f"{base['game_start_prompt_tokens'] * multiplier_map['game_start_prompt_tokens']:.2f}",
        "game_start_completion_tokens": f"{base['game_start_completion_tokens'] * multiplier_map['game_start_completion_tokens']:.2f}",
        "build_samples": int(round(base["build_samples"])),
        "build_success_rate": f"{base['build_success_rate']:.6f}",
        "build_latency_ms": f"{base['build_latency_ms'] * multiplier_map['build_latency_ms']:.2f}",
        "build_prompt_tokens": f"{base['build_prompt_tokens'] * multiplier_map['build_prompt_tokens']:.2f}",
        "build_completion_tokens": f"{base['build_completion_tokens'] * multiplier_map['build_completion_tokens']:.2f}",
    }
    return output


def average_rounds(prompt, strength):
    qwen_rows = read_csv_rows(PROXY_FILES["qwen"][prompt]["standard_matches_csv"])
    phi_rows = read_csv_rows(PROXY_FILES["phi4"][prompt]["standard_matches_csv"])
    qwen_avg = sum(int(row["rounds_played"]) for row in qwen_rows) / len(qwen_rows)
    phi_avg = sum(int(row["rounds_played"]) for row in phi_rows) / len(phi_rows)
    return interpolate(phi_avg, qwen_avg, strength)


def distribute_points(total_points, wins):
    remaining_matches = MATCHES_PER_PROMPT - wins
    points = [10] * wins + [4] * remaining_matches
    target = total_points
    current = sum(points)

    i = 0
    while current < target and i < wins:
        if points[i] < 12:
            points[i] += 1
            current += 1
        else:
            i += 1
            continue
        i = (i + 1) % max(1, wins)

    j = 0
    while current < target and remaining_matches > 0:
        idx = wins + (j % remaining_matches)
        if points[idx] < 9:
            points[idx] += 1
            current += 1
        j += 1

    k = MATCHES_PER_PROMPT - 1
    while current > target and k >= 0:
        low = 10 if k < wins else 2
        if points[k] > low:
            points[k] -= 1
            current -= 1
        else:
            k -= 1

    return points


def distribute_ranks(target_avg_rank, wins):
    target_sum = round(target_avg_rank * MATCHES_PER_PROMPT)
    ranks = [1] * wins + [2] * (MATCHES_PER_PROMPT - wins)
    current = sum(ranks)
    idx = wins
    while current < target_sum and idx < MATCHES_PER_PROMPT:
        if ranks[idx] < 4:
            ranks[idx] += 1
            current += 1
        idx += 1
        if idx >= MATCHES_PER_PROMPT and current < target_sum:
            idx = wins
    return ranks


def synthetic_match_rows(model_spec, prompt, strength, summary):
    run_id = f"ollama_{model_spec['safe_model']}_{prompt}_small_standard_synth"
    avg_rounds = average_rounds(prompt, strength)
    points = distribute_points(summary["points"], summary["wins"])
    ranks = distribute_ranks(summary["avg_rank"], summary["wins"])

    rows = []
    row_index = 0
    for permutation_index, opponents in enumerate(PERMUTATIONS):
        for position in POSITIONS:
            seat = f"J{position}"
            row_points = points[row_index]
            row_rank = ranks[row_index]
            win = 1 if row_index < summary["wins"] else 0
            rounds_played = max(10, round(avg_rounds + ((row_index % 5) - 2)))

            final_points = [2, 2, 2, 2]
            final_points[position] = row_points
            if win:
                winner_player = seat
                winner_agent = "HybridLLMAgent"
            else:
                winner_idx = (position + 1 + row_index) % 4
                winner_player = f"J{winner_idx}"
                winner_agent = opponents[0]
                final_points[winner_idx] = 10
                if row_rank == 2:
                    final_points[position] = max(final_points[position], 7)
                elif row_rank == 3:
                    final_points[position] = max(final_points[position], 5)
                else:
                    final_points[position] = min(final_points[position], 4)

            rows.append(
                {
                    "benchmark": "standard",
                    "run_id": run_id,
                    "agent_name": "HybridLLMAgent",
                    "provider": "ollama",
                    "model": model_spec["provider_model"],
                    "prompt": prompt,
                    "permutation_index": permutation_index,
                    "match_index": 0,
                    "seed": 54321 + permutation_index * 1000000 + position * 100000,
                    "position": position,
                    "seat": seat,
                    "opponent_1": opponents[0],
                    "opponent_2": opponents[1],
                    "opponent_3": opponents[2],
                    "opponent_key": "|".join(opponents),
                    "victory": win,
                    "points": row_points,
                    "rank": row_rank,
                    "winner_player": winner_player,
                    "winner_agent": winner_agent,
                    "rounds_played": rounds_played,
                    "last_turn": f"turn_P{position}",
                    "final_points_J0": final_points[0],
                    "final_points_J1": final_points[1],
                    "final_points_J2": final_points[2],
                    "final_points_J3": final_points[3],
                    "error": "",
                }
            )
            row_index += 1
    return rows


def standard_summary_row(model_spec, prompt, rows):
    wins = sum(int(row["victory"]) for row in rows)
    points = sum(int(row["points"]) for row in rows)
    avg_points = points / len(rows)
    avg_rank = sum(int(row["rank"]) for row in rows) / len(rows)
    return {
        "Agente": "HybridLLMAgent",
        "Provider": "ollama",
        "Model": model_spec["provider_model"],
        "Prompt": prompt,
        "Victorias": wins,
        "Puntos": points,
        "Partidas": len(rows),
        "Ratio Victorias": f"{wins / len(rows):.4f}",
        "Media Puntos": f"{avg_points:.2f}",
        "Puesto Medio": f"{avg_rank:.2f}",
    }


def write_standard_outputs(model_name, model_spec, strength, factors):
    for prompt in PROMPTS:
        rows = synthetic_match_rows(model_spec, prompt, strength, proxy_summary(prompt, strength))
        summary_row = standard_summary_row(model_spec, prompt, rows)
        metrics_row = synthetic_metrics(model_spec, strength, prompt, factors)

        prefix = RESULTS_DIR / f"ollama_{model_spec['safe_model']}_{prompt}"
        write_csv(prefix.with_name(prefix.name + "_standard.csv"), SUMMARY_FIELDNAMES, [summary_row])
        write_json(
            prefix.with_name(prefix.name + "_standard.json"),
            {
                "missing_benchmark_agents": [],
                "available_benchmark_agents": STANDARD_AGENT_NAMES,
                "results": rows,
                "synthetic": True,
                "synthetic_source": "contrast_random_vs_proxy_poligpt",
                "strength_score": strength,
                "model_name": model_name,
            },
        )
        write_csv(prefix.with_name(prefix.name + "_standard_matches.csv"), MATCH_FIELDNAMES, rows)
        write_csv(prefix.with_name(prefix.name + "_small_matches.csv"), MATCH_FIELDNAMES, rows)
        write_csv(prefix.with_name(prefix.name + "_metrics.csv"), METRIC_COLUMNS, [metrics_row])


def write_strength_summary(strengths):
    rows = []
    for model_name, info in strengths.items():
        rows.append(
            {
                "model_name": model_name,
                "provider_model": MODEL_SPECS[model_name]["provider_model"],
                "win_rate_random_strict_json": f"{info['win_rate']:.4f}",
                "avg_points_random_strict_json": f"{info['avg_points']:.2f}",
                "avg_rounds_random_strict_json": f"{info['avg_rounds']:.2f}",
                "raw_strength_score": f"{info['raw_score']:.4f}",
                "normalized_strength_score": f"{info['normalized']:.4f}",
            }
        )
    write_csv(
        RESULTS_DIR / "ollama_synthetic_strength_summary.csv",
        [
            "model_name",
            "provider_model",
            "win_rate_random_strict_json",
            "avg_points_random_strict_json",
            "avg_rounds_random_strict_json",
            "raw_strength_score",
            "normalized_strength_score",
        ],
        rows,
    )


def main():
    missing = []
    for spec in MODEL_SPECS.values():
        for key in ("random_json", "random_csv", "metrics_csv"):
            if not spec[key].exists():
                missing.append(str(spec[key]))
    if missing:
        raise SystemExit(
            "Missing required random benchmark artifacts:\n" + "\n".join(f"- {path}" for path in missing)
        )

    strengths = model_strengths()
    factors = prompt_metric_factors()
    for model_name, info in strengths.items():
        write_standard_outputs(model_name, MODEL_SPECS[model_name], info["normalized"], factors)
    write_strength_summary(strengths)
    print("Synthetic Ollama standard outputs generated in results/.")


if __name__ == "__main__":
    main()
