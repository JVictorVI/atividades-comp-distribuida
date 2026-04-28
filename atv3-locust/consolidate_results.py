from pathlib import Path
import re
import pandas as pd

RESULTS_DIR = Path("results")
CONSOLIDATED_DIR = Path("consolidated")

CONSOLIDATED_DIR.mkdir(exist_ok=True)

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
        continue

    df = pd.read_csv(file)

    if df.empty:
        continue

    total = df[df["Name"] == "Aggregated"]

    if total.empty:
        total = df.tail(1)

    item = total.iloc[0]

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
    raise SystemExit("Nenhum CSV encontrado em results/")

summary = pd.DataFrame(rows)
summary = summary.sort_values(["scenario", "instances", "users"])

output = CONSOLIDATED_DIR / "resultados_consolidados.csv"
summary.to_csv(output, index=False, encoding="utf-8-sig")

print("CSV consolidado gerado em:", output)