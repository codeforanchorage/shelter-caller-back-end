"""remove calls table -- will be replaced by logs

Revision ID: cd5f307e1854
Revises: 9e42472e63d1
Create Date: 2018-11-18 14:42:11.273889

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'cd5f307e1854'
down_revision = '9e42472e63d1'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('counts_call_id_fkey', 'counts', type_='foreignkey')
    op.drop_table('calls')
    op.add_column('counts', sa.Column('time', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False))
    op.drop_column('counts', 'call_id')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('counts', sa.Column('call_id', sa.INTEGER(), autoincrement=False, nullable=False))
    op.create_foreign_key('counts_call_id_fkey', 'counts', 'calls', ['call_id'], ['id'])
    op.drop_column('counts', 'time')
    op.create_table('calls',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('shelter_id', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('bedcount', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('from_number', sa.VARCHAR(length=16), autoincrement=False, nullable=True),
    sa.Column('time', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('inputtext', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('contact_type', postgresql.ENUM('unknown', 'incoming_text', 'incoming_call', 'outgoing_call', name='contact_types'), autoincrement=False, nullable=True),
    sa.Column('error', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.ForeignKeyConstraint(['shelter_id'], ['shelters.id'], name='calls_shelter_id_fkey'),
    sa.PrimaryKeyConstraint('id', name='calls_pkey')
    )
    # ### end Alembic commands ###