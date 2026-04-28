from locust import HttpUser, task, between

class LightUser(HttpUser):
    wait_time = between(1, 2)

    @task
    def light(self):
        self.client.get("/?name=imagem-com-300kb", name="leve")