from __future__ import annotations

from enum import StrEnum
from typing import Final

from pydantic import BaseModel, ConfigDict, Field


class TenantType(StrEnum):
    PAYER = "payer"
    PROVIDER = "provider"
    HOSPITAL = "hospital"
    TPA = "third_party_administrator"
    DEMO = "demo"


class TenantStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DISABLED = "disabled"


class AccountStatus(StrEnum):
    INVITED = "invited"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DISABLED = "disabled"


class UserRole(StrEnum):
    PATIENT = "patient"
    PROVIDER = "provider"
    HOSPITAL_ADMIN = "hospital_admin"
    CLAIMS_REVIEWER = "claims_reviewer"
    FINANCE_OPERATOR = "finance_operator"
    FINANCE_ANALYST = "finance_analyst"
    FINANCE_APPROVER = "finance_approver"
    ACCOUNTING_CONTROLLER = "accounting_controller"
    AUDITOR = "auditor"
    TENANT_ADMIN = "tenant_admin"
    SYSTEM_ADMIN = "system_admin"


class Permission(StrEnum):
    CLAIM_CREATE = "claim:create"
    CLAIM_READ = "claim:read"
    CLAIM_UPDATE = "claim:update"
    CLAIM_ASSIGN = "claim:assign"
    CLAIM_REVIEW = "claim:review"
    CLAIM_REQUEST_EVIDENCE = "claim:request_evidence"
    CLAIM_VIEW_AI_FINDINGS = "claim:view_ai_findings"
    CLAIM_EDIT_AI_RECOMMENDATION = "claim:edit_ai_recommendation"
    CLAIM_RECORD_HUMAN_DECISION = "claim:record_human_decision"
    FINANCIAL_READ = "financial:read"
    FINANCIAL_PREPARE = "financial:prepare"
    FINANCIAL_AUTHORIZE = "financial:authorize"
    ACCOUNTING_CLOSE = "accounting:close"

    EVIDENCE_UPLOAD = "evidence:upload"
    EVIDENCE_READ = "evidence:read"
    EVIDENCE_VERIFY = "evidence:verify"

    HOSPITAL_RECORD_READ = "hospital_record:read"
    HOSPITAL_RECORD_VERIFY = "hospital_record:verify"

    AUDIT_READ = "audit:read"
    AUDIT_EXPORT = "audit:export"

    TENANT_MEMBER_READ = "tenant_member:read"
    TENANT_MEMBER_MANAGE = "tenant_member:manage"
    TENANT_ROLE_MANAGE = "tenant_role:manage"
    TENANT_SETTINGS_MANAGE = "tenant_settings:manage"
    TENANT_GRANT_MANAGE = "tenant_grant:manage"

    SYSTEM_TENANT_READ = "system_tenant:read"
    SYSTEM_TENANT_MANAGE = "system_tenant:manage"
    SYSTEM_HEALTH_READ = "system_health:read"


class ResourceType(StrEnum):
    CLAIM = "claim"
    EVIDENCE = "evidence"
    HOSPITAL_RECORD = "hospital_record"
    AUDIT_EVENT = "audit_event"
    TENANT_MEMBER = "tenant_member"
    TENANT_SETTINGS = "tenant_settings"
    TENANT = "tenant"
    SYSTEM_HEALTH = "system_health"


class AccessReason(StrEnum):
    ALLOW_ROLE_PERMISSION = "allow_role_permission"
    ALLOW_PATIENT_OWNERSHIP = "allow_patient_ownership"
    ALLOW_PROVIDER_RELATIONSHIP = "allow_provider_relationship"
    ALLOW_ASSIGNED_REVIEWER = "allow_assigned_reviewer"
    ALLOW_EXPLICIT_TENANT_GRANT = "allow_explicit_tenant_grant"
    ALLOW_SYSTEM_SCOPE = "allow_system_scope"

    DENY_INACTIVE_PRINCIPAL = "deny_inactive_principal"
    DENY_TENANT_INACTIVE = "deny_tenant_inactive"
    DENY_PERMISSION_NOT_IN_ROLE = "deny_permission_not_in_role"
    DENY_CROSS_TENANT = "deny_cross_tenant"
    DENY_PATIENT_NOT_OWNER = "deny_patient_not_owner"
    DENY_PROVIDER_NOT_RELATED = "deny_provider_not_related"
    DENY_REVIEWER_NOT_ASSIGNED = "deny_reviewer_not_assigned"
    DENY_RESOURCE_SCOPE = "deny_resource_scope"


class Tenant(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_id: str = Field(min_length=3, max_length=64)
    display_name: str = Field(min_length=2, max_length=160)
    tenant_type: TenantType
    status: TenantStatus = TenantStatus.ACTIVE


class UserAccount(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str = Field(min_length=3, max_length=128)
    external_issuer: str = Field(min_length=8, max_length=512)
    external_subject: str = Field(min_length=3, max_length=256)
    display_name: str = Field(min_length=1, max_length=160)
    status: AccountStatus = AccountStatus.INVITED


class TenantMembership(BaseModel):
    model_config = ConfigDict(extra="forbid")

    membership_id: str = Field(min_length=3, max_length=128)
    user_id: str = Field(min_length=3, max_length=128)
    tenant_id: str = Field(min_length=3, max_length=64)
    role: UserRole
    patient_subject_id: str | None = None
    provider_organization_id: str | None = None


class ResourceGrant(BaseModel):
    """Resolved cross-tenant grant for one protected resource context.

    Expiry/revocation is evaluated by persistence before this model is created; the
    authorization engine receives only an `is_active` result plus permission scope.
    """

    model_config = ConfigDict(extra="forbid")

    grant_id: str = Field(min_length=3, max_length=128)
    grantee_tenant_id: str = Field(min_length=3, max_length=64)
    permissions: frozenset[Permission]
    is_active: bool = True


class Principal(BaseModel):
    """Authenticated identity attributes used by the authorization engine.

    Authentication is intentionally separate from authorization. In production these
    attributes are derived from verified identity/session claims and server-side data,
    never trusted from a client request body.
    """

    model_config = ConfigDict(extra="forbid")

    user_id: str = Field(min_length=3, max_length=128)
    tenant_id: str = Field(min_length=3, max_length=64)
    role: UserRole
    is_active: bool = True
    patient_subject_id: str | None = None
    provider_organization_id: str | None = None


class ResourceAccessContext(BaseModel):
    """Server-resolved resource attributes used for ABAC decisions."""

    model_config = ConfigDict(extra="forbid")

    resource_type: ResourceType
    resource_id: str = Field(min_length=1, max_length=160)
    owner_tenant_id: str = Field(min_length=3, max_length=64)
    owner_patient_subject_id: str | None = None
    related_provider_organization_id: str | None = None
    assigned_reviewer_user_id: str | None = None
    cross_tenant_grants: tuple[ResourceGrant, ...] = ()


class AccessRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    principal: Principal
    permission: Permission
    resource: ResourceAccessContext
    tenant_status: TenantStatus = TenantStatus.ACTIVE


class AccessDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    allowed: bool
    reason: AccessReason
    policy_id: str = "medclaimiq.authz.v1"


ROLE_DESCRIPTIONS: Final[dict[UserRole, str]] = {
    UserRole.PATIENT: "Claim subject who can access only their own scoped claim experience.",
    UserRole.PROVIDER: "Provider participant scoped to claims/evidence linked to their organization.",
    UserRole.HOSPITAL_ADMIN: "Hospital operational user for record verification and evidence workflows.",
    UserRole.CLAIMS_REVIEWER: "Human claims reviewer responsible for evidence review and final human action.",
    UserRole.FINANCE_OPERATOR: "Human finance operator who prepares and stages already-adjudicated claim payment instructions.",
    UserRole.FINANCE_ANALYST: "Human finance analyst with read/preparation access but no fund authorization authority.",
    UserRole.FINANCE_APPROVER: "Independent human finance approver responsible for segregation-of-duties authorization.",
    UserRole.ACCOUNTING_CONTROLLER: "Human accounting controller responsible for governed period close and ledger oversight.",
    UserRole.AUDITOR: "Read-only governance user for audit and compliance review.",
    UserRole.TENANT_ADMIN: "Tenant identity/configuration administrator without implicit claim/evidence access.",
    UserRole.SYSTEM_ADMIN: "Platform administrator without implicit medical-claim or evidence access.",
}


ROLE_PERMISSIONS: Final[dict[UserRole, frozenset[Permission]]] = {
    UserRole.PATIENT: frozenset(
        {
            Permission.CLAIM_CREATE,
            Permission.CLAIM_READ,
            Permission.EVIDENCE_UPLOAD,
            Permission.EVIDENCE_READ,
        }
    ),
    UserRole.PROVIDER: frozenset(
        {
            Permission.CLAIM_CREATE,
            Permission.CLAIM_READ,
            Permission.CLAIM_UPDATE,
            Permission.CLAIM_REQUEST_EVIDENCE,
            Permission.EVIDENCE_UPLOAD,
            Permission.EVIDENCE_READ,
            Permission.HOSPITAL_RECORD_READ,
        }
    ),
    UserRole.HOSPITAL_ADMIN: frozenset(
        {
            Permission.CLAIM_READ,
            Permission.CLAIM_REQUEST_EVIDENCE,
            Permission.EVIDENCE_UPLOAD,
            Permission.EVIDENCE_READ,
            Permission.EVIDENCE_VERIFY,
            Permission.HOSPITAL_RECORD_READ,
            Permission.HOSPITAL_RECORD_VERIFY,
        }
    ),
    UserRole.CLAIMS_REVIEWER: frozenset(
        {
            Permission.CLAIM_READ,
            Permission.CLAIM_UPDATE,
            Permission.CLAIM_ASSIGN,
            Permission.CLAIM_REVIEW,
            Permission.CLAIM_REQUEST_EVIDENCE,
            Permission.CLAIM_VIEW_AI_FINDINGS,
            Permission.CLAIM_EDIT_AI_RECOMMENDATION,
            Permission.CLAIM_RECORD_HUMAN_DECISION,
            Permission.EVIDENCE_READ,
            Permission.EVIDENCE_VERIFY,
            Permission.HOSPITAL_RECORD_READ,
        }
    ),
    UserRole.FINANCE_OPERATOR: frozenset({Permission.CLAIM_READ, Permission.FINANCIAL_READ, Permission.FINANCIAL_PREPARE}),
    UserRole.FINANCE_ANALYST: frozenset({Permission.CLAIM_READ, Permission.FINANCIAL_READ, Permission.FINANCIAL_PREPARE}),
    UserRole.FINANCE_APPROVER: frozenset({Permission.CLAIM_READ, Permission.FINANCIAL_READ, Permission.FINANCIAL_AUTHORIZE}),
    UserRole.ACCOUNTING_CONTROLLER: frozenset({Permission.CLAIM_READ, Permission.FINANCIAL_READ, Permission.ACCOUNTING_CLOSE, Permission.AUDIT_READ}),
    UserRole.AUDITOR: frozenset(
        {
            Permission.AUDIT_READ,
            Permission.AUDIT_EXPORT,
            Permission.SYSTEM_HEALTH_READ,
        }
    ),
    UserRole.TENANT_ADMIN: frozenset(
        {
            Permission.TENANT_MEMBER_READ,
            Permission.TENANT_MEMBER_MANAGE,
            Permission.TENANT_ROLE_MANAGE,
            Permission.TENANT_SETTINGS_MANAGE,
            Permission.TENANT_GRANT_MANAGE,
            Permission.AUDIT_READ,
        }
    ),
    UserRole.SYSTEM_ADMIN: frozenset(
        {
            Permission.SYSTEM_TENANT_READ,
            Permission.SYSTEM_TENANT_MANAGE,
            Permission.SYSTEM_HEALTH_READ,
        }
    ),
}
