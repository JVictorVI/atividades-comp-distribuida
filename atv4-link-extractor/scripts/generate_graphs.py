from pathlib import Path
from urllib.parse import urlparse

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT_DIR = Path(__file__).resolve().parents[1]
CONSOLIDATED_FILE = ROOT_DIR / "consolidated" / "resultados_consolidados.csv"
LINK_COUNTS_FILE = ROOT_DIR / "consolidated" / "links_extraidos_por_url.csv"
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

DISPLAY_LABELS = {
    "python - sem_cache": "Python sem cache",
    "python - com_cache": "Python com cache",
    "ruby - sem_cache": "Ruby sem cache",
    "ruby - com_cache": "Ruby com cache",
}

SCENARIO_TITLES = {
    "python_nocache": "Python sem cache",
    "python_cache": "Python com cache",
    "ruby_nocache": "Ruby sem cache",
    "ruby_cache": "Ruby com cache",
}

SCENARIO_ORDER = [
    "python_nocache",
    "python_cache",
    "ruby_nocache",
    "ruby_cache",
]

COLORS = {
    "python - sem_cache": "#d95f02",
    "python - com_cache": "#1b9e77",
    "ruby - sem_cache": "#7570b3",
    "ruby - com_cache": "#e7298a",
}

LOAD_COLORS = {
    100: "#4c78a8",
    250: "#f58518",
    500: "#54a24b",
}


def ordered_labels():
    labels = set(df["label"].unique())
    return [label for label in LABEL_ORDER if label in labels]


def display_label(label):
    return DISPLAY_LABELS.get(label, label.replace("_", " "))


def url_label(url):
    parsed = urlparse(url)
    return parsed.netloc.replace("www.", "") or url


def format_number(value, suffix=""):
    if pd.isna(value):
        return ""

    if float(value).is_integer():
        text = f"{int(value):,}".replace(",", ".")
    else:
        text = f"{value:,.1f}".replace(",", ".")

    return f"{text}{suffix}"


def style_axes(ax):
    ax.grid(axis="y", linestyle="--", linewidth=0.7, alpha=0.35)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(axis="both", labelsize=9)


def line_chart(metric, title, ylabel, filename):
    fig, ax = plt.subplots(figsize=(10, 6))

    for label in ordered_labels():
        group = df[df["label"] == label].sort_values("users")
        ax.plot(
            group["users"],
            group[metric],
            marker="o",
            linewidth=2,
            markersize=6,
            color=COLORS.get(label),
            label=display_label(label),
        )

    ax.set_title(title, fontsize=14, fontweight="bold", pad=14)
    ax.set_xlabel("Usuários virtuais", fontsize=11)
    ax.set_ylabel(ylabel, fontsize=11)
    ax.set_xticks(sorted(df["users"].unique()))
    ax.legend(title="API", frameon=False, ncols=2)
    style_axes(ax)
    fig.tight_layout()
    fig.savefig(GRAPHS_DIR / filename, dpi=150)
    plt.close()


def format_bar_value(metric, value):
    if metric == "failure_rate_percent":
        return f"{value:.2f}%"

    if metric == "rps":
        return f"{value:.2f}"

    if float(value).is_integer():
        return f"{int(value)}"

    return f"{value:.1f}"


def bar_chart(metric, title, ylabel, filename, source_df=None, labels=None):
    source_df = df if source_df is None else source_df
    users = sorted(source_df["users"].unique())
    labels = ordered_labels() if labels is None else labels

    x = np.arange(len(users))
    width = 0.18
    offset = width * (len(labels) - 1) / 2

    fig, ax = plt.subplots(figsize=(12, 6))
    max_value = 0

    for i, label in enumerate(labels):
        values = []
        for user_count in users:
            val = source_df[(source_df["label"] == label) & (source_df["users"] == user_count)][metric]
            values.append(val.values[0] if not val.empty else 0)

        positions = x + i * width - offset
        bars = ax.bar(
            positions,
            values,
            width,
            color=COLORS.get(label),
            label=display_label(label),
        )
        max_value = max(max_value, max(values) if values else 0)

        for bar, value in zip(bars, values):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height(),
                format_bar_value(metric, value),
                ha="center",
                va="bottom",
                fontsize=7,
                rotation=0,
            )

    ax.set_xticks(x, users)
    ax.set_xlabel("Usuários virtuais", fontsize=11)
    ax.set_ylabel(ylabel, fontsize=11)
    ax.set_title(title, fontsize=14, fontweight="bold", pad=14)
    ax.set_ylim(top=max_value * 1.22 if max_value > 0 else 1)
    ax.legend(title="API", frameon=False, ncols=2)
    style_axes(ax)
    fig.tight_layout()
    fig.savefig(GRAPHS_DIR / filename, dpi=150)
    plt.close()


def latency_comparison_by_cache_chart(cache_value, title, filename):
    source_df = df[df["cache"] == cache_value]
    labels = [label for label in LABEL_ORDER if label in set(source_df["label"])]
    bar_chart("p95_response_ms", title, "Latência P95 (ms)", filename, source_df, labels)


def latency_by_api_chart():
    scenarios = [scenario for scenario in SCENARIO_ORDER if scenario in set(df["scenario"])]
    users = sorted(df["users"].unique())

    fig, axes = plt.subplots(2, 2, figsize=(13, 8), constrained_layout=True)
    axes = axes.flatten()

    for ax, scenario in zip(axes, scenarios):
        group = df[df["scenario"] == scenario].sort_values("users")
        values = [
            group[group["users"] == user_count]["p95_response_ms"].iloc[0]
            if not group[group["users"] == user_count].empty
            else np.nan
            for user_count in users
        ]
        colors = [LOAD_COLORS.get(user_count, "#4c78a8") for user_count in users]
        bars = ax.bar([str(user_count) for user_count in users], values, color=colors, width=0.55)
        max_value = max([value for value in values if not pd.isna(value)], default=0)

        for bar, value in zip(bars, values):
            if pd.isna(value):
                continue

            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height(),
                format_number(value),
                ha="center",
                va="bottom",
                fontsize=8,
            )

        ax.set_title(SCENARIO_TITLES.get(scenario, scenario), fontsize=12, fontweight="bold")
        ax.set_xlabel("Usuários virtuais")
        ax.set_ylabel("Latência P95 (ms)")
        ax.set_ylim(top=max_value * 1.2 if max_value > 0 else 1)
        style_axes(ax)

    for ax in axes[len(scenarios):]:
        ax.axis("off")

    fig.suptitle("Latência P95 por API e carga", fontsize=16, fontweight="bold")
    fig.savefig(GRAPHS_DIR / "latencia_por_api.png", dpi=150)
    plt.close()


line_chart("p95_response_ms", "Evolução da latência P95 por carga", "Latência P95 (ms)", "line_p95.png")
line_chart("failure_rate_percent", "Evolução da taxa de falhas por carga", "Taxa de falhas (%)", "line_taxa_falhas.png")

latency_comparison_by_cache_chart(
    "sem_cache",
    "Comparação da latência P95 entre APIs sem cache",
    "bar_p95_sem_cache.png",
)
latency_comparison_by_cache_chart(
    "com_cache",
    "Comparação da latência P95 entre APIs com cache",
    "bar_p95_com_cache.png",
)
bar_chart("failure_rate_percent", "Comparação da taxa de falhas entre APIs", "Taxa de falhas (%)", "bar_taxa_falhas.png")
latency_by_api_chart()


def extracted_links_chart():
    if not LINK_COUNTS_FILE.exists():
        return

    links_df = pd.read_csv(LINK_COUNTS_FILE)
    links_by_url = (
        links_df.groupby("url", as_index=False)["extracted_links"]
        .max()
        .sort_values("extracted_links", ascending=True)
    )

    fig_height = max(6, len(links_by_url) * 0.45)
    fig, ax = plt.subplots(figsize=(11, fig_height))
    bars = ax.barh(
        links_by_url["url"].map(url_label),
        links_by_url["extracted_links"],
        color="#4c78a8",
        height=0.68,
    )

    max_value = links_by_url["extracted_links"].max()
    for bar, value in zip(bars, links_by_url["extracted_links"]):
        ax.text(
            bar.get_width() + max_value * 0.015,
            bar.get_y() + bar.get_height() / 2,
            format_number(value),
            ha="left",
            va="center",
            fontsize=9,
        )

    ax.set_title("Quantidade de links extraidos por URL", fontsize=14, fontweight="bold", pad=14)
    ax.set_xlabel("Links extraidos")
    ax.set_ylabel("URL")
    ax.set_xlim(right=max_value * 1.14 if max_value > 0 else 1)
    style_axes(ax)
    fig.tight_layout()
    fig.savefig(GRAPHS_DIR / "links_extraidos_por_url.png", dpi=150)
    plt.close()


extracted_links_chart()

print(f"Graficos salvos em: {GRAPHS_DIR}")
