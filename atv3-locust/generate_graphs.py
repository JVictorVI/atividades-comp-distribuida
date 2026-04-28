from pathlib import Path
import re
import pandas as pd
import matplotlib.pyplot as plt

RESULTS_DIR = Path("results")
GRAPHS_DIR = Path("graphs")

GRAPHS_USERS_DIR = GRAPHS_DIR / "por_usuarios"
GRAPHS_INSTANCES_DIR = GRAPHS_DIR / "por_instancias"

RESULTS_DIR.mkdir(exist_ok=True)
GRAPHS_USERS_DIR.mkdir(parents=True, exist_ok=True)
GRAPHS_INSTANCES_DIR.mkdir(parents=True, exist_ok=True)

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


def safe_name(value):
    return (
        str(value)
        .replace(" ", "_")
        .replace("/", "_")
        .replace("\\", "_")
        .replace(":", "_")
    )


# =========================
# Leitura dos CSVs
# =========================
for file in RESULTS_DIR.glob("*_stats.csv"):
    parsed = parse_filename(file.name)

    if not parsed:
        print(f"Ignorando arquivo fora do padrao: {file.name}")
        continue

    df = pd.read_csv(file)

    if df.empty:
        print(f"Ignorando CSV vazio: {file.name}")
        continue

    total = df[df["Name"] == "Aggregated"]

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
        "Nenhum CSV valido encontrado em results/. Verifique os arquivos *_stats.csv."
    )

summary = pd.DataFrame(rows)
summary = summary.sort_values(["scenario", "instances", "users"])

summary_path = RESULTS_DIR / "summary.csv"
summary.to_csv(summary_path, index=False)

print("\nResumo dos resultados:")
print(summary)

# =========================
# Métricas
# =========================
metrics = {
    "avg_response_ms": "Tempo medio de resposta (ms)",
    "median_response_ms": "Mediana do tempo de resposta (ms)",
    "p95_response_ms": "Percentil 95 (ms)",
    "p99_response_ms": "Percentil 99 (ms)",
    "rps": "Requisicoes por segundo",
    "failures": "Falhas",
}

# =========================
# Geração dos gráficos
# =========================
for scenario in summary["scenario"].unique():
    data_scenario = summary[summary["scenario"] == scenario]
    safe_scenario = safe_name(scenario)

    # ----------- POR USUÁRIOS -----------
    for metric, ylabel in metrics.items():
        metric_dir = GRAPHS_USERS_DIR / metric
        metric_dir.mkdir(parents=True, exist_ok=True)

        plt.figure(figsize=(9, 5))

        for instances in sorted(data_scenario["instances"].unique()):
            data_line = data_scenario[data_scenario["instances"] == instances]
            data_line = data_line.sort_values("users")

            plt.plot(
                data_line["users"],
                data_line[metric],
                marker="o",
                label=f"{instances} instancia(s)"
            )

        plt.title(f"{scenario} - {ylabel} por usuarios")
        plt.xlabel("Usuarios simultaneos")
        plt.ylabel(ylabel)
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()

        output = metric_dir / f"{safe_scenario}_{metric}_usuarios.png"
        plt.savefig(output, dpi=150)
        plt.close()

    # ----------- POR INSTÂNCIAS -----------
    for metric, ylabel in metrics.items():
        metric_dir = GRAPHS_INSTANCES_DIR / metric
        metric_dir.mkdir(parents=True, exist_ok=True)

        plt.figure(figsize=(9, 5))

        for users in sorted(data_scenario["users"].unique()):
            data_line = data_scenario[data_scenario["users"] == users]
            data_line = data_line.sort_values("instances")

            plt.plot(
                data_line["instances"],
                data_line[metric],
                marker="o",
                label=f"{users} usuarios"
            )

        plt.title(f"{scenario} - {ylabel} por instancias")
        plt.xlabel("Quantidade de instancias WordPress")
        plt.ylabel(ylabel)
        plt.xticks(sorted(data_scenario["instances"].unique()))
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()

        output = metric_dir / f"{safe_scenario}_{metric}_instancias.png"
        plt.savefig(output, dpi=150)
        plt.close()

print(f"\nResumo salvo em: {summary_path}")
print(f"Graficos por usuarios: {GRAPHS_USERS_DIR}/")
print(f"Graficos por instancias: {GRAPHS_INSTANCES_DIR}/")