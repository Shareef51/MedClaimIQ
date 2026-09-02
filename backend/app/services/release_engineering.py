from __future__ import annotations
import json
from pathlib import Path
from app.repositories.release_engineering import ReleaseEngineeringRepository

ROOT = Path(__file__).resolve().parents[3]


def load_release_policy() -> dict:
    return json.loads((ROOT / "config/release_engineering_policy.json").read_text())


def release_engineering_model_contract() -> dict:
    policy = load_release_policy()
    return {
        "delivery_model": "gitops-immutable-digest-promotion",
        "gitops": policy["gitops"],
        "required_gates": policy["gates"]["required"],
        "migration_strategy": policy["migrations"]["strategy"],
        "progressive_delivery": policy["progressive_delivery"],
        "production_approval": {
            "required": policy["promotion"]["production_human_approval_required"],
            "environment_protection": "github-environment-required-reviewers",
        },
        "rollback": policy["rollback"],
        "audit": policy["audit"],
    }


class ReleaseEngineeringService:
    def __init__(self, repo: ReleaseEngineeringRepository):
        self.repo = repo

    def history(self, limit: int = 50) -> dict:
        manifests = self.repo.manifests(limit)
        deployments = self.repo.deployments(limit * 2)
        return {
            "releases": [
                {
                    "release_id": x.release_id,
                    "git_sha": x.git_sha,
                    "api_image_digest": x.api_image_digest,
                    "frontend_image_digest": x.frontend_image_digest,
                    "alembic_head": x.alembic_head,
                    "manifest_sha256": x.manifest_sha256,
                    "released_at": x.released_at,
                } for x in manifests
            ],
            "deployments": [
                {
                    "deployment_id": x.deployment_id,
                    "release_id": x.release_id,
                    "environment": x.environment,
                    "strategy": x.strategy,
                    "status": x.status,
                    "desired_state_sha": x.desired_state_sha,
                    "rollback_triggered": x.rollback_triggered,
                    "started_at": x.started_at,
                    "completed_at": x.completed_at,
                } for x in deployments
            ],
        }
