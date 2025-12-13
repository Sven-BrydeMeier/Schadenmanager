"""
Audit-Log Modell für die Protokollierung aller Aktionen
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship

from src.models.base import Base


class AuditLog(Base):
    """Protokolliert alle wichtigen Aktionen im System"""
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True)

    # Zeitstempel
    zeitstempel = Column(DateTime, default=datetime.utcnow, index=True)

    # Benutzer
    user_id = Column(Integer, ForeignKey("user.id"))
    user_email = Column(String(255))  # Redundant gespeichert für historische Nachvollziehbarkeit
    user_name = Column(String(255))
    user_rolle = Column(String(50))

    # Aktion
    aktion = Column(String(100), nullable=False, index=True)  # z.B. LOGIN, LOGOUT, DOKUMENT_HOCHGELADEN
    aktion_kategorie = Column(String(50), index=True)  # z.B. AUTH, DOKUMENT, PROJEKT, KOSTEN

    # Betroffenes Objekt
    objekt_typ = Column(String(50))  # z.B. UnfallProjekt, Dokument, User
    objekt_id = Column(Integer)
    objekt_bezeichnung = Column(String(255))  # z.B. Aktenzeichen oder Dateiname

    # Details
    beschreibung = Column(Text)
    details = Column(JSON)  # Zusätzliche strukturierte Daten

    # Projekt-Zuordnung (für einfache Filterung)
    unfallprojekt_id = Column(Integer, ForeignKey("unfallprojekt.id"))
    aktenzeichen = Column(String(20))

    # Technische Details
    ip_adresse = Column(String(45))
    user_agent = Column(String(500))

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    projekt = relationship("UnfallProjekt", foreign_keys=[unfallprojekt_id])

    def __repr__(self):
        return f"<AuditLog(id={self.id}, aktion='{self.aktion}', user='{self.user_email}')>"


# Vordefinierte Aktionstypen
class AktionTyp:
    """Konstanten für Aktionstypen"""

    # Authentifizierung
    LOGIN = "LOGIN"
    LOGIN_FEHLGESCHLAGEN = "LOGIN_FEHLGESCHLAGEN"
    LOGOUT = "LOGOUT"
    PASSWORT_GEAENDERT = "PASSWORT_GEAENDERT"
    ZWEI_FAKTOR_AKTIVIERT = "ZWEI_FAKTOR_AKTIVIERT"

    # Projekte
    PROJEKT_ERSTELLT = "PROJEKT_ERSTELLT"
    PROJEKT_BEARBEITET = "PROJEKT_BEARBEITET"
    PROJEKT_STATUS_GEAENDERT = "PROJEKT_STATUS_GEAENDERT"
    PROJEKT_GELOESCHT = "PROJEKT_GELOESCHT"

    # Dokumente
    DOKUMENT_HOCHGELADEN = "DOKUMENT_HOCHGELADEN"
    DOKUMENT_FREIGEGEBEN = "DOKUMENT_FREIGEGEBEN"
    DOKUMENT_ABGELEHNT = "DOKUMENT_ABGELEHNT"
    DOKUMENT_GELOESCHT = "DOKUMENT_GELOESCHT"
    OCR_KORRIGIERT = "OCR_KORRIGIERT"
    KI_DATEN_UEBERNOMMEN = "KI_DATEN_UEBERNOMMEN"

    # Kosten
    KOSTENPOSITION_ERSTELLT = "KOSTENPOSITION_ERSTELLT"
    KOSTENPOSITION_BEARBEITET = "KOSTENPOSITION_BEARBEITET"
    KOSTENPOSITION_GELOESCHT = "KOSTENPOSITION_GELOESCHT"
    ZAHLUNG_ERFASST = "ZAHLUNG_ERFASST"

    # Korrespondenz
    KORRESPONDENZ_ERSTELLT = "KORRESPONDENZ_ERSTELLT"
    KORRESPONDENZ_GESENDET = "KORRESPONDENZ_GESENDET"

    # Wiedervorlagen
    WIEDERVORLAGE_ERSTELLT = "WIEDERVORLAGE_ERSTELLT"
    WIEDERVORLAGE_ERLEDIGT = "WIEDERVORLAGE_ERLEDIGT"
    WIEDERVORLAGE_GELOESCHT = "WIEDERVORLAGE_GELOESCHT"

    # Benutzerverwaltung
    BENUTZER_ERSTELLT = "BENUTZER_ERSTELLT"
    BENUTZER_BEARBEITET = "BENUTZER_BEARBEITET"
    BENUTZER_DEAKTIVIERT = "BENUTZER_DEAKTIVIERT"
    EINLADUNG_GESENDET = "EINLADUNG_GESENDET"


class AktionKategorie:
    """Konstanten für Aktionskategorien"""
    AUTH = "AUTH"
    PROJEKT = "PROJEKT"
    DOKUMENT = "DOKUMENT"
    KOSTEN = "KOSTEN"
    KORRESPONDENZ = "KORRESPONDENZ"
    WIEDERVORLAGE = "WIEDERVORLAGE"
    BENUTZER = "BENUTZER"
    SYSTEM = "SYSTEM"
