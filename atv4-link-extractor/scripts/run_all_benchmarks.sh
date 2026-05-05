#!/usr/bin/env bash
set -euo pipefail

USERS_LIST=(25 75 150)
SPAWN_RATE=3
RUN_TIME="2m"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RESULTS_DIR="$ROOT_DIR/results"
LOCUST_FILE="$ROOT_DIR/locust/locustfile.py"

mkdir -p "$RESULTS_DIR"

run_python() {
  if command -v python >/dev/null 2>&1; then
    python "$@"
  elif command -v python3 >/dev/null 2>&1; then
    python3 "$@"
  else
    echo "Python nao encontrado no PATH. Instale Python antes de consolidar os resultados." >&2
    exit 1
  fi
}

stop_all_scenarios() {
  for scenario_name in python_nocache python_cache ruby_cache ruby_nocache; do
    (cd "$ROOT_DIR/${SCENARIO_DIRS[$scenario_name]}" && docker compose down --remove-orphans || true)
  done
}

wait_service() {
  local host="$1"
  local deadline=$((SECONDS + 90))

  until curl --silent --show-error "$host" > /dev/null; do
    if ((SECONDS >= deadline)); then
      echo "Servico nao respondeu em $host apos 90 segundos." >&2
      return 1
    fi

    sleep 3
  done
}

curl_with_retry() {
  local url="$1"

  for attempt in 1 2 3; do
    if curl --fail --silent --show-error "$url" > /dev/null; then
      return 0
    fi

    if [[ "$attempt" == "3" ]]; then
      return 1
    fi

    sleep 5
  done
}

URLS=(
  "https://www.tudogostoso.com.br"
  "https://www.dictionary.com"
  "https://canaltech.com.br"
  "https://br.ign.com"
  "https://kotaku.com"
  "https://receitas.globo.com"
  "https://g1.globo.com"
  "https://cnn.com"
  "https://huggingface.co"
  "https://www.todamateria.com.br"
)

declare -A SCENARIO_DIRS
SCENARIO_DIRS["python_nocache"]="step4"
SCENARIO_DIRS["python_cache"]="step5"
SCENARIO_DIRS["ruby_cache"]="step6"
SCENARIO_DIRS["ruby_nocache"]="step6-nocache"

declare -A SCENARIO_HOSTS
SCENARIO_HOSTS["python_nocache"]="http://localhost:5000"
SCENARIO_HOSTS["python_cache"]="http://localhost:5000"
SCENARIO_HOSTS["ruby_cache"]="http://localhost:4567"
SCENARIO_HOSTS["ruby_nocache"]="http://localhost:4567"

declare -A SCENARIO_USES_CACHE
SCENARIO_USES_CACHE["python_nocache"]="false"
SCENARIO_USES_CACHE["python_cache"]="true"
SCENARIO_USES_CACHE["ruby_cache"]="true"
SCENARIO_USES_CACHE["ruby_nocache"]="false"

declare -A SCENARIO_SERVICES
SCENARIO_SERVICES["python_nocache"]="api"
SCENARIO_SERVICES["python_cache"]="api redis"
SCENARIO_SERVICES["ruby_cache"]="api redis"
SCENARIO_SERVICES["ruby_nocache"]="api"

for scenario in python_nocache python_cache ruby_cache ruby_nocache; do
  step_dir="${SCENARIO_DIRS[$scenario]}"
  host="${SCENARIO_HOSTS[$scenario]}"
  services="${SCENARIO_SERVICES[$scenario]}"

  echo ""
  echo "===================================================="
  echo "Cenario: $scenario | Pasta: $step_dir | Host: $host"
  echo "===================================================="

  stop_all_scenarios

  cd "$ROOT_DIR/$step_dir"

  docker compose up -d --build $services

  echo "Aguardando servico responder..."
  if ! wait_service "$host"; then
    docker compose ps
    docker compose logs --tail 80 api
    exit 1
  fi

  if [[ "${SCENARIO_USES_CACHE[$scenario]}" == "true" ]]; then
    echo "Aquecendo cache antes das medicoes..."
    for url in "${URLS[@]}"; do
      if ! curl_with_retry "$host/api/$url"; then
        docker compose ps
        docker compose logs --tail 80 api
        exit 1
      fi
    done
  fi

  for users in "${USERS_LIST[@]}"; do
    echo ""
    echo "Executando: $scenario com $users usuarios"

    output_prefix="$RESULTS_DIR/${scenario}_${users}"

    locust \
      -f "$LOCUST_FILE" \
      --headless \
      -u "$users" \
      -r "$SPAWN_RATE" \
      --run-time "$RUN_TIME" \
      --host "$host" \
      --csv "$output_prefix" \
      --html "${output_prefix}.html"

    sleep 5
  done

  docker compose down --remove-orphans || true
done

cd "$ROOT_DIR"

run_python scripts/consolidate_results.py
run_python scripts/generate_graphs.py

echo ""
echo "Finalizado."
echo "Resultados CSV: results/"
echo "Planilha consolidada: consolidated/resultados_consolidados.csv"
echo "Graficos: graphs/"
