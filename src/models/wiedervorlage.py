"""
Wiedervorlage/Fristen-Modell für Erinnerungen und Termine
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum

from src.models.base import Base


class WiedervorlageTyp(enum.Enum):
    """Typen von Wiedervorlagen"""
    FRIST = "FRIST"                      # Rechtliche Frist
    ERINNERUNG = "ERINNERUNG"            # Allgemeine Erinnerung
    TERMIN = "TERMIN"                    # Termin (Gutachter, Gericht, etc.)
    NACHFASSEN = "NACHFASSEN"            # Nachfass-Aktion
    ZAHLUNG = "ZAHLUNG"                  # Zahlungsfrist


class WiedervorlagePrioritaet(enum.Enum):
    """Priorität der Wiedervorlage"""
    NIEDRIG = "NIEDRIG"
    NORMAL = "NORMAL"
    HOCH = "HOCH"
    KRITISCH = "KRITISCH"


class Wiedervorlage(Base):
    """Wiedervorlage/Erinnerung für Fristen und Termine"""
    __tablename__ = "wiedervorlage"

    id = Column(Integer, primary_key=True)

    # Zuordnung
    unfallprojekt_id = Column(Integer, ForeignKey("unfallprojekt.id"), nullable=False)
    erstellt_von_user_id = Column(Integer, ForeignKey("user.id"))
    zugewiesen_an_user_id = Column(Integer, ForeignKey("user.id"))

    # Wiedervorlage-Details
    typ = Column(SQLEnum(WiedervorlageTyp), default=WiedervorlageTyp.ERINNERUNG)
    prioritaet = Column(SQLEnum(WiedervorlagePrioritaet), default=WiedervorlagePrioritaet.NORMAL)
    titel = Column(String(255), nullable=False)
    beschreibung = Column(Text)

    # Zeitliche Angaben
    faellig_am = Column(DateTime, nullable=False)
    erinnerung_am = Column(DateTime)  # Wann soll die Erinnerung gesendet werden?
    erinnerung_tage_vorher = Column(Integer, default=3)  # Tage vor Fälligkeit erinnern

    # Status
    erledigt = Column(Boolean, default=False)
    erledigt_am = Column(DateTime)
    erledigt_von_user_id = Column(Integer, ForeignKey("user.id"))

    # Benachrichtigungen
    email_benachrichtigung = Column(Boolean, default=True)
    benachrichtigung_gesendet = Column(Boolean, default=False)
    benachrichtigung_gesendet_am = Column(DateTime)

    # Wiederholung
    wiederholen = Column(Boolean, default=False)
    wiederholung_intervall_tage = Column(Integer)  # z.B. 7 für wöchentlich, 30 für monatlich

    # Timestamps
    erstellt_am = Column(DateTime, default=datetime.utcnow)
    aktualisiert_am = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    projekt = relationship("UnfallProjekt", backref="wiedervorlagen")
    erstellt_von = relationship("User", foreign_keys=[erstellt_von_user_id])
    zugewiesen_an = relationship("User", foreign_keys=[zugewiesen_an_user_id])
    erledigt_von = relationship("User", foreign_keys=[erledigt_von_user_id])

    def __repr__(self):
        return f"<Wiedervorlage(id={self.id}, titel='{self.titel}', faellig={self.faellig_am})>"

    @property
    def typ_anzeige(self) -> str:
        """Gibt einen lesbaren Typ zurück"""
        typ_namen = {
            WiedervorlageTyp.FRIST: "Frist",
            WiedervorlageTyp.ERINNERUNG: "Erinnerung",
            WiedervorlageTyp.TERMIN: "Termin",
            WiedervorlageTyp.NACHFASSEN: "Nachfassen",
            WiedervorlageTyp.ZAHLUNG: "Zahlungsfrist"
        }
        return typ_namen.get(self.typ, "Unbekannt")

    @property
    def prioritaet_anzeige(self) -> str:
        """Gibt eine lesbare Priorität zurück"""
        prio_namen = {
            WiedervorlagePrioritaet.NIEDRIG: "Niedrig",
            WiedervorlagePrioritaet.NORMAL: "Normal",
            WiedervorlagePrioritaet.HOCH: "Hoch",
            WiedervorlagePrioritaet.KRITISCH: "Kritisch"
        }
        return prio_namen.get(self.prioritaet, "Normal")

    @property
    def ist_ueberfaellig(self) -> bool:
        """Prüft ob die Wiedervorlage überfällig ist"""
        if self.erledigt:
            return False
        return datetime.now() > self.faellig_am

    @property
    def tage_bis_faellig(self) -> int:
        """Gibt die Anzahl der Tage bis zur Fälligkeit zurück"""
        if self.erledigt:
            return 0
        delta = self.faellig_am - datetime.now()
        return delta.days

    @property
    def status_farbe(self) -> str:
        """Gibt eine Statusfarbe zurück (für Ampelsystem)"""
        if self.erledigt:
            return "success"  # Grün
        if self.ist_ueberfaellig:
            return "danger"  # Rot
        if self.tage_bis_faellig <= 3:
            return "warning"  # Orange
        return "info"  # Blau
