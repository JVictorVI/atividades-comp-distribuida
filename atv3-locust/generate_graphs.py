from pathlib import Path
import re
import pandas as pd
import matplotlib.pyplot as plt

RESULTS_DIR = Path("results")
GRAPHS_DIR = Path("graphs")

RESULTS_DIR.mkdir(exist_ok=True)
GRAPHS_DIR.mkdir(exist_ok=True)

# Aceita nomes como:
# result_1inst_10users_stats.csv
# cenario_1_1wp_10users_stats.csv
# imagem_1mb_3wp_100users_stats.csv
patterns = [
    re.compile(r"(?P<scenario>.+)_(?P<instances>\d+)wp_(?P<users>\d+)users_stats\.csv"),
    re.compile(r"(?P<scenario>.+)_(?P<instances>\d+)inst_(?P<users>\d+)users_stats\.csv"),
    re.compile(r"result_(?P<instances>\d+)inst_(?P<users>\d+)users_stats\.csv"),
]

rows = []

def parse_filename(filename: str):
    for pattern in patterns:
        match = pattern.match(filename)
        if match:
            data = match.groupdict()
            return {
                "scenario": data.get("scenario", "todos_cenarios"),
                "instances": int(data["instances"]),
                "users": int(data["users"]),
            }
    return None


for file in RESULTS_DIR.glob("*_stats.csv"):
    parsed = parse_filename(file.name)

    if not parsed:
        print(f"Ignorando arquivo com nome fora do padrão: {file.name}")
        continue

    df = pd.read_csv(file)

    if df.empty:
        print(f"Ignorando CSV vazio: {file.name}")
        continue

    # Locust geralmente cria uma linha Aggregated
    total = df[df["Name"] == "Aggregated"]

    # Se não tiver Aggregated, pega a última linha
    if total.empty:
        total = df.tail(1)

    item = total.iloc[0].to_dict()

    rows.append({
        "scenario": parsed["scenario"],
        "instances": parsed["instances"],
        "users": parsed["users"],
        "requests": item.get("Request Count", 0),
        "failures": item.get("Failure Count", 0),
        "avg_response_ms": item.get("Average Response Time", 0),
        "median_response_ms": item.get("Median Response Time", 0),
        "min_response_ms": item.get("Min Response Time", 0),
        "max_response_ms": item.get("Max Response Time", 0),
        "p95_response_ms": item.get("95%", 0),
        "p99_response_ms": item.get("99%", 0),
        "rps": item.get("Requests/s", 0),
        "failures_s": item.get("Failures/s", 0),
    })


if not rows:
    raise SystemExit(
        "Nenhum CSV válido do Locust encontrado em results/. "
        "Verifique se existem arquivos terminando com _stats.csv."
    )

summary = pd.DataFrame(rows)
summary = summary.sort_values(["scenario", "instances", "users"])

summary_path = RESULTS_DIR / "summary.csv"
summary.to_csv(summary_path, index=False)

print("\nResumo dos resultados:")
print(summary)

metrics = {
    "avg_response_ms": "Tempo médio de resposta (ms)",
    "median_response_ms": "Mediana do tempo de resposta (ms)",
    "p95_response_ms": "Percentil 95 de resposta (ms)",
    "p99_response_ms": "Percentil 99 de resposta (ms)",
    "rps": "Requisições por segundo",
    "failures": "Falhas",
}

for scenario in summary["scenario"].unique():
    data_scenario = summary[summary["scenario"] == scenario]

    safe_scenario = (
        str(scenario)
        .replace(" ", "_")
        .replace("/", "_")
        .replace("\\", "_")
        .replace(":", "_")
    )

    # Gráficos por usuários
    for metric, ylabel in metrics.items():
        plt.figure(figsize=(9, 5))

        for instances in sorted(data_scenario["instances"].unique()):
            data_line = data_scenario[data_scenario["instances"] == instances]
            data_line = data_line.sort_values("users")

            plt.plot(
                data_line["users"],
                data_line[metric],
                marker="o",
                label=f"{instances} instância(s)"
            )

        plt.title(f"{scenario} - {ylabel} por usuários")
        plt.xlabel("Usuários simultâneos")
        plt.ylabel(ylabel)
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()

        output = GRAPHS_DIR / f"{safe_scenario}_{metric}_por_usuarios.png"
        plt.savefig(output, dpi=150)
        plt.close()

    # Gráficos por instâncias
    for metric, ylabel in metrics.items():
        plt.figure(figsize=(9, 5))

        for users in sorted(data_scenario["users"].unique()):
            data_line = data_scenario[data_scenario["users"] == users]
            data_line = data_line.sort_values("instances")

            plt.plot(
                data_line["instances"],
                data_line[metric],
                marker="o",
                label=f"{users} usuários"
            )

        plt.title(f"{scenario} - {ylabel} por instâncias")
        plt.xlabel("Quantidade de instâncias WordPress")
        plt.ylabel(ylabel)
        plt.xticks(sorted(data_scenario["instances"].unique()))
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()

        output = GRAPHS_DIR / f"{safe_scenario}_{metric}_por_instancias.png"
        plt.savefig(output, dpi=150)
        plt.close()

print(f"\nResumo salvo em: {summary_path}")
print(f"Gráficos salvos em: {GRAPHS_DIR}/")