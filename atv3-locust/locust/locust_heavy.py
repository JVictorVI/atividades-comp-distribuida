from locust import HttpUser, task

class HeavyUser(HttpUser):

    @task
    def heavy(self):
        self.client.get("/?name=post-1mb", name="pesado")