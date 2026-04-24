from locust import HttpUser, task, between
import random

CATEGORIES = [2, 3, 4, 5, 6]
PRODUCTS = list(range(7, 507))

class TeaStoreUser(HttpUser):
    wait_time = between(0.5, 1.5)

    @task(3)
    def browse_home(self):
        self.client.get("/", name="Home")

    @task(5)
    def browse_category(self):
        cid = random.choice(CATEGORIES)
        page = random.randint(1, 5)
        self.client.get(f"/category?category={cid}&page={page}", name="Category")

    @task(7)
    def view_product(self):
        pid = random.choice(PRODUCTS)
        self.client.get(f"/product?id={pid}", name="Product")
