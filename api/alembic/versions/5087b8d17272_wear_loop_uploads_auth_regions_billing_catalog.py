"""wear loop uploads auth regions billing catalog

Revision ID: 5087b8d17272
Revises: 09ab1b5b08dc
Create Date: 2026-10-26 07:23:49.796922
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5087b8d17272'
down_revision: Union[str, None] = '09ab1b5b08dc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('brands',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('slug', sa.String(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('website', sa.String(), nullable=True),
    sa.Column('logo_url', sa.String(), nullable=True),
    sa.Column('regions', sa.JSON(), nullable=False),
    sa.Column('commission_bps', sa.Integer(), nullable=True),
    sa.Column('api_key_hash', sa.String(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_brands_api_key_hash'), 'brands', ['api_key_hash'], unique=False)
    op.create_index(op.f('ix_brands_slug'), 'brands', ['slug'], unique=True)
    op.create_table('revoked_tokens',
    sa.Column('jti', sa.String(), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('jti')
    )
    op.create_index(op.f('ix_revoked_tokens_expires_at'), 'revoked_tokens', ['expires_at'], unique=False)
    op.create_table('products',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('brand_id', sa.Uuid(), nullable=False),
    sa.Column('external_id', sa.String(), nullable=False),
    sa.Column('title', sa.String(), nullable=False),
    sa.Column('category', sa.String(), nullable=False),
    sa.Column('subcategory', sa.String(), nullable=True),
    sa.Column('primary_color', sa.String(), nullable=True),
    sa.Column('secondary_color', sa.String(), nullable=True),
    sa.Column('pattern', sa.String(), nullable=False),
    sa.Column('fit', sa.String(), nullable=False),
    sa.Column('formality_score', sa.SmallInteger(), nullable=False),
    sa.Column('warmth_score', sa.SmallInteger(), nullable=False),
    sa.Column('tags', sa.JSON(), nullable=False),
    sa.Column('prices', sa.JSON(), nullable=False),
    sa.Column('regions', sa.JSON(), nullable=False),
    sa.Column('sizes', sa.JSON(), nullable=False),
    sa.Column('image_url', sa.String(), nullable=True),
    sa.Column('product_url', sa.String(), nullable=False),
    sa.Column('affiliate_url', sa.String(), nullable=True),
    sa.Column('in_stock', sa.Boolean(), nullable=False),
    sa.Column('attributes', sa.JSON(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['brand_id'], ['brands.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('brand_id', 'external_id', name='uq_product_brand_external')
    )
    op.create_index(op.f('ix_products_brand_id'), 'products', ['brand_id'], unique=False)
    op.create_index(op.f('ix_products_category'), 'products', ['category'], unique=False)
    with op.batch_alter_table('affiliate_recommendations') as t:
        t.add_column(sa.Column('product_id', sa.Uuid(), nullable=True))
        t.add_column(sa.Column('brand_id', sa.Uuid(), nullable=True))
        t.add_column(sa.Column('country', sa.String(length=2), nullable=True))
        t.add_column(sa.Column('unlocks', sa.SmallInteger(), nullable=True))
        t.create_index('ix_affiliate_recommendations_brand_id', ['brand_id'])
        t.create_index('ix_affiliate_recommendations_product_id', ['product_id'])
        t.create_foreign_key('fk_affrec_product', 'products', ['product_id'], ['id'])
        t.create_foreign_key('fk_affrec_brand', 'brands', ['brand_id'], ['id'])
    op.add_column('calendar_connections', sa.Column('token_expires_at', sa.DateTime(timezone=True), nullable=True))
    with op.batch_alter_table('clothing_items') as t:
        t.add_column(sa.Column('brand', sa.String(), nullable=True))
        t.add_column(sa.Column('brand_id', sa.Uuid(), nullable=True))
        t.add_column(sa.Column('product_id', sa.Uuid(), nullable=True))
        t.add_column(sa.Column('external_image_url', sa.String(), nullable=True))
        t.create_index('ix_clothing_items_brand_id', ['brand_id'])
        t.create_foreign_key('fk_clothing_items_product', 'products', ['product_id'], ['id'])
        t.create_foreign_key('fk_clothing_items_brand', 'brands', ['brand_id'], ['id'])
    op.add_column('outfits', sa.Column('rank', sa.SmallInteger(), nullable=False, server_default='1'))
    op.add_column('outfits', sa.Column('worn_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index('ix_outfits_outfit_date', 'outfits', ['outfit_date'], unique=False)
    op.add_column('subscriptions', sa.Column('provider', sa.String(), nullable=True))
    op.add_column('subscriptions', sa.Column('product_id', sa.String(), nullable=True))
    with op.batch_alter_table('users') as t:
        t.add_column(sa.Column('apple_sub', sa.String(), nullable=True))
        t.add_column(sa.Column('display_name', sa.String(), nullable=True))
        t.add_column(sa.Column('locale', sa.String(), nullable=False, server_default='en'))
        t.add_column(sa.Column('country', sa.String(length=2), nullable=True))
        t.add_column(sa.Column('units', sa.String(), nullable=False, server_default='metric'))
        t.add_column(sa.Column('timezone', sa.String(), nullable=True))
        t.create_unique_constraint('uq_users_apple_sub', ['apple_sub'])


def downgrade() -> None:
    with op.batch_alter_table('users') as t:
        t.drop_constraint('uq_users_apple_sub', type_='unique')
        for c in ('timezone', 'units', 'country', 'locale', 'display_name', 'apple_sub'):
            t.drop_column(c)
    op.drop_column('subscriptions', 'product_id')
    op.drop_column('subscriptions', 'provider')
    op.drop_index('ix_outfits_outfit_date', table_name='outfits')
    op.drop_column('outfits', 'worn_at')
    op.drop_column('outfits', 'rank')
    with op.batch_alter_table('clothing_items') as t:
        t.drop_constraint('fk_clothing_items_brand', type_='foreignkey')
        t.drop_constraint('fk_clothing_items_product', type_='foreignkey')
        t.drop_index('ix_clothing_items_brand_id')
        for c in ('external_image_url', 'product_id', 'brand_id', 'brand'):
            t.drop_column(c)
    op.drop_column('calendar_connections', 'token_expires_at')
    with op.batch_alter_table('affiliate_recommendations') as t:
        t.drop_constraint('fk_affrec_brand', type_='foreignkey')
        t.drop_constraint('fk_affrec_product', type_='foreignkey')
        t.drop_index('ix_affiliate_recommendations_product_id')
        t.drop_index('ix_affiliate_recommendations_brand_id')
        for c in ('unlocks', 'country', 'brand_id', 'product_id'):
            t.drop_column(c)
    op.drop_index(op.f('ix_products_category'), table_name='products')
    op.drop_index(op.f('ix_products_brand_id'), table_name='products')
    op.drop_table('products')
    op.drop_index(op.f('ix_revoked_tokens_expires_at'), table_name='revoked_tokens')
    op.drop_table('revoked_tokens')
    op.drop_index(op.f('ix_brands_slug'), table_name='brands')
    op.drop_index(op.f('ix_brands_api_key_hash'), table_name='brands')
    op.drop_table('brands')
