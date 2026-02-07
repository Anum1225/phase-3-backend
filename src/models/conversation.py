"""
Conversation model for chat sessions.

This module defines the Conversation SQLModel for Phase 3 chatbot functionality.
A conversation represents a continuous chat session between a user and the AI assistant.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Conversation(SQLModel, table=True):
    """
    Conversation model for chat sessions.

    A conversation represents a continuous chat session between a user
    and the AI assistant. Conversations persist across server restarts
    and enable users to resume previous discussions.

    Relationships:
    - Belongs to User (via user_id foreign key)
    - Has many Messages (one-to-many)

    Indexes:
    - user_id: For filtering user's conversations
    - updated_at: For sorting by recency
    """

    __tablename__ = "conversations"

    # Primary Key
    id: Optional[uuid.UUID] = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        description="Unique conversation identifier",
    )

    # Foreign Keys
    user_id: str = Field(
        foreign_key="user.id",
        index=True,
        nullable=False,
        description="User who owns this conversation",
    )

    # Timestamps
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        nullable=False,
        description="When conversation was created",
    )

    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        nullable=False,
        index=True,
        description="When conversation was last updated (last message time)",
    )

    class Config:
        """Pydantic configuration for JSON serialization"""

        json_encoders = {datetime: lambda v: v.isoformat()}
