from locust import HttpUser, task

class HybridUser(HttpUser):

    @task
    def hybrid(self):
        self.client.get("/?name=post-300kb", name="leve")
        self.client.get("/?name=post-400kb", name="medio")
        self.client.get("/?name=post-1mb", name="pesado")