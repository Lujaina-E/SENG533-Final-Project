from locust import HttpUser, task, between
import random

class TeaStoreUser(HttpUser):
    wait_time = between(1, 2)

    # Recommender-heavy workload

    @task(6)
    def view_product(self):
        product_id = random.randint(1, 50)
        self.client.get(f"/product?id={product_id}")

    @task(2)
    def browse_category(self):
        category_id = random.randint(1, 5)
        self.client.get(f"/category?id={category_id}")

    @task(1)
    def browse_home(self):
        self.client.get("/")

    @task(1)
    def login(self):
        self.client.post(
            "/loginAction",
            data={"username": "user", "password": "password"}
        )
