"""
Agent Runner for Todo Chatbot

This module handles:
- Creating the OpenAI Agent
- Connecting to the MCP server
- Loading conversation history
- Running the agent with user messages
"""

import logging
import os
import asyncio
import uuid
from typing import List, Dict, Any, Optional, Tuple
from sqlmodel import Session, select
from dotenv import load_dotenv

from agents import AsyncOpenAI, OpenAIChatCompletionsModel, Agent, Runner
from openai.types.responses import ResponseTextDeltaEvent
from agents.mcp import MCPServerStreamableHttp
from agents.run import RunConfig

from .config import (
    get_system_prompt,
    get_agent_config,
    format_conversation_history,
)
from ..models.message import Message


async def create_agent(
    mcp_server_url: Optional[str] = None,
) -> tuple[Agent, MCPServerStreamableHttp, RunConfig]:
    """
    Create the Todo Assistant agent with MCP server connection.

    Args:
        mcp_server_url: Optional MCP server URL (uses env var if not provided)

    Returns:
        Tuple of (Agent instance, MCP server connection, RunConfig)

    Raises:
        ValueError: If OPENAI_API_KEY is not set
    """
    # Ensure env vars are loaded
    load_dotenv()
    
    # Get configuration
    config = get_agent_config()
    server_url = mcp_server_url or config["mcp_server_url"]

    # Verify API key
    api_key = os.getenv("OPENAI_API_KEY")
    # Mask key for logging
    masked_key = f"{api_key[:4]}...{api_key[-4:]}" if api_key else "None"
    logging.info(f"Creating agent with API Key: {masked_key}")
    
    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY environment variable is required for OpenAI integration"
        )

    # Get model from config
    model_name = config["model"]
    logging.info(f"Using model: {model_name}")

    # Setup OpenAI client
    external_provider = AsyncOpenAI(
        api_key=api_key,
    )

    # Create model
    model = OpenAIChatCompletionsModel(
        openai_client=external_provider,
        model=model_name,
    )

    # Create run configuration
    run_config = RunConfig(
        model=model,
        model_provider=external_provider,
        tracing_disabled=True
    )

    # Create MCP server connection
    mcp_server = MCPServerStreamableHttp(
        name="Todo MCP Server",
        params={
            "url": server_url,
            "timeout": config["mcp_timeout_seconds"],
        },
        cache_tools_list=True,  # Cache for performance
    )

    # Initialize MCP connection
    await mcp_server.__aenter__()

    # Create agent (model specified in run_config)
    agent = Agent(
        name="Todo Assistant",
        instructions=get_system_prompt(),
        mcp_servers=[mcp_server],
    )

    return agent, mcp_server, run_config


async def run_agent(
    user_id: str,
    message: str,
    conversation_history: Optional[List[Message]] = None,
    session: Optional[Session] = None,
) -> str:
    """
    Run the agent with a user message and conversation context.

    Args:
        user_id: The user's ID (passed to MCP tools)
        message: The user's message
        conversation_history: Optional list of previous messages for context
        session: Optional database session for loading history

    Returns:
        Agent's response text

    Example:
        response = await run_agent(
            user_id="user123",
            message="Add a task to buy groceries",
            conversation_history=messages
        )
    """
    agent = None
    mcp_server = None
    run_config = None

    try:
        # Create agent, MCP connection, and config
        agent, mcp_server, run_config = await create_agent()

        # Format conversation history
        history = []
        if conversation_history:
            history = format_conversation_history(conversation_history)

        # Include user_id in the message so agent knows which user to operate on
        # The agent will extract the user_id and pass it to all MCP tool calls
        full_message = f"[User ID: {user_id}]\n{message}"

        # Prepare the full conversation history
        new_user_message = {"role": "user", "content": full_message}
        full_input = history + [new_user_message]

        # Run the agent with config
        logging.info(f"Running agent for user {user_id} with history length {len(history)}")
        try:
            result = await Runner.run(
                agent,
                full_input,
                run_config=run_config,
                context={"user_id": user_id},
            )
            
            output = result.final_output
            logging.info(f"Agent run completed. Output length: {len(output) if output else 0}")
            
            if not output:
                logging.warning("Agent returned empty output!")
                return "I'm sorry, I processed your request but didn't generate a response. How else can I help?"
                
            return output
        except Exception as e:
            logging.error(f"Error during agent runner: {str(e)}")
            raise

    finally:
        # Cleanup MCP connection
        if mcp_server:
            try:
                await mcp_server.__aexit__(None, None, None)
            except Exception as e:
                print(f"Error closing MCP server: {e}")


async def run_agent_streamed(
    user_id: str,
    message: str,
    conversation_history: Optional[List[Message]] = None,
):
    """
    Run the agent with streaming responses.

    Args:
        user_id: The user's ID
        message: The user's message
        conversation_history: Optional conversation history

    Yields:
        Agent response chunks as they are generated

    Example:
        async for chunk in run_agent_streamed(user_id, message, history):
            print(chunk, end="", flush=True)
    """
    agent = None
    mcp_server = None
    run_config = None

    try:
        # Create agent, MCP connection, and config
        logging.info(f"Creating agent for streaming run (user_id: {user_id})")
        agent, mcp_server, run_config = await create_agent()
        logging.info("Agent and MCP connection established successfully")

        # Format conversation history
        history = []
        if conversation_history:
            history = format_conversation_history(conversation_history)
        logging.info(f"Loaded {len(history)} history messages")

        # Prepare message with user_id context
        full_message = f"[User ID: {user_id}]\n{message}"

        # Prepare the full conversation history
        new_user_message = {"role": "user", "content": full_message}
        full_input = history + [new_user_message]

        # Run agent with streaming and config
        logging.info("Starting agent run_streamed...")
        result = Runner.run_streamed(
            agent,
            full_input,
            run_config=run_config,
            context={"user_id": user_id},
        )

        # Stream text deltas for token-by-token feedback
        logging.info("Iterating over agent events...")
        event_count = 0
        async for event in result.stream_events():
            event_count += 1
            logging.debug(f"Agent event {event_count}: type={event.type}")
            
            if event.type == "raw_response_event":
                if isinstance(event.data, ResponseTextDeltaEvent):
                    yield event.data.delta
            elif event.type == "tool_call_event":
                logging.info(f"Agent tool call: {event.data}")
            elif event.type == "tool_call_result_event":
                logging.info(f"Agent tool call result: {event.data}")
            elif event.type == "error":
                logging.error(f"Agent stream event error: {event.data}")
        
        logging.info(f"Finished streaming {event_count} events")

    finally:
        # Cleanup
        if mcp_server:
            try:
                await mcp_server.__aexit__(None, None, None)
            except Exception:
                pass


def load_conversation_history(
    conversation_id: Any,
    session: Session,
    limit: int = 50,
) -> List[Message]:
    """
    Load recent conversation history from database.

    Args:
        conversation_id: The conversation ID
        session: Database session
        limit: Maximum number of messages to load (default: 50)

    Returns:
        List of Message objects ordered by created_at (oldest first)

    Example:
        messages = load_conversation_history(
            conversation_id=123,
            session=db_session,
            limit=50
        )
    """
    # Query messages for this conversation, ordered by creation time
    statement = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
    )

    messages = session.exec(statement).all()

    # Reverse to get chronological order (oldest first)
    return list(reversed(messages))


# Synchronous wrapper for testing/CLI usage
def run_agent_sync(user_id: str, message: str) -> str:
    """
    Synchronous wrapper for run_agent (for testing/CLI).

    Args:
        user_id: User's ID
        message: User's message

    Returns:
        Agent's response
    """
    return asyncio.run(run_agent(user_id, message))
