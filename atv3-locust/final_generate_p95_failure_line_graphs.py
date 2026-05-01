from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

INPUT_FILE = Path("consolidated/resultados_consolidados.csv")
OUTPUT_DIR = Path("graphs/linhas_p95_falhas")

DIR_USERS = OUTPUT_DIR / "por_usuarios"
DIR_INSTANCES = OUTPUT_DIR / "por_instancias"

DIR_USERS.mkdir(parents=True, exist_ok=True)
DIR_INSTANCES.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(INPUT_FILE)

# Criar taxa de falha (%)
df["failure_rate_pct"] = (df["failures"] / df["requests"]) * 100
df["failure_rate_pct"] = df["failure_rate_pct"].fillna(0)

metrics = {
    "p95_response_ms": "P95 (ms)",
    "failure_rate_pct": "Taxa de falha (%)",
}

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


# =========================
# GRÁFICOS POR USUÁRIOS
# X = usuários
# linhas = instâncias
# =========================
for scenario in df["scenario"].unique():
    data_scenario = df[df["scenario"] == scenario]

    for metric, ylabel in metrics.items():
        plt.figure(figsize=(9, 5))

        for inst in sorted(data_scenario["instances"].unique()):
            data_line = data_scenario[data_scenario["instances"] == inst]
            data_line = data_line.sort_values("users")

            plt.plot(
                data_line["users"],
                data_line[metric],
                marker="o",
                linewidth=2,
                label=f"{inst} instância(s)"
            )

        plt.title(f"{scenario_labels.get(scenario, scenario)} - {ylabel} por usuários")
        plt.xlabel("Número de usuários")
        plt.ylabel(ylabel)
        plt.grid(True, alpha=0.3)
        plt.legend()
        plt.tight_layout()

        output = DIR_USERS / f"{scenario}_{metric}_usuarios_linha.png"
        plt.savefig(output, dpi=150)
        plt.close()

        print(f"✔ Gerado: {output}")


# =========================
# GRÁFICOS POR INSTÂNCIAS
# X = instâncias
# linhas = cenários
# =========================
for metric, ylabel in metrics.items():
    for users in sorted(df["users"].unique()):
        data_users = df[df["users"] == users]

        plt.figure(figsize=(9, 5))

        for scenario in data_users["scenario"].unique():
            data_line = data_users[data_users["scenario"] == scenario]
            data_line = data_line.sort_values("instances")

            plt.plot(
                data_line["instances"],
                data_line[metric],
                marker="o",
                linewidth=2,
                label=scenario_labels.get(scenario, scenario)
            )

        plt.title(f"{ylabel} por instâncias - {users} usuários")
        plt.xlabel("Quantidade de instâncias WordPress")
        plt.ylabel(ylabel)
        plt.xticks(sorted(data_users["instances"].unique()))
        plt.grid(True, alpha=0.3)
        plt.legend(title="Cenário")
        plt.tight_layout()

        output = DIR_INSTANCES / f"{metric}_{users}users_instancias_linha.png"
        plt.savefig(output, dpi=150)
        plt.close()

        print(f"✔ Gerado: {output}")


print("\nTodos os gráficos de linha foram gerados!")