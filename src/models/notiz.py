"""
Notizen-Modell für interne Projekt-Notizen
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from src.models.base import Base


class Notiz(Base):
    """Interne Notiz zu einem Projekt"""
    __tablename__ = "notiz"

    id = Column(Integer, primary_key=True)

    # Zuordnung
    unfallprojekt_id = Column(Integer, ForeignKey("unfallprojekt.id"), nullable=False)
    erstellt_von_user_id = Column(Integer, ForeignKey("user.id"))

    # Inhalt
    titel = Column(String(255))
    inhalt = Column(Text, nullable=False)
    kategorie = Column(String(50))  # z.B. "intern", "telefonat", "email", "wichtig"

    # Markierungen
    wichtig = Column(Boolean, default=False)
    angeheftet = Column(Boolean, default=False)  # Oben in der Liste anzeigen

    # Timestamps
    erstellt_am = Column(DateTime, default=datetime.utcnow)
    aktualisiert_am = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    projekt = relationship("UnfallProjekt", backref="notizen")
    erstellt_von = relationship("User", foreign_keys=[erstellt_von_user_id])

    def __repr__(self):
        return f"<Notiz(id={self.id}, titel='{self.titel}')>"

    @property
    def kategorie_anzeige(self) -> str:
        """Gibt eine lesbare Kategorie zurück"""
        kategorien = {
            "intern": "Interne Notiz",
            "telefonat": "Telefonat",
            "email": "E-Mail",
            "wichtig": "Wichtig",
            "erinnerung": "Erinnerung",
            "mandant": "Mandantengespräch",
        }
        return kategorien.get(self.kategorie, "Notiz")


class Mahnung(Base):
    """Mahnung für ausstehende Zahlungen"""
    __tablename__ = "mahnung"

    id = Column(Integer, primary_key=True)

    # Zuordnung
    unfallprojekt_id = Column(Integer, ForeignKey("unfallprojekt.id"), nullable=False)
    erstellt_von_user_id = Column(Integer, ForeignKey("user.id"))

    # Mahnung-Details
    mahnstufe = Column(Integer, default=1)  # 1, 2, 3, ...
    betrag = Column(String(20))  # Offener Betrag
    empfaenger = Column(String(255))  # An wen geht die Mahnung
    empfaenger_typ = Column(String(50))  # z.B. "versicherung", "werkstatt"

    # Fristen
    ursprungsforderung_datum = Column(DateTime)  # Wann wurde erstmals gefordert
    letzte_mahnung_datum = Column(DateTime)
    naechste_mahnung_datum = Column(DateTime)
    zahlungsfrist = Column(DateTime)

    # Status
    bezahlt = Column(Boolean, default=False)
    bezahlt_am = Column(DateTime)
    bezahlt_betrag = Column(String(20))
    storniert = Column(Boolean, default=False)

    # Dokument-Verknüpfung
    mahnung_dokument_id = Column(Integer, ForeignKey("dokument.id"))

    # Timestamps
    erstellt_am = Column(DateTime, default=datetime.utcnow)
    aktualisiert_am = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    projekt = relationship("UnfallProjekt", backref="mahnungen")
    erstellt_von = relationship("User", foreign_keys=[erstellt_von_user_id])

    def __repr__(self):
        return f"<Mahnung(id={self.id}, stufe={self.mahnstufe}, betrag={self.betrag})>"

    @property
    def mahnstufe_text(self) -> str:
        """Gibt die Mahnstufe als Text zurück"""
        stufen = {
            1: "1. Mahnung (Zahlungserinnerung)",
            2: "2. Mahnung",
            3: "3. Mahnung (letzte Mahnung)",
            4: "Inkasso-Androhung",
        }
        return stufen.get(self.mahnstufe, f"{self.mahnstufe}. Mahnung")

    @property
    def ist_ueberfaellig(self) -> bool:
        """Prüft ob die Zahlungsfrist überschritten ist"""
        if self.bezahlt or self.storniert:
            return False
        if self.zahlungsfrist:
            return datetime.now() > self.zahlungsfrist
        return False
