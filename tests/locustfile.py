from locust import HttpUser, task, between, tag
import random

class BalanceUser(HttpUser):
    wait_time = between(0.01, 0.05)

    @tag("dual_write")
    @task
    def test_dual_write(self):
        self.client.post(f"/balance/dual-write?user_id={random.randint(1, 1000)}&amount=10", name="Dual Write")

    @tag("tx_dual_write")
    @task
    def test_tx_dual_write(self):
        self.client.post(f"/balance/tx-dual-write?user_id={random.randint(1, 1000)}&amount=10", name="Transactional Dual Write")

    @tag("outbox")
    @task
    def test_outbox(self):
        self.client.post(f"/balance/outbox-write?user_id={random.randint(1, 1000)}&amount=10", name="Transactional Outbox")

    @tag("cdc")
    @task
    def test_cdc(self):
        self.client.post(f"/balance/cdc-write?user_id={random.randint(1, 1000)}&amount=10", name="Change Data Capture")