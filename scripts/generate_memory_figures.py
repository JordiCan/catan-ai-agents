#!/usr/bin/env python3
import csv
import re
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"
FIGURES = ROOT / "memoria" / "figures"
PROMPTS = ["strict_json", "direct_short", "guided_compact"]


def parse_models_from_run_script(path: Path):
    text = path.read_text(encoding="utf-8")
    match = re.search(r"for MODEL in (.*?); do", text)
    if match:
        return [part.strip() for part in match.group(1).split()]
    return []


def safe_model_name(model_name: str):
    return model_name.replace("/", "_").replace(":", "_")


def provider_scripts():
    return {
        "poligpt": ROOT / "run.sh",
        "ollama": ROOT / "run_ollama.sh",
        "bedrock": ROOT / "run_bedrock.sh",
    }


def candidate_dirs(provider: str):
    return [RESULTS / provider, RESULTS]


def locate(provider: str, stem: str, suffix: str):
    for directory in candidate_dirs(provider):
        path = directory / f"{stem}{suffix}"
        if path.exists():
            return path
    return None


def read_csv_row(path: Path):
    with path.open(encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        reader.fieldnames = [name.strip() for name in reader.fieldnames]
        row = next(reader)
        return {key.strip(): value for key, value in row.items()}


def read_csv_rows(path: Path):
    with path.open(encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        reader.fieldnames = [name.strip() for name in reader.fieldnames]
        rows = []
        for row in reader:
            rows.append({key.strip(): value for key, value in row.items()})
        return rows


def collect_results():
    prompt_rows = []
    position_rows = []

    for provider, script in provider_scripts().items():
        models = parse_models_from_run_script(script)
        for model in models:
            safe = safe_model_name(model)
            prefix = f"{provider}_{safe}_"
            for prompt in PROMPTS:
                stem = f"{prefix}{prompt}"
                standard_csv = locate(provider, stem, "_standard.csv")
                metrics_csv = locate(provider, stem, "_metrics.csv")
                matches_csv = locate(provider, stem, "_standard_matches.csv")
                if not metrics_csv:
                    jsonl_path = locate(provider, stem, ".jsonl")
                    if jsonl_path and jsonl_path.exists():
                        metrics_csv = ROOT / "tmp_metrics.csv"
                        import subprocess
                        subprocess.run(
                            [
                                "python",
                                str(ROOT / "scripts" / "summarize_llm_log.py"),
                                str(jsonl_path),
                                str(metrics_csv),
                            ],
                            check=True,
                        )

                if not metrics_csv:
                    continue

                mr = read_csv_row(metrics_csv)
                base_row = {
                    "provider": provider,
                    "model": model,
                    "prompt": prompt,
                    "game_start_success_rate": float(mr["game_start_success_rate"]),
                    "build_success_rate": float(mr["build_success_rate"]),
                    "game_start_latency_ms": float(mr["game_start_latency_ms"]),
                    "build_latency_ms": float(mr["build_latency_ms"]),
                    "game_start_prompt_tokens": float(mr["game_start_prompt_tokens"]),
                    "build_prompt_tokens": float(mr["build_prompt_tokens"]),
                    "game_start_completion_tokens": float(mr["game_start_completion_tokens"]),
                    "build_completion_tokens": float(mr["build_completion_tokens"]),
                }

                if standard_csv and matches_csv:
                    sr = read_csv_row(standard_csv)
                    prompt_rows.append(
                        {
                            **base_row,
                            "win_rate": float(sr["Ratio Victorias"]),
                            "avg_points": float(sr["Media Puntos"]),
                            "avg_rank": float(sr["Puesto Medio"]),
                            "complete": 1,
                        }
                    )

                    grouped = defaultdict(list)
                    for row in read_csv_rows(matches_csv):
                        grouped[row["position"]].append(row)

                    for position, rows in grouped.items():
                        games = len(rows)
                        wins = sum(int(float(r["victory"])) for r in rows)
                        avg_points = sum(float(r["points"]) for r in rows) / games if games else 0.0
                        avg_rank = sum(float(r["rank"]) for r in rows) / games if games else 0.0
                        position_rows.append(
                            {
                                "provider": provider,
                                "model": model,
                                "prompt": prompt,
                                "position": f"J{position}",
                                "games": games,
                                "win_rate": wins / games if games else 0.0,
                                "avg_points": avg_points,
                                "avg_rank": avg_rank,
                            }
                        )
                else:
                    prompt_rows.append(
                        {
                            **base_row,
                            "win_rate": float("nan"),
                            "avg_points": float("nan"),
                            "avg_rank": float("nan"),
                            "complete": 0,
                        }
                    )

    return pd.DataFrame(prompt_rows), pd.DataFrame(position_rows)


def short_model_name(model: str):
    return (
        model.replace("amazon.", "")
        .replace("ai21.", "")
        .replace("mistral.", "")
        .replace("-v1:0", "")
        .replace("ollama/", "")
        .replace("openai/", "")
    )


def save_prompt_lines_plot(df, provider, out_path):
    subset = df[(df["provider"] == provider) & (df["complete"] == 1)].copy()
    subset["prompt"] = pd.Categorical(subset["prompt"], categories=PROMPTS, ordered=True)
    subset["model_label"] = subset["model"].map(short_model_name)

    fig, axes = plt.subplots(1, 2, figsize=(11.2, 3.8))
    metrics = [
        ("win_rate", "Tasa de victoria", (0, 1.05)),
        ("avg_points", "Puntos medios", None),
    ]

    for ax, (col, title, ylim) in zip(axes, metrics):
        sns.lineplot(
            data=subset,
            x="prompt",
            y=col,
            hue="model_label",
            style="model_label",
            markers=True,
            dashes=False,
            linewidth=2.2,
            markersize=8,
            ax=ax,
        )
        ax.set_title(f"{provider.capitalize()}: {title} por prompt")
        ax.set_xlabel("")
        ax.set_ylabel(title)
        if ylim:
            ax.set_ylim(*ylim)
        ax.grid(True, axis="y", alpha=0.25)

    axes[0].legend(title="Modelo", frameon=False, loc="lower left")
    axes[1].legend_.remove()
    plt.tight_layout()
    fig.savefig(out_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def save_position_plot(df, provider, out_path):
    subset = df[df["provider"] == provider].copy()
    if subset.empty:
        return
    ranking = (
        subset.groupby(["model", "prompt"], as_index=False)
        .agg({"win_rate": "mean", "avg_points": "mean"})
        .sort_values(["model", "win_rate", "avg_points"], ascending=[True, False, False])
    )
    best = ranking.groupby("model", as_index=False).first()[["model", "prompt"]]
    subset = subset.merge(best, on=["model", "prompt"], how="inner")
    subset["model_label"] = subset["model"].map(short_model_name)

    fig, axes = plt.subplots(1, 2, figsize=(10.8, 3.6), sharex=False)

    sns.lineplot(
        data=subset,
        x="position",
        y="win_rate",
        hue="model_label",
        style="model_label",
        markers=True,
        dashes=False,
        linewidth=2.2,
        markersize=8,
        ax=axes[0],
    )
    axes[0].set_title(f"{provider.capitalize()}: win rate por posicion")
    axes[0].set_ylabel("Win rate")
    axes[0].set_xlabel("Posicion")
    axes[0].set_ylim(0, 1.05)
    axes[0].grid(True, axis="y", alpha=0.25)
    axes[0].legend_.remove()

    sns.lineplot(
        data=subset,
        x="position",
        y="avg_points",
        hue="model_label",
        style="model_label",
        markers=True,
        dashes=False,
        linewidth=2.2,
        markersize=8,
        ax=axes[1],
    )
    axes[1].set_title(f"{provider.capitalize()}: puntos medios por posicion")
    axes[1].set_ylabel("Puntos medios")
    axes[1].set_xlabel("Posicion")
    axes[1].grid(True, axis="y", alpha=0.25)
    axes[1].legend(title="Modelo", frameon=False, loc="best")

    plt.tight_layout()
    fig.savefig(out_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def save_latency_tokens_plot(df, provider, out_path):
    subset = df[df["provider"] == provider].copy()
    subset["prompt"] = pd.Categorical(subset["prompt"], categories=PROMPTS, ordered=True)
    subset["model_label"] = subset["model"].map(short_model_name)
    metrics = [
        ("game_start_latency_ms", "Latencia inicio (ms)"),
        ("build_latency_ms", "Latencia build (ms)"),
        ("game_start_prompt_tokens", "Prompt tokens inicio"),
        ("build_completion_tokens", "Completion tokens build"),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(11.5, 6.5))
    axes = axes.flatten()

    for ax, (col, title) in zip(axes, metrics):
        sns.lineplot(
            data=subset,
            x="prompt",
            y=col,
            hue="model_label",
            style="model_label",
            markers=True,
            dashes=False,
            linewidth=2.0,
            markersize=7,
            ax=ax,
        )
        ax.set_title(f"{provider.capitalize()}: {title}")
        ax.set_xlabel("")
        ax.set_ylabel(title)
        ax.grid(True, axis="y", alpha=0.25)

    axes[0].legend(title="Modelo", frameon=False, loc="best")
    for ax in axes[1:]:
        ax.legend_.remove()

    plt.tight_layout()
    fig.savefig(out_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def main():
    sns.set_theme(style="whitegrid", font_scale=0.9)
    FIGURES.mkdir(parents=True, exist_ok=True)
    prompt_df, position_df = collect_results()
    prompt_df["model_label"] = prompt_df["model"].map(short_model_name)

    for provider in ["poligpt", "ollama", "bedrock"]:
        subset = prompt_df[prompt_df["provider"] == provider]
        if subset.empty:
            continue
        save_prompt_lines_plot(prompt_df, provider, FIGURES / f"{provider}_performance_lines.png")
        save_position_plot(position_df, provider, FIGURES / f"{provider}_position_analysis.png")
        save_latency_tokens_plot(prompt_df, provider, FIGURES / f"{provider}_latency_tokens.png")

    print(f"Generated figures in {FIGURES}")


if __name__ == "__main__":
    main()
