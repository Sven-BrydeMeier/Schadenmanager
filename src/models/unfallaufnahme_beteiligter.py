"""
Model für Beteiligte aus der mobilen Unfallaufnahme
Speichert Personen, die per OCR/manuell erfasst wurden
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean, Float
from sqlalchemy.orm import relationship

from src.models.base import Base


class UnfallaufnahmeBeteiligter(Base):
    """
    Beteiligter aus der mobilen Unfallaufnahme.
    Speichert Personendaten, die durch OCR oder manuelle Eingabe erfasst wurden.
    """
    __tablename__ = "unfallaufnahme_beteiligter"

    id = Column(Integer, primary_key=True)

    # Zuordnung zum Projekt
    unfallprojekt_id = Column(Integer, ForeignKey("unfallprojekt.id"), nullable=False)

    # Rolle des Beteiligten
    rolle = Column(String(50))  # UNFALLGEGNER, ZEUGE, BEIFAHRER, HALTER, etc.

    # Personendaten
    vorname = Column(String(100))
    nachname = Column(String(100))
    geburtsdatum = Column(String(20))  # Format: YYYY-MM-DD oder DD.MM.YYYY

    # Kontaktdaten
    telefon = Column(String(50))
    email = Column(String(200))

    # Adresse - separate Felder für bessere Verarbeitung
    strasse = Column(String(200))
    hausnummer = Column(String(20))
    plz = Column(String(10))
    ort = Column(String(100))
    land = Column(String(50), default="Deutschland")

    # Komplett-Adresse für Anzeige
    adresse_komplett = Column(Text)

    # Fahrzeug/Versicherung
    kennzeichen = Column(String(20))
    versicherung = Column(String(200))
    versicherungsnummer = Column(String(100))

    # OCR-Metadaten
    ocr_erfasst = Column(Boolean, default=False)  # Wurde per OCR erfasst?
    ocr_konfidenz = Column(Float)  # Konfidenz der OCR-Erkennung (0.0-1.0)
    ocr_rohtext = Column(Text)  # Original OCR-Text für Debugging

    # Ausweisdaten (falls per OCR erfasst)
    ausweisnummer = Column(String(50))
    ausweis_foto_pfad = Column(String(500))

    # Timestamps
    erstellt_am = Column(DateTime, default=datetime.utcnow)
    aktualisiert_am = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    projekt = relationship("UnfallProjekt", backref="unfallaufnahme_beteiligte")

    def __repr__(self):
        return f"<UnfallaufnahmeBeteiligter(id={self.id}, rolle='{self.rolle}', name='{self.vorname} {self.nachname}')>"

    @property
    def voller_name(self) -> str:
        """Gibt den vollen Namen zurück"""
        teile = []
        if self.vorname:
            teile.append(self.vorname)
        if self.nachname:
            teile.append(self.nachname)
        return " ".join(teile) if teile else "Unbekannt"

    @property
    def adresse_formatiert(self) -> str:
        """Gibt die formatierte Adresse zurück"""
        if self.adresse_komplett:
            return self.adresse_komplett

        teile = []
        if self.strasse:
            strasse_teil = self.strasse
            if self.hausnummer:
                strasse_teil += f" {self.hausnummer}"
            teile.append(strasse_teil)

        if self.plz or self.ort:
            ort_teil = ""
            if self.plz:
                ort_teil = self.plz
            if self.ort:
                ort_teil += f" {self.ort}" if ort_teil else self.ort
            teile.append(ort_teil)

        return ", ".join(teile) if teile else ""

    def rolle_anzeige(self) -> str:
        """Gibt eine lesbare Rollenbezeichnung zurück"""
        rollen_namen = {
            "UNFALLGEGNER": "Unfallgegner",
            "ZEUGE": "Zeuge",
            "BEIFAHRER": "Beifahrer",
            "HALTER": "Fahrzeughalter",
            "FAHRER": "Fahrer",
            "MITFAHRER": "Mitfahrer",
            "GESCHAEDIGTER": "Geschädigter",
            "SONSTIG": "Sonstiger"
        }
        return rollen_namen.get(self.rolle, self.rolle or "Unbekannt")
