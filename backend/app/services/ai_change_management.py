from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from app.domain.ai_change_management import (
    ExperimentMode, ExperimentStatus, PromotionRisk, PromotionStatus,
    classify_promotion_risk, compare_experiment_metrics, deterministic_cohort,
    sha256_json, validate_configuration_payload,
)
from app.models.ai_change_management import (
    AIChangeEventModel, AIConfigurationDriftEventModel, AIConfigurationPromotionModel,
    AIConfigurationSnapshotModel, AIExperimentAssignmentModel, AIExperimentModel,
    AIExperimentObservationModel,
)
from app.repositories.ai_change_management import AIChangeManagementRepository

ROOT = Path(__file__).resolve().parents[3]


def load_ai_change_policy() -> dict:
    return json.loads((ROOT / "config/ai_change_management_policy.json").read_text())


def ai_change_management_model_contract() -> dict:
    policy = load_ai_change_policy()
    return {
        "registry": "immutable-versioned-model-prompt-retrieval-snapshots",
        "environments": ["development", "staging", "production"],
        "configuration_types": ["model", "prompt", "retrieval", "bundle"],
        "promotion": policy["promotion"],
        "experiments": policy["experiments"],
        "quality_guardrails": policy["quality_guardrails"],
        "drift_detection": policy["drift_detection"],
        "privacy": "cohort subjects are SHA-256 identifiers; configuration snapshots may not contain secrets or runtime PHI",
        "runtime": "environment assignment points to an immutable approved snapshot; rollback changes the pointer, never rewrites a snapshot",
    }


class AIChangeManagementService:
    def __init__(self, repo: AIChangeManagementRepository):
        self.repo = repo
        self.policy = load_ai_change_policy()

    def _event(self, event_type: str, actor: str, subject_type: str, subject_id: str, details: dict) -> None:
        self.repo.add(AIChangeEventModel(
            event_id=f"aice_{uuid4().hex}", tenant_id=self.repo.tenant_id, event_type=event_type,
            actor_user_id=actor, subject_type=subject_type, subject_id=subject_id,
            details=details, details_sha256=sha256_json(details),
        ))

    def create_snapshot(self, *, actor: str, config_key: str, version: str, configuration_type: str, payload: dict,
                        parent_snapshot_id: str | None = None, evaluation_baseline_id: str | None = None,
                        evaluation_run_id: str | None = None):
        validate_configuration_payload(payload)
        snapshot = AIConfigurationSnapshotModel(
            snapshot_id=f"aicfg_{uuid4().hex}", tenant_id=self.repo.tenant_id,
            config_key=config_key, version=version, configuration_type=configuration_type,
            payload=payload, payload_sha256=sha256_json(payload), parent_snapshot_id=parent_snapshot_id,
            evaluation_baseline_id=evaluation_baseline_id, evaluation_run_id=evaluation_run_id, created_by=actor,
        )
        self.repo.add(snapshot)
        self._event("ai.config.snapshot.created", actor, "snapshot", snapshot.snapshot_id, {
            "config_key": config_key, "version": version, "configuration_type": configuration_type,
            "payload_sha256": snapshot.payload_sha256, "evaluation_run_id": evaluation_run_id,
        })
        return snapshot

    def resolve(self, *, environment: str, config_key: str):
        assignment = self.repo.assignment(environment, config_key)
        if assignment is None:
            return None
        snapshot = self.repo.snapshot(assignment.snapshot_id)
        if snapshot is None:
            raise RuntimeError("configuration assignment references a missing snapshot")
        return assignment, snapshot

    def request_promotion(self, *, actor: str, snapshot_id: str, target_environment: str,
                          evaluation_run_id: str | None, evaluation_decision: str | None):
        snapshot = self.repo.snapshot(snapshot_id)
        if snapshot is None:
            raise ValueError("configuration snapshot not found")
        risk = classify_promotion_risk(environment=target_environment, configuration_type=snapshot.configuration_type)
        if target_environment == "production":
            if not evaluation_run_id:
                raise ValueError("production promotion requires a passing linked evaluation run")
            evaluation = self.repo.evaluation_run(evaluation_run_id)
            if evaluation is None or evaluation.decision != "pass":
                raise ValueError("production promotion requires a passing linked evaluation run")
            if evaluation_decision is not None and evaluation_decision != evaluation.decision:
                raise ValueError("caller evaluation decision does not match authoritative evaluation run")
            evaluation_decision = evaluation.decision
        current = self.repo.assignment(target_environment, snapshot.config_key)
        status = PromotionStatus.PENDING_APPROVAL.value if risk == PromotionRisk.HIGH else PromotionStatus.APPROVED.value
        promotion = AIConfigurationPromotionModel(
            promotion_id=f"aiprom_{uuid4().hex}", tenant_id=self.repo.tenant_id, snapshot_id=snapshot.snapshot_id,
            config_key=snapshot.config_key, target_environment=target_environment, risk=risk.value, status=status,
            requested_by=actor, evaluation_run_id=evaluation_run_id, evaluation_decision=evaluation_decision,
            previous_snapshot_id=current.snapshot_id if current else None,
        )
        self.repo.add(promotion)
        self._event("ai.config.promotion.requested", actor, "promotion", promotion.promotion_id, {
            "snapshot_id": snapshot_id, "target_environment": target_environment, "risk": risk.value,
            "evaluation_run_id": evaluation_run_id,
        })
        if risk == PromotionRisk.STANDARD:
            self._activate_promotion(promotion, actor=actor, reason="standard-risk automatic activation after policy checks")
        return promotion

    def decide_promotion(self, *, actor: str, promotion_id: str, approve: bool, reason: str):
        promotion = self.repo.promotion(promotion_id)
        if promotion is None:
            raise ValueError("promotion not found")
        if promotion.status != PromotionStatus.PENDING_APPROVAL.value:
            raise ValueError("promotion is not pending approval")
        if actor == promotion.requested_by and self.policy["promotion"].get("prevent_self_approval", True):
            raise ValueError("promotion requester cannot self-approve a high-risk AI change")
        promotion.approved_by = actor
        promotion.approval_reason = reason
        if not approve:
            promotion.status = PromotionStatus.REJECTED.value
            self.repo.session.flush()
            self._event("ai.config.promotion.rejected", actor, "promotion", promotion_id, {"reason_sha256": sha256(reason.encode()).hexdigest()})
            return promotion
        return self._activate_promotion(promotion, actor=actor, reason=reason)

    def _activate_promotion(self, promotion, *, actor: str, reason: str):
        now = datetime.now(timezone.utc)
        self.repo.upsert_assignment(
            assignment_id=f"aiassign_{uuid4().hex}", environment=promotion.target_environment,
            config_key=promotion.config_key, snapshot_id=promotion.snapshot_id, actor=actor,
            activated_at=now, source="promotion",
        )
        promotion.status = PromotionStatus.ACTIVATED.value
        promotion.approved_by = promotion.approved_by or actor
        promotion.approval_reason = promotion.approval_reason or reason
        promotion.activated_at = now
        self.repo.session.flush()
        self._event("ai.config.promotion.activated", actor, "promotion", promotion.promotion_id, {
            "snapshot_id": promotion.snapshot_id, "previous_snapshot_id": promotion.previous_snapshot_id,
            "environment": promotion.target_environment,
        })
        return promotion

    def rollback(self, *, actor: str, environment: str, config_key: str, target_snapshot_id: str, reason: str):
        target = self.repo.snapshot(target_snapshot_id)
        if target is None or target.config_key != config_key:
            raise ValueError("rollback target snapshot not found for config key")
        current = self.repo.assignment(environment, config_key)
        if current is None:
            raise ValueError("no active configuration assignment to roll back")
        if not self.repo.previously_activated(environment=environment, config_key=config_key, snapshot_id=target_snapshot_id):
            raise ValueError("rollback target was never previously activated in this environment")
        previous_snapshot_id = current.snapshot_id
        self.repo.upsert_assignment(
            assignment_id=current.assignment_id, environment=environment, config_key=config_key,
            snapshot_id=target_snapshot_id, actor=actor, activated_at=datetime.now(timezone.utc), source="rollback",
        )
        self._event("ai.config.rollback.activated", actor, "assignment", current.assignment_id, {
            "environment": environment, "config_key": config_key, "from_snapshot_id": previous_snapshot_id,
            "to_snapshot_id": target_snapshot_id, "reason_sha256": sha256(reason.encode()).hexdigest(),
        })
        return current

    def create_experiment(self, *, actor: str, experiment_key: str, environment: str, mode: str,
                          champion_snapshot_id: str, challenger_snapshot_id: str, challenger_basis_points: int,
                          evaluation_baseline_id: str | None, guardrails: dict[str, float]):
        champion = self.repo.snapshot(champion_snapshot_id); challenger = self.repo.snapshot(challenger_snapshot_id)
        if not champion or not challenger:
            raise ValueError("experiment snapshots must exist")
        if champion.config_key != challenger.config_key:
            raise ValueError("champion and challenger must use the same configuration key")
        max_bp = int(self.policy["experiments"]["max_challenger_basis_points"])
        if challenger_basis_points > max_bp:
            raise ValueError("challenger allocation exceeds policy maximum")
        if environment == "production" and mode != ExperimentMode.SHADOW.value:
            active = self.repo.assignment(environment, champion.config_key)
            if active is None or active.snapshot_id != champion_snapshot_id:
                raise ValueError("production experiment champion must be the currently active configuration")
            if not challenger.evaluation_run_id:
                raise ValueError("production traffic experiment challenger requires a linked evaluation run")
            evaluation = self.repo.evaluation_run(challenger.evaluation_run_id)
            if evaluation is None or evaluation.decision != "pass":
                raise ValueError("production traffic experiment challenger requires a passing evaluation run")
            if self.policy["experiments"].get("production_non_shadow_requires_separate_approval", True):
                status = ExperimentStatus.DRAFT.value
            else:
                status = ExperimentStatus.RUNNING.value
        else:
            status = ExperimentStatus.RUNNING.value
        experiment = AIExperimentModel(
            experiment_id=f"aiexp_{uuid4().hex}", tenant_id=self.repo.tenant_id,
            experiment_key=experiment_key, environment=environment, mode=mode, status=status,
            champion_snapshot_id=champion_snapshot_id, challenger_snapshot_id=challenger_snapshot_id,
            challenger_basis_points=challenger_basis_points, shadow_only=(mode == ExperimentMode.SHADOW.value),
            evaluation_baseline_id=evaluation_baseline_id,
            guardrails={**self.policy["quality_guardrails"], **guardrails}, created_by=actor,
            started_at=datetime.now(timezone.utc) if status == ExperimentStatus.RUNNING.value else None,
        )
        self.repo.add(experiment)
        self._event("ai.experiment.created", actor, "experiment", experiment.experiment_id, {
            "mode": mode, "environment": environment, "challenger_basis_points": challenger_basis_points,
            "status": status,
        })
        return experiment

    def start_experiment(self, *, actor: str, experiment_id: str, approval_reason: str):
        experiment = self.repo.experiment(experiment_id)
        if not experiment or experiment.status != ExperimentStatus.DRAFT.value:
            raise ValueError("experiment is not a startable draft")
        if actor == experiment.created_by and self.policy["promotion"].get("prevent_self_approval", True):
            raise ValueError("experiment creator cannot self-approve a production traffic experiment")
        experiment.status = ExperimentStatus.RUNNING.value
        experiment.started_at = datetime.now(timezone.utc)
        self.repo.session.flush()
        self._event("ai.experiment.started", actor, "experiment", experiment_id, {"approval_reason_sha256": sha256(approval_reason.encode()).hexdigest()})
        return experiment

    def assign_experiment(self, *, experiment_id: str, subject_key: str):
        experiment = self.repo.experiment(experiment_id)
        if not experiment or experiment.status != ExperimentStatus.RUNNING.value:
            raise ValueError("experiment is not running")
        subject_sha = sha256(subject_key.encode()).hexdigest()
        existing = self.repo.experiment_assignment(experiment_id, subject_sha)
        if existing:
            return existing
        cohort = deterministic_cohort(
            tenant_id=self.repo.tenant_id, experiment_id=experiment_id, subject_key=subject_key,
            challenger_basis_points=experiment.challenger_basis_points,
        )
        snapshot_id = experiment.challenger_snapshot_id if cohort.variant == "challenger" else experiment.champion_snapshot_id
        assignment = AIExperimentAssignmentModel(
            assignment_id=f"aiexpa_{uuid4().hex}", tenant_id=self.repo.tenant_id, experiment_id=experiment_id,
            subject_sha256=subject_sha, bucket=cohort.bucket, variant=cohort.variant, snapshot_id=snapshot_id,
        )
        return self.repo.add(assignment)

    def resolve_for_subject(self, *, environment: str, config_key: str, experiment_id: str | None, subject_key: str | None) -> dict:
        resolved = self.resolve(environment=environment, config_key=config_key)
        if resolved is None:
            raise ValueError("no active configuration assignment")
        assignment, champion = resolved
        result = {
            "environment": environment, "config_key": config_key,
            "effective_snapshot_id": champion.snapshot_id, "effective_variant": "champion",
            "shadow_snapshot_id": None, "experiment_assignment_id": None,
            "assignment_version": assignment.assignment_version,
        }
        if not experiment_id:
            return result
        if not subject_key:
            raise ValueError("subject_key is required when resolving an experiment")
        experiment = self.repo.experiment(experiment_id)
        if not experiment or experiment.status != ExperimentStatus.RUNNING.value:
            raise ValueError("experiment is not running")
        if experiment.environment != environment or experiment.champion_snapshot_id != champion.snapshot_id:
            raise ValueError("experiment does not match the active environment configuration")
        cohort = self.assign_experiment(experiment_id=experiment_id, subject_key=subject_key)
        result["experiment_assignment_id"] = cohort.assignment_id
        if experiment.shadow_only:
            result["shadow_snapshot_id"] = experiment.challenger_snapshot_id
            result["effective_variant"] = "champion"
            return result
        result["effective_snapshot_id"] = cohort.snapshot_id
        result["effective_variant"] = cohort.variant
        return result

    def complete_experiment(self, *, actor: str, experiment_id: str) -> dict:
        experiment = self.repo.experiment(experiment_id)
        if not experiment or experiment.status != ExperimentStatus.RUNNING.value:
            raise ValueError("experiment is not running")
        summary = self.experiment_summary(experiment_id)
        experiment.status = ExperimentStatus.COMPLETED.value if summary["decision"] == "pass" else ExperimentStatus.PAUSED.value
        experiment.ended_at = datetime.now(timezone.utc)
        self.repo.session.flush()
        self._event("ai.experiment.completed" if summary["decision"] == "pass" else "ai.experiment.paused_by_guardrail", actor, "experiment", experiment_id, {
            "decision": summary["decision"], "reasons": summary["reasons"],
            "summary_sha256": sha256_json(summary),
        })
        return {**summary, "status": experiment.status}

    def observe_experiment(self, *, experiment_id: str, assignment_id: str | None, variant: str,
                           quality_score: float | None, latency_ms: float | None, cost_usd: float | None,
                           evaluation_run_id: str | None, trace_id: str | None, evidence_sha256: str):
        if not self.repo.experiment(experiment_id):
            raise ValueError("experiment not found")
        observation = AIExperimentObservationModel(
            observation_id=f"aiexpo_{uuid4().hex}", tenant_id=self.repo.tenant_id, experiment_id=experiment_id,
            assignment_id=assignment_id, variant=variant, quality_score=quality_score,
            latency_ms=latency_ms, cost_usd=cost_usd, evaluation_run_id=evaluation_run_id,
            trace_id=trace_id, evidence_sha256=evidence_sha256,
        )
        return self.repo.add(observation)

    def experiment_summary(self, experiment_id: str) -> dict:
        experiment = self.repo.experiment(experiment_id)
        if not experiment:
            raise ValueError("experiment not found")
        grouped: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
        for item in self.repo.observations(experiment_id):
            for key, value in (("quality", item.quality_score), ("latency_ms", item.latency_ms), ("cost_usd", item.cost_usd)):
                if value is not None:
                    grouped[item.variant][key].append(float(value))
        def avg(variant: str, key: str) -> float:
            values = grouped[variant][key]
            return sum(values) / len(values) if values else 0.0
        champion = {k: avg("champion", k) for k in ("quality", "latency_ms", "cost_usd")}
        challenger = {k: avg("challenger", k) for k in ("quality", "latency_ms", "cost_usd")}
        comparison = compare_experiment_metrics(champion=champion, challenger=challenger, guardrails=experiment.guardrails)
        return {"experiment_id": experiment_id, "champion": champion, "challenger": challenger, **comparison}

    def drift_check(self, *, actor: str, environment: str, config_key: str, observed_payload: dict):
        resolved = self.resolve(environment=environment, config_key=config_key)
        if resolved is None:
            raise ValueError("no active assignment")
        _, snapshot = resolved
        observed_sha = sha256_json(observed_payload)
        status = "in_sync" if observed_sha == snapshot.payload_sha256 else "drift_detected"
        event = AIConfigurationDriftEventModel(
            drift_event_id=f"aidrift_{uuid4().hex}", tenant_id=self.repo.tenant_id,
            environment=environment, config_key=config_key, expected_snapshot_id=snapshot.snapshot_id,
            observed_sha256=observed_sha, expected_sha256=snapshot.payload_sha256,
            status=status, detected_by=actor,
        )
        self.repo.add(event)
        if status == "drift_detected":
            self._event("ai.config.drift.detected", actor, "drift", event.drift_event_id, {
                "environment": environment, "config_key": config_key,
                "expected_snapshot_id": snapshot.snapshot_id, "observed_sha256": observed_sha,
                "expected_sha256": snapshot.payload_sha256,
            })
        return event

    def history(self, limit: int = 50) -> dict:
        return {
            "snapshots": [{"snapshot_id": x.snapshot_id, "config_key": x.config_key, "version": x.version,
                           "configuration_type": x.configuration_type, "payload_sha256": x.payload_sha256,
                           "evaluation_run_id": x.evaluation_run_id, "created_at": x.created_at} for x in self.repo.snapshots(limit)],
            "experiments": [{"experiment_id": x.experiment_id, "experiment_key": x.experiment_key,
                             "mode": x.mode, "status": x.status, "environment": x.environment,
                             "champion_snapshot_id": x.champion_snapshot_id,
                             "challenger_snapshot_id": x.challenger_snapshot_id} for x in self.repo.experiments(limit)],
            "drift": [{"drift_event_id": x.drift_event_id, "environment": x.environment, "config_key": x.config_key,
                       "status": x.status, "created_at": x.created_at} for x in self.repo.drift_events(limit)],
            "events": [{"event_id": x.event_id, "event_type": x.event_type, "actor_user_id": x.actor_user_id,
                        "subject_type": x.subject_type, "subject_id": x.subject_id,
                        "details_sha256": x.details_sha256, "created_at": x.created_at} for x in self.repo.events(limit * 2)],
        }
