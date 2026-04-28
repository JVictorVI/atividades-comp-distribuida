from locust import HttpUser, task, between

class HeavyUser(HttpUser):
    wait_time = between(2, 4)

    @task
    def heavy(self):
        self.client.get("/?name=imagem-com-1mb", name="pesado")