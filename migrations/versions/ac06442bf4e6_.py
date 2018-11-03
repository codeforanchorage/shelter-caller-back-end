"""empty message

Revision ID: ac06442bf4e6
Revises: 60fc54da6b93
Create Date: 2018-10-29 18:54:38.696498

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'ac06442bf4e6'
down_revision = '60fc54da6b93'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('calls', sa.Column('time', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False))
    op.drop_column('calls', 'timecall')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('calls', sa.Column('timecall', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False))
    op.drop_column('calls', 'time')
    # ### end Alembic commands ###
