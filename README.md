---
title: Todo App Backend API
emoji: 📝
colorFrom: blue
colorTo: purple
sdk: docker
pinned: false
license: mit
---

# Todo App Backend API 🚀

FastAPI backend for Todo application with JWT authentication, PostgreSQL database, and AI-powered chatbot (Phase 3).

## Features ✨

### Phase 2: Core API
- 🔐 JWT-based authentication
- 📝 Task CRUD operations
- 🎯 Task priorities and categories
- 🔍 Search and filtering
- 📊 Sorting capabilities

### Phase 3: AI Chatbot 🤖
- 💬 Natural language task management
- 🧠 AI agent with Gemini 2.0 Flash (via LiteLLM)
- 🔧 MCP (Model Context Protocol) server with 5 tools
- 💾 Conversation persistence across sessions
- ⚡ Server-Sent Events (SSE) streaming responses
- 🔒 User isolation and JWT authentication

---

## Quick Start 🏃

### Prerequisites
- Python 3.13+
- UV package manager
- PostgreSQL database (Neon recommended)
- Google API key (for Gemini)

### Installation

```bash
cd backend

# Create virtual environment
uv venv

# Activate virtual environment
source .venv/bin/activate  # Linux/Mac
# OR
.venv\Scripts\activate     # Windows

# Install dependencies
uv sync
```

### Configuration

Create `.env` file:

```env
# Database (Required)
DATABASE_URL=postgresql://user:password@host:5432/database?sslmode=require

# Authentication (Required)
BETTER_AUTH_SECRET=your-256-bit-secret-key-here
JWT_ALGORITHM=HS256

# Phase 3: AI Chatbot (Required for chatbot features)
GOOGLE_API_KEY=your-google-gemini-api-key-here
MCP_SERVER_URL=http://localhost:8000/api/mcp/mcp
AGENT_MODEL=gemini/gemini-2.0-flash-exp
AGENT_TEMPERATURE=0.7
AGENT_MAX_TOKENS=1000
MAX_CONVERSATION_HISTORY=50

# CORS (Optional)
ALLOW_ALL_ORIGINS=true
# ALLOWED_ORIGINS=http://localhost:3000,https://your-frontend.vercel.app
```

### Run Server

```bash
uvicorn main:app --reload --port 8000
```

Server will be available at: `http://localhost:8000`

- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **MCP Info**: http://localhost:8000/api/mcp/info

---

## API Endpoints 📡

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login user
- `GET /api/auth/profile` - Get user profile
- `POST /api/auth/logout` - Logout user

### Tasks (Phase 2)
- `POST /api/{user_id}/tasks` - Create task
- `GET /api/{user_id}/tasks` - List tasks (with filters)
- `GET /api/{user_id}/tasks/{task_id}` - Get task
- `PUT /api/{user_id}/tasks/{task_id}` - Update task
- `DELETE /api/{user_id}/tasks/{task_id}` - Delete task
- `PATCH /api/{user_id}/tasks/{task_id}/complete` - Toggle completion

### AI Chatbot (Phase 3) 🤖
- `POST /api/{user_id}/chat` - Send message to AI chatbot (SSE streaming)
- `GET /api/{user_id}/conversations` - List all conversations
- `GET /api/{user_id}/conversations/{conversation_id}` - Get conversation with messages

#### Chat Endpoint Example

**Request**:
```bash
curl -X POST http://localhost:8000/api/USER_ID/chat \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I need to buy groceries",
    "conversation_id": null
  }'
```

**Response** (SSE Stream):
```
data: {"conversation_id": 1, "message": "I've created a task...", "role": "ASSISTANT"}
```

### MCP Server Endpoints
- `GET /api/mcp/info` - MCP server information
- `POST /api/mcp/mcp` - MCP JSON-RPC endpoint (internal use)

---

## MCP Tools 🔧

The AI agent has access to 5 MCP tools for task management:

1. **add_task** - Create new tasks
   - Parameters: `user_id`, `title`, `description`, `priority`, `category`

2. **list_tasks** - List tasks with filters
   - Parameters: `user_id`, `status`, `priority`, `category`

3. **complete_task** - Mark tasks complete/incomplete
   - Parameters: `user_id`, `task_id`, `completed`

4. **delete_task** - Delete tasks
   - Parameters: `user_id`, `task_id`

5. **update_task** - Update task details
   - Parameters: `user_id`, `task_id`, `title`, `description`, `priority`, `category`

All tools enforce user isolation - users can only access their own tasks.

---

## Database Schema 📊

### Phase 2 Tables
- **users** - User accounts
- **tasks** - Todo tasks

### Phase 3 Tables (Chatbot)
- **conversations** - Chat conversations
- **messages** - Chat messages with roles (USER, ASSISTANT)

**Relationships**:
- User → Conversations (1:many)
- Conversation → Messages (1:many)
- User → Tasks (1:many)

---

## Testing 🧪

### Prerequisites

```bash
cd backend
source .venv/bin/activate
uv sync
```

### Run Tests

```bash
# All tests
pytest tests/ -v

# Specific test file
pytest tests/e2e/test_task_creation.py -v

# With coverage
pytest tests/ --cov=. --cov-report=html

# Skip slow tests
pytest tests/ -v -m "not slow"
```

### Test Structure

```
tests/
├── unit/                   # Unit tests
│   ├── test_agent_config.py
│   └── test_chat_schemas.py
├── integration/            # Integration tests
│   ├── test_mcp_agent.py
│   ├── test_intent_recognition.py
│   └── test_chatbot_integration.py
└── e2e/                    # End-to-end tests
    ├── test_task_creation.py
    └── test_multi_action_crud.py
```

**Note**: Tests requiring MCP server connection are currently skipped. See `backend/KNOWN_ISSUES.md` for details.

---

## Architecture 🏗️

### Phase 3: AI Chatbot Stack

```
┌─────────────────────────────────────────┐
│         Frontend (Next.js)              │
│  - Chat UI with SSE streaming           │
└─────────────────┬───────────────────────┘
                  │ HTTP/SSE
┌─────────────────▼───────────────────────┐
│         FastAPI Backend                 │
│  - Chat Router (POST /api/chat)         │
│  - JWT Authentication                   │
│  - Conversation & Message persistence   │
└─────────────────┬───────────────────────┘
                  │
         ┌────────┴────────┐
         │                 │
┌────────▼────────┐  ┌────▼────────────────┐
│  OpenAI Agent   │  │  PostgreSQL (Neon)  │
│  + Gemini 2.0   │  │  - conversations    │
│  via LiteLLM    │  │  - messages         │
└────────┬────────┘  │  - tasks            │
         │           └─────────────────────┘
         │
┌────────▼────────┐
│   MCP Server    │
│  5 Task Tools   │
│  - add_task     │
│  - list_tasks   │
│  - complete     │
│  - update       │
│  - delete       │
└─────────────────┘
```

### Key Design Principles
1. **Stateless Architecture** - No server-side session storage
2. **Database-backed State** - All conversation state in PostgreSQL
3. **User Isolation** - JWT + user_id validation on all operations
4. **Horizontal Scalability** - Stateless design allows multiple instances
5. **Event Streaming** - SSE for real-time agent responses

---

## Troubleshooting 🔍

### Common Issues

**1. MCP Server Connection Error**
```
Error: Session terminated
```
**Fix**: Update `MCP_SERVER_URL` in `.env`:
```env
MCP_SERVER_URL=http://localhost:8000/api/mcp/mcp
```

**2. Missing GOOGLE_API_KEY**
```
Error: GOOGLE_API_KEY environment variable is required
```
**Fix**: Add your Gemini API key to `.env`:
```env
GOOGLE_API_KEY=your-actual-api-key-here
```

**3. Database Connection Failed**
```
Error: Connection refused
```
**Fix**: Verify `DATABASE_URL` in `.env` and database is running

**4. JWT Authentication Failed**
```
401 Unauthorized: Invalid token
```
**Fix**: Ensure `BETTER_AUTH_SECRET` matches between frontend and backend

For more issues, see: `backend/KNOWN_ISSUES.md`

---

## Development 💻

### Code Structure

```
backend/
├── main.py                 # FastAPI app + MCP mount
├── db.py                   # Database connection
├── models.py               # Phase 2 SQLModel models
├── routes/                 # API routers
│   ├── auth.py
│   ├── tasks.py
│   └── chat.py            # Phase 3 chat endpoint
├── schemas/               # Pydantic request/response models
│   └── chat.py
├── middleware/            # JWT verification
│   └── jwt.py
├── src/                   # Phase 3 modules
│   ├── models/           # Conversation & Message models
│   ├── mcp/              # MCP server + tools
│   └── agent/            # OpenAI Agent + config
└── tests/                # Test suite
```

### Adding New MCP Tools

1. Define tool in `src/mcp/server.py`:
```python
@mcp.tool()
def my_new_tool(user_id: str, param: str, ctx: Context = None) -> dict:
    """Tool description for agent"""
    # Implementation
    return {"result": "success"}
```

2. Tool is automatically registered and accessible to agent

### Code Quality

```bash
# Format code
black backend/
ruff check backend/ --fix

# Type checking
mypy backend/

# Run linters
ruff check backend/
```

---

## Environment Variables Reference 📋

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | ✅ Yes | - | PostgreSQL connection string |
| `BETTER_AUTH_SECRET` | ✅ Yes | - | JWT secret key (256-bit) |
| `JWT_ALGORITHM` | No | HS256 | JWT signing algorithm |
| `GOOGLE_API_KEY` | ✅ Yes (Phase 3) | - | Gemini API key |
| `MCP_SERVER_URL` | No | localhost:8000/api/mcp/mcp | MCP server endpoint |
| `AGENT_MODEL` | No | gemini/gemini-2.0-flash-exp | LiteLLM model name |
| `AGENT_TEMPERATURE` | No | 0.7 | Agent temperature (0-1) |
| `AGENT_MAX_TOKENS` | No | 1000 | Max tokens per response |
| `MAX_CONVERSATION_HISTORY` | No | 50 | Max messages to load |
| `ALLOW_ALL_ORIGINS` | No | true | Allow all CORS origins |
| `ALLOWED_ORIGINS` | No | - | Specific CORS origins |

---

## Deployment 🚀

### Hugging Face Spaces

1. Create new Space (Docker SDK)
2. Upload all backend files
3. Add secrets in Space settings (all environment variables)
4. Space will auto-deploy

### Alternative: Railway / Render / Fly.io

Similar process - add environment variables in platform settings.

---

## License 📄

MIT License - see LICENSE file

---

## Support 💬

For issues and questions:
- Check `backend/KNOWN_ISSUES.md`
- Review API docs at `/docs`
- Check logs for detailed error messages

---

**Version**: 1.0.0 (Phase 3 - AI Chatbot Complete)
**Last Updated**: 2025-12-18
