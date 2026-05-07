from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT_DIR = Path(__file__).resolve().parents[1]
CONSOLIDATED_FILE = ROOT_DIR / "consolidated" / "resultados_consolidados.csv"
GRAPHS_DIR = ROOT_DIR / "graphs"
GRAPHS_DIR.mkdir(exist_ok=True)

for old_graph in GRAPHS_DIR.glob("*.png"):
    old_graph.unlink()

df = pd.read_csv(CONSOLIDATED_FILE)
df["label"] = df["language"] + " - " + df["cache"]

LABEL_ORDER = [
    "python - sem_cache",
    "python - com_cache",
    "ruby - sem_cache",
    "ruby - com_cache",
]


def ordered_labels():
    labels = set(df["label"].unique())
    return [label for label in LABEL_ORDER if label in labels]


def line_chart(metric, title, ylabel, filename):
    plt.figure(figsize=(10, 6))

    for label in ordered_labels():
        group = df[df["label"] == label].sort_values("users")
        plt.plot(group["users"], group[metric], marker="o", label=label)

    plt.title(title)
    plt.xlabel("Usuarios virtuais")
    plt.ylabel(ylabel)
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(GRAPHS_DIR / filename, dpi=150)
    plt.close()


def format_bar_value(metric, value):
    if metric == "failure_rate_percent":
        return f"{value:.2f}%"

    if metric == "rps":
        return f"{value:.2f}"

    if float(value).is_integer():
        return f"{int(value)}"

    return f"{value:.1f}"


def bar_chart(metric, title, ylabel, filename):
    users = sorted(df["users"].unique())
    labels = ordered_labels()

    x = np.arange(len(users))
    width = 0.18
    offset = width * (len(labels) - 1) / 2

    plt.figure(figsize=(12, 6))
    max_value = 0

    for i, label in enumerate(labels):
        values = []
        for user_count in users:
            val = df[(df["label"] == label) & (df["users"] == user_count)][metric]
            values.append(val.values[0] if not val.empty else 0)

        positions = x + i * width - offset
        bars = plt.bar(positions, values, width, label=label)
        max_value = max(max_value, max(values) if values else 0)

        for bar, value in zip(bars, values):
            plt.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height(),
                format_bar_value(metric, value),
                ha="center",
                va="bottom",
                fontsize=8,
            )

    plt.xticks(x, users)
    plt.xlabel("Usuarios virtuais")
    plt.ylabel(ylabel)
    plt.title(title)
    plt.ylim(top=max_value * 1.15 if max_value > 0 else 1)
    plt.legend()
    plt.tight_layout()
    plt.savefig(GRAPHS_DIR / filename, dpi=150)
    plt.close()


line_chart("p95_response_ms", "P95", "ms", "line_p95.png")
line_chart("failure_rate_percent", "Taxa de falhas", "%", "line_taxa_falhas.png")

bar_chart("p95_response_ms", "P95", "ms", "bar_p95.png")
bar_chart("failure_rate_percent", "Taxa de falhas", "%", "bar_taxa_falhas.png")

print(f"Graficos salvos em: {GRAPHS_DIR}")
