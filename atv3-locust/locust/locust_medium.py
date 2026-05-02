from locust import HttpUser, task

class MediumUser(HttpUser):

    @task
    def medium(self):
        self.client.get("/?name=texto-400kb", name="medio")