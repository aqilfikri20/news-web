"""Create or bring legacy NewsHub core tables to the baseline schema.

Revision ID: 0001_core_schema
Revises:
"""
from alembic import op
import sqlalchemy as sa


revision = "0001_core_schema"
down_revision = None
branch_labels = None
depends_on = None


def _tables():
    return set(sa.inspect(op.get_bind()).get_table_names())


def _columns(table_name):
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name)}


def _add_column_if_missing(table_name, column):
    if column.name not in _columns(table_name):
        op.add_column(table_name, column)


def upgrade() -> None:
    if "users" not in _tables():
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(length=100), nullable=False),
            sa.Column("email", sa.String(length=255), nullable=False, unique=True),
            sa.Column("password", sa.String(length=255), nullable=False),
            sa.Column("phone", sa.String(length=30), nullable=True),
            sa.Column("address", sa.Text(), nullable=True),
            sa.Column("role", sa.String(length=20), server_default="writer", nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        )
    else:
        _add_column_if_missing("users", sa.Column("phone", sa.String(length=30), nullable=True))
        _add_column_if_missing("users", sa.Column("address", sa.Text(), nullable=True))
        _add_column_if_missing(
            "users",
            sa.Column("role", sa.String(length=20), server_default="writer", nullable=True),
        )
        _add_column_if_missing(
            "users",
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        )

    if "categories" not in _tables():
        op.create_table(
            "categories",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(length=100), nullable=False, unique=True),
        )

    if "news" not in _tables():
        op.create_table(
            "news",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("image_url", sa.Text(), nullable=True),
            sa.Column("category_id", sa.Integer(), sa.ForeignKey("categories.id"), nullable=False),
            sa.Column("author_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        )
    else:
        _add_column_if_missing("news", sa.Column("description", sa.Text(), nullable=True))
        _add_column_if_missing("news", sa.Column("image_url", sa.Text(), nullable=True))
        _add_column_if_missing(
            "news",
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        )
        _add_column_if_missing(
            "news",
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        )


def downgrade() -> None:
    # This baseline may be stamped onto a live legacy database. Dropping its tables
    # would destroy content, so destructive rollback is intentionally omitted.
    pass
