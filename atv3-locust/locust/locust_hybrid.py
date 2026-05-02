from locust import HttpUser, task

class HybridUser(HttpUser):

    @task
    def hybrid(self):
        self.client.get("/?name=imagem-300kb", name="leve")
        self.client.get("/?name=texto-400kb", name="medio")
        self.client.get("/?name=imagem-1mb", name="pesado")