"""add session columns to users (Fix #34 single-session enforcement)

Revision ID: c391192d16be
Revises: f78f0efa440e
Create Date: 2026-06-11 23:55:00.000000

Adds 5 columns to the users table to support single-session-per-user
enforcement (Fix #34). All columns are nullable so the migration is
a pure add-column with no backfill required; existing users with no
active_session_id continue to have their (jti-less) tokens accepted
by verify_token until they next log in (which populates
active_session_id).

  - active_session_id           : the jti of the currently-active access
                                  + refresh token pair; mismatch => 401
  - active_session_ip           : the IP that issued the active session
  - active_session_user_agent   : the User-Agent that issued the active
                                  session
  - active_session_started_at   : ISO timestamp of the login that
                                  created the active session
  - on_new_login_pref           : the "ask first" Settings toggle;
                                  "auto_kick" (default) or "ask_first"
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c391192d16be'
down_revision: Union[str, Sequence[str], None] = 'f78f0efa440e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add 5 nullable session-tracking columns to the users table."""
    op.add_column(
        'users',
        sa.Column('active_session_id', sa.String(length=64), nullable=True),
    )
    op.add_column(
        'users',
        sa.Column('active_session_ip', sa.String(length=45), nullable=True),
    )
    op.add_column(
        'users',
        sa.Column('active_session_user_agent', sa.String(length=500), nullable=True),
    )
    op.add_column(
        'users',
        sa.Column('active_session_started_at', sa.DateTime(), nullable=True),
    )
    op.add_column(
        'users',
        sa.Column('on_new_login_pref', sa.String(length=20), nullable=True),
    )
    # Index the active_session_id column so the verify_token jti check
    # stays O(1) (one row per user — it's already a near-unique lookup,
    # but the index makes it a single PK-style fetch even at scale).
    op.create_index(
        'ix_users_active_session_id',
        'users',
        ['active_session_id'],
        unique=False,
    )


def downgrade() -> None:
    """Reverse the migration. Drops the index then the 5 columns."""
    op.drop_index('ix_users_active_session_id', table_name='users')
    op.drop_column('users', 'on_new_login_pref')
    op.drop_column('users', 'active_session_started_at')
    op.drop_column('users', 'active_session_user_agent')
    op.drop_column('users', 'active_session_ip')
    op.drop_column('users', 'active_session_id')
