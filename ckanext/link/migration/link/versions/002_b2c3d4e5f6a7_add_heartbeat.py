"""add heartbeat_at to link_check_job

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2024-01-02 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'b2c3d4e5f6a7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('link_check_job',
                   sa.Column('heartbeat_at', sa.DateTime, nullable=True))


def downgrade():
    op.drop_column('link_check_job', 'heartbeat_at')
