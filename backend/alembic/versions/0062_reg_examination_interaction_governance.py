"""release 67 regulatory examination interaction governance
Revision ID: 0062_reg_exam_interaction
Revises: 0061_reg_examination_response_orchestration
"""
from alembic import op
import sqlalchemy as sa
revision="0062_reg_exam_interaction"
down_revision="0061_reg_examination_response_orchestration"
branch_labels=None
depends_on=None

def upgrade():
    op.create_table("regulatory_exam_meetings",sa.Column("meeting_id",sa.String(36),primary_key=True),sa.Column("tenant_id",sa.String(128),nullable=False,index=True),sa.Column("examination_id",sa.String(128),nullable=False,index=True),sa.Column("status",sa.String(32),nullable=False),sa.Column("title",sa.Text(),nullable=False),sa.Column("scheduled_at",sa.DateTime(timezone=True),nullable=False),sa.Column("agenda_json",sa.JSON(),nullable=False),sa.Column("attendees_json",sa.JSON(),nullable=False),sa.Column("version_hash",sa.String(64),nullable=False),sa.Column("created_by",sa.String(128),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
    op.create_table("regulatory_exam_interaction_statements",sa.Column("statement_id",sa.String(36),primary_key=True),sa.Column("meeting_id",sa.String(36),sa.ForeignKey("regulatory_exam_meetings.meeting_id",ondelete="CASCADE"),nullable=False,index=True),sa.Column("tenant_id",sa.String(128),nullable=False,index=True),sa.Column("speaker_type",sa.String(64),nullable=False),sa.Column("classification",sa.String(64),nullable=False),sa.Column("text",sa.Text(),nullable=False),sa.Column("source_ref",sa.String(512)),sa.Column("evidence_refs_json",sa.JSON(),nullable=False),sa.Column("provenance_hash",sa.String(64),nullable=False),sa.Column("captured_by",sa.String(128),nullable=False),sa.Column("captured_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
    op.create_table("regulatory_exam_commitments",sa.Column("commitment_id",sa.String(36),primary_key=True),sa.Column("meeting_id",sa.String(36),sa.ForeignKey("regulatory_exam_meetings.meeting_id",ondelete="CASCADE"),nullable=False,index=True),sa.Column("tenant_id",sa.String(128),nullable=False,index=True),sa.Column("statement_id",sa.String(36),nullable=False),sa.Column("description",sa.Text(),nullable=False),sa.Column("status",sa.String(32),nullable=False),sa.Column("binding",sa.Boolean(),nullable=False,server_default=sa.false()),sa.Column("owner_user_id",sa.String(128)),sa.Column("due_at",sa.DateTime(timezone=True)),sa.Column("human_confirmed_by",sa.String(128)),sa.Column("rationale",sa.Text()),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))

def downgrade():
    op.drop_table("regulatory_exam_commitments"); op.drop_table("regulatory_exam_interaction_statements"); op.drop_table("regulatory_exam_meetings")
