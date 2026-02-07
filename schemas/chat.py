"""
Pydantic schemas for chat API request/response models
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from src.models.message import MessageRole


class ChatRequest(BaseModel):
    """Schema for chat message request"""
    message: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="User's chat message"
    )
    conversation_id: Optional[str] = Field(
        None,
        description="Existing conversation ID (optional - creates new if not provided)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "message": "I need to buy groceries",
                "conversation_id": 1
            }
        }


class MessageResponse(BaseModel):
    """Schema for individual message response"""
    id: str
    conversation_id: str
    user_id: str
    role: MessageRole
    content: str
    created_at: datetime

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "conversation_id": 1,
                "user_id": "user123",
                "role": "USER",
                "content": "I need to buy groceries",
                "created_at": "2025-12-17T10:00:00Z"
            }
        }


class ConversationResponse(BaseModel):
    """Schema for conversation response"""
    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime
    messages: Optional[List[MessageResponse]] = Field(
        None,
        description="Recent conversation messages (optional)"
    )

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "user_id": "user123",
                "created_at": "2025-12-17T10:00:00Z",
                "updated_at": "2025-12-17T10:05:00Z",
                "messages": [
                    {
                        "id": 1,
                        "conversation_id": 1,
                        "user_id": "user123",
                        "role": "USER",
                        "content": "I need to buy groceries",
                        "created_at": "2025-12-17T10:00:00Z"
                    },
                    {
                        "id": 2,
                        "conversation_id": 1,
                        "user_id": "user123",
                        "role": "ASSISTANT",
                        "content": "I've created a task 'Buy groceries' for you.",
                        "created_at": "2025-12-17T10:00:05Z"
                    }
                ]
            }
        }


class ChatResponse(BaseModel):
    """Schema for chat response with streaming support"""
    conversation_id: str
    message: str
    role: MessageRole = MessageRole.assistant
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "conversation_id": 1,
                "message": "I've created a task 'Buy groceries' for you.",
                "role": "ASSISTANT",
                "created_at": "2025-12-17T10:00:05Z"
            }
        }
