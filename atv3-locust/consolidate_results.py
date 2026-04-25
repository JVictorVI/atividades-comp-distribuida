from pathlib import Path
import re
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
RESULTS_DIR = BASE_DIR / "results"
OUTPUT_DIR = BASE_DIR / "consolidated"

OUTPUT_DIR.mkdir(exist_ok=True)

patterns = [
    re.compile(r"(?P<scenario>.+)_(?P<instances>\d+)wp_(?P<users>\d+)users_stats\.csv"),
    re.compile(r"(?P<scenario>.+)_(?P<instances>\d+)inst_(?P<users>\d+)users_stats\.csv"),
    re.compile(r"result_(?P<instances>\d+)inst_(?P<users>\d+)users_stats\.csv"),
]


def parse_filename(filename):
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


rows = []

for file in RESULTS_DIR.glob("*_stats.csv"):
    parsed = parse_filename(file.name)

    if not parsed:
        print(f"Ignorando arquivo fora do padrão: {file.name}")
        continue

    df = pd.read_csv(file)

    if df.empty:
        print(f"Ignorando CSV vazio: {file.name}")
        continue

    aggregated = df[df["Name"] == "Aggregated"]

    if aggregated.empty:
        aggregated = df.tail(1)

    item = aggregated.iloc[0]

    rows.append({
        "arquivo": file.name,
        "cenario": parsed["scenario"],
        "instancias_wordpress": parsed["instances"],
        "usuarios": parsed["users"],
        "total_requisicoes": item.get("Request Count", 0),
        "falhas": item.get("Failure Count", 0),
        "taxa_falhas_s": item.get("Failures/s", 0),
        "tempo_medio_ms": item.get("Average Response Time", 0),
        "tempo_mediano_ms": item.get("Median Response Time", 0),
        "tempo_minimo_ms": item.get("Min Response Time", 0),
        "tempo_maximo_ms": item.get("Max Response Time", 0),
        "percentil_50_ms": item.get("50%", 0),
        "percentil_75_ms": item.get("75%", 0),
        "percentil_95_ms": item.get("95%", 0),
        "percentil_99_ms": item.get("99%", 0),
        "requisicoes_por_segundo": item.get("Requests/s", 0),
    })


if not rows:
    raise SystemExit(
        "Nenhum resultado encontrado. Verifique se existem arquivos *_stats.csv na pasta results."
    )

summary = pd.DataFrame(rows)
summary = summary.sort_values(["cenario", "instancias_wordpress", "usuarios"])

summary_csv = OUTPUT_DIR / "resultados_consolidados.csv"
summary_xlsx = OUTPUT_DIR / "resultados_consolidados.xlsx"

summary.to_csv(summary_csv, index=False, encoding="utf-8-sig")
summary.to_excel(summary_xlsx, index=False)

print("\nResultados consolidados:")
print(summary)

print(f"\nCSV salvo em: {summary_csv}")
print(f"Excel salvo em: {summary_xlsx}")