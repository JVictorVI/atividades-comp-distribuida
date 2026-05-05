from pathlib import Path
import pandas as pd
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

OUTPUT_USERS_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_INSTANCES_DIR.mkdir(parents=True, exist_ok=True)


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

        print(f"✔ Gerado: {output_file}")


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

        print(f"✔ Gerado: {output_file}")


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

    print("\nTodos os gráficos foram gerados em:")
    print(OUTPUT_BASE_DIR)


if __name__ == "__main__":
    main()
