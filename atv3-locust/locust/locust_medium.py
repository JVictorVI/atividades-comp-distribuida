from locust import HttpUser, task, between

class MediumUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def medium(self):
        self.client.get("/?name=texto-de-400kb", name="medio")