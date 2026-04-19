import csv
import json
import sys
from pathlib import Path
from statistics import mean


def summarize(rows, decision_type):
    subset = [row for row in rows if row.get("decision_type") == decision_type]
    success = [row for row in subset if not row.get("used_fallback")]
    latencies = [row.get("latency_ms") for row in success if row.get("latency_ms") is not None]
    prompt_tokens = [row.get("prompt_tokens") for row in success if row.get("prompt_tokens") is not None]
    completion_tokens = [row.get("completion_tokens") for row in success if row.get("completion_tokens") is not None]
    return {
        "samples": len(subset),
        "success_rate": (len(success) / len(subset)) if subset else 0.0,
        "latency_ms": mean(latencies) if latencies else 0.0,
        "prompt_tokens": mean(prompt_tokens) if prompt_tokens else 0.0,
        "completion_tokens": mean(completion_tokens) if completion_tokens else 0.0,
    }


def main():
    if len(sys.argv) != 3:
        raise SystemExit("Usage: python scripts/summarize_llm_log.py <input_jsonl> <output_csv>")

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])

    rows = [json.loads(line) for line in input_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not rows:
        raise SystemExit(f"No rows found in {input_path}")

    first = rows[0]
    game_start = summarize(rows, "on_game_start")
    build_phase = summarize(rows, "on_build_phase")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
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
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "provider": first.get("provider", ""),
                "model": first.get("model", ""),
                "prompt": first.get("prompt_name", ""),
                "log_rows": len(rows),
                "game_start_samples": game_start["samples"],
                "game_start_success_rate": f"{game_start['success_rate']:.6f}",
                "game_start_latency_ms": f"{game_start['latency_ms']:.2f}",
                "game_start_prompt_tokens": f"{game_start['prompt_tokens']:.2f}",
                "game_start_completion_tokens": f"{game_start['completion_tokens']:.2f}",
                "build_samples": build_phase["samples"],
                "build_success_rate": f"{build_phase['success_rate']:.6f}",
                "build_latency_ms": f"{build_phase['latency_ms']:.2f}",
                "build_prompt_tokens": f"{build_phase['prompt_tokens']:.2f}",
                "build_completion_tokens": f"{build_phase['completion_tokens']:.2f}",
            }
        )


if __name__ == "__main__":
    main()
