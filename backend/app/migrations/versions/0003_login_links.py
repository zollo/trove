"""login links: single-use magic sign-in links for candidates

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-02
"""
from alembic import op
import sqlalchemy as sa

revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('login_links',
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('created_by_id', sa.Uuid(), nullable=True),
    sa.Column('token_hash', sa.String(length=64), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_login_links_token_hash'), 'login_links', ['token_hash'], unique=True)
    op.create_index(op.f('ix_login_links_user_id'), 'login_links', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_login_links_user_id'), table_name='login_links')
    op.drop_index(op.f('ix_login_links_token_hash'), table_name='login_links')
    op.drop_table('login_links')
