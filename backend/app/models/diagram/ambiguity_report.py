"""AmbiguityReport model for tracking unclear elements in descriptions."""

from datetime import datetime

from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from .base import Base


class AmbiguityReport(Base):
    """
    List of unclear elements found in InputDescription with specific text references.
    
    Contains ambiguous text snippets, suggested clarifications, and resolution status.
    """
    
    __tablename__ = "ambiguity_reports"
    
    id = Column(String(36), primary_key=True)
    diagram_set_id = Column(String(36), ForeignKey("diagram_sets.id", ondelete="CASCADE"), nullable=False, index=True)
    ambiguous_text = Column(Text, nullable=False)
    suggested_clarification = Column(Text, nullable=False)
    resolved = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    diagram_set = relationship("DiagramSet", back_populates="ambiguity_reports")
    
    def __repr__(self) -> str:
        return f"<AmbiguityReport(id={self.id}, resolved={self.resolved})>"
