import argparse
import json
import os
from pathlib import Path
from statistics import mean, median

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

import matplotlib.pyplot as plt


def load_results(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, dict) and "results" in data and isinstance(data["results"], list):
        return data["results"]
    if isinstance(data, list):
        return data
    raise ValueError(f"{path} does not contain a supported list of results")


def label_from_path(path):
    return Path(path).stem


def safe_mean(values):
    return mean(values) if values else 0.0


def compute_stats(label, games):
    if not games:
        return {
            "label": label,
            "games": 0,
            "win_rate": 0.0,
            "avg_points_p0": 0.0,
            "avg_points_others": 0.0,
            "avg_rounds": 0.0,
            "median_rounds": 0.0,
            "largest_army_rate": 0.0,
            "longest_road_rate": 0.0,
            "avg_margin_vs_second": 0.0,
            "max_points_p0": 0.0,
            "min_points_p0": 0.0,
        }

    is_summary_format = "victory_points" in games[0]
    if is_summary_format:
        p0_points = [game["victory_points"]["P0"] for game in games]
        other_points = [
            game["victory_points"][player]
            for game in games
            for player in ("P1", "P2", "P3")
        ]
        winners = [game["winner"] for game in games]
        rounds = [game["rounds_played"] for game in games]
        largest_army = [game["largest_army_player"] for game in games]
        longest_road = [game["longest_road_player"] for game in games]
        margins = []
        for game in games:
            scores = game["victory_points"]
            others = sorted([scores["P1"], scores["P2"], scores["P3"]], reverse=True)
            margins.append(scores["P0"] - others[0])
    else:
        p0_points = [game.get("points", 0) for game in games]
        other_points = []
        winners = [0 if game.get("victory", 0) else -1 for game in games]
        rounds = [game.get("rounds_played", 0) for game in games]
        largest_army = [game.get("largest_army_player", -1) for game in games]
        longest_road = [game.get("longest_road_player", -1) for game in games]
        margins = [game.get("points", 0) for game in games]

    return {
        "label": label,
        "games": len(games),
        "win_rate": winners.count(0) / len(games),
        "avg_points_p0": safe_mean(p0_points),
        "avg_points_others": safe_mean(other_points),
        "avg_rounds": safe_mean(rounds),
        "median_rounds": median(rounds),
        "largest_army_rate": largest_army.count(0) / len(games),
        "longest_road_rate": longest_road.count(0) / len(games),
        "avg_margin_vs_second": safe_mean(margins),
        "max_points_p0": max(p0_points),
        "min_points_p0": min(p0_points),
        "providers": sorted({game.get("provider", "unknown") for game in games}),
        "models": sorted({game.get("model", "unknown") for game in games}),
        "prompts": sorted({game.get("prompt", "unknown") for game in games}),
    }


def print_stats_table(stats_rows):
    columns = [
        ("label", "dataset"),
        ("games", "games"),
        ("providers", "providers"),
        ("models", "models"),
        ("prompts", "prompts"),
        ("win_rate", "win_rate"),
        ("avg_points_p0", "avg_p0"),
        ("avg_points_others", "avg_others"),
        ("avg_margin_vs_second", "avg_margin"),
        ("avg_rounds", "avg_rounds"),
        ("median_rounds", "median_rounds"),
        ("largest_army_rate", "army_rate"),
        ("longest_road_rate", "road_rate"),
    ]

    formatted_rows = []
    for row in stats_rows:
        formatted = {}
        for key, _ in columns:
            value = row[key]
            if isinstance(value, list):
                formatted[key] = ",".join(value)
                continue
            if isinstance(value, float):
                formatted[key] = f"{value:.3f}"
            else:
                formatted[key] = str(value)
        formatted_rows.append(formatted)

    widths = {}
    for key, header in columns:
        widths[key] = max(len(header), *(len(row[key]) for row in formatted_rows))

    header_line = "  ".join(header.ljust(widths[key]) for key, header in columns)
    separator = "  ".join("-" * widths[key] for key, _ in columns)
    print(header_line)
    print(separator)
    for row in formatted_rows:
        print("  ".join(row[key].ljust(widths[key]) for key, _ in columns))


def ensure_output_dir(output_dir):
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    return output


def save_stats_json(stats_rows, output_dir):
    output_path = Path(output_dir) / "summary_stats.json"
    output_path.write_text(json.dumps(stats_rows, indent=2, ensure_ascii=True), encoding="utf-8")
    return output_path


def plot_bar_metric(stats_rows, metric, title, ylabel, output_path):
    labels = [row["label"] for row in stats_rows]
    values = [row[metric] for row in stats_rows]

    plt.figure(figsize=(9, 5))
    bars = plt.bar(labels, values)
    plt.title(title)
    plt.ylabel(ylabel)
    plt.xticks(rotation=20, ha="right")

    for bar, value in zip(bars, values):
        plt.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"{value:.2f}",
            ha="center",
            va="bottom",
        )

    plt.tight_layout()
    plt.savefig(output_path, dpi=160)
    plt.close()


def plot_points_boxplot(series_by_label, output_path):
    labels = list(series_by_label.keys())
    data = [series_by_label[label] for label in labels]

    plt.figure(figsize=(9, 5))
    plt.boxplot(data, labels=labels)
    plt.title("Distribution of P0 Victory Points")
    plt.ylabel("Victory Points")
    plt.xticks(rotation=20, ha="right")
    plt.tight_layout()
    plt.savefig(output_path, dpi=160)
    plt.close()


def plot_rounds_boxplot(series_by_label, output_path):
    labels = list(series_by_label.keys())
    data = [series_by_label[label] for label in labels]

    plt.figure(figsize=(9, 5))
    plt.boxplot(data, labels=labels)
    plt.title("Distribution of Game Length")
    plt.ylabel("Rounds Played")
    plt.xticks(rotation=20, ha="right")
    plt.tight_layout()
    plt.savefig(output_path, dpi=160)
    plt.close()


def plot_seed_progression(seed_points, output_path):
    plt.figure(figsize=(10, 5))
    for label, series in seed_points.items():
        series = sorted(series, key=lambda item: item[0])
        xs = [item[0] for item in series]
        ys = [item[1] for item in series]
        plt.plot(xs, ys, marker="o", label=label)

    plt.title("P0 Victory Points by Seed")
    plt.xlabel("Seed")
    plt.ylabel("P0 Victory Points")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path, dpi=160)
    plt.close()


def parse_args():
    parser = argparse.ArgumentParser(description="Generate stats and plots from experiment result JSON files")
    parser.add_argument("inputs", nargs="+", help="One or more JSON result files generated by Experiments.runner")
    parser.add_argument("--labels", nargs="*", help="Optional labels matching the input files")
    parser.add_argument("--output-dir", default="artifacts/analysis", help="Directory where stats and plots will be saved")
    return parser.parse_args()


def main():
    args = parse_args()
    if args.labels and len(args.labels) != len(args.inputs):
        raise ValueError("--labels must have the same length as inputs")

    labels = args.labels if args.labels else [label_from_path(path) for path in args.inputs]
    output_dir = ensure_output_dir(args.output_dir)

    stats_rows = []
    points_by_label = {}
    rounds_by_label = {}
    seed_points = {}

    for label, path in zip(labels, args.inputs):
        games = load_results(path)
        stats_rows.append(compute_stats(label, games))
        if games and "victory_points" in games[0]:
            points_by_label[label] = [game["victory_points"]["P0"] for game in games]
            rounds_by_label[label] = [game["rounds_played"] for game in games]
            seed_points[label] = [(game["seed"], game["victory_points"]["P0"]) for game in games]
        else:
            points_by_label[label] = [game.get("points", 0) for game in games]
            rounds_by_label[label] = [game.get("rounds_played", 0) for game in games]
            seed_points[label] = [(game.get("seed", index), game.get("points", 0)) for index, game in enumerate(games)]

    print_stats_table(stats_rows)
    stats_json_path = save_stats_json(stats_rows, output_dir)

    plot_bar_metric(stats_rows, "win_rate", "Win Rate of P0", "Win Rate", output_dir / "win_rate.png")
    plot_bar_metric(stats_rows, "avg_points_p0", "Average Victory Points of P0", "Average Victory Points", output_dir / "avg_points_p0.png")
    plot_bar_metric(stats_rows, "avg_rounds", "Average Game Length", "Average Rounds", output_dir / "avg_rounds.png")
    plot_bar_metric(stats_rows, "avg_margin_vs_second", "Average Margin vs Second Place", "Average Margin", output_dir / "avg_margin_vs_second.png")
    plot_points_boxplot(points_by_label, output_dir / "points_distribution.png")
    plot_rounds_boxplot(rounds_by_label, output_dir / "rounds_distribution.png")

    if any(seed_points.values()):
        plot_seed_progression(seed_points, output_dir / "seed_progression.png")

    print(f"\nSummary JSON saved to: {stats_json_path}")
    print(f"Plots saved to: {output_dir}")


if __name__ == "__main__":
    main()
