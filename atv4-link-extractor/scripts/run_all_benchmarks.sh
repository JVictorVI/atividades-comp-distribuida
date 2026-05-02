#!/usr/bin/env bash
set -euo pipefail

USERS_LIST=(25 75 150)
SPAWN_RATE=3
RUN_TIME="2m"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RESULTS_DIR="$ROOT_DIR/results"
LOCUST_FILE="$ROOT_DIR/locust/locustfile.py"

mkdir -p "$RESULTS_DIR"

declare -A SCENARIOS
SCENARIOS["python_nocache"]="step4"
SCENARIOS["python_cache"]="step5"
SCENARIOS["ruby_cache"]="step6"
SCENARIOS["ruby_nocache"]="step6-nocache"

for scenario in python_nocache python_cache ruby_cache ruby_nocache; do
  step_dir="${SCENARIOS[$scenario]}"
  echo ""
  echo "===================================================="
  echo "Cenário: $scenario | Pasta: $step_dir"
  echo "===================================================="

  cd "$ROOT_DIR/$step_dir"

  docker compose down --remove-orphans || true
  docker compose up -d --build

  echo "Aguardando serviços iniciarem..."
  sleep 10

  for users in "${USERS_LIST[@]}"; do
    echo ""
    echo "Executando: $scenario com $users usuários"

    output_prefix="$RESULTS_DIR/${scenario}_${users}"

    locust \
      -f "$LOCUST_FILE" \
      --headless \
      -u "$users" \
      -r "$SPAWN_RATE" \
      --run-time "$RUN_TIME" \
      --host "http://localhost" \
      --csv "$output_prefix" \
      --html "${output_prefix}.html"

    sleep 5
  done

  docker compose down --remove-orphans || true
done

cd "$ROOT_DIR"

python scripts/consolidate_results.py
python scripts/generate_graphs.py

echo ""
echo "Finalizado."
echo "Resultados CSV: results/"
echo "Planilha consolidada: consolidated/resultados_consolidados.csv"
echo "Gráficos: graphs/"