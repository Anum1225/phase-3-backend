"""Add messages table

Revision ID: 005
Revises: 004
Create Date: 2025-12-17

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create enum type using raw SQL with IF NOT EXISTS
    conn = op.get_bind()
    conn.execute(sa.text(
        "DO $$ BEGIN "
        "CREATE TYPE message_role AS ENUM ('user', 'assistant'); "
        "EXCEPTION WHEN duplicate_object THEN null; "
        "END $$;"
    ))

    # Create messages table
    # Note: Using STRING type for role column instead of Enum to avoid create_type issues
    # The enum constraint is enforced at database level via the column type
    op.create_table(
        'messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('conversation_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('role', sa.String(), nullable=False),  # Will be cast to message_role enum
        sa.Column('content', sa.String(length=5000), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.CheckConstraint('LENGTH(content) <= 5000', name='chk_message_content_length'),
    )

    # Alter the role column to use the enum type
    conn.execute(sa.text(
        "ALTER TABLE messages ALTER COLUMN role TYPE message_role USING role::message_role"
    ))

    # Create indexes
    op.create_index('idx_messages_conversation_id', 'messages', ['conversation_id'])
    op.create_index('idx_messages_created_at', 'messages', ['created_at'])
    op.create_index('idx_messages_user_id', 'messages', ['user_id'])


def downgrade() -> None:
    op.drop_index('idx_messages_user_id')
    op.drop_index('idx_messages_created_at')
    op.drop_index('idx_messages_conversation_id')
    op.drop_table('messages')
    sa.Enum(name='message_role').drop(op.get_bind())
