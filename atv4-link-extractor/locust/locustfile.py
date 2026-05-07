import csv
import os
from threading import Lock

from locust import HttpUser, events, task

URLS = [
    "https://g1.globo.com", #682 links
    "https://cnn.com", #486 links
    "https://br.ign.com", #383 links 
    "https://gshow.globo.com", #284 links
    "https://www12.senado.leg.br", #250 links
    "https://receitas.globo.com", #235 links 
    "https://www.tudogostoso.com.br", #208 links 
    "https://www.todamateria.com.br", #179 links 
    "https://canaltech.com.br", #155 links
    "https://kotaku.com" #136 links
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
