#!/usr/bin/env bash
set -euo pipefail

USERS_LIST=(10 100 1000)
INSTANCES_LIST=(1 2 3)

RUN_TIME="1m"
SPAWN_RATE="10"
RESULTS_DIR="results"
GRAPHS_DIR="graphs"

# Arquivos de teste do Locust.
# Total esperado de *_stats.csv: 4 testes x 3 instâncias x 3 cargas de usuários = 36.
declare -A TEST_FILES=(
  [leve]="locust_light.py"
  [medio]="locust_medium.py"
  [pesado]="locust_heavy.py"
  [hibrido]="locust_hybrid.py"
)

TEST_ORDER=(leve medio pesado hibrido)

mkdir -p "$RESULTS_DIR" "$GRAPHS_DIR"

# Opcional: limpa resultados anteriores para garantir exatamente 36 CSVs de estatísticas no final.
rm -f "$RESULTS_DIR"/*.csv

echo "Preparando ambiente..."

for instances in "${INSTANCES_LIST[@]}"; do
  echo ""
  echo "====================================="
  echo "Subindo ambiente com ${instances} instância(s) WordPress"
  echo "====================================="

  cp "nginx-${instances}.conf" nginx.conf

  docker compose down >/dev/null 2>&1 || true

  docker compose up -d mysql wordpress1

  if [ "$instances" -ge 2 ]; then
    docker compose up -d wordpress2
  fi

  if [ "$instances" -ge 3 ]; then
    docker compose up -d wordpress3
  fi

  docker compose up -d nginx

  echo "Aguardando serviços inicializarem..."
  sleep 10

  for test_name in "${TEST_ORDER[@]}"; do
    locust_file="${TEST_FILES[$test_name]}"

    for users in "${USERS_LIST[@]}"; do
      result_name="${test_name}_${instances}wp_${users}users"
      prefix="/mnt/locust/results/${result_name}"

      echo ""
      echo ">>> Teste=${test_name} | arquivo=${locust_file} | instâncias=${instances} | usuários=${users}"

      docker compose run --rm \
        -e POST_LIGHT_PATH="/?name=imagem-de-300kb" \
        -e POST_MEDIUM_PATH="/?name=texto-de-400kb" \
        -e POST_HEAVY_PATH="/?name=imagem-com-1mb" \
        locust \
        -f "/mnt/locust/${locust_file}" \
        --headless \
        --host http://nginx \
        -u "$users" \
        -r "$SPAWN_RATE" \
        --run-time "$RUN_TIME" \
        --csv "$prefix" \
        --only-summary

      # Mantém apenas o CSV principal de estatísticas, para fechar em 36 CSVs no total.
      rm -f "${RESULTS_DIR}/${result_name}_failures.csv" \
            "${RESULTS_DIR}/${result_name}_exceptions.csv" \
            "${RESULTS_DIR}/${result_name}_stats_history.csv"

      echo "✔ Resultado salvo: results/${result_name}_stats.csv"
    done
  done
done

echo ""
echo "Gerando gráficos..."
python generate_graphs.py

echo ""
echo "====================================="
echo "TODOS OS TESTES FINALIZADOS"
echo "====================================="
echo "CSVs esperados: 36 arquivos *_stats.csv em ${RESULTS_DIR}/"
echo "Gráficos em: ${GRAPHS_DIR}/"
