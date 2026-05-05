from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[1]
CONSOLIDATED_FILE = ROOT_DIR / "consolidated" / "resultados_consolidados.csv"
GRAPHS_DIR = ROOT_DIR / "graphs"
GRAPHS_DIR.mkdir(exist_ok=True)

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


def bar_chart(metric, title, ylabel, filename):
    users = sorted(df["users"].unique())
    labels = ordered_labels()

    x = np.arange(len(users))
    width = 0.18
    offset = width * (len(labels) - 1) / 2

    plt.figure(figsize=(12, 6))

    for i, label in enumerate(labels):
        values = []
        for user_count in users:
            val = df[(df["label"] == label) & (df["users"] == user_count)][metric]
            values.append(val.values[0] if not val.empty else 0)

        plt.bar(x + i * width - offset, values, width, label=label)

    plt.xticks(x, users)
    plt.xlabel("Usuarios virtuais")
    plt.ylabel(ylabel)
    plt.title(title)
    plt.legend()
    plt.tight_layout()
    plt.savefig(GRAPHS_DIR / filename, dpi=150)
    plt.close()


line_chart("average_response_ms", "Tempo medio de resposta", "ms", "line_tempo_medio.png")
line_chart("median_response_ms", "Mediana", "ms", "line_mediana.png")
line_chart("p95_response_ms", "P95", "ms", "line_p95.png")
line_chart("p99_response_ms", "P99", "ms", "line_p99.png")
line_chart("rps", "Throughput", "req/s", "line_rps.png")
line_chart("failures", "Falhas", "count", "line_falhas.png")

bar_chart("average_response_ms", "Tempo medio de resposta", "ms", "bar_tempo_medio.png")
bar_chart("median_response_ms", "Mediana", "ms", "bar_mediana.png")
bar_chart("p95_response_ms", "P95", "ms", "bar_p95.png")
bar_chart("p99_response_ms", "P99", "ms", "bar_p99.png")
bar_chart("rps", "Throughput", "req/s", "bar_rps.png")
bar_chart("failures", "Falhas", "count", "bar_falhas.png")

print(f"Graficos salvos em: {GRAPHS_DIR}")
