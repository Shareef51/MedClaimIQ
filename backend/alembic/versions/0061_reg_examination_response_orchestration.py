"""release66 regulatory examination response orchestration
Revision ID: 0061_reg_exam_response
Revises: 0060_reg_examination_readiness_operations
"""
from alembic import op
import sqlalchemy as sa
revision="0061_reg_exam_response"; down_revision="0060_reg_examination_readiness_operations"; branch_labels=None; depends_on=None

def upgrade():
    op.create_table("reg_exam_questions",sa.Column("id",sa.String(64),primary_key=True),sa.Column("tenant_id",sa.String(64),nullable=False,index=True),sa.Column("examination_id",sa.String(64),nullable=False,index=True),sa.Column("external_question_ref",sa.String(128),nullable=False),sa.Column("parent_question_id",sa.String(64)),sa.Column("status",sa.String(32),nullable=False),sa.Column("question_text",sa.Text(),nullable=False),sa.Column("due_at",sa.DateTime(timezone=True)),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False))
    op.create_table("reg_exam_response_revisions",sa.Column("id",sa.String(64),primary_key=True),sa.Column("tenant_id",sa.String(64),nullable=False,index=True),sa.Column("question_id",sa.String(64),nullable=False,index=True),sa.Column("revision_no",sa.Integer(),nullable=False),sa.Column("status",sa.String(32),nullable=False),sa.Column("response_text",sa.Text(),nullable=False),sa.Column("revision_hash",sa.String(64),nullable=False,unique=True),sa.Column("supersedes_id",sa.String(64)),sa.Column("created_by",sa.String(64),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),sa.UniqueConstraint("tenant_id","question_id","revision_no",name="uq_reg_exam_response_revision"))
    op.create_table("reg_exam_submission_receipts",sa.Column("id",sa.String(64),primary_key=True),sa.Column("tenant_id",sa.String(64),nullable=False,index=True),sa.Column("submission_id",sa.String(64),nullable=False,index=True),sa.Column("status",sa.String(32),nullable=False),sa.Column("regulator_reference",sa.String(256)),sa.Column("received_at",sa.DateTime(timezone=True)),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False))
def downgrade():
    op.drop_table("reg_exam_submission_receipts"); op.drop_table("reg_exam_response_revisions"); op.drop_table("reg_exam_questions")
