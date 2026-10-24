"""google sign-in: link Google accounts; passwords become optional

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-24
"""
from alembic import op
import sqlalchemy as sa

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('users') as batch:
        batch.add_column(sa.Column('google_sub', sa.String(length=255), nullable=True))
        batch.add_column(sa.Column('google_email', sa.String(length=320), nullable=True))
        batch.alter_column('hashed_password', existing_type=sa.String(length=255), nullable=True)
        batch.create_index(batch.f('ix_users_google_sub'), ['google_sub'], unique=True)


def downgrade() -> None:
    # Google-only accounts have no password; give them an unusable one.
    op.execute("UPDATE users SET hashed_password = '!' WHERE hashed_password IS NULL")
    with op.batch_alter_table('users') as batch:
        batch.drop_index(batch.f('ix_users_google_sub'))
        batch.alter_column('hashed_password', existing_type=sa.String(length=255), nullable=False)
        batch.drop_column('google_email')
        batch.drop_column('google_sub')
