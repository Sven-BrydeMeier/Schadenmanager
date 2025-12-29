from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Text
from sqlalchemy.orm import relationship

from src.models.base import Base
from src.models.enums import MeilensteinStatus


class TimelineMeilenstein(Base):
    """Timeline-Meilensteine für ein Unfallprojekt"""
    __tablename__ = "timeline_meilenstein"

    id = Column(Integer, primary_key=True)
    unfallprojekt_id = Column(Integer, ForeignKey("unfallprojekt.id"), nullable=False)

    # Meilenstein-Definition
    code = Column(String(100), nullable=False)  # z.B. "BASISDATEN", "GUTACHTEN_EINGEGANGEN"
    beschreibung = Column(String(255))
    reihenfolge = Column(Integer, default=0)  # Für Sortierung in der Timeline

    # Status (Ampel)
    status = Column(Enum(MeilensteinStatus), default=MeilensteinStatus.ROT)

    # Zuständigkeit und Fristen
    partei_zustaendig = Column(String(50))  # z.B. "WERKSTATT", "ANWALT"
    faelligkeitsdatum = Column(DateTime)

    # Erledigungsdaten
    erledigt_am = Column(DateTime)
    erledigt_von_user_id = Column(Integer, ForeignKey("user.id"))

    # Zusätzliche Informationen
    notizen = Column(Text)
    automatisch_berechnet = Column(String(10), default="JA")  # "JA" oder "NEIN"

    # Timestamps
    erstellt_am = Column(DateTime, default=datetime.utcnow)
    aktualisiert_am = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    projekt = relationship("UnfallProjekt", back_populates="timeline_meilensteine")
    erledigt_von = relationship("User")

    def __repr__(self):
        return f"<TimelineMeilenstein(id={self.id}, code='{self.code}', status={self.status.value})>"

    @property
    def status_farbe(self) -> str:
        """Gibt die CSS-Farbe für den Status zurück"""
        farben = {
            # Ampel-System
            MeilensteinStatus.ROT: "#dc3545",
            MeilensteinStatus.ORANGE: "#fd7e14",
            MeilensteinStatus.GRUEN: "#28a745",
            # Workflow-System
            MeilensteinStatus.ERLEDIGT: "#28a745",
            MeilensteinStatus.IN_BEARBEITUNG: "#fd7e14",
            MeilensteinStatus.AUSSTEHEND: "#6c757d"
        }
        return farben.get(self.status, "#6c757d")

    @property
    def status_icon(self) -> str:
        """Gibt ein Icon für den Status zurück"""
        icons = {
            # Ampel-System
            MeilensteinStatus.ROT: "🔴",
            MeilensteinStatus.ORANGE: "🟠",
            MeilensteinStatus.GRUEN: "🟢",
            # Workflow-System
            MeilensteinStatus.ERLEDIGT: "✅",
            MeilensteinStatus.IN_BEARBEITUNG: "🔄",
            MeilensteinStatus.AUSSTEHEND: "⏳"
        }
        return icons.get(self.status, "⚪")

    @property
    def ist_erledigt(self) -> bool:
        """Prüft ob der Meilenstein erledigt ist"""
        return self.status in (MeilensteinStatus.GRUEN, MeilensteinStatus.ERLEDIGT)
