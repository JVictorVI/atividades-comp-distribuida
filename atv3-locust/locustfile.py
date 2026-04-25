from locust import HttpUser, task, between
import os


class WordpressUser(HttpUser):
    wait_time = between(1, 3)

    # URLs dos posts criados no WordPress
    POST_IMAGEM_1MB = os.getenv("POST_IMAGEM_1MB", "/?p=1")
    POST_TEXTO_400KB = os.getenv("POST_TEXTO_400KB", "/?p=2")
    POST_IMAGEM_300KB = os.getenv("POST_IMAGEM_300KB", "/?p=3")

    @task(1)
    def post_imagem_1mb(self):
        self.client.get(
            self.POST_IMAGEM_1MB,
            name="Cenario 1 - Post imagem 1MB"
        )

    @task(1)
    def post_texto_400kb(self):
        self.client.get(
            self.POST_TEXTO_400KB,
            name="Cenario 2 - Post texto 400KB"
        )

    @task(1)
    def post_imagem_300kb(self):
        self.client.get(
            self.POST_IMAGEM_300KB,
            name="Cenario 3 - Post imagem 300KB"
        )