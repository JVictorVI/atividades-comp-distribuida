import csv
import json
import os
from html import escape
from pathlib import Path


RESULTS_DIR = Path(os.getenv("LOCUST_RESULTS_DIR", "results"))
CHARTS_DIR = Path(os.getenv("LOCUST_CHARTS_DIR")) if os.getenv("LOCUST_CHARTS_DIR") else RESULTS_DIR / "charts"

TECHNOLOGIES = [
    {"label": "REST", "slug": "rest"},
    {"label": "GraphQL", "slug": "graphql"},
    {"label": "SOAP", "slug": "soap"},
    {"label": "gRPC", "slug": "grpc"},
]

def scenario_name(users):
    names = {
        50: ("Carga baixa", "carga-baixa"),
        250: ("Carga média", "carga-media"),
        500: ("Carga alta", "carga-alta"),
    }
    return names.get(users, (f"{users} usuários", f"usuarios-{users}"))


def configured_scenarios():
    users_list = [
        int(value.strip())
        for value in os.getenv("LOCUST_USER_COUNTS", "50,250,500").split(",")
        if value.strip()
    ]
    scenarios = []
    for users in users_list:
        label, slug = scenario_name(users)
        scenarios.append({"label": label, "slug": slug, "users": users})
    return scenarios


SCENARIOS = configured_scenarios()

WORKLOADS = ["catalogo-leitura", "relacionamentos-leitura", "usuarios-escrita"]

COLORS = {
    "REST": "#2563eb",
    "GraphQL": "#d946ef",
    "SOAP": "#ea580c",
    "gRPC": "#16a34a",
}


def number(value):
    try:
        return float(value or 0)
    except ValueError:
        return 0.0


def read_locust_stats(scenario, technology):
    path = RESULTS_DIR / f"locust-{technology['slug']}-{scenario['slug']}-u{scenario['users']}_stats.csv"
    if not path.exists():
        raise FileNotFoundError(
            f"Arquivo Locust não encontrado: {path}. "
            "Execute a bateria de testes antes de gerar os gráficos."
        )

    grouped = {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            name = row.get("Name", "")
            prefix = f"{technology['label']}/"
            if not name.startswith(prefix):
                continue
            workload = name.split("/", 1)[1]
            if workload not in WORKLOADS:
                continue

            current = grouped.setdefault(
                workload,
                {
                    "scenario": scenario["slug"],
                    "scenarioLabel": scenario["label"],
                    "users": scenario["users"],
                    "technology": technology["label"],
                    "workload": workload,
                    "requestCount": 0,
                    "failureCount": 0,
                    "throughputRps": 0.0,
                    "p95LatencyMs": 0.0,
                },
            )
            current["requestCount"] += int(number(row.get("Request Count")))
            current["failureCount"] += int(number(row.get("Failure Count")))
            current["throughputRps"] += number(row.get("Requests/s"))
            current["p95LatencyMs"] = max(current["p95LatencyMs"], number(row.get("95%")))

    return grouped


def collect_rows():
    rows = []
    for scenario in SCENARIOS:
        for technology in TECHNOLOGIES:
            stats = read_locust_stats(scenario, technology)
            for workload in WORKLOADS:
                if workload not in stats:
                    raise ValueError(f"Dados ausentes para {technology['label']}/{workload} em {scenario['slug']}")
                row = stats[workload]
                row["throughputRps"] = round(row["throughputRps"], 2)
                row["p95LatencyMs"] = round(row["p95LatencyMs"], 2)
                row["errorRatePercent"] = (
                    0
                    if row["requestCount"] == 0
                    else round((row["failureCount"] / row["requestCount"]) * 100, 4)
                )
                rows.append(row)
    return rows


def format_value(metric, value):
    if metric == "throughputRps":
        return f"{value:.1f}"
    if metric == "errorRatePercent":
        return f"{value:.2f}%"
    return str(round(value))


def format_axis_tick(metric, value):
    if metric == "errorRatePercent":
        return f"{value:.2f}" if value < 10 else f"{value:.1f}"
    return str(round(value))


def make_chart(scenario, rows, metric, title, unit):
    selected_rows = [row for row in rows if row["scenario"] == scenario["slug"]]
    width = 1040
    height = 580
    margin = {"top": 72, "right": 38, "bottom": 126, "left": 92}
    plot_width = width - margin["left"] - margin["right"]
    plot_height = height - margin["top"] - margin["bottom"]
    max_raw_value = max(row[metric] for row in selected_rows)
    max_value = max(1, max_raw_value * 1.14)
    group_width = plot_width / len(WORKLOADS)
    bar_gap = 9
    bar_width = (group_width - 48 - bar_gap * (len(TECHNOLOGIES) - 1)) / len(TECHNOLOGIES)

    def y(value):
        return margin["top"] + plot_height - (value / max_value) * plot_height

    axis_ticks = [max_value * ratio for ratio in [0, 0.25, 0.5, 0.75, 1]]

    bars = []
    for workload_index, workload in enumerate(WORKLOADS):
        x_base = margin["left"] + workload_index * group_width + 24
        for technology_index, technology in enumerate(TECHNOLOGIES):
            row = next(
                item
                for item in selected_rows
                if item["workload"] == workload and item["technology"] == technology["label"]
            )
            value = row[metric]
            bar_x = x_base + technology_index * (bar_width + bar_gap)
            bar_y = y(value)
            bar_height = margin["top"] + plot_height - bar_y
            bars.append(
                f"""
        <rect x="{bar_x:.1f}" y="{bar_y:.1f}" width="{bar_width:.1f}" height="{bar_height:.1f}" fill="{COLORS[technology['label']]}"/>
        <text x="{bar_x + bar_width / 2:.1f}" y="{bar_y - 7:.1f}" text-anchor="middle" font-size="11" fill="#111827">{format_value(metric, value)}</text>"""
            )

    x_labels = []
    for index, workload in enumerate(WORKLOADS):
        x = margin["left"] + index * group_width + group_width / 2
        x_labels.append(
            f'<text x="{x:.1f}" y="{height - 78}" text-anchor="middle" font-size="13" fill="#111827">{escape(workload)}</text>'
        )

    y_ticks = []
    for tick in axis_ticks:
        tick_y = y(tick)
        y_ticks.append(
            f"""
      <line x1="{margin['left']}" x2="{width - margin['right']}" y1="{tick_y:.1f}" y2="{tick_y:.1f}" stroke="#e5e7eb"/>
      <text x="{margin['left'] - 12}" y="{tick_y + 4:.1f}" text-anchor="end" font-size="12" fill="#4b5563">{format_axis_tick(metric, tick)}</text>"""
        )

    legend = []
    for index, technology in enumerate(TECHNOLOGIES):
        x = margin["left"] + index * 132
        y_legend = height - 34
        legend.append(
            f"""
      <rect x="{x}" y="{y_legend - 12}" width="14" height="14" fill="{COLORS[technology['label']]}"/>
      <text x="{x + 22}" y="{y_legend}" font-size="13" fill="#111827">{technology['label']}</text>"""
        )

    subtitle = f"{scenario['label']} - {scenario['users']} usuários virtuais - unidade: {unit}"
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{escape(title + ' - ' + scenario['label'])}">
  <rect width="100%" height="100%" fill="#ffffff"/>
  <text x="{margin['left']}" y="38" font-size="22" font-weight="700" fill="#111827">{escape(title)}</text>
  <text x="{margin['left']}" y="61" font-size="13" fill="#4b5563">{escape(subtitle)}</text>
  {''.join(y_ticks)}
  <line x1="{margin['left']}" x2="{margin['left']}" y1="{margin['top']}" y2="{margin['top'] + plot_height}" stroke="#111827"/>
  <line x1="{margin['left']}" x2="{width - margin['right']}" y1="{margin['top'] + plot_height}" y2="{margin['top'] + plot_height}" stroke="#111827"/>
  {''.join(bars)}
  {''.join(x_labels)}
  {''.join(legend)}
</svg>"""


def write_summary(rows):
    headers = [
        "scenario",
        "scenarioLabel",
        "users",
        "technology",
        "workload",
        "requestCount",
        "failureCount",
        "errorRatePercent",
        "throughputRps",
        "p95LatencyMs",
    ]
    with (RESULTS_DIR / "locust-summary.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)
    (RESULTS_DIR / "locust-summary.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")


def main():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    rows = collect_rows()
    write_summary(rows)

    generated = []
    for scenario in SCENARIOS:
        outputs = [
            (
                CHARTS_DIR / f"locust-throughput-{scenario['slug']}-u{scenario['users']}.svg",
                "throughputRps",
                "Vazão por tecnologia e cenário",
                "req/s",
            ),
            (
                CHARTS_DIR / f"locust-p95-latency-{scenario['slug']}-u{scenario['users']}.svg",
                "p95LatencyMs",
                "Latência p95 por tecnologia e cenário",
                "ms",
            ),
            (
                CHARTS_DIR / f"locust-error-rate-{scenario['slug']}-u{scenario['users']}.svg",
                "errorRatePercent",
                "Taxa de erros por tecnologia e cenário",
                "%",
            ),
        ]
        for path, metric, title, unit in outputs:
            path.write_text(make_chart(scenario, rows, metric, title, unit), encoding="utf-8")
            generated.append(path)

    print("Gráficos Locust gerados:")
    for path in generated:
        print(path)
    print("Resumo agregado:")
    print(RESULTS_DIR / "locust-summary.csv")
    print(RESULTS_DIR / "locust-summary.json")


if __name__ == "__main__":
    main()
