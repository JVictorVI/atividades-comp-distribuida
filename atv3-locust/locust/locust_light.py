from locust import HttpUser, task

class LightUser(HttpUser):

    @task
    def light(self):
        self.client.get("/?name=post-300kb", name="leve")