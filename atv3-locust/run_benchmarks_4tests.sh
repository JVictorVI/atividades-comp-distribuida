#!/usr/bin/env bash
set -euo pipefail

# Cargas escolhidas para esta maquina de teste, mantendo a taxa de erros em ate 10%.
USERS_LIST=(25 75 155)

# Quantidade de instancias WordPress usadas para avaliar escalabilidade horizontal.
INSTANCES_LIST=(1 2 3)

RUN_TIME="2m"
SPAWN_RATE="3"
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

# Garante que as pastas de saida existam antes de gravar CSVs e graficos.
mkdir -p "$RESULTS_DIR" "$GRAPHS_DIR"

# Opcional: limpa resultados anteriores para garantir exatamente 36 CSVs de estatísticas no final.
rm -f "$RESULTS_DIR"/*.csv

echo "Preparando ambiente..."

for instances in "${INSTANCES_LIST[@]}"; do
  echo ""
  echo "====================================="
  echo "Subindo ambiente com ${instances} instância(s) WordPress"
  echo "====================================="

  # Troca a configuracao do Nginx para balancear apenas as instancias desta rodada.
  cp "nginx-${instances}.conf" nginx.conf

  # Reinicia o ambiente para evitar interferencia entre rodadas de benchmark.
  docker compose down >/dev/null 2>&1 || true

  # O MySQL e a primeira instancia do WordPress sempre participam dos testes.
  docker compose up -d mysql wordpress1

  # Sobe instancias adicionais somente quando a rodada exigir.
  if [ "$instances" -ge 2 ]; then
    docker compose up -d wordpress2
  fi

  if [ "$instances" -ge 3 ]; then
    docker compose up -d wordpress3
  fi

  # Inicia o balanceador depois que as instancias WordPress necessarias estiverem ativas.
  docker compose up -d nginx

  # Aguarda os containers aceitarem requisicoes antes de disparar carga.
  echo "Aguardando serviços inicializarem..."
  sleep 10

  for test_name in "${TEST_ORDER[@]}"; do
    locust_file="${TEST_FILES[$test_name]}"

    for users in "${USERS_LIST[@]}"; do
      # O prefixo define o nome base dos CSVs gerados pelo Locust dentro de results/.
      result_name="${test_name}_${instances}wp_${users}users"
      prefix="/mnt/locust/results/${result_name}"

      echo ""
      echo ">>> Teste=${test_name} | arquivo=${locust_file} | instâncias=${instances} | usuários=${users}"

      # Executa o Locust em modo headless contra o Nginx, salvando as metricas em CSV.
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
