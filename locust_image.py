"""Read-heavy Locust workload for the TeaStore Image Provider service (Person 5).

Targets image-heavy WebUI pages that trigger the internal Image Provider:
  - Category pages (product thumbnail grid)        — weight 5
  - Product detail pages (full-size product image) — weight 3
  - Home page (banner and category images)         — weight 2

Run via:
    ./run_image_tests.sh
Or manually:
    locust -f locust_image.py --host=http://localhost:8080 \
        --users 50 --spawn-rate 5 --run-time 2m --headless \
        --csv=results/image_service/raw/50_users --csv-full-history
"""

from locust import HttpUser, task, between
import random

WEBUI = "/tools.descartes.teastore.webui"

# TeaStore ships 5 categories (IDs 2-6) and 500 products (IDs 7-506)
CATEGORIES = [2, 3, 4, 5, 6]
PRODUCTS = list(range(7, 507))


class ImageServiceUser(HttpUser):
    """Simulates an image-heavy user: browses categories, product pages,
    and home — all of which trigger image fetches inside the TeaStore."""

    wait_time = between(0.5, 2)

    @task(5)
    def browse_category(self):
        """Category page renders a thumbnail grid — highest image load."""
        cid = random.choice(CATEGORIES)
        page = random.randint(1, 5)
        self.client.get(
            f"{WEBUI}/category?category={cid}&page={page}",
            name=f"{WEBUI}/category?category=[id]&page=[n]",
        )

    @task(3)
    def view_product(self):
        """Product detail page fetches the full-size product image."""
        pid = random.choice(PRODUCTS)
        self.client.get(
            f"{WEBUI}/product?id={pid}",
            name=f"{WEBUI}/product?id=[id]",
        )

    @task(2)
    def browse_home(self):
        """Home page loads banner + category hero images."""
        self.client.get(f"{WEBUI}/", name=f"{WEBUI}/home")
