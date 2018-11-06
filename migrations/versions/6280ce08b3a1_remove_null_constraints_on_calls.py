"""remove null constraints on calls

Revision ID: 6280ce08b3a1
Revises: 07bf99722b0b
Create Date: 2018-11-05 17:02:30.271140

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6280ce08b3a1'
down_revision = '07bf99722b0b'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('calls', 'bedcount',
               existing_type=sa.INTEGER(),
               nullable=True)
    op.alter_column('calls', 'shelter_id',
               existing_type=sa.INTEGER(),
               nullable=True)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('calls', 'shelter_id',
               existing_type=sa.INTEGER(),
               nullable=False)
    op.alter_column('calls', 'bedcount',
               existing_type=sa.INTEGER(),
               nullable=False)
    # ### end Alembic commands ###
