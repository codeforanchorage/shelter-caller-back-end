"""Add input_text to Call

Revision ID: 247f66e73d2a
Revises: 733f7547efc8
Create Date: 2018-11-03 11:22:29.437483

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '247f66e73d2a'
down_revision = '733f7547efc8'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('calls', sa.Column('inputtext', sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('calls', 'inputtext')
    # ### end Alembic commands ###
