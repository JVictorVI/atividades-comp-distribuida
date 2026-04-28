from locust import HttpUser, task, between

class HybridUser(HttpUser):
    wait_time = between(1, 2)

    @task
    def hybrid(self):
        self.client.get("/?name=imagem-com-300kb", name="leve")
        self.client.get("/?name=texto-de-400kb", name="medio")
        self.client.get("/?name=imagem-com-1mb", name="pesado")