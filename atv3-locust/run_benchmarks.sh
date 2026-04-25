#!/usr/bin/env bash
set -euo pipefail

USERS_LIST=(10 100 1000)
INSTANCES_LIST=(1 2 3)
SCENARIOS=("image_1mb" "text_400kb" "image_300kb")

RUN_TIME="1m"
SPAWN_RATE="10"

RESULTS_DIR="results"

echo "Preparando ambiente..."

# 🔥 Cria pasta de resultados se não existir
mkdir -p "$RESULTS_DIR"

for instances in "${INSTANCES_LIST[@]}"; do
  echo ""
  echo "====================================="
  echo "Subindo ambiente com ${instances} instância(s)"
  echo "====================================="

  # 🔧 Ajusta configuração do Nginx
  cp "nginx-${instances}.conf" nginx.conf

  # 🔁 Reinicia ambiente base
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
  sleep 40

  for scenario in "${SCENARIOS[@]}"; do
    for users in "${USERS_LIST[@]}"; do

      result_name="${scenario}_${instances}wp_${users}users"
      prefix="/mnt/locust/results/${result_name}"

      echo ""
      echo ">>> Teste: cenário=${scenario} | instâncias=${instances} | usuários=${users}"

      docker compose run --rm \
        locust \
        -f /mnt/locust/locustfile.py \
        --headless \
        --host http://nginx \
        -u "$users" \
        -r "$SPAWN_RATE" \
        --run-time "$RUN_TIME" \
        --csv "$prefix" \
        --only-summary

      echo "✔ Resultado salvo: results/${result_name}_stats.csv"
    done
  done
done

echo ""
echo "====================================="
echo "TODOS OS TESTES FINALIZADOS"
echo "====================================="

echo "Arquivos CSV em: ${RESULTS_DIR}/"
echo "Para gerar gráficos:"
echo "python generate_graphs.py"