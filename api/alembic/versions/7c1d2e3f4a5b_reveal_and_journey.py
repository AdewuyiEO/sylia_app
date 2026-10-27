"""morning reveal + style journey (streak freezes, weekly challenge, points)

Revision ID: 7c1d2e3f4a5b
Revises: 5087b8d17272
Create Date: 2026-10-27 09:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '7c1d2e3f4a5b'
down_revision: Union[str, None] = '5087b8d17272'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('users') as t:
        t.add_column(sa.Column('reveal_hour', sa.SmallInteger(), nullable=False, server_default='7'))
        t.add_column(sa.Column('streak_freezes', sa.SmallInteger(), nullable=False, server_default='2'))
        t.add_column(sa.Column('freeze_dates', sa.JSON(), nullable=False, server_default='[]'))
        t.add_column(sa.Column('freeze_awarded_on', sa.Date(), nullable=True))
        t.add_column(sa.Column('challenge_week', sa.String(), nullable=True))
        t.add_column(sa.Column('challenge_item_id', sa.Uuid(), nullable=True))
        t.add_column(sa.Column('challenge_done_week', sa.String(), nullable=True))
        t.add_column(sa.Column('bonus_points', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('outfits', sa.Column('revealed_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('outfits', 'revealed_at')
    with op.batch_alter_table('users') as t:
        for c in ('bonus_points', 'challenge_done_week', 'challenge_item_id', 'challenge_week',
                  'freeze_awarded_on', 'freeze_dates', 'streak_freezes', 'reveal_hour'):
            t.drop_column(c)
