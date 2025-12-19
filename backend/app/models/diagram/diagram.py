"""Diagram model for individual diagram instances."""

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import Column, String, Text, DateTime, ForeignKey, LargeBinary
from sqlalchemy.orm import relationship

from .base import Base


class DiagramType(str, Enum):
    """Diagram type enumeration."""
    
    MERMAID_FUNCTIONAL = "mermaid_functional"
    C4_CONTEXT = "c4_context"
    C4_CONTAINER = "c4_container"
    PLANTUML_AZURE = "plantuml_azure"


class Diagram(Base):
    """
    Individual diagram instance with type, source code, version, and rendered images.
    
    For PlantUML diagrams, includes rendered SVG/PNG images.
    Mermaid diagrams are rendered client-side by React component.
    """
    
    __tablename__ = "diagrams"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    diagram_set_id = Column(String(36), ForeignKey("diagram_sets.id", ondelete="CASCADE"), nullable=False, index=True)
    diagram_type = Column(String(50), nullable=False)
    source_code = Column(Text, nullable=False)
    rendered_svg = Column(LargeBinary, nullable=True)  # PlantUML only
    rendered_png = Column(LargeBinary, nullable=True)  # PlantUML only
    version = Column(String(20), nullable=False, default="v1.0.0")
    previous_version_id = Column(String(36), ForeignKey("diagrams.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    diagram_set = relationship("DiagramSet", back_populates="diagrams")
    previous_version = relationship("Diagram", remote_side=[id], foreign_keys=[previous_version_id])
    
    def __repr__(self) -> str:
        return f"<Diagram(id={self.id}, type={self.diagram_type}, version={self.version})>"
