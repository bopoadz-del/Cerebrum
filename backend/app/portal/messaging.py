"""
Messaging Module
Handles project-specific messaging between team members.
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from enum import Enum
from pydantic import BaseModel, Field
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Boolean, JSON, Integer
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import relationship

from app.database import Base


class MessageType(str, Enum):
    DIRECT = "direct"
    GROUP = "group"
    PROJECT = "project"
    SYSTEM = "system"


class ConversationType(str, Enum):
    DIRECT = "direct"
    GROUP = "group"
    PROJECT = "project"


class Conversation(Base):
    """Message conversation/thread."""
    __tablename__ = 'conversations'
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(PG_UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False)
    project_id = Column(PG_UUID(as_uuid=True), ForeignKey('projects.id'))
    
    conversation_type = Column(String(50), nullable=False)
    title = Column(String(500))
    
    created_by = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    last_message_at = Column(DateTime)
    last_message_preview = Column(String(500))
    
    is_archived = Column(Boolean, default=False)
    
    participants = Column(JSONB, default=list)  # List of user IDs
    
    # Relationships
    messages = relationship("Message", back_populates="conversation")


class Message(Base):
    """Individual message."""
    __tablename__ = 'messages'
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(PG_UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False)
    conversation_id = Column(PG_UUID(as_uuid=True), ForeignKey('conversations.id'), nullable=False)
    
    sender_id = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'))
    sender_company_id = Column(PG_UUID(as_uuid=True), ForeignKey('subcontractor_companies.id'))
    
    content = Column(Text, nullable=False)
    message_type = Column(String(50), default="text")  # text, file, system
    
    attachments = Column(JSONB, default=list)  # List of attached files
    
    reply_to_id = Column(PG_UUID(as_uuid=True), ForeignKey('messages.id'))
    
    edited_at = Column(DateTime)
    is_deleted = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    read_receipts = relationship("MessageReadReceipt", back_populates="message")


class MessageReadReceipt(Base):
    """Message read receipt."""
    __tablename__ = 'message_read_receipts'
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(PG_UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False)
    message_id = Column(PG_UUID(as_uuid=True), ForeignKey('messages.id'), nullable=False)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    
    read_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    message = relationship("Message", back_populates="read_receipts")


class ProjectAnnouncement(Base):
    """Project-wide announcement."""
    __tablename__ = 'project_announcements'
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(PG_UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False)
    project_id = Column(PG_UUID(as_uuid=True), ForeignKey('projects.id'), nullable=False)
    
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    
    priority = Column(String(50), default="normal")  # low, normal, high, urgent
    
    posted_by = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'))
    posted_at = Column(DateTime, default=datetime.utcnow)
    
    expires_at = Column(DateTime)
    
    attachments = Column(JSONB, default=list)
    
    read_count = Column(Integer, default=0)


# Pydantic Models

class MessageAttachment(BaseModel):
    file_url: str
    file_name: str
    file_size: int
    file_type: str


class ConversationCreateRequest(BaseModel):
    project_id: Optional[str] = None
    conversation_type: ConversationType
    title: Optional[str] = None
    participant_ids: List[str]


class SendMessageRequest(BaseModel):
    conversation_id: str
    content: str
    message_type: str = "text"
    attachments: List[MessageAttachment] = []
    reply_to_id: Optional[str] = None


class CreateAnnouncementRequest(BaseModel):
    project_id: str
    title: str
    content: str
    priority: str = "normal"
    expires_at: Optional[datetime] = None
    attachments: List[MessageAttachment] = []


class ConversationResponse(BaseModel):
    id: str
    project_id: Optional[str]
    conversation_type: str
    title: Optional[str]
    created_by: Optional[str]
    created_by_name: Optional[str]
    participant_count: int
    last_message_at: Optional[datetime]
    last_message_preview: Optional[str]
    unread_count: int = 0
    
    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    sender_id: Optional[str]
    sender_name: Optional[str]
    sender_company_name: Optional[str]
    content: str
    message_type: str
    attachments: List[Dict[str, Any]]
    reply_to_id: Optional[str]
    reply_to_preview: Optional[str]
    edited_at: Optional[datetime]
    is_deleted: bool
    created_at: datetime
    read_by: List[str]
    
    class Config:
        from_attributes = True


class AnnouncementResponse(BaseModel):
    id: str
    project_id: str
    title: str
    content: str
    priority: str
    posted_by: Optional[str]
    posted_by_name: Optional[str]
    posted_at: datetime
    expires_at: Optional[datetime]
    read_count: int
    
    class Config:
        from_attributes = True


class MessagingService:
    """Service for project messaging."""
    
    def __init__(self, db_session):
        self.db = db_session
    
    def create_conversation(
        self,
        tenant_id: str,
        user_id: str,
        request: ConversationCreateRequest
    ) -> Conversation:
        """Create a new conversation."""
        conversation = Conversation(
            tenant_id=tenant_id,
            project_id=request.project_id,
            conversation_type=request.conversation_type,
            title=request.title,
            created_by=user_id,
            participants=list(set(request.participant_ids + [user_id]))  # Include creator
        )
        
        self.db.add(conversation)
        self.db.commit()
        return conversation
    
    def send_message(
        self,
        tenant_id: str,
        user_id: str,
        company_id: Optional[str],
        request: SendMessageRequest
    ) -> Message:
        """Send a message."""
        conversation = self.db.query(Conversation).filter(
            Conversation.tenant_id == tenant_id,
            Conversation.id == request.conversation_id
        ).first()
        
        if not conversation:
            raise ValueError("Conversation not found")
        
        # Check if user is participant
        if user_id not in conversation.participants:
            raise ValueError("User is not a participant in this conversation")
        
        message = Message(
            tenant_id=tenant_id,
            conversation_id=request.conversation_id,
            sender_id=user_id,
            sender_company_id=company_id,
            content=request.content,
            message_type=request.message_type,
            attachments=[att.dict() for att in request.attachments],
            reply_to_id=request.reply_to_id
        )
        
        self.db.add(message)
        
        # Update conversation
        conversation.last_message_at = datetime.utcnow()
        conversation.last_message_preview = request.content[:200] if len(request.content) > 200 else request.content
        
        self.db.commit()
        return message
    
    def mark_message_read(
        self,
        tenant_id: str,
        message_id: str,
        user_id: str
    ) -> MessageReadReceipt:
        """Mark a message as read."""
        # Check if already read
        existing = self.db.query(MessageReadReceipt).filter(
            MessageReadReceipt.tenant_id == tenant_id,
            MessageReadReceipt.message_id == message_id,
            MessageReadReceipt.user_id == user_id
        ).first()
        
        if existing:
            return existing
        
        receipt = MessageReadReceipt(
            tenant_id=tenant_id,
            message_id=message_id,
            user_id=user_id
        )
        
        self.db.add(receipt)
        self.db.commit()
        return receipt
    
    def create_announcement(
        self,
        tenant_id: str,
        user_id: str,
        request: CreateAnnouncementRequest
    ) -> ProjectAnnouncement:
        """Create a project announcement."""
        announcement = ProjectAnnouncement(
            tenant_id=tenant_id,
            project_id=request.project_id,
            title=request.title,
            content=request.content,
            priority=request.priority,
            posted_by=user_id,
            expires_at=request.expires_at,
            attachments=[att.dict() for att in request.attachments]
        )
        
        self.db.add(announcement)
        self.db.commit()
        return announcement
    
    def get_conversations(
        self,
        tenant_id: str,
        user_id: str,
        project_id: Optional[str] = None
    ) -> List[Conversation]:
        """Get conversations for a user."""
        query = self.db.query(Conversation).filter(
            Conversation.tenant_id == tenant_id,
            Conversation.participants.contains([user_id]),
            Conversation.is_archived == False
        )
        
        if project_id:
            query = query.filter(Conversation.project_id == project_id)
        
        return query.order_by(Conversation.last_message_at.desc()).all()
    
    def get_messages(
        self,
        tenant_id: str,
        conversation_id: str,
        user_id: str,
        limit: int = 50,
        before_id: Optional[str] = None
    ) -> List[Message]:
        """Get messages in a conversation."""
        conversation = self.db.query(Conversation).filter(
            Conversation.tenant_id == tenant_id,
            Conversation.id == conversation_id
        ).first()
        
        if not conversation:
            raise ValueError("Conversation not found")
        
        if user_id not in conversation.participants:
            raise ValueError("User is not a participant in this conversation")
        
        query = self.db.query(Message).filter(
            Message.tenant_id == tenant_id,
            Message.conversation_id == conversation_id,
            Message.is_deleted == False
        )
        
        if before_id:
            before_message = self.db.query(Message).filter(Message.id == before_id).first()
            if before_message:
                query = query.filter(Message.created_at < before_message.created_at)
        
        return query.order_by(Message.created_at.desc()).limit(limit).all()
    
    def get_unread_count(
        self,
        tenant_id: str,
        user_id: str
    ) -> Dict[str, int]:
        """Get unread message count for user."""
        # Get user's conversations
        conversations = self.db.query(Conversation).filter(
            Conversation.tenant_id == tenant_id,
            Conversation.participants.contains([user_id])
        ).all()
        
        conversation_ids = [c.id for c in conversations]
        
        if not conversation_ids:
            return {"total": 0, "by_conversation": {}}
        
        # Count unread messages
        total_unread = 0
        by_conversation = {}
        
        for conv_id in conversation_ids:
            # Get messages in conversation
            messages = self.db.query(Message).filter(
                Message.tenant_id == tenant_id,
                Message.conversation_id == conv_id,
                Message.sender_id != user_id,
                Message.is_deleted == False
            ).all()
            
            # Count unread
            unread = 0
            for msg in messages:
                read = self.db.query(MessageReadReceipt).filter(
                    MessageReadReceipt.message_id == msg.id,
                    MessageReadReceipt.user_id == user_id
                ).first()
                
                if not read:
                    unread += 1
            
            if unread > 0:
                by_conversation[str(conv_id)] = unread
                total_unread += unread
        
        return {
            "total": total_unread,
            "by_conversation": by_conversation
        }
    
    def get_announcements(
        self,
        tenant_id: str,
        project_id: str,
        include_expired: bool = False
    ) -> List[ProjectAnnouncement]:
        """Get project announcements."""
        query = self.db.query(ProjectAnnouncement).filter(
            ProjectAnnouncement.tenant_id == tenant_id,
            ProjectAnnouncement.project_id == project_id
        )
        
        if not include_expired:
            query = query.filter(
                (ProjectAnnouncement.expires_at == None) | 
                (ProjectAnnouncement.expires_at > datetime.utcnow())
            )
        
        return query.order_by(ProjectAnnouncement.posted_at.desc()).all()
    
    def edit_message(
        self,
        tenant_id: str,
        message_id: str,
        user_id: str,
        new_content: str
    ) -> Message:
        """Edit a message."""
        message = self.db.query(Message).filter(
            Message.tenant_id == tenant_id,
            Message.id == message_id
        ).first()
        
        if not message:
            raise ValueError("Message not found")
        
        if message.sender_id != user_id:
            raise ValueError("Can only edit your own messages")
        
        message.content = new_content
        message.edited_at = datetime.utcnow()
        
        self.db.commit()
        return message
    
    def delete_message(
        self,
        tenant_id: str,
        message_id: str,
        user_id: str
    ) -> Message:
        """Soft delete a message."""
        message = self.db.query(Message).filter(
            Message.tenant_id == tenant_id,
            Message.id == message_id
        ).first()
        
        if not message:
            raise ValueError("Message not found")
        
        if message.sender_id != user_id:
            raise ValueError("Can only delete your own messages")
        
        message.is_deleted = True
        message.content = "[This message has been deleted]"
        
        self.db.commit()
        return message
