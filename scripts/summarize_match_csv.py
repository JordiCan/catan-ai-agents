import argparse
import csv
import os
from collections import Counter, defaultdict
from pathlib import Path


def parse_float(value, default=0.0):
    if value in (None, ""):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def parse_int(value, default=0):
    if value in (None, ""):
        return default
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def percent(value):
    return f"{value * 100:.2f}%"


def number(value):
    return f"{value:.2f}"


def latex_escape(value):
    replacements = {
        "\\": r"\textbackslash{}",
        "_": r"\_",
        "%": r"\%",
        "&": r"\&",
        "#": r"\#",
        "$": r"\$",
        "{": r"\{",
        "}": r"\}",
    }
    text = str(value)
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def read_rows(path):
    with Path(path).open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def summarize(rows):
    games = len(rows)
    wins = sum(parse_int(row.get("victory")) for row in rows)
    points = [parse_float(row.get("points")) for row in rows]
    ranks = [parse_float(row.get("rank")) for row in rows]
    rounds = [parse_float(row.get("rounds_played")) for row in rows]
    errors = sum(1 for row in rows if row.get("error"))
    winners = Counter(row.get("winner_agent", "") for row in rows if row.get("winner_agent"))

    return {
        "games": games,
        "wins": wins,
        "win_rate": wins / games if games else 0.0,
        "avg_points": sum(points) / games if games else 0.0,
        "avg_rank": sum(ranks) / games if games else 0.0,
        "avg_rounds": sum(rounds) / games if games else 0.0,
        "errors": errors,
        "winner_counts": winners,
    }


def group_by(rows, key):
    groups = defaultdict(list)
    for row in rows:
        groups[row.get(key, "")].append(row)
    return groups


def group_by_individual_opponent(rows):
    groups = defaultdict(list)
    for row in rows:
        for key in ("opponent_1", "opponent_2", "opponent_3"):
            opponent = row.get(key, "")
            if opponent:
                groups[opponent].append(row)
    return groups


def label_for_path(path):
    return Path(path).stem


def display_dataset_label(label):
    lower = label.lower()
    if "heuristic" in lower:
        return "Heuristico"
    if "poligpt" in lower:
        return "Poligpt"
    return label.replace("_matches", "")


def display_opponent_label(label):
    if label.endswith("Agent"):
        return label[:-5]
    return label


def slugify_label(label):
    return display_dataset_label(label).lower().replace(" ", "_")


def text_summary(dataset):
    lines = []
    stats = dataset["summary"]
    lines.append(f"== {dataset['label']} ==")
    lines.append(
        "partidas={games} victorias={wins} win_rate={win_rate:.4f} "
        "puntos_medios={avg_points:.2f} puesto_medio={avg_rank:.2f} "
        "rondas_medias={avg_rounds:.2f} errores={errors}".format(**stats)
    )

    lines.append("Por posición:")
    for position, rows in sorted(dataset["by_position"].items(), key=lambda item: parse_int(item[0])):
        row_stats = summarize(rows)
        lines.append(
            "  J{position}: partidas={games} victorias={wins} win_rate={win_rate:.4f} "
            "puntos_medios={avg_points:.2f} rondas_medias={avg_rounds:.2f}".format(
                position=position,
                **row_stats,
            )
        )

    if dataset["by_opponents"]:
        opponent_stats = []
        for key, rows in dataset["by_opponents"].items():
            row_stats = summarize(rows)
            opponent_stats.append((row_stats["win_rate"], row_stats["avg_points"], key, row_stats))
        lines.append("Peores grupos de rivales:")
        for _, _, key, row_stats in sorted(opponent_stats)[:5]:
            lines.append(
                "  {key}: partidas={games} victorias={wins} win_rate={win_rate:.4f} "
                "puntos_medios={avg_points:.2f}".format(key=key, **row_stats)
            )

    if dataset["by_individual_opponent"]:
        lines.append("Por rival individual:")
        for opponent, rows in sorted(dataset["by_individual_opponent"].items()):
            row_stats = summarize(rows)
            lines.append(
                "  {opponent}: apariciones={games} victorias={wins} win_rate={win_rate:.4f} "
                "puntos_medios={avg_points:.2f} puesto_medio={avg_rank:.2f} rondas_medias={avg_rounds:.2f}".format(
                    opponent=opponent,
                    **row_stats,
                )
            )

    return "\n".join(lines)


def latex_table(headers, rows, caption, column_spec=None):
    if column_spec is None:
        column_spec = "l" + "r" * (len(headers) - 1)
    lines = [
        r"\begin{table}[h]",
        r"\centering",
        rf"\begin{{tabular}}{{{column_spec}}}",
        r"\toprule",
        " & ".join(headers) + r" \\",
        r"\midrule",
    ]
    for row in rows:
        lines.append(" & ".join(latex_escape(value) for value in row) + r" \\")
    lines.extend(
        [
            r"\bottomrule",
            r"\end{tabular}",
            rf"\caption{{{latex_escape(caption)}}}",
            r"\end{table}",
        ]
    )
    return "\n".join(lines)


def latex_summary(datasets):
    global_rows = []
    position_rows = []
    individual_opponent_rows = []

    for dataset in datasets:
        stats = dataset["summary"]
        global_rows.append(
            [
                dataset["label"],
                stats["games"],
                stats["wins"],
                percent(stats["win_rate"]),
                number(stats["avg_points"]),
                number(stats["avg_rank"]),
                number(stats["avg_rounds"]),
            ]
        )

        for position, rows in sorted(dataset["by_position"].items(), key=lambda item: parse_int(item[0])):
            row_stats = summarize(rows)
            position_rows.append(
                [
                    f"{dataset['label']} J{position}",
                    row_stats["games"],
                    row_stats["wins"],
                    percent(row_stats["win_rate"]),
                    number(row_stats["avg_points"]),
                    number(row_stats["avg_rounds"]),
                ]
            )

        for opponent, rows in sorted(dataset["by_individual_opponent"].items()):
            row_stats = summarize(rows)
            individual_opponent_rows.append(
                [
                    dataset["label"],
                    opponent,
                    row_stats["games"],
                    row_stats["wins"],
                    percent(row_stats["win_rate"]),
                    number(row_stats["avg_points"]),
                    number(row_stats["avg_rank"]),
                ]
            )

    tables = [
        latex_table(
            ["Dataset", "Partidas", "Victorias", "Win rate", "Puntos", "Puesto", "Rondas"],
            global_rows,
            "Resumen agregado de CSV de partidas.",
        )
    ]

    if position_rows:
        tables.append(
            latex_table(
                ["Dataset", "Partidas", "Victorias", "Win rate", "Puntos", "Rondas"],
                position_rows,
                "Resumen por posición del agente evaluado.",
            )
        )

    if individual_opponent_rows:
        tables.append(
            latex_table(
                ["Dataset", "Rival", "Apariciones", "Victorias", "Win rate", "Puntos", "Puesto"],
                individual_opponent_rows,
                "Resumen por rival individual. Cada fila cuenta partidas donde ese rival aparece entre los oponentes.",
                column_spec="llrrrrr",
            )
        )

    return "\n\n".join(tables)


def ensure_matplotlib():
    os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")
    import matplotlib.pyplot as plt

    return plt


def plot_global_summary(datasets, output_dir):
    plt = ensure_matplotlib()
    labels = [display_dataset_label(dataset["label"]) for dataset in datasets]
    win_rates = [dataset["summary"]["win_rate"] * 100 for dataset in datasets]
    avg_points = [dataset["summary"]["avg_points"] for dataset in datasets]

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    axes[0].bar(labels, win_rates, color="#4C78A8")
    axes[0].set_ylabel("Win rate (%)")
    axes[0].set_ylim(0, 105)
    axes[0].set_title("Tasa de victoria")

    axes[1].bar(labels, avg_points, color="#F58518")
    axes[1].set_ylabel("Puntos medios")
    axes[1].set_ylim(0, max(avg_points + [10]) + 1)
    axes[1].set_title("Puntos medios")

    for axis in axes:
        axis.tick_params(axis="x", labelrotation=20)
        for label in axis.get_xticklabels():
            label.set_ha("right")

    fig.tight_layout()
    output_path = output_dir / "global_summary.png"
    fig.savefig(output_path, dpi=180)
    plt.close(fig)
    return output_path


def plot_single_dataset_opponents(dataset, output_dir):
    plt = ensure_matplotlib()
    if not dataset["by_individual_opponent"]:
        return None

    opponents = sorted(dataset["by_individual_opponent"])
    win_rates = []
    avg_points = []
    for opponent in opponents:
        stats = summarize(dataset["by_individual_opponent"][opponent])
        win_rates.append(stats["win_rate"] * 100)
        avg_points.append(stats["avg_points"])

    x_positions = list(range(len(opponents)))
    win_color = "#2563A6"
    point_color = "#D97706"

    fig, axis_win = plt.subplots(figsize=(12, 5.4))
    axis_points = axis_win.twinx()

    axis_win.plot(
        x_positions,
        win_rates,
        color=win_color,
        marker="o",
        linewidth=2.2,
        label="Win rate",
    )
    axis_points.plot(
        x_positions,
        avg_points,
        color=point_color,
        marker="s",
        linewidth=2.2,
        label="Puntos medios",
    )

    axis_win.set_ylabel("Win rate (%)", color=win_color)
    axis_points.set_ylabel("Puntos medios", color=point_color)
    axis_win.tick_params(axis="y", labelcolor=win_color)
    axis_points.tick_params(axis="y", labelcolor=point_color)

    win_padding = max(1.0, (max(win_rates) - min(win_rates)) * 0.35)
    point_padding = max(0.05, (max(avg_points) - min(avg_points)) * 0.45)
    axis_win.set_ylim(max(0, min(win_rates) - win_padding), min(100, max(win_rates) + win_padding))
    axis_points.set_ylim(min(avg_points) - point_padding, max(avg_points) + point_padding)

    axis_win.set_xticks(x_positions)
    axis_win.set_xticklabels([display_opponent_label(opponent) for opponent in opponents], rotation=25, ha="right")
    axis_win.grid(axis="y", linestyle="--", linewidth=0.6, alpha=0.35)
    axis_win.set_title(f"{display_dataset_label(dataset['label'])}: rendimiento por rival presente")

    lines = axis_win.get_lines() + axis_points.get_lines()
    axis_win.legend(lines, [line.get_label() for line in lines], loc="lower right")

    fig.tight_layout()
    output_path = output_dir / f"{slugify_label(dataset['label'])}_by_opponent.png"
    fig.savefig(output_path, dpi=180)
    plt.close(fig)
    return output_path


def write_plots(datasets, output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = [plot_global_summary(datasets, output_dir)]
    for dataset in datasets:
        opponent_path = plot_single_dataset_opponents(dataset, output_dir)
        if opponent_path is not None:
            paths.append(opponent_path)
    return paths


def build_dataset(path):
    rows = read_rows(path)
    return {
        "label": label_for_path(path),
        "path": str(path),
        "rows": rows,
        "summary": summarize(rows),
        "by_position": group_by(rows, "position"),
        "by_opponents": group_by(rows, "opponent_key") if rows and "opponent_key" in rows[0] else {},
        "by_individual_opponent": group_by_individual_opponent(rows),
    }


def parse_args():
    parser = argparse.ArgumentParser(description="Summarize Catan match CSV files")
    parser.add_argument("inputs", nargs="+", help="CSV files generated by the benchmark scripts")
    parser.add_argument("--latex", action="store_true", help="Print LaTeX tables instead of plain text")
    parser.add_argument("--output", help="Optional path where the summary should be written")
    parser.add_argument("--plot-dir", help="Optional directory where summary plots should be written")
    return parser.parse_args()


def main():
    args = parse_args()
    datasets = [build_dataset(path) for path in args.inputs]

    if args.latex:
        output = latex_summary(datasets)
    else:
        output = "\n\n".join(text_summary(dataset) for dataset in datasets)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output + "\n", encoding="utf-8")
    else:
        print(output)

    if args.plot_dir:
        paths = write_plots(datasets, args.plot_dir)
        for path in paths:
            print(f"Wrote plot: {path}")


if __name__ == "__main__":
    main()
