from locust import HttpUser, task

class MediumUser(HttpUser):

    @task
    def medium(self):
        self.client.get("/?name=texto-de-400kb", name="medio")