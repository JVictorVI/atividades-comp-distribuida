# Testes de Carga com WordPress + Locust

## Visão Geral

Este projeto realiza testes de carga automatizados em um ambiente com múltiplas instâncias do WordPress, utilizando:

- Locust para geração de carga;
- Docker Compose para orquestração dos serviços;
- Nginx como balanceador de carga;
- MySQL como banco de dados compartilhado;
- Python para consolidação dos resultados e geração de gráficos.

O objetivo é avaliar o desempenho, a escalabilidade e o comportamento do WordPress sob diferentes níveis de carga e diferentes quantidades de instâncias.

---

## Arquitetura

O ambiente é composto por:

- 1 Nginx;
- 1 MySQL;
- 1 a 3 instâncias WordPress;
- 1 container Locust.

Fluxo geral:

```text
Usuários simulados pelo Locust
        ↓
      Nginx
        ↓
WordPress 1, 2 ou 3 instâncias
        ↓
      MySQL
```

O Nginx distribui as requisições entre as instâncias ativas do WordPress. Todas as instâncias compartilham o mesmo banco MySQL e o mesmo volume de arquivos.

---

## Tipos de Teste

O projeto utiliza quatro arquivos Locust, cada um representando um tipo de carga diferente.

| Tipo de teste | Arquivo                   | Descrição                                               |
| ------------- | ------------------------- | ------------------------------------------------------- |
| Light         | `locust/locust_light.py`  | Acessa o post com imagem de aproximadamente 300KB       |
| Medium        | `locust/locust_medium.py` | Acessa o post com texto de aproximadamente 400KB        |
| Heavy         | `locust/locust_heavy.py`  | Acessa o post com imagem de aproximadamente 1MB         |
| Hybrid        | `locust/locust_hybrid.py` | Executa requisições em sequência: leve → médio → pesado |

---

## Funcionamento dos Testes

Cada teste é executado variando:

- quantidade de instâncias WordPress: 1, 2 e 3;
- quantidade de usuários simultâneos: 10, 100 e 1000;
- tipo de carga: light, medium, heavy e hybrid.

Com isso, o projeto executa:

```text
4 tipos de teste × 3 quantidades de instâncias × 3 níveis de usuários = 36 execuções
```

Cada execução gera arquivos CSV brutos do Locust dentro da pasta `results/`.

---

## Comportamento do Teste Híbrido

O teste híbrido executa os três cenários em sequência:

```text
leve → médio → pesado → repete
```

Ou seja, cada usuário simulado acessa primeiro o cenário leve, depois o médio, depois o pesado, repetindo essa ordem durante a execução.

---

## Estrutura do Projeto

```text
.
├── locust/
│   ├── locust_light.py
│   ├── locust_medium.py
│   ├── locust_heavy.py
│   └── locust_hybrid.py
│
├── results/
│   └── CSVs brutos gerados pelo Locust
│
├── consolidated/
│   └── resultados_consolidados.csv
│
├── graphs/
│   ├── por_usuarios/
│   └── por_instancias/
|
|── nginx/
│   ├── nginx-1.conf
│   |── nginx-2.conf
|   └── nginx-3.conf
│
├── docker-compose.yml
├── run_benchmarks_4tests.ps1
├── run_benchmarks_4tests.sh
├── consolidate_results.py
└── generate_graphs.py
```

---

## Posts Necessários no WordPress

Antes de executar os testes, crie os seguintes posts no WordPress:

| Tipo   | Conteúdo                        | Slug              |
| ------ | ------------------------------- | ----------------- |
| Light  | Imagem de aproximadamente 300KB | `imagem-de-300kb` |
| Medium | Texto de aproximadamente 400KB  | `texto-de-400kb`  |
| Heavy  | Imagem de aproximadamente 1MB   | `imagem-com-1mb`  |

As URLs esperadas são:

```text
http://localhost/?name=imagem-de-300kb
http://localhost/?name=texto-de-400kb
http://localhost/?name=imagem-com-1mb
```

---

## Como Executar

### 1. Subir o ambiente

```bash
docker compose up -d
```

Aguarde alguns segundos para o MySQL, WordPress e Nginx inicializarem corretamente.

---

### 2. Executar os testes

No Windows PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\run_benchmarks_4tests.ps1
```

No Linux, macOS ou Git Bash:

```bash
bash run_benchmarks_4tests.sh
```

O script irá:

- configurar o Nginx para 1, 2 ou 3 instâncias;
- subir as instâncias necessárias do WordPress;
- executar os quatro tipos de teste;
- variar os usuários entre 10, 100 e 1000;
- salvar os CSVs brutos em `results/`.

---

## Resultados Brutos

Os arquivos brutos do Locust são salvos em:

```text
results/
```

Exemplos:

```text
light_1wp_10users_stats.csv
medium_2wp_100users_stats.csv
heavy_3wp_1000users_stats.csv
hybrid_1wp_100users_stats.csv
```

---

## Consolidar Resultados

Para gerar o CSV consolidado:

```bash
python consolidate_results.py
```

Saída gerada:

```text
consolidated/resultados_consolidados.csv
```

Esse arquivo reúne os principais dados de todas as execuções, incluindo:

- cenário;
- número de instâncias;
- número de usuários;
- total de requisições;
- total de falhas;
- tempo médio de resposta;
- mediana;
- menor tempo;
- maior tempo;
- percentil 95;
- percentil 99;
- requisições por segundo;
- falhas por segundo.

---

## Gerar Gráficos

Para gerar os gráficos:

```bash
python generate_graphs.py
```

Os gráficos são salvos na pasta:

```text
graphs/
```

A estrutura fica assim:

```text
graphs/
├── por_usuarios/
│   ├── avg_response_ms/
│   ├── median_response_ms/
│   ├── p95_response_ms/
│   ├── p99_response_ms/
│   ├── rps/
│   └── failures/
│
└── por_instancias/
    ├── avg_response_ms/
    ├── median_response_ms/
    ├── p95_response_ms/
    ├── p99_response_ms/
    ├── rps/
    └── failures/
```

---

## Métricas Analisadas

| Métrica              | Significado                                                |
| -------------------- | ---------------------------------------------------------- |
| `avg_response_ms`    | Tempo médio de resposta em milissegundos                   |
| `median_response_ms` | Mediana do tempo de resposta                               |
| `p95_response_ms`    | Tempo abaixo do qual 95% das requisições foram respondidas |
| `p99_response_ms`    | Tempo abaixo do qual 99% das requisições foram respondidas |
| `rps`                | Requisições por segundo                                    |
| `failures`           | Quantidade total de falhas                                 |
| `failures_s`         | Falhas por segundo                                         |

---

## Interpretação dos Resultados

Algumas leituras importantes:

- quanto menor a latência média, melhor o tempo de resposta;
- quanto menor o p95 e o p99, melhor o comportamento nas requisições mais lentas;
- quanto maior o RPS, maior a vazão do sistema;
- falhas indicam saturação, erro de aplicação ou indisponibilidade;
- comparar 1, 2 e 3 instâncias permite avaliar se o sistema escala horizontalmente;
- comparar light, medium, heavy e hybrid permite entender o impacto do tipo de conteúdo.

---

## Problemas Comuns

### Erro 404

Verifique se os posts foram criados com os slugs corretos:

```text
imagem-de-300kb
texto-de-400kb
imagem-com-1mb
```

---

### Locust não encontra o arquivo

Confirme se os arquivos estão dentro da pasta `locust/` e se o volume no `docker-compose.yml` está correto:

```yaml
volumes:
  - ./locust:/mnt/locust
```

---

### Erro de permissão ao salvar CSV

Use o caminho interno correto no script:

```text
/mnt/locust/results
```

E garanta que a pasta `results/` existe no projeto.

---

## Fluxo Recomendado

```bash
docker compose up -d
bash run_benchmarks_4tests.sh
python consolidate_results.py
python generate_graphs.py
```

No Windows:

```powershell
docker compose up -d
powershell -ExecutionPolicy Bypass -File .\run_benchmarks_4tests.ps1
python consolidate_results.py
python generate_graphs.py
```

---

## Saídas Finais

Ao final do processo, os principais artefatos são:

```text
results/                               # CSVs brutos do Locust
consolidated/resultados_consolidados.csv
graphs/                               # gráficos organizados por eixo e métrica
```
