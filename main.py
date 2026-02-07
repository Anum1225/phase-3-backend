"""
FastAPI application entry point.

This module initializes the FastAPI application with:
- Database connection and table creation
- CORS middleware for frontend integration
- API routes and endpoints
"""

import contextlib
import os
from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session
from starlette.routing import Mount
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import models before db to ensure they're registered
import models  # noqa: F401
import src.models  # Import chat models (Conversation, Message) to ensure registration
from db import create_db_and_tables, get_session

# Import routers
from routes import auth, tasks, chat

# Configure MCP server path (before creating FastAPI app)
# Import MCP server first to configure it
from src.mcp import mcp

# Note: Default streamable_http_path is "/mcp", so when mounted at "/api/mcp",
# the endpoint will be at "/api/mcp/mcp"

# Create FastAPI application with lifespan context manager
@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager.
    
    Handles:
    - Database table creation
    - MCP session manager initialization
    """
    # Startup: Create database tables
    create_db_and_tables()
    
    # Initialize MCP session manager
    async with mcp.session_manager.run():
        yield
    # Shutdown: Cleanup happens automatically

app = FastAPI(
    title="EvoluTodo API",
    summary="The detailed backend API for EvoluTodo.",
    description="""
# EvoluTodo API 🚀

FastAPI backend for **EvoluTodo** application with JWT authentication, PostgreSQL database, and AI-powered chatbot.

## Features ✨

### Core API
- 🔐 **JWT-based authentication**
- 📝 **Task CRUD operations**
- 🎯 **Task priorities and categories**
- 🔍 **Search and filtering**
- 📊 **Sorting capabilities**

### AI Chatbot 🤖
- 💬 **Natural language task management**
- 🧠 **AI agent with Gemini 2.0 Flash** (via LiteLLM)
- 🔧 **MCP (Model Context Protocol) server** with 5 tools
- 💾 **Conversation persistence** across sessions
- ⚡ **Server-Sent Events (SSE)** streaming responses
- 🔒 **User isolation** and JWT authentication

## Architecture 🏗️

The system is built on a **Stateless Architecture** with **Database-backed State** (PostgreSQL/Neon). It features **User Isolation** via JWT and supports **Horizontal Scalability**.
""",
    version="1.0.0",
    lifespan=lifespan,
    contact={
        "name": "EvoluTodo Team",
        "url": "https://evolutodo.app", 
        "email": "support@evolutodo.app",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
    openapi_tags=[
        {
            "name": "authentication",
            "description": "Operations for **User Registration**, **Login**, and **Profile Management**.",
        },
        {
            "name": "tasks",
            "description": "Manaage your todo items. Support for **CRUD**, **Filtering**, **Searching**, and **Sorting**.",
        },
        {
            "name": "chat",
            "description": "Interact with the **AI Chatbot**. Supports streaming responses via SSE.",
        },
    ]
)

# Configure CORS for frontend integration
# For Hugging Face Spaces, allow all origins by default
# You can restrict this in production by setting ALLOW_ALL_ORIGINS=false
allow_all_origins = os.getenv("ALLOW_ALL_ORIGINS", "true").lower() == "true"

if allow_all_origins:
    # If allowing all origins with credentials, we must use a regex or specific list
    # The wildcard "*" is not valid with allow_credentials=True
    cors_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
    # We could use allow_origin_regex, but explicitly listing common dev origins is safer/simpler
    # If you need to allow dynamic origins, you can add them to ALLOWED_ORIGINS
else:
    # Specific origins (comma-separated in ALLOWED_ORIGINS env var)
    allowed_origins_str = os.getenv("ALLOWED_ORIGINS", "")
    cors_origins = [
        origin.strip() for origin in allowed_origins_str.split(",") if origin.strip()
    ]
    # Default to localhost if none specified
    if not cors_origins:
        cors_origins = [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

# Register API routers
app.include_router(auth.router, prefix="/api", tags=["authentication"])
app.include_router(tasks.router, prefix="/api", tags=["tasks"])
app.include_router(chat.router, prefix="/api", tags=["chat"])

# Mount MCP server at /api/mcp
# The MCP endpoint will be available at: http://localhost:8000/api/mcp/mcp
# Note: Default path is "/mcp", so mounting at "/api/mcp" creates endpoint at "/api/mcp/mcp"
# Note: streamable_http_app() creates an ASGI app that can be mounted in FastAPI
# Note: MCP endpoints use JSON-RPC protocol, so browser GET requests may not work properly
app.mount("/api/mcp", mcp.streamable_http_app())

# Type alias for database session dependency
SessionDep = Annotated[Session, Depends(get_session)]


@app.get("/api/mcp/info")
def mcp_info():
    """
    Information endpoint about the MCP server.
    
    Note: The actual MCP endpoint at /api/mcp/mcp uses JSON-RPC protocol
    and requires proper MCP client requests, not simple browser GET requests.
    
    Returns:
        dict: MCP server information and available tools
    """
    try:
        tools = list(mcp._tool_manager._tools.keys())
        return {
            "mcp_server": "Todo Task Manager",
            "endpoint": "http://localhost:8000/api/mcp/mcp",
            "protocol": "JSON-RPC (MCP)",
            "transport": "streamable-http",
            "available_tools": tools,
            "tool_count": len(tools),
            "note": "MCP endpoints require JSON-RPC protocol requests. Use an MCP client or test with proper JSON-RPC POST requests.",
        }
    except Exception as e:
        return {
            "error": "Failed to get MCP info",
            "message": str(e),
        }


@app.get("/", response_class=HTMLResponse)
def read_root():
    """
    Root endpoint - serves the API status dashboard.
    """
    return """
<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EvoluTodo API Status</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');

        body {
            font-family: 'Outfit', sans-serif;
            background-color: #0f0c29;
            background-image:
                radial-gradient(at 0% 0%, rgba(76, 29, 149, 0.3) 0px, transparent 50%),
                radial-gradient(at 100% 0%, rgba(139, 92, 246, 0.3) 0px, transparent 50%),
                radial-gradient(at 100% 100%, rgba(236, 72, 153, 0.3) 0px, transparent 50%),
                radial-gradient(at 0% 100%, rgba(59, 130, 246, 0.3) 0px, transparent 50%);
            background-attachment: fixed;
            color: white;
        }

        .glass-panel {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(16px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        }

        .status-dot {
            box-shadow: 0 0 10px currentColor;
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0% {
                opacity: 1;
                transform: scale(1);
            }

            50% {
                opacity: 0.7;
                transform: scale(1.1);
            }

            100% {
                opacity: 1;
                transform: scale(1);
            }
        }

        .mesh-bg {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            z-index: -1;
            overflow: hidden;
        }

        .orb {
            position: absolute;
            border-radius: 50%;
            filter: blur(80px);
            opacity: 0.3;
            animation: float 20s infinite ease-in-out;
        }

        @keyframes float {

            0%,
            100% {
                transform: translate(0, 0);
            }

            25% {
                transform: translate(100px, 50px);
            }

            50% {
                transform: translate(50px, 100px);
            }

            75% {
                transform: translate(-50px, 50px);
            }
        }
    </style>
</head>

<body class="min-h-screen flex flex-col items-center justify-center p-4 relative overflow-x-hidden">

    <!-- Animated Background -->
    <div class="mesh-bg">
        <div class="orb w-96 h-96 bg-violet-600 top-[-50px] left-[-50px]"></div>
        <div class="orb w-[500px] h-[500px] bg-indigo-600 bottom-[-100px] right-[-100px]" style="animation-delay: -5s">
        </div>
        <div class="orb w-64 h-64 bg-fuchsia-500 top-[40%] left-[60%]" style="animation-delay: -10s"></div>
    </div>

    <!-- Main Card -->
    <div class="glass-panel w-full max-w-4xl rounded-3xl p-8 md:p-12 relative z-10 animate-[fadeIn_1s_ease-out]">

        <!-- Header -->
        <div class="flex flex-col md:flex-row justify-between items-center mb-12 gap-6">
            <div class="flex items-center gap-4">
                <div class="relative">
                    <div
                        class="w-12 h-12 rounded-xl bg-gradient-to-tr from-violet-600 to-indigo-600 flex items-center justify-center text-2xl shadow-lg ring-1 ring-white/20">
                        🚀
                    </div>
                    <div
                        class="absolute -bottom-1 -right-1 w-4 h-4 bg-emerald-500 rounded-full border-2 border-[#0f0c29] status-dot text-emerald-500">
                    </div>
                </div>
                <div>
                    <h1
                        class="text-3xl md:text-4xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-white to-gray-300">
                        EvoluTodo API
                    </h1>
                    <p class="text-gray-400 text-sm tracking-widest uppercase font-medium mt-1">System Status &
                        Diagnostics</p>
                </div>
            </div>

            <div class="flex gap-3">
                <a href="/docs"
                    class="px-5 py-2.5 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 transition-all font-medium flex items-center gap-2 group">
                    <span>Docs</span>
                    <svg class="w-4 h-4 text-gray-400 group-hover:text-white transition-colors" fill="none"
                        stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
                    </svg>
                </a>
                <a href="/redoc"
                    class="px-5 py-2.5 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 transition-all font-medium flex items-center gap-2 group">
                    <span>ReDoc</span>
                    <svg class="w-4 h-4 text-gray-400 group-hover:text-white transition-colors" fill="none"
                        stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
                    </svg>
                </a>
            </div>
        </div>

        <!-- Status Grid -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-12">
            <!-- System Health -->
            <div
                class="bg-gray-900/40 rounded-2xl p-5 border border-white/5 hover:border-violet-500/30 transition-colors group">
                <div class="flex justify-between items-start mb-4">
                    <div
                        class="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 group-hover:bg-emerald-500/20 transition-colors">
                        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                                d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                        </svg>
                    </div>
                    <span id="api-status-badge"
                        class="px-2 py-1 rounded text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">Active</span>
                </div>
                <h3 class="text-gray-400 text-sm font-medium mb-1">System Health</h3>
                <p id="api-latency" class="text-2xl font-bold text-white">Checking...</p>
            </div>

            <!-- Database -->
            <div
                class="bg-gray-900/40 rounded-2xl p-5 border border-white/5 hover:border-blue-500/30 transition-colors group">
                <div class="flex justify-between items-start mb-4">
                    <div
                        class="p-2 rounded-lg bg-blue-500/10 text-blue-400 group-hover:bg-blue-500/20 transition-colors">
                        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                                d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4">
                            </path>
                        </svg>
                    </div>
                    <span id="db-status-badge"
                        class="px-2 py-1 rounded text-xs font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/20">Checking...</span>
                </div>
                <h3 class="text-gray-400 text-sm font-medium mb-1">Database</h3>
                <p class="text-2xl font-bold text-white">PostgreSQL</p>
            </div>

            <!-- AI Services -->
            <div
                class="bg-gray-900/40 rounded-2xl p-5 border border-white/5 hover:border-fuchsia-500/30 transition-colors group">
                <div class="flex justify-between items-start mb-4">
                    <div
                        class="p-2 rounded-lg bg-fuchsia-500/10 text-fuchsia-400 group-hover:bg-fuchsia-500/20 transition-colors">
                        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                                d="M19.428 15.428a2 2 0 00-1.022-.547l-2.384-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z">
                            </path>
                        </svg>
                    </div>
                    <span
                        class="px-2 py-1 rounded text-xs font-semibold bg-fuchsia-500/10 text-fuchsia-400 border border-fuchsia-500/20">Ready</span>
                </div>
                <h3 class="text-gray-400 text-sm font-medium mb-1">AI Services</h3>
                <p class="text-2xl font-bold text-white">GPT-4o</p>
            </div>

            <!-- API Version -->
            <div
                class="bg-gray-900/40 rounded-2xl p-5 border border-white/5 hover:border-amber-500/30 transition-colors group">
                <div class="flex justify-between items-start mb-4">
                    <div
                        class="p-2 rounded-lg bg-amber-500/10 text-amber-400 group-hover:bg-amber-500/20 transition-colors">
                        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                                d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z">
                            </path>
                        </svg>
                    </div>
                    <span id="version-badge"
                        class="px-2 py-1 rounded text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">Latest</span>
                </div>
                <h3 class="text-gray-400 text-sm font-medium mb-1">Version</h3>
                <p id="api-version" class="text-2xl font-bold text-white">v1.0.0</p>
            </div>
        </div>

        <!-- Endpoints Preview -->
        <div class="space-y-4">
            <h2 class="text-xl font-semibold mb-6 flex items-center gap-2">
                <span class="w-1 h-6 bg-violet-500 rounded-full"></span>
                API Endpoints
            </h2>

            <div class="grid gap-3">
                <!-- Auth -->
                <div
                    class="flex items-center justify-between p-4 rounded-xl bg-white/5 border border-white/5 hover:bg-white/10 transition-colors">
                    <div class="flex items-center gap-4">
                        <span
                            class="text-xs font-bold text-violet-400 bg-violet-400/10 px-2 py-1 rounded uppercase">POST</span>
                        <code class="text-sm font-mono text-gray-300">/api/auth/login</code>
                    </div>
                    <div class="flex items-center gap-2">
                        <div class="w-2 h-2 rounded-full bg-emerald-500"></div>
                        <span class="text-xs text-gray-400">Operational</span>
                    </div>
                </div>

                <!-- Tasks -->
                <div
                    class="flex items-center justify-between p-4 rounded-xl bg-white/5 border border-white/5 hover:bg-white/10 transition-colors">
                    <div class="flex items-center gap-4">
                        <span
                            class="text-xs font-bold text-blue-400 bg-blue-400/10 px-2 py-1 rounded uppercase">GET</span>
                        <code class="text-sm font-mono text-gray-300">/api/{user_id}/tasks</code>
                    </div>
                    <div class="flex items-center gap-2">
                        <div class="w-2 h-2 rounded-full bg-emerald-500"></div>
                        <span class="text-xs text-gray-400">Operational</span>
                    </div>
                </div>

                <!-- Chat -->
                <div
                    class="flex items-center justify-between p-4 rounded-xl bg-white/5 border border-white/5 hover:bg-white/10 transition-colors">
                    <div class="flex items-center gap-4">
                        <span
                            class="text-xs font-bold text-fuchsia-400 bg-fuchsia-400/10 px-2 py-1 rounded uppercase">POST</span>
                        <code class="text-sm font-mono text-gray-300">/api/{user_id}/chat</code>
                    </div>
                    <div class="flex items-center gap-2">
                        <div class="w-2 h-2 rounded-full bg-emerald-500"></div>
                        <span class="text-xs text-gray-400">Operational</span>
                    </div>
                </div>
            </div>
        </div>

        <!-- Footer -->
        <div
            class="mt-12 pt-8 border-t border-white/10 flex flex-col md:flex-row justify-between items-center gap-4 text-sm text-gray-500">
            <div>&copy; 2024 EvoluTodo API. All rights reserved.</div>
            <div class="flex gap-6">
                <a href="#" class="hover:text-white transition-colors">Features</a>
                <a href="#" class="hover:text-white transition-colors">Privacy</a>
                <a href="#" class="hover:text-white transition-colors">Terms</a>
                <a href="#" class="hover:text-white transition-colors">Contact</a>
            </div>
        </div>
    </div>

    <script>
        // Simple status checker
        async function checkHealth() {
            const start = Date.now();
            try {
                const res = await fetch('/health');
                const diff = Date.now() - start;

                if (res.ok) {
                    const data = await res.json();
                    
                    // Update System Health
                    document.getElementById('api-latency').textContent = diff + 'ms';
                    document.getElementById('api-status-badge').textContent = 'Active';
                    document.getElementById('api-status-badge').className = 'px-2 py-1 rounded text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20';
                    
                    // Update Database Status
                    const dbStatus = document.getElementById('db-status-badge');
                    if (data.database === 'connected') {
                        dbStatus.textContent = 'Connected';
                        dbStatus.className = 'px-2 py-1 rounded text-xs font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/20';
                    } else {
                        dbStatus.textContent = 'Error';
                        dbStatus.className = 'px-2 py-1 rounded text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20';
                    }

                    // Update Version if available
                    if (data.version) {
                        document.getElementById('api-version').textContent = 'v' + data.version;
                    }

                } else {
                    throw new Error('Health check failed');
                }
            } catch (e) {
                // System Health Error
                document.getElementById('api-latency').textContent = 'Offline';
                document.getElementById('api-latency').className = 'text-2xl font-bold text-rose-500';
                document.getElementById('api-status-badge').textContent = 'Error';
                document.getElementById('api-status-badge').className = 'px-2 py-1 rounded text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20';
                
                // Database Status Error (assume offline if health check fails)
                const dbStatus = document.getElementById('db-status-badge');
                dbStatus.textContent = 'Unknown';
                dbStatus.className = 'px-2 py-1 rounded text-xs font-semibold bg-gray-500/10 text-gray-400 border border-gray-500/20';
            }
        }

        // Check immediately and then every 30s
        checkHealth();
        setInterval(checkHealth, 30000);
    </script>
</body>

</html>
"""


@app.get("/health")
def health_check(session: SessionDep):
    """
    Health check endpoint with database connectivity test.

    Args:
        session: Database session (injected)

    Returns:
        dict: Health status including database connectivity
    """
    try:
        # Simple database query to verify connectivity
        session.exec("SELECT 1")
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {
        "status": "healthy",
        "database": db_status,
        "version": "1.0.0",
    }


# Test endpoints for User model validation (will be removed in Phase 6: Polish)


@app.post("/test/users")
def create_test_user(email: str, name: str, session: SessionDep):
    """
    Test endpoint to verify User model creation.

    This endpoint will be removed after validation (Task T049).

    Args:
        email: User's email address
        name: User's display name
        session: Database session (injected)

    Returns:
        dict: Created user data
    """
    from models import User

    user = User(email=email, name=name)
    session.add(user)
    session.commit()
    session.refresh(user)

    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "created_at": user.created_at.isoformat(),
    }


@app.get("/test/users/{email}")
def get_test_user(email: str, session: SessionDep):
    """
    Test endpoint to verify User model query.

    This endpoint will be removed after validation (Task T049).

    Args:
        email: User's email address to search for
        session: Database session (injected)

    Returns:
        dict: User data if found, error otherwise
    """
    from sqlmodel import select

    from models import User

    statement = select(User).where(User.email == email)
    user = session.exec(statement).first()

    if not user:
        return {"error": "User not found"}

    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "created_at": user.created_at.isoformat(),
    }
