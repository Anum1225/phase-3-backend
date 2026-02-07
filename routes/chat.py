"""
Chat API routes for AI chatbot functionality.

This module provides endpoints for:
- Creating and continuing conversations
- Sending messages to the AI agent
- Retrieving conversation history
- Server-Sent Events (SSE) streaming responses
"""
import asyncio
import json
from datetime import datetime
from typing import AsyncGenerator
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from sse_starlette.sse import EventSourceResponse

from db import get_session
from middleware.jwt import get_current_user_id
from models import User  # Import User model
from src.models import Conversation, Message, MessageRole
from schemas.chat import ChatRequest, ChatResponse
from src.agent.runner import run_agent, run_agent_streamed, load_conversation_history as load_history

router = APIRouter()


def verify_user_exists(user_id: str, session: Session) -> None:
    """
    Verify that user exists in database.

    This validation is required because JWT authentication only verifies
    the token validity, not the user's existence in our database.

    Args:
        user_id: User ID from JWT token
        session: Database session

    Raises:
        HTTPException 400: If user not found in database

    Note:
        Users should be created during registration/signup flow via Better Auth.
        If you're getting this error, ensure the user registration endpoint
        properly creates the user in the database.
    """
    user = session.get(User, user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "User not found in database. Please complete registration first. "
                "This typically happens when the JWT token is valid but the user "
                "record doesn't exist in the database."
            )
        )


async def generate_agent_response(
    user_id: str,
    message: str,
    conversation_id: str,
    session: Session
) -> AsyncGenerator[str, None]:
    """
    Generate streaming response from AI agent.

    This function:
    1. Loads conversation history
    2. Invokes the AI agent with user message
    3. Streams the response back
    4. Saves assistant message to database

    Args:
        user_id: User ID for agent context
        message: User's message
        conversation_id: Conversation ID for history context
        session: Database session

    Yields:
        JSON-formatted SSE events with assistant response chunks
    """
    try:
        # Load conversation history for context (excluding current user message)
        history = load_history(conversation_id, session, limit=50)

        # Run agent with conversation context using the streaming runner
        full_content = ""
        try:
            async for chunk in run_agent_streamed(
                user_id=user_id,
                message=message,
                conversation_history=history
            ):
                if chunk:
                    # Update buffered content for DB saving later
                    full_content += chunk
                    
                    # Yield chunk to frontend as SSE event
                    yield json.dumps({
                        "conversation_id": str(conversation_id),
                        "message": chunk,
                        "role": "assistant",
                        "created_at": datetime.utcnow().isoformat()
                    })
        except Exception as e:
            import traceback
            error_msg = f"Agent stream event error: {str(e)}\n{traceback.format_exc()}"
            logging.error(error_msg)
            yield json.dumps({
                "error": error_msg,
                "conversation_id": str(conversation_id)
            })
            return

        # Save assistant response to database after stream finishes
        if full_content:
            assistant_message = Message(
                conversation_id=conversation_id,
                user_id=user_id,
                role=MessageRole.assistant,
                content=full_content,
                created_at=datetime.utcnow()
            )

            session.add(assistant_message)

            # Update conversation timestamp
            conversation = session.get(Conversation, conversation_id)
            if conversation:
                conversation.updated_at = datetime.utcnow()
                session.add(conversation)

            session.commit()

    except Exception as e:
        # Send error event with full traceback
        import traceback
        error_details = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
        print(f"Error in generate_agent_response: {error_details}")

        yield json.dumps({
            "error": str(e),
            "error_type": type(e).__name__,
            "conversation_id": conversation_id
        })


@router.post("/{user_id}/chat")
async def chat(
    user_id: str,
    request: ChatRequest,
    session: Session = Depends(get_session),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Send a message to the AI chatbot and receive streaming response.

    This endpoint:
    1. Validates user authentication and authorization
    2. Creates new conversation or retrieves existing one
    3. Saves user message to database
    4. Invokes AI agent with conversation context
    5. Streams assistant response using Server-Sent Events (SSE)
    6. Saves assistant response to database

    Args:
        user_id: User ID from path (must match JWT token)
        request: ChatRequest with message and optional conversation_id
        session: Database session (injected)
        current_user_id: Authenticated user ID from JWT (injected)

    Returns:
        EventSourceResponse: SSE stream with assistant responses

    Raises:
        HTTPException 401: Unauthorized (invalid JWT)
        HTTPException 403: Forbidden (user_id mismatch)
        HTTPException 404: Conversation not found or not owned by user
        HTTPException 422: Validation error (empty message, too long, etc.)
        HTTPException 500: Internal server error

    Request Example:
        POST /api/user123/chat
        Authorization: Bearer <jwt-token>
        {
            "message": "I need to buy groceries",
            "conversation_id": 1  // optional
        }

    Response Example (SSE Stream):
        data: {"conversation_id": 1, "message": "I've created...", "role": "ASSISTANT"}

    Security:
        - JWT authentication required
        - User isolation enforced (user_id must match token)
        - Conversation ownership validated
    """
    # Validate user_id matches authenticated user
    if user_id != current_user_id:
        print(f"Auth mismatch: path user_id={user_id}, token user_id={current_user_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this user's chat"
        )

    # Validate message is not empty and within length limit
    if not request.message or not request.message.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Message cannot be empty"
        )

    if len(request.message) > 5000:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Message cannot exceed 5000 characters"
        )

    try:
        # Verify user exists in database
        verify_user_exists(user_id, session)

        # Create new conversation or retrieve existing one
        if request.conversation_id is None:
            # Create new conversation
            conversation = Conversation(
                user_id=user_id,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            session.add(conversation)
            session.commit()
            session.refresh(conversation)
            conversation_id = conversation.id
        else:
            # Retrieve existing conversation
            conversation = session.get(Conversation, request.conversation_id)

            if not conversation:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Conversation not found"
                )

            # Verify conversation ownership
            if conversation.user_id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to access this conversation"
                )

            conversation_id = conversation.id

        # Save user message to database
        user_message = Message(
            conversation_id=conversation_id,
            user_id=user_id,
            role=MessageRole.user,
            content=request.message,
            created_at=datetime.utcnow()
        )

        session.add(user_message)

        # Update conversation timestamp
        conversation.updated_at = datetime.utcnow()
        session.add(conversation)

        session.commit()

        # Return SSE stream with agent response
        return EventSourceResponse(
            generate_agent_response(
                user_id=user_id,
                message=request.message,
                conversation_id=str(conversation_id),
                session=session
            )
        )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise

    except Exception as e:
        # Log error and return 500
        # TODO: Add proper logging
        print(f"Error in chat endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/{user_id}/conversations/{conversation_id}")
def get_conversation(
    user_id: str,
    conversation_id: str,
    session: Session = Depends(get_session),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Retrieve a conversation with its message history.

    Args:
        user_id: User ID from path
        conversation_id: Conversation ID to retrieve
        session: Database session (injected)
        current_user_id: Authenticated user ID from JWT (injected)

    Returns:
        ConversationResponse with messages

    Raises:
        HTTPException 403: Forbidden (user_id mismatch or not owner)
        HTTPException 404: Conversation not found
    """
    # Validate user_id matches authenticated user
    if user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this user's conversations"
        )

    # Retrieve conversation
    conversation = session.get(Conversation, conversation_id)

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )

    # Verify ownership
    if conversation.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this conversation"
        )

    # Load messages
    statement = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )

    messages = session.exec(statement).all()

    return {
        "id": conversation.id,
        "user_id": conversation.user_id,
        "created_at": conversation.created_at,
        "updated_at": conversation.updated_at,
        "messages": messages
    }


@router.get("/{user_id}/conversations")
def list_conversations(
    user_id: str,
    session: Session = Depends(get_session),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    List all conversations for a user.

    Args:
        user_id: User ID from path
        session: Database session (injected)
        current_user_id: Authenticated user ID from JWT (injected)

    Returns:
        List of conversations (without messages)

    Raises:
        HTTPException 403: Forbidden (user_id mismatch)
    """
    # Validate user_id matches authenticated user
    if user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this user's conversations"
        )

    # Query conversations
    statement = (
        select(Conversation)
        .where(Conversation.user_id == user_id)
        .order_by(Conversation.updated_at.desc())
    )

    conversations = session.exec(statement).all()

    return conversations
