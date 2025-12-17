"""DiagramSet model for storing diagram collections."""

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.orm import relationship

from .base import Base


class DiagramSet(Base):
    """
    DiagramSet represents all diagrams generated from a single architecture description.
    
    Contains multiple diagram types (functional Mermaid, C4 C1/C2, PlantUML),
    version history, ADR references, and creation/update timestamps.
    """
    
    __tablename__ = "diagram_sets"
    
    id = Column(String(36), primary_key=True)
    adr_id = Column(String(255), nullable=True, index=True)
    input_description = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    diagrams = relationship("Diagram", back_populates="diagram_set", cascade="all, delete-orphan")
    ambiguity_reports = relationship("AmbiguityReport", back_populates="diagram_set", cascade="all, delete-orphan")
    lock = relationship("Lock", back_populates="diagram_set", uselist=False, cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<DiagramSet(id={self.id}, adr_id={self.adr_id})>"
