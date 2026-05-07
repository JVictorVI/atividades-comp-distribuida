from pathlib import Path
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT_DIR / "results"
CONSOLIDATED_DIR = ROOT_DIR / "consolidated"
CONSOLIDATED_DIR.mkdir(exist_ok=True)

rows = []
link_count_rows = []

for stats_file in RESULTS_DIR.glob("*_stats.csv"):
    name = stats_file.stem.replace("_stats", "")
    parts = name.split("_")

    if len(parts) < 3:
        continue

    language = parts[0]
    cache_mode = parts[1]
    users = int(parts[2])

    df = pd.read_csv(stats_file)

    aggregated = df[df["Name"] == "Aggregated"]
    if aggregated.empty:
        aggregated = df.tail(1)

    row = aggregated.iloc[0]

    rows.append({
        "scenario": f"{language}_{cache_mode}",
        "language": language,
        "cache": "com_cache" if cache_mode == "cache" else "sem_cache",
        "users": users,
        "requests": row.get("Request Count", 0),
        "failures": row.get("Failure Count", 0),
        "failure_rate_percent": (
            (row.get("Failure Count", 0) / row.get("Request Count", 0)) * 100
            if row.get("Request Count", 0)
            else 0
        ),
        "median_response_ms": row.get("Median Response Time", 0),
        "average_response_ms": row.get("Average Response Time", 0),
        "min_response_ms": row.get("Min Response Time", 0),
        "max_response_ms": row.get("Max Response Time", 0),
        "p95_response_ms": row.get("95%", 0),
        "p99_response_ms": row.get("99%", 0),
        "rps": row.get("Requests/s", 0),
        "failures_s": row.get("Failures/s", 0),
    })

for link_counts_file in RESULTS_DIR.glob("*_link_counts.csv"):
    name = link_counts_file.stem.replace("_link_counts", "")
    parts = name.split("_")

    if len(parts) < 3:
        continue

    language = parts[0]
    cache_mode = parts[1]
    users = int(parts[2])

    df_links = pd.read_csv(link_counts_file)

    for _, link_row in df_links.iterrows():
        link_count_rows.append({
            "scenario": f"{language}_{cache_mode}",
            "language": language,
            "cache": "com_cache" if cache_mode == "cache" else "sem_cache",
            "users": users,
            "url": link_row.get("url", ""),
            "extracted_links": link_row.get("extracted_links", 0),
        })

result = pd.DataFrame(rows)
link_counts_result = pd.DataFrame(link_count_rows)

if result.empty:
    print("Nenhum CSV encontrado em results/.")
else:
    result = result.sort_values(["language", "cache", "users"])
    output_csv = CONSOLIDATED_DIR / "resultados_consolidados.csv"
    output_xlsx = CONSOLIDATED_DIR / "resultados_consolidados.xlsx"

    result.to_csv(output_csv, index=False)
    result.to_excel(output_xlsx, index=False)

    print(f"CSV consolidado salvo em: {output_csv}")
    print(f"Planilha Excel salva em: {output_xlsx}")

    if link_counts_result.empty:
        print("Nenhum CSV de links extraidos encontrado em results/.")
    else:
        link_counts_result = link_counts_result.sort_values(["language", "cache", "users", "url"])
        link_counts_csv = CONSOLIDATED_DIR / "links_extraidos_por_url.csv"
        link_counts_result.to_csv(link_counts_csv, index=False)
        print(f"CSV de links extraidos salvo em: {link_counts_csv}")
