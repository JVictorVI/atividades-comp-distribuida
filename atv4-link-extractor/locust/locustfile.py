from locust import HttpUser, task

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

class LinkExtractorUser(HttpUser):
    @task
    def extract_links_sequence(self):
        for url in URLS:
            self.client.get(f"/api/{url}", name="/api/<target>")
