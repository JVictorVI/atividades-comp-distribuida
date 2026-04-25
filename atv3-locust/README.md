# Trabalho 3 – Testes de Carga com WordPress e Locust

## Descrição

Este projeto tem como objetivo realizar **testes de carga em um ambiente com múltiplas instâncias do WordPress**, utilizando o **Locust** como ferramenta de geração de carga.

A arquitetura foi herdada do Trabalho 2, composta por:

- 1 Nginx (balanceador de carga)
- 1 MySQL (banco compartilhado)
- 1 a 3 instâncias do WordPress
- 1 container Locust (geração de carga)

---

## Arquitetura

- O Nginx distribui requisições entre múltiplas instâncias do WordPress.
- Todas as instâncias compartilham:
  - Banco MySQL
  - Volume de arquivos (`html`)

- O MySQL utiliza **volume persistente**, garantindo que os dados não sejam perdidos entre execuções.

---

## Arquivos principais

| Arquivo              | Função                                          |
| -------------------- | ----------------------------------------------- |
| `docker-compose.yml` | Define MySQL, WordPress, Nginx e Locust         |
| `nginx-1.conf`       | Nginx com 1 instância WordPress                 |
| `nginx-2.conf`       | Nginx com 2 instâncias WordPress                |
| `nginx-3.conf`       | Nginx com 3 instâncias WordPress                |
| `nginx.conf`         | Configuração ativa usada pelo Nginx             |
| `locustfile.py`      | Script com os cenários de carga                 |
| `run_benchmarks.sh`  | Executa todos os testes no Linux/macOS/Git Bash |
| `run_benchmarks.ps1` | Executa todos os testes no PowerShell           |
| `generate_graphs.py` | Gera gráficos a partir dos CSVs do Locust       |

---

## Persistência de Dados

O banco de dados é persistido via volume Docker:

```yaml
mysql:
  volumes:
    - mysql_data:/var/lib/mysql

volumes:
  mysql_data:
```

Importante:

```bash
docker compose down
```

Não use:

```bash
docker compose down -v
```

Pois isso apagará o banco de dados.

---

## Como Executar

### 1. Subir o ambiente

```bash
docker compose up -d
```

Aguarde cerca de **60 segundos** para inicialização completa.

---

### 2. Criar os posts de teste

Crie **3 posts no WordPress**, com os seguintes slugs:

| Cenário | Conteúdo      | Slug              |
| ------- | ------------- | ----------------- |
| 1       | Imagem ~1MB   | `imagem-com-1mb`  |
| 2       | Texto ~400KB  | `texto-de-400kb`  |
| 3       | Imagem ~300KB | `imagem-de-300kb` |

---

### 3. Validar acesso

Teste no navegador:

```text
http://localhost/?name=imagem-com-1mb
http://localhost/?name=texto-de-400kb
http://localhost/?name=imagem-de-300kb
```

Se abrir corretamente, os testes funcionarão.

---

## Execução dos Testes

Windows PowerShell

```bash
powershell -ExecutionPolicy Bypass -File .\run_benchmarks.ps1
```

ou (Linux/macOS):

```bash
bash run_benchmarks.sh
```

---

## O que o script faz

Para cada combinação:

- Instâncias: 1, 2, 3
- Usuários: 10, 100, 1000

Ele:

1. Ajusta o Nginx automaticamente
2. Sobe o ambiente correto
3. Executa o Locust
4. Salva resultados em CSV

---

## Resultados

Os resultados são gerados em:

```text
/results
```

Exemplo:

```text
result_1inst_10users_stats.csv
result_3inst_1000users_stats.csv
```

---

## Geração de Gráficos

Execute:

```bash
python generate_graphs.py
```

Os gráficos serão salvos em:

```text
/graphs
```

---

## Consolidação dos Resultados

Execute:

```bash
python consolidate_results.py
```

Saída:

```text
/consolidated/resultados_consolidados.csv
/consolidated/resultados_consolidados.xlsx
```

---

## Validação dos Testes

Os testes são considerados válidos quando:

- Todos os cenários aparecem no CSV
- `Request Count > 0`
- `Failure Count = 0`
- Status HTTP = 200

---

## Problemas Comuns

### 404 Not Found

Causa:

- Post não existe
- URL incorreta
- Permalinks não configurados

Solução:

- Usar:

```text
/?name=slug-do-post
```

---

### Nginx não encontra instâncias

Causa:

- Configuração de upstream incorreta

Solução:

- Usar arquivos `nginx-1.conf`, `nginx-2.conf`, `nginx-3.conf`

---

### Locust não gera CSV

Causa:

- Pasta `results` inexistente

Solução:

```bash
mkdir results
```

---

## Métricas coletadas

O Locust gera arquivos CSV com métricas como:

- número de requisições;
- número de falhas;
- tempo médio de resposta;
- mediana;
- percentis de latência;
- requisições por segundo;
- falhas por segundo.

As principais métricas para análise são:

| Métrica                 | Interpretação                                              |
| ----------------------- | ---------------------------------------------------------- |
| Tempo médio de resposta | Quanto tempo, em média, o WordPress levou para responder   |
| Percentil 95            | Tempo abaixo do qual 95% das requisições foram respondidas |
| Requisições por segundo | Vazão do sistema durante o teste                           |
| Falhas                  | Quantidade de erros durante a execução                     |

---
