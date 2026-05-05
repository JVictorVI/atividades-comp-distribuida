# Atividade 4 - Link Extractor

Este projeto executa testes de desempenho da aplicacao Link Extractor conforme o enunciado do Trabalho 4.

## Ferramenta

Os testes usam Locust. Cada usuario virtual executa uma sequencia de 10 invocacoes ao servico de extracao de links, sempre chamando diretamente a API:

```text
GET /api/<url>
```

As 10 URLs usadas no comportamento do usuario virtual estao em `locust/locustfile.py`.

## Cenarios

Os cenarios variam os tres fatores pedidos no enunciado:

- Quantidade de usuarios virtuais: 25, 75 e 150
- Versao do servico de extracao: Python e Ruby
- Uso de cache: sem cache e com cache

Mapeamento dos cenarios:

| Cenario | Pasta | Host testado | Cache |
| --- | --- | --- | --- |
| `python_nocache` | `step4` | `http://localhost:5000` | sem cache |
| `python_cache` | `step5` | `http://localhost:5000` | com Redis |
| `ruby_nocache` | `step6-nocache` | `http://localhost:4567` | sem cache |
| `ruby_cache` | `step6` | `http://localhost:4567` | com Redis |

Nos cenarios com cache, o script aquece previamente o Redis com as 10 URLs antes de iniciar as medicoes. Assim, o grafico "com cache" mede o comportamento esperado do servico usando respostas cacheadas, em vez de misturar misses iniciais com hits.

## Rodar testes

No Windows/PowerShell:

```powershell
.\scripts\run_all_benchmarks.ps1
```

No Linux, WSL ou Git Bash:

```bash
bash scripts/run_all_benchmarks.sh
```

O script sobe cada composicao Docker, executa os testes do Locust para cada quantidade de usuarios, salva os CSVs em `results/`, consolida as metricas em `consolidated/resultados_consolidados.csv` e gera os graficos em `graphs/`.

## Metricas

- Quantidade de requisicoes
- Falhas
- Media do tempo de resposta
- Mediana do tempo de resposta
- Percentis P95 e P99
- Throughput em requisicoes por segundo
