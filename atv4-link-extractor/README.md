# Atividade 4 - Link Extractor

## Relatório do projeto

Este projeto apresenta a implementação e a avaliação experimental de desempenho da aplicação Link Extractor, utilizada como estudo prático de sistemas distribuídos. A aplicação recebe uma URL por meio de uma API HTTP, acessa a página correspondente, extrai os links presentes no documento HTML e retorna esses links em formato JSON.

O trabalho compara diferentes versões do serviço de extração, variando a linguagem de implementação e a presença de cache. A avaliação foi conduzida por meio de testes de carga automatizados com Locust, gerando arquivos CSV, planilhas consolidadas e gráficos para apoiar a análise.

## Objetivo

O objetivo principal foi medir como diferentes configurações do Link Extractor se comportam sob carga concorrente. Para isso, foram avaliados três aspectos:

- impacto da quantidade de usuários virtuais no tempo de resposta;
- diferença de comportamento entre as implementações em Python e Ruby;
- efeito do uso de cache Redis sobre desempenho e estabilidade.

Como resultado complementar, o experimento também registra quantos links foram extraídos de cada URL testada. Essa informação ajuda a caracterizar a carga de trabalho, pois páginas com mais links tendem a produzir respostas maiores e podem exigir mais processamento.

## Descrição da aplicação

O serviço exposto pela aplicação segue o formato:

```text
GET /api/<url>
```

Ao receber uma requisição, a API consulta a página remota informada, interpreta o HTML e retorna uma lista de objetos JSON com os links encontrados. Cada objeto representa um link extraído da página.

As versões sem cache executam a extração a cada requisição. Nas versões com cache, o resultado da primeira extração é armazenado no Redis e pode ser reutilizado em chamadas posteriores para a mesma URL. Isso reduz a necessidade de acessar novamente a página externa e de reprocessar seu HTML.

## Estrutura do projeto

| Pasta ou arquivo | Finalidade |
| --- | --- |
| `step4/` | Serviço Python sem cache, com API e interface web em containers |
| `step5/` | Serviço Python com cache Redis |
| `step6/` | Serviço Ruby com cache Redis |
| `step6-nocache/` | Serviço Ruby sem cache |
| `locust/locustfile.py` | Modelo de usuário virtual usado nos testes de carga |
| `scripts/run_all_benchmarks.ps1` | Execução automatizada dos testes no Windows/PowerShell |
| `scripts/run_all_benchmarks.sh` | Execução automatizada dos testes no Linux, WSL ou Git Bash |
| `scripts/consolidate_results.py` | Consolidação dos CSVs gerados pelo Locust |
| `scripts/generate_graphs.py` | Geração dos gráficos finais |
| `results/` | Resultados brutos de cada rodada de teste |
| `consolidated/` | CSV e XLSX consolidados |
| `graphs/` | Gráficos finais em PNG |

## Ferramentas utilizadas

Os testes de carga foram executados com Locust. Essa ferramenta permite modelar usuários virtuais em Python e medir automaticamente métricas como quantidade de requisições, falhas, tempos de resposta e throughput.

Também foram utilizadas as seguintes ferramentas e bibliotecas:

- Docker e Docker Compose, para iniciar os ambientes de teste;
- Redis, nos cenários com cache;
- Pandas, para consolidação dos resultados;
- Matplotlib, para geração dos gráficos;
- OpenPyXL, para exportação da planilha Excel consolidada.

As dependências Python do ambiente de análise estão listadas em `requirements.txt`.

## Carga de trabalho

Cada usuário virtual executa uma sequência de requisições para 10 URLs predefinidas. As URLs estão declaradas em `locust/locustfile.py` e representam páginas reais com diferentes tamanhos e quantidades de links.

O comportamento executado por cada usuário virtual é:

```text
1. requisitar /api/<url_1>
2. requisitar /api/<url_2>
3. continuar até /api/<url_10>
4. repetir a sequência enquanto durar o teste
```

Durante a execução, o Locust também interpreta a resposta JSON de cada URL e registra a quantidade de links extraídos. Ao final de cada rodada, essa contagem é salva em um CSV próprio.

## Cenários avaliados

Foram avaliadas quatro configurações principais:

| Cenário | Pasta | Host testado | Linguagem | Cache |
| --- | --- | --- | --- | --- |
| `python_nocache` | `step4` | `http://localhost:5000` | Python | sem cache |
| `python_cache` | `step5` | `http://localhost:5000` | Python | com Redis |
| `ruby_nocache` | `step6-nocache` | `http://localhost:4567` | Ruby | sem cache |
| `ruby_cache` | `step6` | `http://localhost:4567` | Ruby | com Redis |

Para cada cenário, o teste é repetido com diferentes quantidades de usuários virtuais. No script PowerShell, usado para os resultados consolidados deste repositório, são utilizados 25, 75 e 125 usuários.

Nos cenários com cache, o script aquece previamente o Redis antes do início das medições. Esse aquecimento consiste em executar uma chamada para cada uma das 10 URLs. Assim, os resultados com cache representam majoritariamente o comportamento de consultas já armazenadas, evitando misturar misses iniciais com hits durante a medição principal.

## Procedimento experimental

O procedimento automatizado segue as seguintes etapas:

1. encerrar containers de cenários anteriores;
2. iniciar a composição Docker do cenário atual;
3. aguardar até que o serviço HTTP esteja disponível;
4. aquecer o Redis, quando o cenário possui cache;
5. executar o Locust em modo headless para cada quantidade de usuários;
6. salvar os CSVs e o relatório HTML de cada rodada em `results/`;
7. consolidar as métricas em `consolidated/resultados_consolidados.csv`;
8. exportar uma planilha em `consolidated/resultados_consolidados.xlsx`;
9. consolidar as contagens de links em `consolidated/links_extraidos_por_url.csv`;
10. gerar os gráficos finais em `graphs/`.

## Como executar

Antes de executar os testes, é necessário ter Docker, Docker Compose e Python disponíveis no ambiente.

Instale as dependências Python:

```powershell
pip install -r requirements.txt
```

No Windows/PowerShell:

```powershell
.\scripts\run_all_benchmarks.ps1
```

No Linux, WSL ou Git Bash:

```bash
bash scripts/run_all_benchmarks.sh
```

Ao final da execução, os principais artefatos estarão nas pastas `results/`, `consolidated/` e `graphs/`.

## Métricas coletadas

O arquivo `consolidated/resultados_consolidados.csv` contém as principais métricas de desempenho:

| Coluna | Significado |
| --- | --- |
| `scenario` | Nome do cenário testado |
| `language` | Linguagem da implementação avaliada |
| `cache` | Indica se o cenário usa cache |
| `users` | Quantidade de usuários virtuais |
| `requests` | Total de requisições executadas |
| `failures` | Total de requisições com falha |
| `failure_rate_percent` | Percentual de falhas em relação ao total de requisições |
| `median_response_ms` | Mediana do tempo de resposta |
| `average_response_ms` | Média do tempo de resposta |
| `min_response_ms` | Menor tempo de resposta observado |
| `max_response_ms` | Maior tempo de resposta observado |
| `p95_response_ms` | Percentil 95 do tempo de resposta |
| `p99_response_ms` | Percentil 99 do tempo de resposta |
| `rps` | Requisições por segundo |
| `failures_s` | Falhas por segundo |

A taxa de falhas é calculada pela fórmula:

```text
failure_rate_percent = (failures / requests) * 100
```

O arquivo `consolidated/links_extraidos_por_url.csv` contém a caracterização da carga por URL:

| Coluna | Significado |
| --- | --- |
| `scenario` | Nome do cenário testado |
| `language` | Linguagem da implementação |
| `cache` | Modo de cache |
| `users` | Quantidade de usuários virtuais da rodada |
| `url` | URL utilizada na extração |
| `extracted_links` | Quantidade de links retornados pela API para aquela URL |

## Gráficos gerados

A versão atual do relatório gráfico exibe apenas as métricas mais relevantes para a comparação final:

- `graphs/line_p95.png`: evolução do P95 conforme aumenta a quantidade de usuários;
- `graphs/bar_p95.png`: comparação do P95 entre cenários e cargas;
- `graphs/line_taxa_falhas.png`: evolução da taxa de falhas em porcentagem;
- `graphs/bar_taxa_falhas.png`: comparação da taxa de falhas entre cenários e cargas.

O P95 foi escolhido porque representa um comportamento de cauda mais adequado que a média para observar degradação percebida por usuários. A taxa de falhas em porcentagem facilita a comparação entre rodadas com quantidades diferentes de requisições.

## Análise dos resultados consolidados

Os resultados presentes em `consolidated/resultados_consolidados.csv` mostram diferenças claras entre os cenários com e sem cache.

Nos cenários com cache, tanto Python quanto Ruby apresentaram taxa de falhas igual a 0% nas rodadas consolidadas. Além disso, o throughput foi significativamente maior que nos cenários sem cache, pois a API deixou de depender da busca e do processamento completo das páginas remotas a cada chamada.

O cenário `ruby_cache` apresentou os maiores valores de requisições por segundo nos dados consolidados, mantendo P95 menor que os cenários sem cache. O cenário `python_cache` também se manteve estável, embora com P95 crescente conforme o número de usuários aumentou.

Nos cenários sem cache, o tempo de resposta foi mais elevado, especialmente quando a carga aumentou. Isso ocorre porque cada requisição precisa acessar a página externa, aguardar a resposta da rede, processar o HTML e montar o JSON de retorno. O cenário `ruby_nocache` também apresentou taxa de falhas relevante nas rodadas consolidadas, indicando maior sensibilidade sob carga quando o cache não está presente.

De forma geral, os resultados reforçam a importância do cache em uma aplicação distribuída que depende de recursos externos. Ao armazenar respostas já processadas, o sistema reduz latência, aumenta throughput e diminui a probabilidade de falhas causadas por tempo de resposta elevado ou indisponibilidade momentânea das páginas acessadas.

## Considerações finais

O experimento permitiu observar, de maneira prática, como escolhas arquiteturais afetam o desempenho de um serviço distribuído. A comparação entre implementações e modos de cache evidencia que o desempenho não depende apenas da linguagem utilizada, mas também da dependência de rede, do reuso de resultados e da forma como o sistema responde ao aumento da concorrência.

Como continuidade, seria possível ampliar a avaliação com mais níveis de carga, maior tempo de execução, repetições estatísticas por cenário e coleta de métricas de CPU, memória e uso de rede dos containers.
