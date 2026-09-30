# CODE_STORM Architecture & Hackathon Guidelines

## System Overview
CODE_STORM is a production-grade full-stack GenAI hackathon platform engineered with React (Vite + Vanilla CSS), FastAPI, Aiven PostgreSQL, Pinecone Vector Database, and an enterprise multi-provider LLM cascade combining Groq and Google Gemini.

## Two-Tier Database Architecture
The platform strictly separates relational application state from vector representations:
1. **Aiven PostgreSQL**: Manages persistent users, conversations, chat messages, document metadata, extraction jobs, and audit events using SQLAlchemy 2.0 asyncpg with robust connection pooling.
2. **Pinecone Vector Database**: Dedicated to semantic retrieval, storing high-dimensional document chunk embeddings with metadata attribution and SHA-256 deduplication.

## Dual-Provider LLM Resilience
The system prioritizes Groq for sub-second, high-throughput inference (Llama 3.3 70B) with automated, bounded failover to Google Gemini (Gemini 2.5 Flash) upon encountering transient rate limits (HTTP 429), server overload (HTTP 503), or network timeouts.

## Security & Multimodal Extraction
1. **Two-Tier Safety Scaffold**: Tier 0 deterministic regex scan (<5ms) protects against prompt injections, system override attempts, and dangerous inputs before expensive operations occur. Tier 1 performs semantic policy classification.
2. **Multimodal Pydantic Extraction**: Strictly extracts typed schema data from text and images with 1-attempt feedback-driven error correction.
