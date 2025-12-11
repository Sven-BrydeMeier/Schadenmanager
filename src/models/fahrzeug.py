from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Date, Text

from src.models.base import Base


class Fahrzeug(Base):
    """Fahrzeugdaten (aus OCR des Fahrzeugscheins oder manueller Eingabe)"""
    __tablename__ = "fahrzeug"

    id = Column(Integer, primary_key=True)

    # Halter
    halter_name = Column(String(255))
    halter_vorname = Column(String(100))
    halter_strasse = Column(String(255))
    halter_hausnummer = Column(String(20))
    halter_plz = Column(String(20))
    halter_ort = Column(String(100))

    # Fahrzeugdaten
    fin = Column(String(50))  # Fahrzeug-Identifizierungsnummer
    kennzeichen = Column(String(20))
    hersteller = Column(String(100))
    modell = Column(String(100))
    typ = Column(String(100))

    # Technische Daten (aus Fahrzeugschein)
    hsn = Column(String(10))  # Herstellerschlüsselnummer
    tsn = Column(String(10))  # Typschlüsselnummer
    erstzulassung = Column(Date)
    hubraum = Column(Integer)  # in ccm
    leistung_kw = Column(Integer)
    kraftstoff = Column(String(50))
    farbe = Column(String(50))

    # Versicherungsdaten
    versicherung_name = Column(String(255))
    versicherung_nummer = Column(String(100))

    # Metadaten
    quelle = Column(String(50), default="MANUELL")  # "OCR" oder "MANUELL"
    ocr_rohdaten = Column(Text)  # JSON der OCR-Ergebnisse
    erstellt_am = Column(DateTime, default=datetime.utcnow)
    aktualisiert_am = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Fahrzeug(id={self.id}, kennzeichen='{self.kennzeichen}', modell='{self.hersteller} {self.modell}')>"

    @property
    def halter_vollstaendig(self) -> str:
        """Gibt den Halter als vollständigen String zurück"""
        name = f"{self.halter_vorname or ''} {self.halter_name or ''}".strip()
        adresse_teile = []
        if self.halter_strasse:
            adresse_teile.append(f"{self.halter_strasse} {self.halter_hausnummer or ''}".strip())
        if self.halter_plz or self.halter_ort:
            adresse_teile.append(f"{self.halter_plz or ''} {self.halter_ort or ''}".strip())
        adresse = ", ".join(adresse_teile)
        return f"{name}, {adresse}" if adresse else name

    @property
    def fahrzeug_bezeichnung(self) -> str:
        """Gibt eine kurze Fahrzeugbezeichnung zurück"""
        teile = [self.hersteller, self.modell, self.typ]
        return " ".join(t for t in teile if t) or "Unbekanntes Fahrzeug"
