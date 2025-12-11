from datetime import datetime
import uuid
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from src.models.base import Base


def generate_projektnummer() -> str:
    """Generiert eine eindeutige Projektnummer"""
    timestamp = datetime.now().strftime("%Y%m%d")
    unique_id = uuid.uuid4().hex[:6].upper()
    return f"UP-{timestamp}-{unique_id}"


class UnfallProjekt(Base):
    """Zentrales Unfallprojekt - verbindet alle Parteien und Daten"""
    __tablename__ = "unfallprojekt"

    id = Column(Integer, primary_key=True)
    projektnummer = Column(String(50), unique=True, nullable=False, default=generate_projektnummer)

    # Unfalldaten
    datum_unfall = Column(DateTime)
    uhrzeit_unfall = Column(String(10))
    ort_unfall = Column(String(255))
    beschreibung_unfall = Column(Text)
    polizei_aktenzeichen = Column(String(100))

    # Schuldfrage
    schuld_eigen_prozent = Column(Integer, default=0)  # 0 = keine Schuld, 100 = volle Schuld
    schuld_begruendung = Column(Text)

    # Anlegende Organisation
    anlegende_organisation_id = Column(Integer, ForeignKey("organisation.id"))
    angelegt_von_user_id = Column(Integer, ForeignKey("user.id"))

    # Fahrzeuge
    kfz_eigen_id = Column(Integer, ForeignKey("fahrzeug.id"))
    kfz_gegner_id = Column(Integer, ForeignKey("fahrzeug.id"))

    # Beteiligte Parteien (User-IDs)
    unfallopfer_user_id = Column(Integer, ForeignKey("user.id"))
    anwalt_user_id = Column(Integer, ForeignKey("user.id"))
    werkstatt_user_id = Column(Integer, ForeignKey("user.id"))
    gutachter_user_id = Column(Integer, ForeignKey("user.id"))
    versicherung_eigen_user_id = Column(Integer, ForeignKey("user.id"))
    versicherung_gegner_user_id = Column(Integer, ForeignKey("user.id"))

    # Ersatzwagen
    ersatzwagenanbieter_id = Column(Integer, ForeignKey("organisation.id"))
    ersatzwagen_von = Column(DateTime)
    ersatzwagen_bis = Column(DateTime)

    # Status
    status = Column(String(50), default="OFFEN")  # OFFEN, IN_BEARBEITUNG, ABGESCHLOSSEN, STORNIERT
    abgeschlossen = Column(Boolean, default=False)
    abgeschlossen_am = Column(DateTime)

    # Einladungslink für Unfallopfer
    einladungs_code = Column(String(100))
    einladung_gueltig_bis = Column(DateTime)

    # Timestamps
    erstellt_am = Column(DateTime, default=datetime.utcnow)
    aktualisiert_am = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    anlegende_organisation = relationship("Organisation", foreign_keys=[anlegende_organisation_id])
    angelegt_von = relationship("User", foreign_keys=[angelegt_von_user_id])

    kfz_eigen = relationship("Fahrzeug", foreign_keys=[kfz_eigen_id])
    kfz_gegner = relationship("Fahrzeug", foreign_keys=[kfz_gegner_id])

    unfallopfer = relationship("User", foreign_keys=[unfallopfer_user_id])
    anwalt = relationship("User", foreign_keys=[anwalt_user_id])
    werkstatt = relationship("User", foreign_keys=[werkstatt_user_id])
    gutachter = relationship("User", foreign_keys=[gutachter_user_id])
    versicherung_eigen = relationship("User", foreign_keys=[versicherung_eigen_user_id])
    versicherung_gegner = relationship("User", foreign_keys=[versicherung_gegner_user_id])

    ersatzwagenanbieter = relationship("Organisation", foreign_keys=[ersatzwagenanbieter_id])

    timeline_meilensteine = relationship("TimelineMeilenstein", back_populates="projekt", cascade="all, delete-orphan")
    dokumente = relationship("Dokument", back_populates="projekt", cascade="all, delete-orphan")
    kostenpositionen = relationship("KostenPosition", back_populates="projekt", cascade="all, delete-orphan")
    gebuehrenberechnungen = relationship("GebuehrenBerechnung", back_populates="projekt", cascade="all, delete-orphan")
    korrespondenzen = relationship("Korrespondenz", back_populates="projekt", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<UnfallProjekt(id={self.id}, projektnummer='{self.projektnummer}')>"

    @property
    def status_anzeige(self) -> str:
        """Gibt einen lesbaren Status zurück"""
        status_namen = {
            "OFFEN": "Offen",
            "IN_BEARBEITUNG": "In Bearbeitung",
            "ABGESCHLOSSEN": "Abgeschlossen",
            "STORNIERT": "Storniert"
        }
        return status_namen.get(self.status, self.status)
