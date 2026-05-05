from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


INPUT_FILE = Path("consolidated/resultados_consolidados.csv")
OUTPUT_BASE_DIR = Path("graphs/cenarios_instancias_p95_taxa_erros")

SCENARIO_ORDER = ["leve", "medio", "pesado", "hibrido"]
SCENARIO_ALIASES = {
    "leve": "leve",
    "light": "leve",
    "medio": "medio",
    "medium": "medio",
    "pesado": "pesado",
    "heavy": "pesado",
    "hibrido": "hibrido",
    "hybrid": "hibrido",
}
SCENARIO_LABELS = {
    "leve": "Leve",
    "medio": "M\u00e9dio",
    "pesado": "Pesado",
    "hibrido": "H\u00edbrido",
}

METRICS = {
    "p95_response_ms": {
        "dir": "p95",
        "ylabel": "Tempo de resposta P95 (ms)",
        "title": "Tempo de resposta P95",
        "filename": "tempo_resposta_p95",
    },
    "failure_rate_percent": {
        "dir": "taxa_erros",
        "ylabel": "Taxa de erros (%)",
        "title": "Taxa de erros",
        "filename": "taxa_erros",
    },
}


def normalize_scenario(value):
    scenario = str(value).strip().lower()
    return SCENARIO_ALIASES.get(scenario)


def validate_columns(df):
    required = {
        "scenario",
        "instances",
        "users",
        "requests",
        "failures",
        "p95_response_ms",
    }
    missing = required - set(df.columns)

    if missing:
        raise SystemExit(f"Colunas ausentes no CSV consolidado: {sorted(missing)}")


def add_failure_rate_column(df):
    df = df.copy()
    df["failure_rate_percent"] = np.where(
        df["requests"] > 0,
        (df["failures"] / df["requests"]) * 100,
        0,
    )
    return df


def prepare_data(df):
    df = df.copy()
    df["scenario_norm"] = df["scenario"].apply(normalize_scenario)
    df = df[df["scenario_norm"].isin(SCENARIO_ORDER)]

    if df.empty:
        raise SystemExit(
            "Nenhum cenario leve/medio/pesado/hibrido encontrado no CSV consolidado."
        )

    return df


def annotate_bars(ax, bars):
    for bar in bars:
        height = bar.get_height()
        if np.isnan(height):
            continue

        ax.annotate(
            f"{height:.0f}",
            xy=(bar.get_x() + bar.get_width() / 2, height),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=8,
        )


def generate_metric_graph(df, users, metric, config):
    data_users = df[df["users"] == users]

    pivot = data_users.pivot_table(
        index="scenario_norm",
        columns="instances",
        values=metric,
        aggfunc="mean",
    ).reindex(SCENARIO_ORDER)

    if pivot.dropna(how="all").empty:
        return None

    instances = sorted(pivot.columns)
    scenario_labels = [SCENARIO_LABELS[item] for item in SCENARIO_ORDER]
    x = np.arange(len(SCENARIO_ORDER))
    width = 0.75 / max(len(instances), 1)

    fig, ax = plt.subplots(figsize=(9, 5))

    for index, instance in enumerate(instances):
        values = pivot[instance].to_numpy(dtype=float)
        offset = (index - (len(instances) - 1) / 2) * width

        bars = ax.bar(
            x + offset,
            values,
            width=width,
            label=f"Inst\u00e2ncia {int(instance)}",
        )
        annotate_bars(ax, bars)

    ax.set_title(f"{config['title']} por cen\u00e1rio - {users} usu\u00e1rios")
    ax.set_xlabel("Cen\u00e1rio")
    ax.set_ylabel(config["ylabel"])
    ax.set_xticks(x)
    ax.set_xticklabels(scenario_labels)
    ax.legend(title="Inst\u00e2ncias")
    ax.grid(axis="y", alpha=0.3)

    upper_limit = np.nanmax(pivot.to_numpy(dtype=float))
    if not np.isnan(upper_limit) and upper_limit > 0:
        ax.set_ylim(0, upper_limit * 1.15)

    fig.tight_layout()

    output_dir = OUTPUT_BASE_DIR / config["dir"]
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / f"{config['filename']}_{int(users)}users.png"
    fig.savefig(output_file, dpi=150)
    plt.close(fig)

    return output_file


def main():
    if not INPUT_FILE.exists():
        raise SystemExit(
            f"Arquivo nao encontrado: {INPUT_FILE}\n"
            "Execute primeiro: python consolidate_results.py"
        )

    df = pd.read_csv(INPUT_FILE)
    validate_columns(df)
    df = add_failure_rate_column(df)
    df = prepare_data(df)

    generated_files = []

    for metric, config in METRICS.items():
        if metric not in df.columns:
            print(f"Pulando metrica ausente no CSV: {metric}")
            continue

        for users in sorted(df["users"].unique()):
            output_file = generate_metric_graph(df, users, metric, config)
            if output_file:
                generated_files.append(output_file)
                print(f"Gerado: {output_file}")

    if not generated_files:
        raise SystemExit("Nenhum grafico foi gerado.")

    print("\nGraficos gerados em:")
    print(OUTPUT_BASE_DIR)


if __name__ == "__main__":
    main()
