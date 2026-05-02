from locust import HttpUser, task

class HeavyUser(HttpUser):

    @task
    def heavy(self):
        self.client.get("/?name=imagem-1mb", name="pesado")