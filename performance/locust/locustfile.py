from __future__ import annotations
import os
from locust import HttpUser, between, task

TOKEN = os.getenv("ACCESS_TOKEN", "")
TENANT = os.getenv("TENANT_ID", "tenant-synthetic")
CLAIM_ID = os.getenv("CLAIM_ID", "claim-synthetic")


class ReviewerJourney(HttpUser):
    wait_time = between(0.3, 1.5)
    weight = 2

    def on_start(self):
        self.client.headers.update({"Authorization": f"Bearer {TOKEN}", "X-Tenant-Id": TENANT})

    @task(4)
    def queue(self):
        self.client.get("/api/v1/review/queue", name="review.queue", timeout=5)

    @task(2)
    def workbench(self):
        self.client.get(f"/api/v1/claims/{CLAIM_ID}/review/workbench", name="review.workbench", timeout=8)

    @task(1)
    def sla_countdowns(self):
        self.client.get(f"/api/v1/claims/{CLAIM_ID}/sla/countdowns", name="sla.countdowns", timeout=5)


class PortalJourney(HttpUser):
    wait_time = between(0.5, 2.0)
    weight = 3

    def on_start(self):
        self.client.headers.update({"Authorization": f"Bearer {TOKEN}", "X-Tenant-Id": TENANT})

    @task(3)
    def claim_list(self):
        self.client.get("/api/v1/portal/claims", name="portal.claims", timeout=5)

    @task(1)
    def claim_detail(self):
        self.client.get(f"/api/v1/portal/claims/{CLAIM_ID}", name="portal.claim", timeout=5)
