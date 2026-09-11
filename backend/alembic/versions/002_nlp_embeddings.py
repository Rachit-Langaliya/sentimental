"""add post_embeddings and post_topics tables

Revision ID: 002
Revises: 001
Create Date: 2026-09-11 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # post_embeddings — stores sentence embeddings as JSONB float array
    # (pgvector vector(384) column added separately if pgvector extension is available)
    op.create_table(
        "post_embeddings",
        sa.Column("post_id", sa.BigInteger(), nullable=False),
        sa.Column("embedding_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("model_version", sa.String(100), nullable=False, server_default="multilingual-minilm-l12-v2"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["post_id"], ["raw_posts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("post_id"),
    )

    # post_topics — assignment of posts to topics
    op.create_table(
        "post_topics",
        sa.Column("post_id", sa.BigInteger(), nullable=False),
        sa.Column("topic_id", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("assigned_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["post_id"], ["raw_posts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("post_id"),
    )
    op.create_index("ix_post_topics_topic_id", "post_topics", ["topic_id"])

    # Add topic_id index on post_topics
    op.create_index("ix_post_embeddings_created_at", "post_embeddings", ["created_at"])

    # Try to add pgvector vector column (optional, requires pgvector extension)
    try:
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
        op.execute(
            "ALTER TABLE post_embeddings "
            "ADD COLUMN IF NOT EXISTS embedding vector(384)"
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_post_embeddings_ivfflat "
            "ON post_embeddings USING ivfflat (embedding vector_cosine_ops) "
            "WITH (lists = 100)"
        )
    except Exception:
        pass  # pgvector not available — embedding_json fallback will be used


def downgrade() -> None:
    op.drop_table("post_topics")
    op.drop_table("post_embeddings")
