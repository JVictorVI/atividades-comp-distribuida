# Testes de Carga com WordPress + Locust

## Visão Geral

Este projeto realiza testes de carga em um ambiente com múltiplas instâncias do WordPress utilizando:

- Locust para geração de carga
- Docker Compose para orquestração dos serviços
- Nginx como balanceador de carga
- MySQL como banco de dados compartilhado
- Python para consolidação dos resultados e geração de gráficos

O objetivo é avaliar o desempenho do sistema sob diferentes níveis de carga e diferentes quantidades de instâncias.

---

## Ambiente de Teste

Os testes foram executados em um notebook com as seguintes especificações:

- **CPU:** Intel Core i5-1135G7
- **Memória:** 16GB DDR4 3200MHz
- **Armazenamento:** SSD 256GB
- **Sistema Operacional:** Windows 11

---

## Arquitetura

```text
Locust
  ↓
Nginx
  ↓
WordPress (1, 2 ou 3 instâncias)
  ↓
MySQL (compartilhado)
```

---

## Cenários de Teste

| Cenário | Descrição                             |
| ------- | ------------------------------------- |
| Light   | Requisição de texto (~300KB)          |
| Medium  | Requisição de texto (~400KB)          |
| Heavy   | Requisição de texto (~1MB)            |
| Hybrid  | Execução sequencial dos três cenários |

---

## Configuração dos Testes

### Quantidade de usuários

```text
25, 75 e 155 usuários
```

### Quantidade de instâncias WordPress

```text
1, 2 e 3 instâncias
```

### Parâmetros de execução (Locust)

```text
spawn_rate = 3
run_time = 2m
```

---

## Execução

Para executar os testes:

```bash
docker compose up -d
powershell -ExecutionPolicy Bypass -File .\run_benchmarks_4tests.ps1
```

---

## Consolidação dos Resultados

Os resultados gerados pelo Locust são armazenados em arquivos CSV na pasta `results/`.

O script abaixo consolida os dados:

```bash
python consolidate_results.py
```

Gerando:

```text
consolidated/resultados_consolidados.csv
```

---

## Geração de Gráficos

Os gráficos são gerados a partir do arquivo consolidado utilizando o script:

```bash
python final_generate_p95_failure_bar_graphs.py
```

Esse script produz gráficos de:

- P95 do tempo de resposta
- Taxa de falhas (%)

A taxa de falha é calculada como:

```text
(failures / requests) * 100
```

---

## Estrutura do Projeto

```text
.
├── locust/
├── results/
├── consolidated/
├── graphs/
├── docker-compose.yml
├── run_benchmarks_4tests.ps1
├── consolidate_results.py
├── final_generate_p95_failure_bar_graphs.py
└── final_generate_p95_failure_line_graphs.py
```

---
