from locust import HttpUser, task

class LightUser(HttpUser):

    @task
    def light(self):
        self.client.get("/?name=imagem-300kb", name="leve")