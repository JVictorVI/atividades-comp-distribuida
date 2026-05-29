import csv
import json
import os
from html import escape
from pathlib import Path


DEFAULT_RESULTS_DIR = Path("results")
RESULTS_DIR_ENV = os.getenv("LOCUST_RESULTS_DIR")
CHARTS_DIR_ENV = os.getenv("LOCUST_CHARTS_DIR")

TECHNOLOGIES = [
    {"label": "REST", "slug": "rest"},
    {"label": "GraphQL", "slug": "graphql"},
    {"label": "SOAP", "slug": "soap"},
    {"label": "gRPC", "slug": "grpc"},
]

LANGUAGES = [
    {"label": "Python", "slug": "python"},
    {"label": "JavaScript", "slug": "javascript"},
]

def scenario_name(users):
    names = {
        50: ("Carga leve", "carga-leve", "leve", ["carga-baixa"]),
        250: ("Carga média", "carga-media", "medio", []),
        500: ("Carga alta", "carga-alta", "alto", []),
    }
    return names.get(users, (f"{users} usuários", f"usuarios-{users}", f"usuarios-{users}", []))


def configured_scenarios():
    users_list = [
        int(value.strip())
        for value in os.getenv("LOCUST_USER_COUNTS", "50,250,500").split(",")
        if value.strip()
    ]
    scenarios = []
    for users in users_list:
        label, slug, folder, aliases = scenario_name(users)
        scenarios.append({"label": label, "slug": slug, "folder": folder, "aliases": aliases, "users": users})
    return scenarios


SCENARIOS = configured_scenarios()

WORKLOAD_ORDER = [
    "listar-usuarios",
    "listar-musicas",
    "listar-playlists-usuario",
    "listar-musicas-playlist",
    "listar-playlists-musica",
]

WORKLOAD_LABELS = {
    "listar-usuarios": ("Usuários",),
    "listar-musicas": ("Músicas",),
    "listar-playlists-usuario": ("Playlists", "do usuário"),
    "listar-musicas-playlist": ("Músicas", "da playlist"),
    "listar-playlists-musica": ("Playlists", "com música"),
}

COLORS = {
    "REST": "#2563eb",
    "GraphQL": "#d946ef",
    "SOAP": "#ea580c",
    "gRPC": "#16a34a",
}

LANGUAGE_COLORS = {
    "Python": "#2563eb",
    "JavaScript": "#f59e0b",
}


def number(value):
    try:
        return float(value or 0)
    except ValueError:
        return 0.0


def locust_stats_path(results_dir, scenario, technology):
    names = [scenario["slug"], *scenario.get("aliases", [])]
    for slug in names:
        path = results_dir / f"locust-{technology['slug']}-{slug}-u{scenario['users']}_stats.csv"
        if path.exists():
            return path
    return None


def read_locust_stats(results_dir, scenario, technology):
    path = locust_stats_path(results_dir, scenario, technology)
    if path is None:
        return {}

    grouped = {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            name = row.get("Name", "")
            prefix = f"{technology['label']}/"
            if not name.startswith(prefix):
                continue
            workload = name.split("/", 1)[1]
            current = grouped.setdefault(
                workload,
                {
                    "scenario": scenario["slug"],
                    "scenarioLabel": scenario["label"],
                    "users": scenario["users"],
                    "technology": technology["label"],
                    "workload": workload,
                    "requestCount": 0,
                    "throughputRps": 0.0,
                    "p95LatencyMs": 0.0,
                },
            )
            current["requestCount"] += int(number(row.get("Request Count")))
            current["throughputRps"] += number(row.get("Requests/s"))
            current["p95LatencyMs"] = max(current["p95LatencyMs"], number(row.get("95%")))

    return grouped


def collect_rows(results_dir):
    rows = []
    for scenario in SCENARIOS:
        for technology in TECHNOLOGIES:
            stats = read_locust_stats(results_dir, scenario, technology)
            for row in stats.values():
                row["throughputRps"] = round(row["throughputRps"], 2)
                row["p95LatencyMs"] = round(row["p95LatencyMs"], 2)
                rows.append(row)
    return rows


def collect_language_rows(results_root=DEFAULT_RESULTS_DIR):
    rows = []
    for language in LANGUAGES:
        results_dir = results_root / language["slug"]
        if not has_locust_stats(results_dir):
            continue
        for row in collect_rows(results_dir):
            row["language"] = language["label"]
            row["languageSlug"] = language["slug"]
            rows.append(row)
    return rows


def average_metric(total, count):
    return round(total / count, 2) if count else 0.0


def aggregate_technology_rows(rows, scenario):
    grouped = {}
    for row in rows:
        if row["scenario"] != scenario["slug"]:
            continue

        current = grouped.setdefault(
            row["technology"],
            {
                "technology": row["technology"],
                "requestCount": 0,
                "throughputTotal": 0.0,
                "p95Total": 0.0,
                "workloadCount": 0,
            },
        )
        current["requestCount"] += row["requestCount"]
        current["throughputTotal"] += row["throughputRps"]
        current["p95Total"] += row["p95LatencyMs"]
        current["workloadCount"] += 1

    for current in grouped.values():
        count = current["workloadCount"]
        current["throughputRps"] = average_metric(current["throughputTotal"], count)
        current["p95LatencyMs"] = average_metric(current["p95Total"], count)

    return grouped


def workload_label_lines(workload):
    return WORKLOAD_LABELS.get(workload, (workload,))


def ordered_workloads(rows):
    present = {row["workload"] for row in rows}
    ordered = [workload for workload in WORKLOAD_ORDER if workload in present]
    ordered.extend(sorted(present - set(ordered)))
    return ordered


def aggregate_comparison_rows(rows, scenario):
    grouped = {}
    for row in rows:
        if row["scenario"] != scenario["slug"]:
            continue

        key = (row["language"], row["technology"])
        current = grouped.setdefault(
            key,
            {
                "language": row["language"],
                "technology": row["technology"],
                "requestCount": 0,
                "throughputTotal": 0.0,
                "p95Total": 0.0,
                "workloadCount": 0,
            },
        )
        current["requestCount"] += row["requestCount"]
        current["throughputTotal"] += row["throughputRps"]
        current["p95Total"] += row["p95LatencyMs"]
        current["workloadCount"] += 1

    for current in grouped.values():
        count = current["workloadCount"]
        current["throughputRps"] = average_metric(current["throughputTotal"], count)
        current["p95LatencyMs"] = average_metric(current["p95Total"], count)

    return grouped


def format_value(metric, value):
    if metric == "throughputRps":
        return f"{value:.1f}"
    return str(round(value))


def format_axis_tick(metric, value):
    return str(round(value))


def make_detailed_chart(scenario, rows, metric, title, unit):
    selected_rows = [row for row in rows if row["scenario"] == scenario["slug"]]
    workloads = ordered_workloads(selected_rows)
    width = 1040
    height = 580
    margin = {"top": 72, "right": 38, "bottom": 126, "left": 92}
    plot_width = width - margin["left"] - margin["right"]
    plot_height = height - margin["top"] - margin["bottom"]
    max_raw_value = max((row[metric] for row in selected_rows), default=0)
    max_value = max(1, max_raw_value * 1.14)
    group_width = plot_width / max(1, len(workloads))
    bar_gap = 9
    bar_width = (group_width - 48 - bar_gap * (len(TECHNOLOGIES) - 1)) / len(TECHNOLOGIES)

    def y(value):
        return margin["top"] + plot_height - (value / max_value) * plot_height

    axis_ticks = [max_value * ratio for ratio in [0, 0.25, 0.5, 0.75, 1]]

    bars = []
    for workload_index, workload in enumerate(workloads):
        x_base = margin["left"] + workload_index * group_width + 24
        for technology_index, technology in enumerate(TECHNOLOGIES):
            row = next(
                (
                    item
                    for item in selected_rows
                    if item["workload"] == workload and item["technology"] == technology["label"]
                ),
                None,
            )
            if row is None:
                continue
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
    for index, workload in enumerate(workloads):
        x = margin["left"] + index * group_width + group_width / 2
        tspans = "".join(
            f'<tspan x="{x:.1f}" dy="{0 if line_index == 0 else 16}">{escape(line)}</tspan>'
            for line_index, line in enumerate(workload_label_lines(workload))
        )
        x_labels.append(
            f'<text x="{x:.1f}" y="{height - 82}" text-anchor="middle" font-size="13" fill="#111827">{tspans}</text>'
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

    subtitle = f"{scenario['label']} - {scenario['users']} usuários virtuais - cenários de leitura - unidade: {unit}"
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


def make_average_chart(scenario, rows, metric, title, unit):
    grouped = aggregate_technology_rows(rows, scenario)
    width = 1040
    height = 580
    margin = {"top": 72, "right": 46, "bottom": 106, "left": 92}
    plot_width = width - margin["left"] - margin["right"]
    plot_height = height - margin["top"] - margin["bottom"]
    max_raw_value = max((row[metric] for row in grouped.values()), default=0)
    max_value = max(1, max_raw_value * 1.14)
    group_width = plot_width / max(1, len(TECHNOLOGIES))
    bar_width = min(120, group_width - 80)

    def y(value):
        return margin["top"] + plot_height - (value / max_value) * plot_height

    axis_ticks = [max_value * ratio for ratio in [0, 0.25, 0.5, 0.75, 1]]

    bars = []
    x_labels = []
    for technology_index, technology in enumerate(TECHNOLOGIES):
        row = grouped.get(technology["label"])
        if row is None:
            continue
        value = row[metric]
        x_center = margin["left"] + technology_index * group_width + group_width / 2
        bar_x = x_center - bar_width / 2
        bar_y = y(value)
        bar_height = margin["top"] + plot_height - bar_y
        bars.append(
            f"""
        <rect x="{bar_x:.1f}" y="{bar_y:.1f}" width="{bar_width:.1f}" height="{bar_height:.1f}" fill="{COLORS[technology['label']]}"/>
        <text x="{x_center:.1f}" y="{bar_y - 7:.1f}" text-anchor="middle" font-size="12" fill="#111827">{format_value(metric, value)}</text>"""
        )
        x_labels.append(
            f'<text x="{x_center:.1f}" y="{height - 64}" text-anchor="middle" font-size="14" fill="#111827">{technology["label"]}</text>'
        )

    y_ticks = []
    for tick in axis_ticks:
        tick_y = y(tick)
        y_ticks.append(
            f"""
      <line x1="{margin['left']}" x2="{width - margin['right']}" y1="{tick_y:.1f}" y2="{tick_y:.1f}" stroke="#e5e7eb"/>
      <text x="{margin['left'] - 12}" y="{tick_y + 4:.1f}" text-anchor="end" font-size="12" fill="#4b5563">{format_axis_tick(metric, tick)}</text>"""
        )

    subtitle = f"{scenario['label']} - {scenario['users']} usuários virtuais - média dos cenários de leitura - unidade: {unit}"
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
</svg>"""


def make_comparison_chart(scenario, rows, metric, title, unit):
    grouped = aggregate_comparison_rows(rows, scenario)
    width = 1060
    height = 590
    margin = {"top": 82, "right": 52, "bottom": 104, "left": 92}
    plot_width = width - margin["left"] - margin["right"]
    plot_height = height - margin["top"] - margin["bottom"]
    group_width = plot_width / max(1, len(TECHNOLOGIES))
    bar_gap = 12
    bar_width = (group_width - 86 - bar_gap) / len(LANGUAGES)
    max_raw_value = max((row[metric] for row in grouped.values()), default=0)
    max_value = max(1, max_raw_value * 1.16)

    def y(value):
        return margin["top"] + plot_height - (value / max_value) * plot_height

    axis_ticks = [max_value * ratio for ratio in [0, 0.25, 0.5, 0.75, 1]]

    y_ticks = []
    for tick in axis_ticks:
        tick_y = y(tick)
        y_ticks.append(
            f"""
      <line x1="{margin['left']}" x2="{width - margin['right']}" y1="{tick_y:.1f}" y2="{tick_y:.1f}" stroke="#e5e7eb"/>
      <text x="{margin['left'] - 12}" y="{tick_y + 4:.1f}" text-anchor="end" font-size="12" fill="#4b5563">{format_axis_tick(metric, tick)}</text>"""
        )

    bars = []
    x_labels = []
    for technology_index, technology in enumerate(TECHNOLOGIES):
        group_x = margin["left"] + technology_index * group_width
        x_base = group_x + 42
        label_x = group_x + group_width / 2
        x_labels.append(
            f'<text x="{label_x:.1f}" y="{height - 68}" text-anchor="middle" font-size="14" fill="#111827">{technology["label"]}</text>'
        )

        for language_index, language in enumerate(LANGUAGES):
            row = grouped.get((language["label"], technology["label"]))
            if row is None:
                continue
            value = row[metric]
            bar_x = x_base + language_index * (bar_width + bar_gap)
            bar_y = y(value)
            bar_height = margin["top"] + plot_height - bar_y
            bars.append(
                f"""
      <rect x="{bar_x:.1f}" y="{bar_y:.1f}" width="{bar_width:.1f}" height="{bar_height:.1f}" fill="{LANGUAGE_COLORS[language['label']]}"/>
      <text x="{bar_x + bar_width / 2:.1f}" y="{bar_y - 7:.1f}" text-anchor="middle" font-size="11" fill="#111827">{format_value(metric, value)}</text>"""
            )

    legend = []
    for index, language in enumerate(LANGUAGES):
        x_legend = margin["left"] + index * 148
        y_legend = height - 30
        legend.append(
            f"""
      <rect x="{x_legend}" y="{y_legend - 12}" width="14" height="14" fill="{LANGUAGE_COLORS[language['label']]}"/>
      <text x="{x_legend + 22}" y="{y_legend}" font-size="13" fill="#111827">{language['label']}</text>"""
        )

    subtitle = (
        f"{scenario['label']} - {scenario['users']} usuários virtuais - "
        f"média dos cenários de leitura por tecnologia - unidade: {unit}"
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{escape(title + ' - ' + scenario['label'])}">
  <rect width="100%" height="100%" fill="#ffffff"/>
  <text x="{margin['left']}" y="38" font-size="22" font-weight="700" fill="#111827">{escape(title)}</text>
  <text x="{margin['left']}" y="62" font-size="13" fill="#4b5563">{escape(subtitle)}</text>
  {''.join(y_ticks)}
  <line x1="{margin['left']}" x2="{margin['left']}" y1="{margin['top']}" y2="{margin['top'] + plot_height}" stroke="#111827"/>
  <line x1="{margin['left']}" x2="{width - margin['right']}" y1="{margin['top'] + plot_height}" y2="{margin['top'] + plot_height}" stroke="#111827"/>
  {''.join(bars)}
  {''.join(x_labels)}
  {''.join(legend)}
</svg>"""


def make_detailed_comparison_chart(scenario, rows, metric, title, unit):
    selected_rows = [row for row in rows if row["scenario"] == scenario["slug"]]
    workloads = ordered_workloads(selected_rows)
    lookup = {
        (row["workload"], row["technology"], row["language"]): row
        for row in selected_rows
    }
    width = max(1320, 290 * max(1, len(workloads)) + 120)
    height = 660
    margin = {"top": 82, "right": 52, "bottom": 148, "left": 92}
    plot_width = width - margin["left"] - margin["right"]
    plot_height = height - margin["top"] - margin["bottom"]
    group_width = plot_width / max(1, len(workloads))
    technology_width = (group_width - 46) / len(TECHNOLOGIES)
    bar_gap = 4
    bar_width = max(10, min(24, (technology_width - 18 - bar_gap) / len(LANGUAGES)))
    max_raw_value = max((row[metric] for row in selected_rows), default=0)
    max_value = max(1, max_raw_value * 1.16)

    def y(value):
        return margin["top"] + plot_height - (value / max_value) * plot_height

    axis_ticks = [max_value * ratio for ratio in [0, 0.25, 0.5, 0.75, 1]]

    y_ticks = []
    for tick in axis_ticks:
        tick_y = y(tick)
        y_ticks.append(
            f"""
      <line x1="{margin['left']}" x2="{width - margin['right']}" y1="{tick_y:.1f}" y2="{tick_y:.1f}" stroke="#e5e7eb"/>
      <text x="{margin['left'] - 12}" y="{tick_y + 4:.1f}" text-anchor="end" font-size="12" fill="#4b5563">{format_axis_tick(metric, tick)}</text>"""
        )

    bars = []
    technology_labels = []
    workload_labels = []
    for workload_index, workload in enumerate(workloads):
        group_x = margin["left"] + workload_index * group_width + 23
        workload_center = margin["left"] + workload_index * group_width + group_width / 2
        tspans = "".join(
            f'<tspan x="{workload_center:.1f}" dy="{0 if line_index == 0 else 15}">{escape(line)}</tspan>'
            for line_index, line in enumerate(workload_label_lines(workload))
        )
        workload_labels.append(
            f'<text x="{workload_center:.1f}" y="{height - 76}" text-anchor="middle" font-size="12" fill="#111827">{tspans}</text>'
        )

        for technology_index, technology in enumerate(TECHNOLOGIES):
            pair_width = len(LANGUAGES) * bar_width + (len(LANGUAGES) - 1) * bar_gap
            pair_x = group_x + technology_index * technology_width + (technology_width - pair_width) / 2
            pair_center = pair_x + pair_width / 2
            technology_labels.append(
                f'<text x="{pair_center:.1f}" y="{height - 106}" text-anchor="middle" font-size="10" fill="#4b5563">{technology["label"]}</text>'
            )

            for language_index, language in enumerate(LANGUAGES):
                row = lookup.get((workload, technology["label"], language["label"]))
                if row is None:
                    continue
                value = row[metric]
                bar_x = pair_x + language_index * (bar_width + bar_gap)
                bar_y = y(value)
                bar_height = margin["top"] + plot_height - bar_y
                bars.append(
                    f"""
      <rect x="{bar_x:.1f}" y="{bar_y:.1f}" width="{bar_width:.1f}" height="{bar_height:.1f}" fill="{LANGUAGE_COLORS[language['label']]}"/>
      <text x="{bar_x + bar_width / 2:.1f}" y="{bar_y - 6:.1f}" text-anchor="middle" font-size="9" fill="#111827">{format_value(metric, value)}</text>"""
                )

    legend = []
    for index, language in enumerate(LANGUAGES):
        x_legend = margin["left"] + index * 148
        y_legend = height - 28
        legend.append(
            f"""
      <rect x="{x_legend}" y="{y_legend - 12}" width="14" height="14" fill="{LANGUAGE_COLORS[language['label']]}"/>
      <text x="{x_legend + 22}" y="{y_legend}" font-size="13" fill="#111827">{language['label']}</text>"""
        )

    subtitle = (
        f"{scenario['label']} - {scenario['users']} usuários virtuais - "
        f"cenários de leitura por tecnologia - unidade: {unit}"
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{escape(title + ' - ' + scenario['label'])}">
  <rect width="100%" height="100%" fill="#ffffff"/>
  <text x="{margin['left']}" y="38" font-size="22" font-weight="700" fill="#111827">{escape(title)}</text>
  <text x="{margin['left']}" y="62" font-size="13" fill="#4b5563">{escape(subtitle)}</text>
  {''.join(y_ticks)}
  <line x1="{margin['left']}" x2="{margin['left']}" y1="{margin['top']}" y2="{margin['top'] + plot_height}" stroke="#111827"/>
  <line x1="{margin['left']}" x2="{width - margin['right']}" y1="{margin['top'] + plot_height}" y2="{margin['top'] + plot_height}" stroke="#111827"/>
  {''.join(bars)}
  {''.join(technology_labels)}
  {''.join(workload_labels)}
  {''.join(legend)}
</svg>"""


def write_summary(results_dir, rows):
    headers = [
        "scenario",
        "scenarioLabel",
        "users",
        "technology",
        "workload",
        "requestCount",
        "throughputRps",
        "p95LatencyMs",
    ]
    with (results_dir / "locust-summary.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)
    (results_dir / "locust-summary.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")


def write_combined_summary(results_root, rows):
    if not rows:
        return

    headers = [
        "language",
        "scenario",
        "scenarioLabel",
        "users",
        "technology",
        "workload",
        "requestCount",
        "throughputRps",
        "p95LatencyMs",
    ]
    csv_rows = [{key: row[key] for key in headers} for row in rows]
    with (results_root / "locust-combined-summary.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(csv_rows)
    (results_root / "locust-combined-summary.json").write_text(
        json.dumps(csv_rows, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def has_locust_stats(results_dir):
    return results_dir.exists() and any(results_dir.glob("locust-*_stats.csv"))


def language_targets(results_root, charts_root=None):
    targets = []
    for language in LANGUAGES:
        results_dir = results_root / language["slug"]
        if has_locust_stats(results_dir):
            charts_dir = charts_root / language["slug"] if charts_root else results_dir / "charts"
            targets.append((results_dir, charts_dir))
    return targets


def chart_targets():
    if RESULTS_DIR_ENV:
        results_dir = Path(RESULTS_DIR_ENV)
        charts_root = Path(CHARTS_DIR_ENV) if CHARTS_DIR_ENV else None
        targets = language_targets(results_dir, charts_root)
        if targets:
            return targets
        charts_dir = charts_root if charts_root else results_dir / "charts"
        return [(results_dir, charts_dir)]

    charts_root = Path(CHARTS_DIR_ENV) if CHARTS_DIR_ENV else None
    targets = language_targets(DEFAULT_RESULTS_DIR, charts_root)

    if targets:
        return targets

    if has_locust_stats(DEFAULT_RESULTS_DIR):
        charts_dir = Path(CHARTS_DIR_ENV) if CHARTS_DIR_ENV else DEFAULT_RESULTS_DIR / "charts"
        return [(DEFAULT_RESULTS_DIR, charts_dir)]

    return []


def generate_for_target(results_dir, charts_dir):
    results_dir.mkdir(parents=True, exist_ok=True)
    charts_dir.mkdir(parents=True, exist_ok=True)
    rows = collect_rows(results_dir)
    if not rows:
        raise FileNotFoundError(
            f"Nenhum dado Locust encontrado em {results_dir}. "
            "Execute a bateria de testes antes de gerar os gráficos."
        )
    write_summary(results_dir, rows)

    generated = []
    for scenario in SCENARIOS:
        if not any(row["scenario"] == scenario["slug"] for row in rows):
            continue
        scenario_charts_dir = charts_dir / scenario["folder"]
        scenario_charts_dir.mkdir(parents=True, exist_ok=True)
        average_outputs = [
            (
                scenario_charts_dir / f"locust-throughput-{scenario['slug']}-u{scenario['users']}.svg",
                "throughputRps",
                "Vazão média por tecnologia",
                "req/s",
            ),
            (
                scenario_charts_dir / f"locust-p95-latency-{scenario['slug']}-u{scenario['users']}.svg",
                "p95LatencyMs",
                "Latência p95 média por tecnologia",
                "ms",
            ),
        ]
        detailed_outputs = [
            (
                scenario_charts_dir / f"locust-throughput-por-cenario-{scenario['slug']}-u{scenario['users']}.svg",
                "throughputRps",
                "Vazão por tecnologia e cenário de leitura",
                "req/s",
            ),
            (
                scenario_charts_dir / f"locust-p95-latency-por-cenario-{scenario['slug']}-u{scenario['users']}.svg",
                "p95LatencyMs",
                "Latência p95 por tecnologia e cenário de leitura",
                "ms",
            ),
        ]
        for path, metric, title, unit in average_outputs:
            path.write_text(make_average_chart(scenario, rows, metric, title, unit), encoding="utf-8")
            generated.append(path)
        for path, metric, title, unit in detailed_outputs:
            path.write_text(make_detailed_chart(scenario, rows, metric, title, unit), encoding="utf-8")
            generated.append(path)

    print(f"Graficos Locust gerados para {results_dir}:")
    for path in generated:
        print(path)
    print("Resumo agregado:")
    print(results_dir / "locust-summary.csv")
    print(results_dir / "locust-summary.json")


def generate_combined_charts(results_root=DEFAULT_RESULTS_DIR):
    rows = collect_language_rows(results_root)
    languages = {row["language"] for row in rows}
    if len(languages) < 2:
        return []

    write_combined_summary(results_root, rows)
    charts_dir = results_root / "charts" / "comparativo"
    generated = []
    for scenario in SCENARIOS:
        grouped = aggregate_comparison_rows(rows, scenario)
        if not grouped:
            continue
        scenario_charts_dir = charts_dir / scenario["folder"]
        scenario_charts_dir.mkdir(parents=True, exist_ok=True)
        average_outputs = [
            (
                scenario_charts_dir / f"locust-comparison-throughput-{scenario['slug']}-u{scenario['users']}.svg",
                "throughputRps",
                "Comparativo Python x JavaScript - vazão",
                "req/s",
            ),
            (
                scenario_charts_dir / f"locust-comparison-p95-latency-{scenario['slug']}-u{scenario['users']}.svg",
                "p95LatencyMs",
                "Comparativo Python x JavaScript - latência p95",
                "ms",
            ),
        ]
        detailed_outputs = [
            (
                scenario_charts_dir / f"locust-comparison-throughput-por-cenario-{scenario['slug']}-u{scenario['users']}.svg",
                "throughputRps",
                "Comparativo Python x JavaScript por cenário - vazão",
                "req/s",
            ),
            (
                scenario_charts_dir / f"locust-comparison-p95-latency-por-cenario-{scenario['slug']}-u{scenario['users']}.svg",
                "p95LatencyMs",
                "Comparativo Python x JavaScript por cenário - latência p95",
                "ms",
            ),
        ]
        for path, metric, title, unit in average_outputs:
            path.write_text(make_comparison_chart(scenario, rows, metric, title, unit), encoding="utf-8")
            generated.append(path)
        for path, metric, title, unit in detailed_outputs:
            path.write_text(make_detailed_comparison_chart(scenario, rows, metric, title, unit), encoding="utf-8")
            generated.append(path)

    if generated:
        print("Graficos comparativos Python x JavaScript:")
        for path in generated:
            print(path)
        print("Resumo combinado:")
        print(results_root / "locust-combined-summary.csv")
        print(results_root / "locust-combined-summary.json")

    return generated


def main():
    targets = chart_targets()
    if not targets:
        raise SystemExit(
            "Nenhum CSV Locust encontrado. Execute a bateria de testes ou informe LOCUST_RESULTS_DIR."
        )

    for results_dir, charts_dir in targets:
        generate_for_target(results_dir, charts_dir)

    if len(targets) > 1 or not RESULTS_DIR_ENV:
        results_root = Path(RESULTS_DIR_ENV) if RESULTS_DIR_ENV and len(targets) > 1 else DEFAULT_RESULTS_DIR
        generate_combined_charts(results_root)


if __name__ == "__main__":
    main()
