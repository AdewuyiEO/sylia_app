"""try-on: fitting-room profile, rendered previews, garment size on closet items

Revision ID: 8e4f2a1b9c3d
Revises: 7c1d2e3f4a5b
Create Date: 2026-10-27 15:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '8e4f2a1b9c3d'
down_revision: Union[str, None] = '7c1d2e3f4a5b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'tryon_profiles',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('photo_key', sa.String(), nullable=False),
        sa.Column('height_cm', sa.Float(), nullable=False),
        sa.Column('bust_cm', sa.Float(), nullable=False),
        sa.Column('waist_cm', sa.Float(), nullable=False),
        sa.Column('hips_cm', sa.Float(), nullable=False),
        sa.Column('shoulder_cm', sa.Float(), nullable=True),
        sa.Column('inseam_cm', sa.Float(), nullable=True),
        sa.Column('landmarks', sa.JSON(), nullable=False),
        sa.Column('retention', sa.String(), nullable=False),
        sa.Column('consent_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_tryon_profiles_user_id_users'),
        sa.PrimaryKeyConstraint('id', name='pk_tryon_profiles'),
        sa.UniqueConstraint('user_id', name='uq_tryon_profiles_user_id'),
    )
    op.create_table(
        'tryon_renders',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('item_id', sa.Uuid(), nullable=True),
        sa.Column('product_id', sa.Uuid(), nullable=True),
        sa.Column('size', sa.String(), nullable=False),
        sa.Column('image_key', sa.String(), nullable=False),
        sa.Column('fit', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_tryon_renders_user_id_users'),
        sa.ForeignKeyConstraint(['item_id'], ['clothing_items.id'], name='fk_tryon_renders_item_id_clothing_items'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], name='fk_tryon_renders_product_id_products'),
        sa.PrimaryKeyConstraint('id', name='pk_tryon_renders'),
    )
    op.create_index('ix_tryon_renders_user_id', 'tryon_renders', ['user_id'])
    with op.batch_alter_table('clothing_items') as t:
        t.add_column(sa.Column('size_label', sa.String(), nullable=True))
        t.add_column(sa.Column('garment_measurements', sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('clothing_items') as t:
        t.drop_column('garment_measurements')
        t.drop_column('size_label')
    op.drop_index('ix_tryon_renders_user_id', table_name='tryon_renders')
    op.drop_table('tryon_renders')
    op.drop_table('tryon_profiles')
