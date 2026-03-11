"""create link_check_result and link_check_job tables

Revision ID: a1b2c3d4e5f6
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'a1b2c3d4e5f6'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'link_check_result',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('resource_id', sa.UnicodeText, nullable=False),
        sa.Column('package_id', sa.UnicodeText, nullable=False),
        sa.Column('package_name', sa.UnicodeText, nullable=True),
        sa.Column('url', sa.UnicodeText, nullable=False),
        sa.Column('status_code', sa.Integer, nullable=True),
        sa.Column('error', sa.UnicodeText, nullable=True),
        sa.Column('checked_at', sa.DateTime),
        sa.Column('is_broken', sa.Boolean, default=False),
    )
    op.create_index('ix_link_check_result_resource_id',
                     'link_check_result', ['resource_id'])
    op.create_index('ix_link_check_result_package_id',
                     'link_check_result', ['package_id'])

    op.create_table(
        'link_check_job',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('job_id', sa.UnicodeText, nullable=False),
        sa.Column('created_at', sa.DateTime),
    )


def downgrade():
    op.drop_table('link_check_job')
    op.drop_index('ix_link_check_result_package_id',
                   table_name='link_check_result')
    op.drop_index('ix_link_check_result_resource_id',
                   table_name='link_check_result')
    op.drop_table('link_check_result')
