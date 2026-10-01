# ⚡ CODE_STORM — Full-Stack GenAI Hackathon Platform

A production-grade, enterprise-resilient GenAI platform engineered for 36-hour hackathons and production deployments. Built with a decoupled **React (Vite + Vanilla CSS)** frontend, an async **FastAPI** backend, **Aiven PostgreSQL** for transactional persistence, **Pinecone** for high-dimensional vector search, and an automated **Groq + Gemini multi-provider resilience cascade**.

---

## 🏛️ System Architecture

```text
                    ┌──────────────────────────┐
                    │      USER / BROWSER      │
                    └────────────┬─────────────┘
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │       React + Vite       │
                    │   Vanilla CSS (Dark Mode)│
                    │    Central API Client    │
                    └────────────┬─────────────┘
                                 │
                            REST / JSON
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │         FastAPI          │
                    │        API Layer         │
                    │ (Request-ID / Rate-Limit)│
                    └────────────┬─────────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              │                  │                  │
              ▼                  ▼                  ▼
       ┌──────────────┐  ┌──────────────┐  ┌────────────────┐
       │    Aiven     │  │   Pinecone   │  │  LLM Service   │
       │  PostgreSQL  │  │  Vector DB   │  │                │
       │              │  │              │  │ Groq (Primary) │
       │ Users        │  │ Embeddings   │  │      ↓         │
       │ Messages     │  │ Chunks       │  │ Gemini         │
       │ Conversations│  │ Metadata     │  │  (Fallback)    │
       │ Documents    │  │ Top-K Search │  │                │
       │ Extraction   │  │ Deduplication│  │ JSON Healing   │
       │ Audit Events │  │ Deletion Sync│  │ Bounded Retry  │
       └──────────────┘  └──────────────┘  └────────────────┘
```

---

## 🗄️ Database Separation of Concerns

The architecture strictly delineates persistence responsibilities between relational and vector stores:

| Storage Engine | Responsibility | Stored Entities |
|---|---|---|
| **Aiven PostgreSQL** | Transactional Application State & Metadata | `users`, `conversations`, `messages`, `documents`, `extraction_jobs`, `audit_events` |
| **Pinecone** | High-Dimensional Vector Representations & Search | Normalized chunk embeddings, vector IDs (`doc_{id}_{chunk}`), section tags, and retrieval text |

---

## 📁 Project Directory Structure

```text
CODE_STORM/
├── backend/
│   ├── api/
│   │   ├── main.py              # FastAPI app initialization, middleware, error handlers
│   │   ├── middleware.py        # X-Request-ID propagation & structured access logging
│   │   └── routes/
│   │       ├── health.py        # /health (liveness) & /ready (PostgreSQL + Pinecone check)
│   │       ├── chat.py          # /api/process & /api/chat with conversation persistence
│   │       ├── extraction.py    # /api/extract & /api/extract/image with Pydantic validation
│   │       └── rag.py           # /api/rag/stats, /api/rag/reindex, /api/documents
│   │
│   ├── core/
│   │   ├── llm_client.py        # Unified call_llm interface with fallback
│   │   ├── rag.py               # Pinecone RAG query pipeline & deduplication
│   │   ├── extraction.py        # Pydantic schema validation with 1-attempt correction
│   │   └── safety_scaffold.py   # Tier 0 prompt injection defense & Tier 1 semantic safety
│   │
│   ├── db/
│   │   ├── database.py          # SQLAlchemy 2.0 asyncpg engine & connection pool
│   │   ├── models.py            # Declarative models (Users, Conversations, Documents, etc.)
│   │   └── repositories.py      # Async repository abstractions for clean DB access
│   │
│   ├── integrations/
│   │   ├── embeddings.py        # EmbeddingService (Pinecone, Gemini, deterministic fallback)
│   │   ├── pinecone_client.py   # PineconeService (batch upsert, query, delete sync)
│   │   └── llm_service.py       # LLMService (GroqProvider, GeminiProvider, exponential backoff)
│   │
│   ├── migrations/              # Alembic migration environment
│   │   ├── env.py               # Asyncpg migration runner
│   │   └── versions/
│   │       └── 0001_initial_schema.py # Initial reproducible schema DDL
│   │
│   ├── data/
│   │   └── knowledge/           # Drop domain guidelines (.md / .txt) here
│   ├── tests/                   # Pytest test suite (100+ tests passing)
│   ├── alembic.ini              # Alembic migration configuration
│   ├── config.py                # Centralized settings & environment sanitizer
│   ├── requirements.txt         # Pinned backend dependencies
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── api/                 # Centralized API communication layer
│   │   │   ├── client.js        # Base fetch client (timeouts, errors, headers)
│   │   │   ├── chat.js          # RAG processing & conversational methods
│   │   │   ├── extraction.js    # Structured text & multimodal image extraction
│   │   │   ├── knowledge.js     # Vector index stats, reindex, document upload/delete
│   │   │   └── health.js        # Health & readiness polling
│   │   ├── components/
│   │   │   ├── Navbar.jsx       # Real-time backend status pulse (ONLINE / DEGRADED / OFFLINE)
│   │   │   ├── ChatTab.jsx      # AI Copilot with grounded citations & provider pills
│   │   │   ├── ExtractTab.jsx   # Drag & drop multimodal extractor with Pydantic JSON viewer
│   │   │   └── KnowledgeTab.jsx # Real-time Pinecone metrics & document management
│   │   ├── App.jsx              # Main platform container & navigation
│   │   ├── App.css              # Custom Vanilla CSS: Glassmorphism, glow effects, tables
│   │   ├── index.css            # Typography & design tokens
│   │   └── main.jsx
│   ├── package.json
│   ├── vite.config.js           # Proxies /api, /health, /ready to FastAPI
│   └── .env.example
│
├── .gitignore
├── README.md
└── SETUP_INSTRUCTIONS.md
```

---

## 🛠️ Technology Stack

- **Frontend**: React 19, Vite, Vanilla CSS (Glassmorphism, Dark Mode, Micro-animations)
- **Backend**: FastAPI, Uvicorn, Python 3.10+
- **Relational Database**: Aiven PostgreSQL with SSL, SQLAlchemy 2.0, Asyncpg, Alembic
- **Vector Database**: Pinecone Serverless (Cosine Metric, 1024-dimension)
- **Primary LLM**: Groq Cloud API (`llama-3.3-70b-versatile`, sub-second inference)
- **Fallback LLM**: Google Gemini API (`gemini-2.5-flash` / `gemini-1.5-flash`)
- **Data Validation**: Pydantic v2 with 1-attempt feedback correction

---

## ⚡ Quick Start

### 1. Backend Setup

```bash
cd backend

# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate       # On Windows
# source .venv/bin/activate  # On macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env with your Aiven PostgreSQL, Pinecone, Groq, and Gemini credentials

# Run database migrations
alembic upgrade head

# Start FastAPI development server
uvicorn api.main:app --reload --port 8000
```

Verify backend health:
- `http://localhost:8000/health` (Liveness)
- `http://localhost:8000/ready` (Readiness: PostgreSQL + Pinecone)
- `http://localhost:8000/docs` (Interactive OpenAPI Swagger UI)

---

### 2. Frontend Setup

```bash
cd frontend

# Install Node modules
npm install

# Start Vite development server
npm run dev
```

Open **`http://localhost:5173`** in your browser.

---

## 🔑 Environment Variables Reference

Create `backend/.env` from `backend/.env.example`:

```env
# ------------------------------------------------------------------------------
# Database (Aiven PostgreSQL with SSL)
# ------------------------------------------------------------------------------
DATABASE_URL=postgresql+asyncpg://avnadmin:PASSWORD@pg-host.aivencloud.com:PORT/defaultdb?ssl=require
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_TIMEOUT=30.0
DB_POOL_RECYCLE=1800
DB_SSL_MODE=require

# ------------------------------------------------------------------------------
# Vector Database (Pinecone)
# ------------------------------------------------------------------------------
PINECONE_API_KEY=pcsk_your_pinecone_api_key_here
PINECONE_INDEX_NAME=code-storm
PINECONE_NAMESPACE=default
PINECONE_HOST=
PINECONE_DIMENSION=1024
PINECONE_METRIC=cosine
EMBEDDING_PROVIDER=pinecone
EMBEDDING_MODEL_NAME=multilingual-e5-large

# ------------------------------------------------------------------------------
# LLM Providers (Groq Primary -> Gemini Fallback)
# ------------------------------------------------------------------------------
PRIMARY_LLM_PROVIDER=groq
PRIMARY_LLM_MODEL=llama-3.3-70b-versatile
FALLBACK_LLM_PROVIDER=gemini
FALLBACK_LLM_MODEL=gemini-2.5-flash

GROQ_API_KEY=gsk_your_groq_api_key_here
GEMINI_API_KEY=AIzaSy_your_gemini_api_key_here

LLM_TIMEOUT_SECONDS=30.0
LLM_MAX_RETRIES=1

# ------------------------------------------------------------------------------
# Security & Uploads
# ------------------------------------------------------------------------------
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
MAX_UPLOAD_SIZE_MB=10
```

---

## 🔌 API Endpoints Summary

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Liveness check (API process up) |
| `GET` | `/ready` | Readiness check (Aiven DB, Pinecone, LLM status) |
| `POST` | `/api/process` | Tier 0 scan + Pinecone retrieval + Groq/Gemini synthesis with sources |
| `POST` | `/api/chat` | Conversational RAG with conversation & message persistence |
| `GET` | `/api/conversations` | List conversation sessions |
| `GET` | `/api/conversations/{id}/messages` | Get past messages for a conversation |
| `POST` | `/api/extract` | Structured extraction from raw text with Pydantic retry |
| `POST` | `/api/extract/image` | Multimodal extraction from uploaded image with file validation |
| `GET` | `/api/rag/stats` | Pinecone vector metrics and PostgreSQL document count |
| `POST` | `/api/rag/query` | Direct semantic search returning top-K chunks |
| `POST` | `/api/rag/reindex` | Trigger idempotent reindexing of `data/knowledge/` documents |
| `GET` | `/api/documents` | List indexed documents from PostgreSQL |
| `POST` | `/api/documents` | Upload and index new document file |
| `DELETE` | `/api/documents/{id}` | Delete document from PostgreSQL and purge Pinecone vectors |

---

## 🛡️ Security & Defense Architecture

1. **Two-Tier Safety Scaffold**:
   - **Tier 0 Deterministic Filter**: Scans input in <5ms using compiled regex patterns for prompt injection (`ignore previous instructions`, `jailbreak mode`, `bypass safety`) and system overrides.
   - **Tier 1 Semantic Safety**: Evaluates edge-case ambiguity using low-temperature LLM classification.
2. **Untrusted Context Isolation**:
   - Retrieved document passages are explicitly isolated inside `--- UNTRUSTED REFERENCE PASSAGES ---` tags. The system prompt instructs the LLM never to treat retrieved content as commands.
3. **File Upload Security**:
   - Validates file size against `MAX_UPLOAD_SIZE_MB`.
   - Prevents path traversal in filenames (`..`, `/`, `\`).
   - Validates MIME types (`image/png`, `image/jpeg`, `image/webp`).
   - Verifies binary magic headers for PNG (`\x89PNG`) and JPEG (`\xff\xd8`).
4. **Standard Error Sanitation**:
   - All errors return structured JSON with unique `X-Request-ID` and code. Raw Python tracebacks and secrets are never exposed to clients.

---

## 🧪 Testing & Verification

Run the entire backend test suite:

```bash
cd backend
python -m pytest tests/
```

Run workspace integration tests:

```bash
python -m pytest tests/test_workspace_integration.py -v
```

Build the frontend for production:

```bash
cd frontend
npm run build
```

---

## 🎯 4-Step Hackathon Pivot (When Problem Statement Drops)

When the problem statement is announced:

1. **Knowledge Ingestion**: Drop problem guidelines (`.md`/`.txt`) into `backend/data/knowledge/` and click *"Re-Index"* in the web UI.
2. **Safety Tuning**: Add 3–5 domain-specific keywords into `DEFAULT_RED_FLAG_PATTERNS` in `backend/core/safety_scaffold.py`.
3. **Extraction Schema**: Update `DefaultExtractSchema` in `backend/api/routes/extraction.py` to match the target problem fields.
4. **Copilot Persona**: Tune the system prompt in `backend/api/routes/chat.py` to match your solution's domain persona.
