from locust import HttpUser, task, between, constant
import random

BASE = "/tools.descartes.teastore.persistence/rest"

class PersistenceUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        self.user_id = random.randint(57, 156)
        self.product_ids = list(range(7, 57))

    @task(3)
    def get_user(self):
        self.client.get(f"{BASE}/users/{self.user_id}", name="GET /users/[id]")

    @task(2)
    def get_user_orders(self):
        self.client.get(f"{BASE}/orders/user/{self.user_id}", name="GET /orders/user/[id]")

    @task(3)
    def create_order(self):
        payload = {
            "userId": self.user_id,
            "time": "2024-01-01T00:00:00",
            "totalPriceInCents": random.randint(500, 20000)
        }
        with self.client.post(f"{BASE}/orders", json=payload,
                               name="POST /orders", catch_response=True) as r:
            if r.status_code == 201:
                order_id = int(r.text.strip())
                if order_id > 0:
                    self._add_order_item(order_id)
                    r.success()
                else:
                    r.failure("Got -1")
            else:
                r.failure(f"Status {r.status_code}")

    def _add_order_item(self, order_id):
        payload = {
            "orderId": order_id,
            "productId": random.choice(self.product_ids),
            "quantity": random.randint(1, 3),
            "unitPriceInCents": random.randint(200, 5000)
        }
        self.client.post(f"{BASE}/orderitems", json=payload, name="POST /orderitems")

    @task(1)
    def get_product(self):
        pid = random.choice(self.product_ids)
        self.client.get(f"{BASE}/products/{pid}", name="GET /products/[id]")