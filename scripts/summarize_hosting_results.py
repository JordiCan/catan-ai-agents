#!/usr/bin/env python3
import csv
import re
from collections import defaultdict
from pathlib import Path
from statistics import mean


ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"
ANALYSIS = RESULTS / "analysis"

PROMPTS = ["strict_json", "direct_short", "guided_compact"]


def parse_models_from_run_script(path: Path):
    text = path.read_text(encoding="utf-8")
    match = re.search(r"for MODEL in (.*?); do", text)
    if match:
        return [part.strip() for part in match.group(1).split()]

    match = re.search(r"MODELS=\((.*?)\)", text, re.S)
    if match:
        return [part.strip().strip('"') for part in match.group(1).split()]

    return []


def safe_model_name(model_name: str):
    return model_name.replace("/", "_").replace(":", "_")


def csv_row(path: Path):
    with path.open(encoding="utf-8") as handle:
        return next(csv.DictReader(handle))


def result_prefixes():
    return {
        "poligpt": ("poligpt", parse_models_from_run_script(ROOT / "run.sh")),
        "ollama": ("ollama", parse_models_from_run_script(ROOT / "run_ollama.sh")),
        "bedrock": ("bedrock", parse_models_from_run_script(ROOT / "run_bedrock.sh")),
    }


def candidate_dirs(provider: str):
    paths = [RESULTS / provider]
    if provider == "ollama":
        # Some latest Ollama runs may still live in results/ root before consolidation.
        paths.append(RESULTS)
    return paths


def locate_file(provider: str, stem: str, suffix: str):
    for directory in candidate_dirs(provider):
        path = directory / f"{stem}{suffix}"
        if path.exists():
            return path
    return None


def collect_rows():
    rows = []
    for provider, (label, models) in result_prefixes().items():
        for model in models:
            safe_model = safe_model_name(model)
            stem_base = f"{label}_{safe_model}_"
            for prompt in PROMPTS:
                stem = f"{stem_base}{prompt}"
                standard_csv = locate_file(provider, stem, "_standard.csv")
                metrics_csv = locate_file(provider, stem, "_metrics.csv")
                if not standard_csv or not metrics_csv:
                    rows.append(
                        {
                            "provider": provider,
                            "model": model,
                            "prompt": prompt,
                            "available": 0,
                            "source_dir": "",
                        }
                    )
                    continue

                standard = csv_row(standard_csv)
                metrics = csv_row(metrics_csv)
                rows.append(
                    {
                        "provider": provider,
                        "model": model,
                        "prompt": prompt,
                        "available": 1,
                        "source_dir": str(standard_csv.parent.relative_to(ROOT)),
                        "wins": int(standard["Victorias"]),
                        "games": int(standard["Partidas"]),
                        "win_rate": float(standard["Ratio Victorias"]),
                        "total_points": int(standard["Puntos"]),
                        "avg_points": float(standard["Media Puntos"]),
                        "avg_rank": float(standard["Puesto Medio"]),
                        "log_rows": int(float(metrics["log_rows"])),
                        "game_start_samples": int(float(metrics["game_start_samples"])),
                        "game_start_success_rate": float(metrics["game_start_success_rate"]),
                        "game_start_latency_ms": float(metrics["game_start_latency_ms"]),
                        "game_start_prompt_tokens": float(metrics["game_start_prompt_tokens"]),
                        "game_start_completion_tokens": float(metrics["game_start_completion_tokens"]),
                        "build_samples": int(float(metrics["build_samples"])),
                        "build_success_rate": float(metrics["build_success_rate"]),
                        "build_latency_ms": float(metrics["build_latency_ms"]),
                        "build_prompt_tokens": float(metrics["build_prompt_tokens"]),
                        "build_completion_tokens": float(metrics["build_completion_tokens"]),
                    }
                )
    return rows


def aggregate_models(rows):
    grouped = defaultdict(list)
    for row in rows:
        if not row.get("available"):
            continue
        grouped[(row["provider"], row["model"])].append(row)

    aggregates = []
    for (provider, model), items in sorted(grouped.items()):
        aggregates.append(
            {
                "provider": provider,
                "model": model,
                "prompts_available": len(items),
                "best_prompt_by_win_rate": max(items, key=lambda row: (row["win_rate"], row["avg_points"]))["prompt"],
                "avg_win_rate": mean(row["win_rate"] for row in items),
                "avg_points": mean(row["avg_points"] for row in items),
                "avg_rank": mean(row["avg_rank"] for row in items),
                "avg_game_start_success_rate": mean(row["game_start_success_rate"] for row in items),
                "avg_build_success_rate": mean(row["build_success_rate"] for row in items),
                "avg_game_start_latency_ms": mean(row["game_start_latency_ms"] for row in items),
                "avg_build_latency_ms": mean(row["build_latency_ms"] for row in items),
                "avg_game_start_prompt_tokens": mean(row["game_start_prompt_tokens"] for row in items),
                "avg_build_prompt_tokens": mean(row["build_prompt_tokens"] for row in items),
                "avg_game_start_completion_tokens": mean(row["game_start_completion_tokens"] for row in items),
                "avg_build_completion_tokens": mean(row["build_completion_tokens"] for row in items),
            }
        )
    return aggregates


def write_csv(path: Path, rows):
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main():
    detailed_rows = collect_rows()
    model_rows = aggregate_models(detailed_rows)
    write_csv(ANALYSIS / "llm_prompt_summary.csv", detailed_rows)
    write_csv(ANALYSIS / "llm_model_summary.csv", model_rows)
    print(f"Wrote {ANALYSIS / 'llm_prompt_summary.csv'}")
    print(f"Wrote {ANALYSIS / 'llm_model_summary.csv'}")


if __name__ == "__main__":
    main()
