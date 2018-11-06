"""add error column on calls

Revision ID: 07bf99722b0b
Revises: c9147995db59
Create Date: 2018-11-05 16:47:29.911641

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '07bf99722b0b'
down_revision = 'c9147995db59'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('calls', sa.Column('error', sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('calls', 'error')
    # ### end Alembic commands ###