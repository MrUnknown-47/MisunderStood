"""Initial database schema with seven core tables

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-10-17 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from app.database import GUID, UniversalJSON

revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. sessions
    op.create_table(
        'sessions',
        sa.Column('id', GUID(), primary_key=True),
        sa.Column('join_code', sa.String(length=32), nullable=False, unique=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('context', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='collecting_responses'),
        sa.Column('min_participants', sa.Integer(), nullable=False, server_default='2'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_sessions_join_code', 'sessions', ['join_code'])
    op.create_index('ix_sessions_status', 'sessions', ['status'])

    # 2. participants
    op.create_table(
        'participants',
        sa.Column('id', GUID(), primary_key=True),
        sa.Column('session_id', GUID(), sa.ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('display_name', sa.String(length=100), nullable=False),
        sa.Column('role', sa.String(length=32), nullable=False, server_default='participant'),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('joined_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_participants_session_id', 'participants', ['session_id'])
    op.create_index('ix_participants_token_hash', 'participants', ['token_hash'])

    # 3. interpretations
    op.create_table(
        'interpretations',
        sa.Column('id', GUID(), primary_key=True),
        sa.Column('session_id', GUID(), sa.ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('participant_id', GUID(), sa.ForeignKey('participants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('response_text', sa.Text(), nullable=False),
        sa.Column('assumptions', UniversalJSON(), nullable=True),
        sa.Column('success_criteria', UniversalJSON(), nullable=True),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('session_id', 'participant_id', name='uq_session_participant_interpretation')
    )
    op.create_index('ix_interpretations_session_id', 'interpretations', ['session_id'])
    op.create_index('ix_interpretations_participant_id', 'interpretations', ['participant_id'])

    # 4. analyses
    op.create_table(
        'analyses',
        sa.Column('id', GUID(), primary_key=True),
        sa.Column('session_id', GUID(), sa.ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('model_name', sa.String(length=64), nullable=True),
        sa.Column('prompt_version', sa.String(length=32), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='pending'),
        sa.Column('result_json', UniversalJSON(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_analyses_session_id', 'analyses', ['session_id'])
    op.create_index('ix_analyses_status', 'analyses', ['status'])

    # 5. issues
    op.create_table(
        'issues',
        sa.Column('id', GUID(), primary_key=True),
        sa.Column('session_id', GUID(), sa.ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('analysis_id', GUID(), sa.ForeignKey('analyses.id', ondelete='CASCADE'), nullable=False),
        sa.Column('type', sa.String(length=64), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('evidence_json', UniversalJSON(), nullable=False),
        sa.Column('priority', sa.String(length=16), nullable=False),
        sa.Column('clarification_question', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='open'),
        sa.Column('resolution_text', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_issues_session_id', 'issues', ['session_id'])
    op.create_index('ix_issues_analysis_id', 'issues', ['analysis_id'])
    op.create_index('ix_issues_type', 'issues', ['type'])
    op.create_index('ix_issues_status', 'issues', ['status'])
    op.create_index('ix_issues_priority', 'issues', ['priority'])

    # 6. agreements
    op.create_table(
        'agreements',
        sa.Column('id', GUID(), primary_key=True),
        sa.Column('session_id', GUID(), sa.ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('content_json', UniversalJSON(), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='pending_confirmation'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_agreements_session_id', 'agreements', ['session_id'])
    op.create_index('ix_agreements_status', 'agreements', ['status'])

    # 7. agreement_confirmations
    op.create_table(
        'agreement_confirmations',
        sa.Column('id', GUID(), primary_key=True),
        sa.Column('agreement_id', GUID(), sa.ForeignKey('agreements.id', ondelete='CASCADE'), nullable=False),
        sa.Column('participant_id', GUID(), sa.ForeignKey('participants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('confirmed', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('confirmed_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('agreement_id', 'participant_id', name='uq_agreement_participant_confirmation')
    )
    op.create_index('ix_agreement_confirmations_agreement_id', 'agreement_confirmations', ['agreement_id'])
    op.create_index('ix_agreement_confirmations_participant_id', 'agreement_confirmations', ['participant_id'])


def downgrade() -> None:
    op.drop_table('agreement_confirmations')
    op.drop_table('agreements')
    op.drop_table('issues')
    op.drop_table('analyses')
    op.drop_table('interpretations')
    op.drop_table('participants')
    op.drop_table('sessions')
