"""add teacher_id to sections

Revision ID: 2f8d46a92514
Revises: 0e7c35911403
Create Date: 2024-12-17 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2f8d46a92514'
down_revision = '0e7c35911403'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add teacher_id column to sections table
    op.add_column('sections', sa.Column('teacher_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_sections_teacher_id'), 'sections', ['teacher_id'], unique=False)
    op.create_foreign_key(None, 'sections', 'teachers', ['teacher_id'], ['id'])


def downgrade() -> None:
    # Remove teacher_id column
    op.drop_constraint(None, 'sections', type_='foreignkey')
    op.drop_index(op.f('ix_sections_teacher_id'), table_name='sections')
    op.drop_column('sections', 'teacher_id')
