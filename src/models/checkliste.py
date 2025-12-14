"""
Checklisten-Model für Projekt-Checklisten
"""
from datetime import datetime

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from src.models.base import Base


class ChecklistenItem(Base):
    """Einzelnes Checklistenelement für ein Projekt"""
    __tablename__ = "checklisten_item"

    id = Column(Integer, primary_key=True)
    unfallprojekt_id = Column(Integer, ForeignKey("unfallprojekt.id"), nullable=False)

    # Item-Details
    checkliste_typ = Column(String(50))  # z.B. "auffahrunfall", "parkschaden"
    kategorie = Column(String(100))
    titel = Column(String(255), nullable=False)
    beschreibung = Column(Text)
    reihenfolge = Column(Integer, default=0)

    # Status
    erledigt = Column(Boolean, default=False)
    erledigt_am = Column(DateTime)
    erledigt_von_user_id = Column(Integer, ForeignKey("user.id"))
    notiz = Column(Text)

    # Timestamps
    erstellt_am = Column(DateTime, default=datetime.utcnow)

    # Relationships
    projekt = relationship("UnfallProjekt", backref="checklisten_items")
    erledigt_von = relationship("User", foreign_keys=[erledigt_von_user_id])
