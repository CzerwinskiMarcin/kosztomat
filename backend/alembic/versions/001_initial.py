"""initial schema

Revision ID: 001_initial
Revises:
Create Date: 2026-08-28
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = '001_initial'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'source_profiles',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(200), nullable=False, unique=True),
        sa.Column('delimiter', sa.String(8), nullable=False),
        sa.Column('encoding', sa.String(40), nullable=False),
        sa.Column('has_header', sa.Boolean(), nullable=False),
        sa.Column('skip_rows', sa.Integer(), nullable=False),
        sa.Column('decimal_separator', sa.String(4), nullable=False),
        sa.Column('thousand_separator', sa.String(4), nullable=False),
        sa.Column('date_format', sa.String(40), nullable=False),
        sa.Column('amount_mode', sa.String(16), nullable=False),
        sa.Column('column_mapping', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        'source_files',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('display_name', sa.String(255), nullable=False),
        sa.Column('original_filename', sa.String(255), nullable=False),
        sa.Column('stored_path', sa.String(500), nullable=False),
        sa.Column('byte_size', sa.Integer(), nullable=False),
        sa.Column('checksum_sha256', sa.String(64), nullable=False),
        sa.Column('profile_id', sa.Integer(), sa.ForeignKey('source_profiles.id', ondelete='SET NULL')),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('row_count', sa.Integer(), nullable=False),
        sa.Column('error_message', sa.Text()),
        sa.Column('uploaded_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('imported_at', sa.DateTime()),
    )
    op.create_index('ix_source_files_checksum_sha256', 'source_files', ['checksum_sha256'])
    op.create_table(
        'transactions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column(
            'source_file_id',
            sa.Integer(),
            sa.ForeignKey('source_files.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column('row_index', sa.Integer(), nullable=False),
        sa.Column('booking_date', sa.Date(), nullable=False),
        sa.Column('amount', sa.Numeric(14, 2), nullable=False),
        sa.Column('amount_abs', sa.Numeric(14, 2), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('raw_payload', sa.JSON(), nullable=False),
    )
    op.create_index('ix_transactions_source_file_id', 'transactions', ['source_file_id'])
    op.create_index(
        'ix_transactions_file_amount_date',
        'transactions',
        ['source_file_id', 'amount_abs', 'booking_date'],
    )
    op.create_table(
        'comparisons',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column(
            'file_a_id',
            sa.Integer(),
            sa.ForeignKey('source_files.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column(
            'file_b_id',
            sa.Integer(),
            sa.ForeignKey('source_files.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column('date_tolerance_days', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('file_a_id', 'file_b_id', name='uq_comparison_pair'),
    )
    op.create_table(
        'comparison_matches',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column(
            'comparison_id',
            sa.Integer(),
            sa.ForeignKey('comparisons.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column('kind', sa.String(20), nullable=False),
        sa.Column('confidence', sa.Integer(), nullable=False),
        sa.Column(
            'transaction_a_id',
            sa.Integer(),
            sa.ForeignKey('transactions.id', ondelete='SET NULL'),
        ),
        sa.Column(
            'transaction_b_id',
            sa.Integer(),
            sa.ForeignKey('transactions.id', ondelete='SET NULL'),
        ),
        sa.Column('date_delta_days', sa.Integer()),
        sa.Column('amount', sa.Numeric(14, 2), nullable=False),
    )
    op.create_index(
        'ix_comparison_matches_comparison_id', 'comparison_matches', ['comparison_id']
    )


def downgrade() -> None:
    op.drop_table('comparison_matches')
    op.drop_table('comparisons')
    op.drop_table('transactions')
    op.drop_table('source_files')
    op.drop_table('source_profiles')
