from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Enum, Boolean
from sqlalchemy.orm import relationship

from src.models.base import Base
from src.models.enums import KorrespondenzRichtung


class Korrespondenz(Base):
    """Korrespondenz zwischen den Parteien"""
    __tablename__ = "korrespondenz"

    id = Column(Integer, primary_key=True)
    unfallprojekt_id = Column(Integer, ForeignKey("unfallprojekt.id"), nullable=False)

    # Absender/Ersteller
    erstellt_von_user_id = Column(Integer, ForeignKey("user.id"), nullable=False)

    # Korrespondenzdaten
    richtung = Column(Enum(KorrespondenzRichtung), nullable=False)
    betreff = Column(String(255))
    bezug = Column(String(255))  # Aktenzeichen, Bezugsschreiben etc.

    # Texte
    text_entwurf = Column(Text)  # KI-generierter Entwurf
    text_final = Column(Text)   # Finaler, freigegebener Text
    ki_generiert = Column(Boolean, default=False)

    # Status
    status = Column(String(50), default="ENTWURF")  # ENTWURF, FREIGEGEBEN, VERSENDET
    versendet_am = Column(DateTime)
    versendet_via = Column(String(50))  # EMAIL, POST, FAX

    # Antwort-Tracking
    antwort_erwartet = Column(Boolean, default=True)
    antwort_frist = Column(DateTime)
    antwort_erhalten = Column(Boolean, default=False)
    antwort_erhalten_am = Column(DateTime)

    # Dokument-Referenz
    dokument_id = Column(Integer, ForeignKey("dokument.id"))

    # Timestamps
    erstellt_am = Column(DateTime, default=datetime.utcnow)
    aktualisiert_am = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    projekt = relationship("UnfallProjekt", back_populates="korrespondenzen")
    erstellt_von = relationship("User")
    dokument = relationship("Dokument")

    def __repr__(self):
        return f"<Korrespondenz(id={self.id}, richtung={self.richtung.value}, status='{self.status}')>"

    @property
    def richtung_anzeige(self) -> str:
        """Gibt eine lesbare Richtungsbezeichnung zurück"""
        richtung_namen = {
            KorrespondenzRichtung.RA_AN_VERSICHERUNG: "Anwalt → Versicherung",
            KorrespondenzRichtung.VERSICHERUNG_AN_RA: "Versicherung → Anwalt",
            KorrespondenzRichtung.RA_AN_MANDANT: "Anwalt → Mandant",
            KorrespondenzRichtung.MANDANT_AN_RA: "Mandant → Anwalt",
            KorrespondenzRichtung.WERKSTATT_AN_VERSICHERUNG: "Werkstatt → Versicherung",
            KorrespondenzRichtung.SONSTIG: "Sonstige"
        }
        return richtung_namen.get(self.richtung, self.richtung.value)

    @property
    def status_anzeige(self) -> str:
        """Gibt eine lesbare Statusbezeichnung zurück"""
        status_namen = {
            "ENTWURF": "Entwurf",
            "FREIGEGEBEN": "Freigegeben",
            "VERSENDET": "Versendet"
        }
        return status_namen.get(self.status, self.status)

    @property
    def aktueller_text(self) -> str:
        """Gibt den aktuellen Text zurück (final wenn vorhanden, sonst Entwurf)"""
        return self.text_final or self.text_entwurf or ""
