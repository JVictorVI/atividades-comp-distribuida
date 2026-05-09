from pathlib import Path
import matplotlib
import pandas as pd

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

# ============================================================
# Gera gráficos de barras para P95 e taxa de falhas (%)
#
# Entrada:
#   consolidated/resultados_consolidados.csv
#
# Saída:
#   graphs/barras_p95_falhas/por_usuarios/
#   graphs/barras_p95_falhas/por_instancias/
#
# Ideia dos gráficos:
#   1) X = número de usuários
#      Y = P95 ou taxa de falhas
#      Barras = quantidade de instâncias
#
#   2) X = quantidade de instâncias
#      Y = P95 ou taxa de falhas
#      Barras = cenários
# ============================================================

INPUT_FILE = Path("consolidated/resultados_consolidados.csv")

OUTPUT_BASE_DIR = Path("graphs/barras_p95_falhas")
OUTPUT_USERS_DIR = OUTPUT_BASE_DIR / "por_usuarios"
OUTPUT_INSTANCES_DIR = OUTPUT_BASE_DIR / "por_instancias"
OUTPUT_COMBINED_DIR = OUTPUT_BASE_DIR / "consolidado"

OUTPUT_USERS_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_INSTANCES_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_COMBINED_DIR.mkdir(parents=True, exist_ok=True)


scenario_labels = {
    "leve": "Leve",
    "medio": "Médio",
    "pesado": "Pesado",
    "hibrido": "Híbrido",
    "light": "Leve",
    "medium": "Médio",
    "heavy": "Pesado",
    "hybrid": "Híbrido",
}

scenario_order = {
    "leve": 0,
    "light": 0,
    "medio": 1,
    "medium": 1,
    "pesado": 2,
    "heavy": 2,
    "hibrido": 3,
    "hybrid": 3,
}


def safe_name(value):
    return (
        str(value)
        .replace(" ", "_")
        .replace("/", "_")
        .replace("\\", "_")
        .replace(":", "_")
    )


def get_scenario_label(scenario):
    return scenario_labels.get(str(scenario), str(scenario))


def get_scenario_order(scenario):
    return scenario_order.get(str(scenario).lower(), len(scenario_order))


def annotate_bars(bars):
    for bar in bars:
        height = bar.get_height()

        plt.annotate(
            f"{height:.0f}",
            xy=(bar.get_x() + bar.get_width() / 2, height),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=8,
        )


def annotate_axis_bars(ax, bars, value_format="{:.0f}", fontsize=7):
    for bar in bars:
        height = bar.get_height()

        if np.isnan(height):
            continue

        ax.annotate(
            value_format.format(height),
            xy=(bar.get_x() + bar.get_width() / 2, height),
            xytext=(0, 2),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=fontsize,
        )


def validate_columns(df):
    required_columns = {
        "scenario",
        "instances",
        "users",
        "requests",
        "failures",
        "p95_response_ms",
    }

    missing = required_columns - set(df.columns)

    if missing:
        raise SystemExit(
            f"Colunas ausentes no CSV consolidado: {sorted(missing)}"
        )


def add_failure_rate_column(df):
    df = df.copy()

    df["failure_rate_percent"] = np.where(
        df["requests"] > 0,
        (df["failures"] / df["requests"]) * 100,
        0,
    )

    return df


def generate_by_users(df, metric, ylabel):
    """
    Gera gráficos onde:
    - X = número de usuários
    - Y = métrica
    - Cada barra = quantidade de instâncias
    - Um gráfico por cenário
    """
    metric_dir = OUTPUT_USERS_DIR / metric
    metric_dir.mkdir(parents=True, exist_ok=True)

    for scenario in sorted(df["scenario"].unique(), key=get_scenario_order):
        data_scenario = df[df["scenario"] == scenario]

        users = sorted(data_scenario["users"].unique())
        instances = sorted(data_scenario["instances"].unique())

        x = np.arange(len(users))
        width = 0.8 / len(instances)

        plt.figure(figsize=(9, 5))

        for i, instance in enumerate(instances):
            values = []

            for user_count in users:
                row = data_scenario[
                    (data_scenario["users"] == user_count)
                    & (data_scenario["instances"] == instance)
                ]

                if row.empty:
                    values.append(0)
                else:
                    values.append(row.iloc[0][metric])

            offset = (i - (len(instances) - 1) / 2) * width

            bars = plt.bar(
                x + offset,
                values,
                width=width,
                label=f"{instance} instância(s)",
            )
            annotate_bars(bars)

        plt.title(f"{get_scenario_label(scenario)} - {ylabel} por usuários")
        plt.xlabel("Número de usuários")
        plt.ylabel(ylabel)
        plt.xticks(x, users)
        plt.legend(title="Instâncias")
        plt.grid(axis="y", alpha=0.3)
        plt.tight_layout()

        output_file = metric_dir / f"{safe_name(scenario)}_{metric}_por_usuarios.png"
        plt.savefig(output_file, dpi=150)
        plt.close()

        print(f"Gerado: {output_file}")


def generate_by_instances(df, metric, ylabel):
    """
    Gera gráficos onde:
    - X = quantidade de instâncias
    - Y = métrica
    - Cada barra = cenário
    - Um gráfico por número de usuários
    """
    metric_dir = OUTPUT_INSTANCES_DIR / metric
    metric_dir.mkdir(parents=True, exist_ok=True)

    for user_count in sorted(df["users"].unique()):
        data_users = df[df["users"] == user_count]

        instances = sorted(data_users["instances"].unique())
        scenarios = sorted(
            data_users["scenario"].drop_duplicates(),
            key=get_scenario_order,
        )

        x = np.arange(len(instances))
        width = 0.8 / len(scenarios)

        plt.figure(figsize=(10, 5))

        for i, scenario in enumerate(scenarios):
            values = []

            for instance in instances:
                row = data_users[
                    (data_users["instances"] == instance)
                    & (data_users["scenario"] == scenario)
                ]

                if row.empty:
                    values.append(0)
                else:
                    values.append(row.iloc[0][metric])

            offset = (i - (len(scenarios) - 1) / 2) * width

            bars = plt.bar(
                x + offset,
                values,
                width=width,
                label=get_scenario_label(scenario),
            )
            annotate_bars(bars)

        plt.title(f"{ylabel} por instância - {user_count} usuários")
        plt.xlabel("Quantidade de instâncias WordPress")
        plt.ylabel(ylabel)
        plt.xticks(x, instances)
        plt.legend(title="Cenário")
        plt.grid(axis="y", alpha=0.3)
        plt.tight_layout()

        output_file = metric_dir / f"{metric}_{user_count}users_por_instancia.png"
        plt.savefig(output_file, dpi=150)
        plt.close()

        print(f"Gerado: {output_file}")


def generate_combined_by_scenario_and_users(df, metric, ylabel):
    """
    Gera um unico arquivo consolidando os 4 graficos por cenario.

    Layout:
    - Eixos/subplots = cenarios
    - X = numero de usuarios
    - Barras = quantidade de instancias
    """
    scenarios = sorted(df["scenario"].unique(), key=get_scenario_order)
    users = sorted(df["users"].unique())
    instances = sorted(df["instances"].unique())

    if not scenarios or not users or not instances:
        return None

    ncols = 2
    nrows = int(np.ceil(len(scenarios) / ncols))

    fig, axes = plt.subplots(
        nrows=nrows,
        ncols=ncols,
        figsize=(10, 4.8 * nrows),
        squeeze=False,
    )
    axes_flat = axes.flatten()

    x = np.arange(len(users))
    width = 0.75 / len(instances)
    metric_max = df[metric].max()
    value_format = "{:.2f}" if metric == "failure_rate_percent" else "{:.0f}"

    for scenario_index, scenario in enumerate(scenarios):
        ax = axes_flat[scenario_index]
        data_scenario = df[df["scenario"] == scenario]

        for instance_index, instance in enumerate(instances):
            values = []

            for user_count in users:
                row = data_scenario[
                    (data_scenario["users"] == user_count)
                    & (data_scenario["instances"] == instance)
                ]

                if row.empty:
                    values.append(0)
                else:
                    values.append(row.iloc[0][metric])

            offset = (instance_index - (len(instances) - 1) / 2) * width
            bars = ax.bar(
                x + offset,
                values,
                width=width,
                label=f"{instance} instancia(s)",
            )
            annotate_axis_bars(ax, bars, value_format=value_format)

        ax.set_title(get_scenario_label(scenario))

        if scenario_index % ncols == 0:
            ax.set_ylabel(ylabel)

        ax.set_xlabel("Usuarios")
        ax.set_xticks(x)
        ax.set_xticklabels(users)
        ax.grid(axis="y", alpha=0.3)

        if metric_max > 0:
            ax.set_ylim(0, metric_max * 1.18)

    for ax in axes_flat[len(scenarios):]:
        ax.axis("off")

    handles, labels = axes_flat[0].get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        title="Instancias",
        loc="upper center",
        bbox_to_anchor=(0.5, 0.94),
        ncol=len(instances),
    )
    fig.suptitle(f"{ylabel} por cenario e usuarios", fontsize=16, y=0.99)
    fig.tight_layout(rect=(0, 0, 1, 0.88))

    output_file = OUTPUT_COMBINED_DIR / f"{metric}_por_cenario_e_usuarios.png"
    fig.savefig(output_file, dpi=150)
    plt.close(fig)

    print(f"Gerado consolidado: {output_file}")
    return output_file


def generate_combined_by_users_and_instances(df, metric, ylabel):
    """
    Gera um unico arquivo consolidando os graficos por quantidade de usuarios.

    Layout:
    - Colunas = numero de usuarios
    - X = quantidade de instancias
    - Barras = cenarios
    """
    users = sorted(df["users"].unique())
    instances = sorted(df["instances"].unique())
    scenarios = sorted(df["scenario"].unique(), key=get_scenario_order)

    if not users or not instances or not scenarios:
        return None

    fig, axes = plt.subplots(
        nrows=1,
        ncols=len(users),
        figsize=(5.2 * len(users), 4.8),
        squeeze=False,
    )

    x = np.arange(len(instances))
    width = 0.75 / len(scenarios)
    metric_max = df[metric].max()
    value_format = "{:.2f}" if metric == "failure_rate_percent" else "{:.0f}"

    for col_index, user_count in enumerate(users):
        ax = axes[0][col_index]
        data_users = df[df["users"] == user_count]

        for scenario_index, scenario in enumerate(scenarios):
            values = []

            for instance in instances:
                row = data_users[
                    (data_users["instances"] == instance)
                    & (data_users["scenario"] == scenario)
                ]

                if row.empty:
                    values.append(0)
                else:
                    values.append(row.iloc[0][metric])

            offset = (scenario_index - (len(scenarios) - 1) / 2) * width
            bars = ax.bar(
                x + offset,
                values,
                width=width,
                label=get_scenario_label(scenario),
            )
            annotate_axis_bars(ax, bars, value_format=value_format)

        ax.set_title(f"{user_count} usuarios")

        if col_index == 0:
            ax.set_ylabel(ylabel)

        ax.set_xlabel("Instancias WordPress")
        ax.set_xticks(x)
        ax.set_xticklabels(instances)
        ax.grid(axis="y", alpha=0.3)

        if metric_max > 0:
            ax.set_ylim(0, metric_max * 1.18)

    handles, labels = axes[0][0].get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        title="Cenario",
        loc="upper center",
        bbox_to_anchor=(0.5, 0.94),
        ncol=len(scenarios),
    )
    fig.suptitle(f"{ylabel} por instancias e usuarios", fontsize=16, y=0.99)
    fig.tight_layout(rect=(0, 0, 1, 0.88))

    output_file = OUTPUT_COMBINED_DIR / f"{metric}_por_instancias_e_usuarios.png"
    fig.savefig(output_file, dpi=150)
    plt.close(fig)

    print(f"Gerado consolidado: {output_file}")
    return output_file


def main():
    if not INPUT_FILE.exists():
        raise SystemExit(
            f"Arquivo não encontrado: {INPUT_FILE}\n"
            "Execute primeiro: python consolidate_results.py"
        )

    df = pd.read_csv(INPUT_FILE)
    validate_columns(df)
    df = add_failure_rate_column(df)

    metrics = {
        "p95_response_ms": "P95 do tempo de resposta (ms)",
        "failure_rate_percent": "Taxa de falhas (%)",
    }

    for metric, ylabel in metrics.items():
        generate_by_users(df, metric, ylabel)
        generate_by_instances(df, metric, ylabel)

    for metric, ylabel in metrics.items():
        generate_combined_by_scenario_and_users(df, metric, ylabel)
        generate_combined_by_users_and_instances(df, metric, ylabel)

    print("\nTodos os gráficos foram gerados em:")
    print(OUTPUT_BASE_DIR)


if __name__ == "__main__":
    main()
