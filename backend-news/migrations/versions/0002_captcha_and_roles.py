"""Add CAPTCHA storage and normalize account roles.

Revision ID: 0002_captcha_and_roles
Revises: 0001_core_schema
"""
from alembic import op
import sqlalchemy as sa


revision = "0002_captcha_roles"
down_revision = "0001_core_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "captcha_challenges" not in tables:
        op.create_table(
            "captcha_challenges",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("answer_hash", sa.String(length=64), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("consumed", sa.Integer(), nullable=False, server_default="0"),
        )

    users_columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("users")}
    if "phone" not in users_columns:
        op.add_column("users", sa.Column("phone", sa.String(length=30), nullable=True))
    if "address" not in users_columns:
        op.add_column("users", sa.Column("address", sa.Text(), nullable=True))
    if "role" not in users_columns:
        op.add_column("users", sa.Column("role", sa.String(length=20), nullable=True))

    op.execute(sa.text("UPDATE users SET role = 'writer' WHERE role IS NULL OR role NOT IN ('admin', 'writer')"))
    op.alter_column("users", "role", existing_type=sa.String(length=20), server_default="writer", nullable=False)


def downgrade() -> None:
    op.drop_table("captcha_challenges")
    # Keep added writer profile columns and role data during downgrade.
