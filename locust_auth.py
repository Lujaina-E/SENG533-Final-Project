from locust import HttpUser, task, between
import random

class AuthUser(HttpUser):
    wait_time = between(1, 3)

    # authentication workload

    @task(1)
    def home(self):
        self.client.get("/login")

    @task(5)
    def login(self):
            user = f"user{random.randint(1,50)}"
            self.client.post(
                "/loginAction",
                data={"username": user, "password": "password", "signin": "Sign in"}
            )

    @task(2)
    def profile(self):
         self.client.get("/profile")

    

