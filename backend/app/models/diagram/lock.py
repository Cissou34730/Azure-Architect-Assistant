"""Lock model for pessimistic locking of diagram updates."""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from .base import Base


class Lock(Base):
    """
    Pessimistic lock for diagram set updates.
    
    Allows only one architect to edit a diagram at a time while others have read-only access.
    Locks automatically expire after 10 minutes.
    """
    
    __tablename__ = "locks"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    diagram_set_id = Column(String(36), ForeignKey("diagram_sets.id", ondelete="CASCADE"), unique=True, nullable=False)
    lock_held_by = Column(String(255), nullable=False)
    lock_acquired_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    lock_expires_at = Column(DateTime, nullable=False)
    
    # Relationships
    diagram_set = relationship("DiagramSet", back_populates="lock")
    
    def __init__(self, *args, **kwargs):
        """Initialize lock with 10-minute expiration."""
        super().__init__(*args, **kwargs)
        if not self.lock_expires_at:
            self.lock_expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    
    def is_expired(self) -> bool:
        """Check if lock has expired."""
        return datetime.now(timezone.utc) > self.lock_expires_at
    
    def __repr__(self) -> str:
        return f"<Lock(id={self.id}, held_by={self.lock_held_by}, expires={self.lock_expires_at})>"
