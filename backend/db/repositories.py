import uuid
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func, desc

from db.models import (
    Document,
    Conversation,
    Message,
    ExtractionJob,
    AuditEvent,
    User
)


class DocumentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, doc_id: str) -> Optional[Document]:
        result = await self.session.execute(select(Document).where(Document.id == doc_id))
        return result.scalar_one_or_none()

    async def get_by_hash(self, content_hash: str) -> Optional[Document]:
        result = await self.session.execute(select(Document).where(Document.content_hash == content_hash))
        return result.scalar_one_or_none()

    async def list_all(self, limit: int = 100, offset: int = 0) -> List[Document]:
        stmt = select(Document).order_by(desc(Document.created_at)).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_all(self) -> int:
        stmt = select(func.count(Document.id))
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def create_or_update(
        self,
        name: str,
        content_hash: str,
        chunk_count: int,
        file_size: int,
        mime_type: str = "text/plain",
        status: str = "indexed",
        doc_id: Optional[str] = None
    ) -> Document:
        existing = await self.get_by_hash(content_hash)
        if existing:
            existing.name = name
            existing.chunk_count = chunk_count
            existing.file_size = file_size
            existing.mime_type = mime_type
            existing.status = status
            await self.session.flush()
            return existing

        doc = Document(
            id=doc_id or str(uuid.uuid4()),
            name=name,
            content_hash=content_hash,
            chunk_count=chunk_count,
            file_size=file_size,
            mime_type=mime_type,
            status=status
        )
        self.session.add(doc)
        await self.session.flush()
        return doc

    async def delete_by_id(self, doc_id: str) -> bool:
        doc = await self.get_by_id(doc_id)
        if not doc:
            return False
        await self.session.delete(doc)
        await self.session.flush()
        return True


class ConversationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, title: str = "New Chat", user_id: Optional[str] = None) -> Conversation:
        conv = Conversation(title=title, user_id=user_id)
        self.session.add(conv)
        await self.session.flush()
        return conv

    async def get_by_id(self, conv_id: str) -> Optional[Conversation]:
        result = await self.session.execute(select(Conversation).where(Conversation.id == conv_id))
        return result.scalar_one_or_none()

    async def list_recent(self, user_id: Optional[str] = None, limit: int = 50) -> List[Conversation]:
        stmt = select(Conversation)
        if user_id:
            stmt = stmt.where(Conversation.user_id == user_id)
        stmt = stmt.order_by(desc(Conversation.updated_at)).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        provider: Optional[str] = None,
        sources: Optional[List[Dict[str, Any]]] = None
    ) -> Message:
        msg = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            provider=provider,
            sources=sources or []
        )
        self.session.add(msg)
        await self.session.flush()
        return msg

    async def get_messages(self, conversation_id: str, limit: int = 100) -> List[Message]:
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class ExtractionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_job(
        self,
        input_type: str,
        schema_name: str,
        user_id: Optional[str] = None
    ) -> ExtractionJob:
        job = ExtractionJob(
            input_type=input_type,
            schema_name=schema_name,
            user_id=user_id,
            status="processing"
        )
        self.session.add(job)
        await self.session.flush()
        return job

    async def complete_job(self, job_id: str, extracted_data: Dict[str, Any]) -> Optional[ExtractionJob]:
        result = await self.session.execute(select(ExtractionJob).where(ExtractionJob.id == job_id))
        job = result.scalar_one_or_none()
        if job:
            job.status = "success"
            job.extracted_data = extracted_data
            await self.session.flush()
        return job

    async def fail_job(self, job_id: str, error_message: str) -> Optional[ExtractionJob]:
        result = await self.session.execute(select(ExtractionJob).where(ExtractionJob.id == job_id))
        job = result.scalar_one_or_none()
        if job:
            job.status = "failed"
            job.error = error_message
            await self.session.flush()
        return job


class AuditRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def log_event(
        self,
        request_id: str,
        event_type: str,
        principal_id: Optional[str] = None,
        role: Optional[str] = None,
        decision: Optional[str] = None,
        reason_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> AuditEvent:
        event = AuditEvent(
            request_id=request_id,
            event_type=event_type,
            principal_id=principal_id,
            role=role,
            decision=decision,
            reason_code=reason_code,
            details=details or {}
        )
        self.session.add(event)
        await self.session.flush()
        return event

    async def list_events(self, limit: int = 50) -> List[AuditEvent]:
        stmt = select(AuditEvent).order_by(desc(AuditEvent.created_at)).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
