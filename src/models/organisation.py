from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Enum

from src.models.base import Base
from src.models.enums import OrgTyp


class Organisation(Base):
    """Organisation (Kanzlei, Werkstatt, Versicherung, Gutachterbüro, Ersatzwagenanbieter)"""
    __tablename__ = "organisation"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    typ = Column(Enum(OrgTyp), nullable=False)

    # Adresse
    strasse = Column(String(255))
    hausnummer = Column(String(20))
    plz = Column(String(20))
    ort = Column(String(100))
    land = Column(String(100), default="Deutschland")

    # Geo-Koordinaten für Entfernungsberechnung
    geo_lat = Column(Float)
    geo_lon = Column(Float)

    # Kontakt
    telefon = Column(String(50))
    email = Column(String(255))
    website = Column(String(255))

    # Status
    aktiv = Column(Boolean, default=True)
    erstellt_am = Column(DateTime, default=datetime.utcnow)
    aktualisiert_am = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Organisation(id={self.id}, name='{self.name}', typ={self.typ.value})>"

    @property
    def vollstaendige_adresse(self) -> str:
        """Gibt die vollständige Adresse als String zurück"""
        teile = []
        if self.strasse:
            adresse = self.strasse
            if self.hausnummer:
                adresse += f" {self.hausnummer}"
            teile.append(adresse)
        if self.plz or self.ort:
            teile.append(f"{self.plz or ''} {self.ort or ''}".strip())
        return ", ".join(teile)
