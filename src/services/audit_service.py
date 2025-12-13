"""
Audit-Log Service für die Protokollierung aller Aktionen
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import desc

from src.models import AuditLog, AktionTyp, AktionKategorie, UnfallProjekt, User


class AuditService:
    """Service für Audit-Logging"""

    def __init__(self, db: Session):
        self.db = db

    def log(
        self,
        aktion: str,
        kategorie: str,
        user_id: Optional[int] = None,
        user_email: Optional[str] = None,
        user_name: Optional[str] = None,
        user_rolle: Optional[str] = None,
        objekt_typ: Optional[str] = None,
        objekt_id: Optional[int] = None,
        objekt_bezeichnung: Optional[str] = None,
        beschreibung: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        unfallprojekt_id: Optional[int] = None,
        aktenzeichen: Optional[str] = None,
        ip_adresse: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> AuditLog:
        """
        Erstellt einen Audit-Log-Eintrag.

        Args:
            aktion: Art der Aktion (z.B. LOGIN, DOKUMENT_HOCHGELADEN)
            kategorie: Kategorie der Aktion (z.B. AUTH, DOKUMENT)
            user_id: ID des ausführenden Benutzers
            user_email: E-Mail des Benutzers (für historische Nachvollziehbarkeit)
            user_name: Name des Benutzers
            user_rolle: Rolle des Benutzers
            objekt_typ: Typ des betroffenen Objekts
            objekt_id: ID des betroffenen Objekts
            objekt_bezeichnung: Bezeichnung des Objekts
            beschreibung: Beschreibung der Aktion
            details: Zusätzliche strukturierte Details
            unfallprojekt_id: ID des zugehörigen Projekts
            aktenzeichen: Aktenzeichen des Projekts
            ip_adresse: IP-Adresse des Benutzers
            user_agent: User-Agent des Browsers

        Returns:
            Der erstellte AuditLog-Eintrag
        """
        log_entry = AuditLog(
            aktion=aktion,
            aktion_kategorie=kategorie,
            user_id=user_id,
            user_email=user_email,
            user_name=user_name,
            user_rolle=user_rolle,
            objekt_typ=objekt_typ,
            objekt_id=objekt_id,
            objekt_bezeichnung=objekt_bezeichnung,
            beschreibung=beschreibung,
            details=details,
            unfallprojekt_id=unfallprojekt_id,
            aktenzeichen=aktenzeichen,
            ip_adresse=ip_adresse,
            user_agent=user_agent
        )

        self.db.add(log_entry)
        self.db.flush()

        return log_entry

    def log_mit_session_daten(
        self,
        aktion: str,
        kategorie: str,
        session_state: dict,
        objekt_typ: Optional[str] = None,
        objekt_id: Optional[int] = None,
        objekt_bezeichnung: Optional[str] = None,
        beschreibung: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        projekt: Optional[UnfallProjekt] = None
    ) -> AuditLog:
        """
        Erstellt einen Audit-Log-Eintrag mit Daten aus der Streamlit-Session.

        Args:
            aktion: Art der Aktion
            kategorie: Kategorie der Aktion
            session_state: Streamlit session_state Dictionary
            objekt_typ: Typ des betroffenen Objekts
            objekt_id: ID des betroffenen Objekts
            objekt_bezeichnung: Bezeichnung des Objekts
            beschreibung: Beschreibung der Aktion
            details: Zusätzliche Details
            projekt: Optional - UnfallProjekt für automatische Zuordnung

        Returns:
            Der erstellte AuditLog-Eintrag
        """
        return self.log(
            aktion=aktion,
            kategorie=kategorie,
            user_id=session_state.get("user_id"),
            user_email=session_state.get("user_email"),
            user_name=session_state.get("user_name"),
            user_rolle=session_state.get("user_rolle"),
            objekt_typ=objekt_typ,
            objekt_id=objekt_id,
            objekt_bezeichnung=objekt_bezeichnung,
            beschreibung=beschreibung,
            details=details,
            unfallprojekt_id=projekt.id if projekt else None,
            aktenzeichen=projekt.aktenzeichen if projekt else None
        )

    def get_logs(
        self,
        limit: int = 100,
        offset: int = 0,
        user_id: Optional[int] = None,
        kategorie: Optional[str] = None,
        unfallprojekt_id: Optional[int] = None,
        von_datum: Optional[datetime] = None,
        bis_datum: Optional[datetime] = None
    ) -> List[AuditLog]:
        """
        Ruft Audit-Logs mit Filterung ab.

        Args:
            limit: Maximale Anzahl der Einträge
            offset: Offset für Paginierung
            user_id: Filter nach Benutzer
            kategorie: Filter nach Kategorie
            unfallprojekt_id: Filter nach Projekt
            von_datum: Filter ab Datum
            bis_datum: Filter bis Datum

        Returns:
            Liste der AuditLog-Einträge
        """
        query = self.db.query(AuditLog)

        if user_id:
            query = query.filter(AuditLog.user_id == user_id)

        if kategorie:
            query = query.filter(AuditLog.aktion_kategorie == kategorie)

        if unfallprojekt_id:
            query = query.filter(AuditLog.unfallprojekt_id == unfallprojekt_id)

        if von_datum:
            query = query.filter(AuditLog.zeitstempel >= von_datum)

        if bis_datum:
            query = query.filter(AuditLog.zeitstempel <= bis_datum)

        query = query.order_by(desc(AuditLog.zeitstempel))
        query = query.offset(offset).limit(limit)

        return query.all()

    def get_projekt_historie(self, unfallprojekt_id: int, limit: int = 50) -> List[AuditLog]:
        """
        Ruft die komplette Historie eines Projekts ab.

        Args:
            unfallprojekt_id: ID des Projekts
            limit: Maximale Anzahl der Einträge

        Returns:
            Liste der AuditLog-Einträge für das Projekt
        """
        return self.get_logs(
            limit=limit,
            unfallprojekt_id=unfallprojekt_id
        )

    def count_logs(
        self,
        user_id: Optional[int] = None,
        kategorie: Optional[str] = None,
        unfallprojekt_id: Optional[int] = None
    ) -> int:
        """
        Zählt Audit-Logs mit Filterung.

        Args:
            user_id: Filter nach Benutzer
            kategorie: Filter nach Kategorie
            unfallprojekt_id: Filter nach Projekt

        Returns:
            Anzahl der Einträge
        """
        query = self.db.query(AuditLog)

        if user_id:
            query = query.filter(AuditLog.user_id == user_id)

        if kategorie:
            query = query.filter(AuditLog.aktion_kategorie == kategorie)

        if unfallprojekt_id:
            query = query.filter(AuditLog.unfallprojekt_id == unfallprojekt_id)

        return query.count()


def get_audit_service(db: Session) -> AuditService:
    """Factory-Funktion für den Audit-Service"""
    return AuditService(db)
