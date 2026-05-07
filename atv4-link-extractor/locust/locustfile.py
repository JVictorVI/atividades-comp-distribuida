import csv
import os
from threading import Lock

from locust import HttpUser, events, task

URLS = [
    "https://www.tudogostoso.com.br", #197.995 
    "https://www.dictionary.com", #186.679
    "https://canaltech.com.br", #145.405
    "https://br.ign.com", #111.828
    "https://kotaku.com", #107.614
    "https://receitas.globo.com", #101.434 
    "https://g1.globo.com", #79.895
    "https://cnn.com", #58.036
    "https://huggingface.co", #32.932
    "https://www.todamateria.com.br", #14.543 
]

link_counts = {}
link_counts_lock = Lock()


@events.quitting.add_listener
def write_link_counts(environment, **kwargs):
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
        for url in URLS:
            with self.client.get(f"/api/{url}", name=f"/api/{url}", catch_response=True) as response:
                try:
                    links = response.json()
                except ValueError as exc:
                    response.failure(f"Resposta JSON invalida para {url}: {exc}")
                    continue

                if not isinstance(links, list):
                    response.failure(f"Resposta inesperada para {url}: esperado lista de links")
                    continue

                with link_counts_lock:
                    link_counts[url] = len(links)
