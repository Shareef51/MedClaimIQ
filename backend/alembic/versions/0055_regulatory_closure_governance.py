"""executive certification enterprise closure and sustainability assurance
Revision ID: 0055_reg_closure_governance
Revises: 0054_reg_deficiency_lifecycle
"""
from alembic import op
import sqlalchemy as sa
revision="0055_reg_closure_governance"; down_revision="0054_reg_deficiency_lifecycle"; branch_labels=None; depends_on=None

def upgrade():
    op.create_table("regulatory_closure_packages",
      sa.Column("package_id",sa.String(128),primary_key=True),sa.Column("tenant_id",sa.String(128),sa.ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False,index=True),sa.Column("deficiency_key",sa.String(160),nullable=False,index=True),sa.Column("corrective_action_refs",sa.JSON(),nullable=False),sa.Column("retest_refs",sa.JSON(),nullable=False),sa.Column("independent_validation_refs",sa.JSON(),nullable=False),sa.Column("regulatory_commitment_refs",sa.JSON(),nullable=False),sa.Column("unresolved_exceptions",sa.JSON(),nullable=False),sa.Column("compensating_control_exit",sa.JSON(),nullable=False),sa.Column("residual_risk",sa.JSON(),nullable=False),sa.Column("readiness_score",sa.Integer(),nullable=False),sa.Column("status",sa.String(32),nullable=False),sa.Column("created_by_user_id",sa.String(128),sa.ForeignKey("user_accounts.user_id",ondelete="RESTRICT"),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False))
    op.create_table("regulatory_closure_certifications",
      sa.Column("certification_id",sa.String(128),primary_key=True),sa.Column("tenant_id",sa.String(128),sa.ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False,index=True),sa.Column("deficiency_key",sa.String(160),nullable=False,index=True),sa.Column("version",sa.Integer(),nullable=False),sa.Column("conclusion",sa.String(32),nullable=False),sa.Column("rationale",sa.Text(),nullable=False),sa.Column("human_certification",sa.Boolean(),nullable=False),sa.Column("certified_by_user_id",sa.String(128),sa.ForeignKey("user_accounts.user_id",ondelete="RESTRICT"),nullable=False),sa.Column("certified_at",sa.DateTime(timezone=True),nullable=False),sa.UniqueConstraint("tenant_id","deficiency_key","version",name="uq_reg_closure_cert_version"))
    op.create_table("regulatory_sustainability_windows",
      sa.Column("window_id",sa.String(128),primary_key=True),sa.Column("tenant_id",sa.String(128),sa.ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False,index=True),sa.Column("deficiency_key",sa.String(160),nullable=False,index=True),sa.Column("starts_at",sa.DateTime(timezone=True),nullable=False),sa.Column("ends_at",sa.DateTime(timezone=True),nullable=False),sa.Column("required_observations",sa.Integer(),nullable=False),sa.Column("observed_passes",sa.Integer(),nullable=False),sa.Column("recurrence_detected",sa.Boolean(),nullable=False),sa.Column("status",sa.String(32),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False))
    op.create_table("regulatory_reopen_decisions",
      sa.Column("decision_id",sa.String(128),primary_key=True),sa.Column("tenant_id",sa.String(128),sa.ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False,index=True),sa.Column("deficiency_key",sa.String(160),nullable=False,index=True),sa.Column("trigger",sa.String(80),nullable=False),sa.Column("evidence_refs",sa.JSON(),nullable=False),sa.Column("decision",sa.String(24),nullable=False),sa.Column("rationale",sa.Text(),nullable=False),sa.Column("decided_by_user_id",sa.String(128),sa.ForeignKey("user_accounts.user_id",ondelete="RESTRICT"),nullable=False),sa.Column("decided_at",sa.DateTime(timezone=True),nullable=False))

def downgrade():
    op.drop_table("regulatory_reopen_decisions"); op.drop_table("regulatory_sustainability_windows"); op.drop_table("regulatory_closure_certifications"); op.drop_table("regulatory_closure_packages")
