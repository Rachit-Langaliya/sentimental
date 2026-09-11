"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-09-11 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # users
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", sa.String(50), nullable=False, server_default="analyst"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("last_login", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    # platforms
    op.create_table(
        "platforms",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("api_status", sa.String(50), nullable=False, server_default="mock"),
        sa.Column("icon", sa.String(50), nullable=True),
        sa.Column("color", sa.String(20), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    # raw_posts
    op.create_table(
        "raw_posts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("platform_id", sa.Integer(), nullable=False),
        sa.Column("external_id", sa.String(255), nullable=False),
        sa.Column("author_hash", sa.String(64), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_cleaned", sa.Text(), nullable=True),
        sa.Column("language", sa.String(10), nullable=True),
        sa.Column("geo_hint", sa.String(100), nullable=True),
        sa.Column("post_ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("parent_hash", sa.String(64), nullable=True),
        sa.Column("metadata_", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["platform_id"], ["platforms.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("platform_id", "external_id", name="uq_raw_posts_platform_external"),
    )
    op.create_index("ix_raw_posts_post_ts", "raw_posts", ["post_ts"])
    op.create_index("ix_raw_posts_author_hash", "raw_posts", ["author_hash"])
    op.create_index("ix_raw_posts_expires_at", "raw_posts", ["expires_at"])

    # post_nlp
    op.create_table(
        "post_nlp",
        sa.Column("post_id", sa.Integer(), nullable=False),
        sa.Column("sentiment", sa.String(20), nullable=True),
        sa.Column("sentiment_score", sa.Float(), nullable=True),
        sa.Column("emotion", sa.String(30), nullable=True),
        sa.Column("emotion_score", sa.Float(), nullable=True),
        sa.Column("support_score", sa.Float(), nullable=True),
        sa.Column("intensity", sa.Float(), nullable=True),
        sa.Column("sarcasm_flag", sa.Boolean(), nullable=True),
        sa.Column("sarcasm_conf", sa.Float(), nullable=True),
        sa.Column("model_version", sa.String(50), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["post_id"], ["raw_posts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("post_id"),
    )

    # topics
    op.create_table(
        "topics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("keywords", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("first_seen", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("platform_ids", postgresql.ARRAY(sa.Integer()), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # narrative_clusters
    op.create_table(
        "narrative_clusters",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("platforms", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("post_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("first_seen", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("last_updated", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # demographic_segments
    op.create_table(
        "demographic_segments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("dominant_language", sa.String(50), nullable=True),
        sa.Column("geo_distribution", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("topic_prefs", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("sentiment_profile", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("activity_profile", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("size_estimate", sa.Integer(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("evidence_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # personas
    op.create_table(
        "personas",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("segment_id", sa.Integer(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("interests", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("reaction", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("influence_score", sa.Float(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("evidence_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["segment_id"], ["demographic_segments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # trends
    op.create_table(
        "trends",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("topic_id", sa.Integer(), nullable=True),
        sa.Column("narrative_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("trend_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("volume_decay", sa.Float(), nullable=False, server_default="0"),
        sa.Column("velocity", sa.Float(), nullable=False, server_default="0"),
        sa.Column("acceleration", sa.Float(), nullable=False, server_default="0"),
        sa.Column("engagement", sa.Float(), nullable=False, server_default="0"),
        sa.Column("unique_users", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("platform_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("community_spread", sa.Float(), nullable=False, server_default="0"),
        sa.Column("sentiment_shift", sa.Float(), nullable=True),
        sa.Column("baseline_7d", sa.Float(), nullable=True),
        sa.Column("is_emerging", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("platforms", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("measured_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["narrative_id"], ["narrative_clusters.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_trends_trend_score", "trends", ["trend_score"])

    # audit_logs
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource", sa.String(255), nullable=True),
        sa.Column("query_hash", sa.String(64), nullable=True),
        sa.Column("ip_hash", sa.String(64), nullable=True),
        sa.Column("ts", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_logs_ts", "audit_logs", ["ts"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("trends")
    op.drop_table("personas")
    op.drop_table("demographic_segments")
    op.drop_table("narrative_clusters")
    op.drop_table("topics")
    op.drop_table("post_nlp")
    op.drop_table("raw_posts")
    op.drop_table("platforms")
    op.drop_table("users")
