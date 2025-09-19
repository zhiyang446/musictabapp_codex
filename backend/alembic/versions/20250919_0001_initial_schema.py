"""Initial schema for transcription platform."""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20250919_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """å»ºç«‹æ ¸å¿ƒè³‡æ–™è¡¨èˆ‡åˆ—èˆ‰ã€‚"""

    enum_source_type = postgresql.ENUM("local", "youtube", name="source_type_enum")
    enum_job_status = postgresql.ENUM("pending", "processing", "rendering", "completed", "failed", name="job_status_enum")
    enum_score_format = postgresql.ENUM("midi", "musicxml", "pdf", name="score_format_enum")
    enum_preset_visibility = postgresql.ENUM("public", "private", name="preset_visibility_enum")

    bind = op.get_bind()
    enum_source_type.create(bind, checkfirst=True)
    enum_job_status.create(bind, checkfirst=True)
    enum_score_format.create(bind, checkfirst=True)
    enum_preset_visibility.create(bind, checkfirst=True)

    source_type_enum = postgresql.ENUM("local", "youtube", name="source_type_enum", create_type=False)
    job_status_enum = postgresql.ENUM("pending", "processing", "rendering", "completed", "failed", name="job_status_enum", create_type=False)
    score_format_enum = postgresql.ENUM("midi", "musicxml", "pdf", name="score_format_enum", create_type=False)
    preset_visibility_enum = postgresql.ENUM("public", "private", name="preset_visibility_enum", create_type=False)

    op.create_table(
        "profiles",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("auth.users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("display_name", sa.Text(), nullable=True),
        sa.Column("avatar_url", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("timezone('utc', now())"), nullable=False),
    )
    op.create_index(op.f("ix_profiles_created_at"), "profiles", ["created_at"], unique=False)

    op.create_table(
        "transcription_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("auth.users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_type", source_type_enum, nullable=False),
        sa.Column("source_uri", sa.Text(), nullable=True),
        sa.Column("storage_object_path", sa.Text(), nullable=True),
        sa.Column("instrument_modes", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("model_profile", sa.Text(), nullable=False, server_default=sa.text("'balanced'")),
        sa.Column("status", job_status_enum, nullable=False, server_default=sa.text("'pending'")),
        sa.Column("progress", sa.Float(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("timezone('utc', now())"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("timezone('utc', now())"), nullable=False),
    )
    op.create_index(op.f("ix_transcription_jobs_user_id"), "transcription_jobs", ["user_id"], unique=False)
    op.create_index(op.f("ix_transcription_jobs_status"), "transcription_jobs", ["status"], unique=False)
    op.create_index(op.f("ix_transcription_jobs_created_at"), "transcription_jobs", ["created_at"], unique=False)

    op.create_table(
        "job_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("transcription_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("stage", sa.Text(), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("timezone('utc', now())"), nullable=False),
    )
    op.create_index("ix_job_events_job_id_created_at", "job_events", ["job_id", "created_at"], unique=False)

    op.create_table(
        "score_assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("transcription_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("instrument", sa.Text(), nullable=False),
        sa.Column("format", score_format_enum, nullable=False),
        sa.Column("storage_object_path", sa.Text(), nullable=False),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("timezone('utc', now())"), nullable=False),
        sa.UniqueConstraint("job_id", "instrument", "format", name="uq_score_assets_job_instrument_format"),
    )
    op.create_index(op.f("ix_score_assets_job_id"), "score_assets", ["job_id"], unique=False)

    op.create_table(
        "processing_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("transcription_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("cpu_usage", sa.Float(), nullable=True),
        sa.Column("memory_mb", sa.Float(), nullable=True),
        sa.Column("model_versions", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("timezone('utc', now())"), nullable=False),
    )
    op.create_index(op.f("ix_processing_metrics_job_id"), "processing_metrics", ["job_id"], unique=False)

    op.create_table(
        "presets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("auth.users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("instrument_modes", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("tempo_hint", sa.Integer(), nullable=True),
        sa.Column("visibility", preset_visibility_enum, nullable=False, server_default=sa.text("'private'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("timezone('utc', now())"), nullable=False),
        sa.UniqueConstraint("user_id", "name", name="uq_presets_user_name"),
    )
    op.create_index(op.f("ix_presets_user_id"), "presets", ["user_id"], unique=False)
    op.create_index("ix_presets_public_name", "presets", ["name"], unique=True, postgresql_where=sa.text("user_id IS NULL"))

    op.execute(
        sa.text(
            "CREATE OR REPLACE FUNCTION trigger_set_timestamp() RETURNS TRIGGER AS $$\n"
            "BEGIN\n"
            "  NEW.updated_at = timezone('utc', now());\n"
            "  RETURN NEW;\n"
            "END;\n"
            "$$ LANGUAGE plpgsql;"
        )
    )
    op.execute(
        sa.text(
            "CREATE TRIGGER set_timestamp BEFORE UPDATE ON transcription_jobs"
            " FOR EACH ROW EXECUTE PROCEDURE trigger_set_timestamp();"
        )
    )


def downgrade() -> None:
    """ç§»é™¤æ ¸å¿ƒè³‡æ–™è¡¨èˆ‡åˆ—èˆ‰ã€‚"""

    op.execute(sa.text("DROP TRIGGER IF EXISTS set_timestamp ON transcription_jobs"))
    op.execute(sa.text("DROP FUNCTION IF EXISTS trigger_set_timestamp"))

    op.drop_index("ix_presets_public_name", table_name="presets")
    op.drop_index(op.f("ix_presets_user_id"), table_name="presets")
    op.drop_table("presets")

    op.drop_index(op.f("ix_processing_metrics_job_id"), table_name="processing_metrics")
    op.drop_table("processing_metrics")

    op.drop_index(op.f("ix_score_assets_job_id"), table_name="score_assets")
    op.drop_table("score_assets")

    op.drop_index("ix_job_events_job_id_created_at", table_name="job_events")
    op.drop_table("job_events")

    op.drop_index(op.f("ix_transcription_jobs_created_at"), table_name="transcription_jobs")
    op.drop_index(op.f("ix_transcription_jobs_status"), table_name="transcription_jobs")
    op.drop_index(op.f("ix_transcription_jobs_user_id"), table_name="transcription_jobs")
    op.drop_table("transcription_jobs")

    op.drop_index(op.f("ix_profiles_created_at"), table_name="profiles")
    op.drop_table("profiles")

    enum_source_type = postgresql.ENUM("local", "youtube", name="source_type_enum", create_type=False)
    enum_job_status = postgresql.ENUM("pending", "processing", "rendering", "completed", "failed", name="job_status_enum", create_type=False)
    enum_score_format = postgresql.ENUM("midi", "musicxml", "pdf", name="score_format_enum", create_type=False)
    enum_preset_visibility = postgresql.ENUM("public", "private", name="preset_visibility_enum", create_type=False)

    bind = op.get_bind()
    enum_preset_visibility.drop(bind, checkfirst=True)
    enum_score_format.drop(bind, checkfirst=True)
    enum_job_status.drop(bind, checkfirst=True)
    enum_source_type.drop(bind, checkfirst=True)
