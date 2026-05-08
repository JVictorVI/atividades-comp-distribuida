import csv
import os
from threading import Lock

from locust import HttpUser, events, task

# Conjunto fixo de URLs usado em cada rodada do usuario virtual. A sequencia
# atende ao requisito da atividade de fazer 10 invocacoes com URLs diferentes.
URLS = [
    "https://www.foxnews.com", #911 links
    "https://cnn.com", #486 links
    "https://br.ign.com", #383 links 
    "https://www.estadao.com.br", #308 links
    "https://www12.senado.leg.br", #250 links
    "https://receitas.globo.com", #235 links 
    "https://www.tudogostoso.com.br", #208 links 
    "https://www.todamateria.com.br", #179 links 
    "https://canaltech.com.br", #155 links
    "https://kotaku.com" #136 links
]

# Estrutura compartilhada entre usuarios virtuais para registrar quantos links
# cada URL retornou. O Lock evita escrita concorrente no dicionario.
link_counts = {}
link_counts_lock = Lock()


@events.quitting.add_listener
def write_link_counts(environment, **kwargs):
    # Os scripts run_all_benchmarks definem este caminho antes de iniciar o
    # Locust. Se a variavel nao existir, o Locust roda normalmente sem CSV extra.
    output_file = os.getenv("LINK_COUNTS_CSV")
    if not output_file:
        return

    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    with link_counts_lock:
        rows = sorted(link_counts.items())

    with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=["url", "extracted_links"])
        writer.writeheader()
        for url, extracted_links in rows:
            writer.writerow({
                "url": url,
                "extracted_links": extracted_links,
            })


class LinkExtractorUser(HttpUser):
    @task
    def extract_links_sequence(self):
        # Cada execucao da tarefa percorre as 10 URLs em ordem. Depois que a
        # sequencia termina, o Locust pode iniciar outra enquanto durar o teste.
        for url in URLS:
            # O endpoint recebe a URL no proprio caminho. O name mantem a
            # metrica separada por URL no relatorio padrao do Locust.
            with self.client.get(f"/api/{url}", name=f"/api/{url}", catch_response=True) as response:
                try:
                    links = response.json()
                except ValueError as exc:
                    response.failure(f"Resposta JSON invalida para {url}: {exc}")
                    continue

                # Todas as versoes da API devem retornar uma lista JSON de links.
                # Qualquer outro formato conta como falha da rodada.
                if not isinstance(links, list):
                    response.failure(f"Resposta inesperada para {url}: esperado lista de links")
                    continue

                # Guarda a contagem mais recente de links extraidos dessa URL para
                # caracterizar a carga usada no experimento.
                with link_counts_lock:
                    link_counts[url] = len(links)
