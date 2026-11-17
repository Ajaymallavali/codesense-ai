"""Add conversations, conversation messages, reports, and indexing metadata

Revision ID: 002_conversations_and_reports
Revises: 001_initial_schema
Create Date: 2026-10-28 00:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002_conversations_and_reports'
down_revision: Union[str, None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. conversations table
    op.create_table(
        'conversations',
        sa.Column('id', sa.String(length=255), nullable=False),
        sa.Column('repository_id', sa.UUID(), nullable=True),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['repository_id'], ['repositories.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_conversations_user_id', 'conversations', ['user_id'])
    op.create_index('ix_conversations_repository_id', 'conversations', ['repository_id'])

    # 2. conversation_messages table
    op.create_table(
        'conversation_messages',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('conversation_id', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('citations', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_conversation_messages_conversation_id', 'conversation_messages', ['conversation_id'])

    # 3. reports table
    op.create_table(
        'reports',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('repository_id', sa.UUID(), nullable=False),
        sa.Column('owner_id', sa.UUID(), nullable=False),
        sa.Column('report_type', sa.String(length=50), server_default='assessment', nullable=False),
        sa.Column('format', sa.String(length=20), server_default='pdf', nullable=False),
        sa.Column('analysis_id', sa.UUID(), nullable=True),
        sa.Column('maintainability_score', sa.Integer(), server_default='0', nullable=False),
        sa.Column('technical_debt_hours', sa.Integer(), server_default='0', nullable=False),
        sa.Column('findings_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['repository_id'], ['repositories.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['analysis_id'], ['analyses.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_reports_owner_id', 'reports', ['owner_id'])
    op.create_index('ix_reports_repository_id', 'reports', ['repository_id'])

    # 4. indexing_metadata table
    op.create_table(
        'indexing_metadata',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('repository_id', sa.UUID(), nullable=False),
        sa.Column('commit_sha', sa.String(length=64), nullable=False),
        sa.Column('chunks_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('indexed_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['repository_id'], ['repositories.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('repository_id', 'commit_sha', name='uq_repo_commit_index')
    )


def downgrade() -> None:
    op.drop_table('indexing_metadata')
    op.drop_table('reports')
    op.drop_table('conversation_messages')
    op.drop_table('conversations')
