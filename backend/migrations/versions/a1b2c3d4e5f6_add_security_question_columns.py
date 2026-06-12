"""add security question columns to users (Fix #35 wire SQLAlchemy User into auth flow)

Revision ID: a1b2c3d4e5f6
Revises: c391192d16be
Create Date: 2026-06-12 14:00:00.000000

Adds 2 columns to the users table to persist the password-reset
security-question feature. The pre-Fix-35 JSON-file user store has had
these fields since Phase 4, but the SQLAlchemy `User` model never had
a column for them. Fix #35 makes the SQLAlchemy table the single
source of truth, so these columns are the persistence layer for the
"what is your favorite pet's name?" / "what city were you born in?"
flows used by `/auth/reset-password`.

Both columns are nullable so the migration is a pure add-column with
no backfill required. Existing users that never set a security
question have `security_question = NULL` and `hashed_security_answer =
NULL`; the `/auth/reset-password` route handles the NULL case by
falling back to the (legacy) admin-reset path.

  - security_question       : a free-form question string the user
                              chose at registration. The full set of
                              allowed questions is small (8 from the
                              registration UI) and the column has no
                              FK; the API validates against the allow-
                              list.
  - hashed_security_answer  : bcrypt-hashed answer, using the same
                              `pwd_context` and bcrypt<4.1 pin the
                              password uses. NULL when the user never
                              set a question.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'c391192d16be'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add 2 nullable security-question columns to the users table."""
    op.add_column(
        'users',
        sa.Column('security_question', sa.String(length=200), nullable=True),
    )
    op.add_column(
        'users',
        sa.Column('hashed_security_answer', sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    """Reverse the migration. Drops the 2 columns."""
    op.drop_column('users', 'hashed_security_answer')
    op.drop_column('users', 'security_question')
