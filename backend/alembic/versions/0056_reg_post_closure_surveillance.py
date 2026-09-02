"""post-closure surveillance recurrence intelligence and reopening governance
Revision ID: 0056_reg_post_closure_surveillance
Revises: 0055_reg_closure_governance
"""
from alembic import op
import sqlalchemy as sa
revision="0056_reg_post_closure_surveillance"; down_revision="0055_reg_closure_governance"; branch_labels=None; depends_on=None

def upgrade():
    op.create_table("post_closure_surveillance_signals",
      sa.Column("signal_id",sa.String(128),primary_key=True),sa.Column("tenant_id",sa.String(128),sa.ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False,index=True),sa.Column("deficiency_key",sa.String(160),nullable=False,index=True),sa.Column("signal_type",sa.String(64),nullable=False),sa.Column("source_ref",sa.JSON(),nullable=False),sa.Column("evidence_refs",sa.JSON(),nullable=False),sa.Column("recurrence_score",sa.Float(),nullable=False),sa.Column("sustainability_decay_score",sa.Float(),nullable=False),sa.Column("control_regression_score",sa.Float(),nullable=False),sa.Column("cross_entity_keys",sa.JSON(),nullable=False),sa.Column("status",sa.String(32),nullable=False),sa.Column("detected_at",sa.DateTime(timezone=True),nullable=False))
    op.create_table("regulatory_reopen_candidates",
      sa.Column("candidate_id",sa.String(128),primary_key=True),sa.Column("tenant_id",sa.String(128),sa.ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False,index=True),sa.Column("deficiency_key",sa.String(160),nullable=False,index=True),sa.Column("version",sa.Integer(),nullable=False),sa.Column("trigger",sa.String(80),nullable=False),sa.Column("matched_closed_finding_refs",sa.JSON(),nullable=False),sa.Column("prior_certification_refs",sa.JSON(),nullable=False),sa.Column("recurrence_evidence_refs",sa.JSON(),nullable=False),sa.Column("renewed_corrective_action_refs",sa.JSON(),nullable=False),sa.Column("regulator_followup_refs",sa.JSON(),nullable=False),sa.Column("recommended_action",sa.String(32),nullable=False),sa.Column("human_decision_required",sa.Boolean(),nullable=False),sa.Column("status",sa.String(32),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),sa.UniqueConstraint("tenant_id","deficiency_key","version",name="uq_reg_reopen_candidate_version"))
    op.create_table("reopened_issue_investigations",
      sa.Column("investigation_id",sa.String(128),primary_key=True),sa.Column("tenant_id",sa.String(128),sa.ForeignKey("tenants.tenant_id",ondelete="CASCADE"),nullable=False,index=True),sa.Column("deficiency_key",sa.String(160),nullable=False,index=True),sa.Column("candidate_id",sa.String(128),nullable=False,index=True),sa.Column("decision",sa.String(24),nullable=False),sa.Column("rationale",sa.Text(),nullable=False),sa.Column("renewed_corrective_action_refs",sa.JSON(),nullable=False),sa.Column("revalidation_required",sa.Boolean(),nullable=False),sa.Column("decided_by_user_id",sa.String(128),sa.ForeignKey("user_accounts.user_id",ondelete="RESTRICT"),nullable=False),sa.Column("decided_at",sa.DateTime(timezone=True),nullable=False))

def downgrade():
    op.drop_table("reopened_issue_investigations"); op.drop_table("regulatory_reopen_candidates"); op.drop_table("post_closure_surveillance_signals")
