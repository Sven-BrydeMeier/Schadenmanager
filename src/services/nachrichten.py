"""
Mandanten-Kommunikation (Chat/Nachrichten) Service
Interne Nachrichtenverwaltung zwischen Parteien
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from src.models.base import Base


class NachrichtTyp(str, Enum):
    """Typen von Nachrichten"""
    TEXT = "TEXT"
    DATEI = "DATEI"
    SYSTEM = "SYSTEM"
    STATUSAENDERUNG = "STATUSAENDERUNG"


class NachrichtPrioritaet(str, Enum):
    """Priorität einer Nachricht"""
    NORMAL = "NORMAL"
    WICHTIG = "WICHTIG"
    DRINGEND = "DRINGEND"


class Nachricht(Base):
    """Model für Nachrichten"""
    __tablename__ = "nachricht"

    id = Column(Integer, primary_key=True)

    # Projekt-Zuordnung (optional - kann auch projektübergreifend sein)
    projekt_id = Column(Integer, ForeignKey("unfallprojekt.id"))
    projekt = relationship("UnfallProjekt", backref="nachrichten")

    # Konversation
    konversation_id = Column(String(50), nullable=False, index=True)

    # Absender/Empfänger
    absender_user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    absender = relationship("User", foreign_keys=[absender_user_id])
    empfaenger_user_id = Column(Integer, ForeignKey("user.id"))
    empfaenger = relationship("User", foreign_keys=[empfaenger_user_id])

    # Gruppenkonversation
    ist_gruppenkonversation = Column(Boolean, default=False)

    # Nachricht
    nachricht_typ = Column(SQLEnum(NachrichtTyp), default=NachrichtTyp.TEXT)
    prioritaet = Column(SQLEnum(NachrichtPrioritaet), default=NachrichtPrioritaet.NORMAL)
    betreff = Column(String(200))
    inhalt = Column(Text, nullable=False)

    # Dateianhang
    dokument_id = Column(Integer, ForeignKey("dokument.id"))

    # Status
    gelesen = Column(Boolean, default=False)
    gelesen_am = Column(DateTime)

    # Antwort auf
    antwort_auf_id = Column(Integer, ForeignKey("nachricht.id"))

    # Metadaten
    erstellt_am = Column(DateTime, default=datetime.now)
    geaendert_am = Column(DateTime)
    geloescht = Column(Boolean, default=False)

    @property
    def prioritaet_anzeige(self) -> str:
        """Anzeigetext für Priorität"""
        return {
            NachrichtPrioritaet.NORMAL: "",
            NachrichtPrioritaet.WICHTIG: "⚠️ Wichtig",
            NachrichtPrioritaet.DRINGEND: "🔴 Dringend"
        }.get(self.prioritaet, "")

    @property
    def typ_icon(self) -> str:
        """Icon für Nachrichtentyp"""
        return {
            NachrichtTyp.TEXT: "💬",
            NachrichtTyp.DATEI: "📎",
            NachrichtTyp.SYSTEM: "ℹ️",
            NachrichtTyp.STATUSAENDERUNG: "🔄"
        }.get(self.nachricht_typ, "💬")


class KonversationsTeilnehmer(Base):
    """Model für Konversationsteilnehmer bei Gruppenchats"""
    __tablename__ = "konversations_teilnehmer"

    id = Column(Integer, primary_key=True)
    konversation_id = Column(String(50), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    user = relationship("User")

    # Status
    beigetreten_am = Column(DateTime, default=datetime.now)
    verlassen_am = Column(DateTime)
    stumm_geschaltet = Column(Boolean, default=False)
    letzte_gelesen_nachricht_id = Column(Integer)


class NachrichtenService:
    """Service für Nachrichtenverwaltung"""

    def __init__(self, db_session):
        self.db = db_session

    def _generiere_konversation_id(self, user1_id: int, user2_id: int, projekt_id: Optional[int] = None) -> str:
        """Generiert eine eindeutige Konversations-ID für zwei Benutzer"""
        # Sortiere IDs für konsistente ID
        ids = sorted([user1_id, user2_id])
        if projekt_id:
            return f"p{projekt_id}_u{ids[0]}_u{ids[1]}"
        return f"u{ids[0]}_u{ids[1]}"

    def nachricht_senden(
        self,
        absender_user_id: int,
        empfaenger_user_id: int,
        inhalt: str,
        projekt_id: Optional[int] = None,
        betreff: Optional[str] = None,
        prioritaet: NachrichtPrioritaet = NachrichtPrioritaet.NORMAL,
        dokument_id: Optional[int] = None,
        antwort_auf_id: Optional[int] = None
    ) -> Nachricht:
        """Sendet eine Nachricht an einen Benutzer"""
        konversation_id = self._generiere_konversation_id(
            absender_user_id, empfaenger_user_id, projekt_id
        )

        nachricht_typ = NachrichtTyp.DATEI if dokument_id else NachrichtTyp.TEXT

        nachricht = Nachricht(
            projekt_id=projekt_id,
            konversation_id=konversation_id,
            absender_user_id=absender_user_id,
            empfaenger_user_id=empfaenger_user_id,
            nachricht_typ=nachricht_typ,
            prioritaet=prioritaet,
            betreff=betreff,
            inhalt=inhalt,
            dokument_id=dokument_id,
            antwort_auf_id=antwort_auf_id
        )
        self.db.add(nachricht)
        self.db.flush()
        return nachricht

    def system_nachricht_senden(
        self,
        empfaenger_user_id: int,
        inhalt: str,
        projekt_id: Optional[int] = None,
        betreff: Optional[str] = None
    ) -> Nachricht:
        """Sendet eine Systemnachricht"""
        nachricht = Nachricht(
            projekt_id=projekt_id,
            konversation_id=f"system_u{empfaenger_user_id}",
            absender_user_id=empfaenger_user_id,  # System als Absender (gleicher User)
            empfaenger_user_id=empfaenger_user_id,
            nachricht_typ=NachrichtTyp.SYSTEM,
            betreff=betreff or "Systemnachricht",
            inhalt=inhalt
        )
        self.db.add(nachricht)
        self.db.flush()
        return nachricht

    def nachrichten_fuer_konversation(self, konversation_id: str, limit: int = 100) -> List[Nachricht]:
        """Holt alle Nachrichten einer Konversation"""
        return self.db.query(Nachricht).filter(
            Nachricht.konversation_id == konversation_id,
            Nachricht.geloescht == False
        ).order_by(Nachricht.erstellt_am.desc()).limit(limit).all()

    def konversationen_fuer_user(self, user_id: int) -> List[Dict[str, Any]]:
        """Holt alle Konversationen eines Benutzers"""
        from sqlalchemy import or_, func
        from src.models import User

        # Finde alle eindeutigen Konversations-IDs für diesen User
        subquery = self.db.query(
            Nachricht.konversation_id,
            func.max(Nachricht.erstellt_am).label("letzte_nachricht_am"),
            func.count(Nachricht.id).label("anzahl_nachrichten")
        ).filter(
            or_(
                Nachricht.absender_user_id == user_id,
                Nachricht.empfaenger_user_id == user_id
            ),
            Nachricht.geloescht == False
        ).group_by(Nachricht.konversation_id).subquery()

        # Hole die neueste Nachricht pro Konversation
        konversationen = []

        for row in self.db.query(subquery).all():
            letzte_nachricht = self.db.query(Nachricht).filter(
                Nachricht.konversation_id == row.konversation_id
            ).order_by(Nachricht.erstellt_am.desc()).first()

            if letzte_nachricht:
                # Finde den Gesprächspartner
                if letzte_nachricht.absender_user_id == user_id:
                    partner_id = letzte_nachricht.empfaenger_user_id
                else:
                    partner_id = letzte_nachricht.absender_user_id

                partner = self.db.query(User).get(partner_id) if partner_id else None

                # Zähle ungelesene Nachrichten
                ungelesen = self.db.query(Nachricht).filter(
                    Nachricht.konversation_id == row.konversation_id,
                    Nachricht.empfaenger_user_id == user_id,
                    Nachricht.gelesen == False
                ).count()

                konversationen.append({
                    "konversation_id": row.konversation_id,
                    "letzte_nachricht": letzte_nachricht,
                    "letzte_nachricht_am": row.letzte_nachricht_am,
                    "anzahl_nachrichten": row.anzahl_nachrichten,
                    "ungelesen": ungelesen,
                    "partner": partner,
                    "projekt_id": letzte_nachricht.projekt_id
                })

        # Sortiere nach letzter Nachricht
        konversationen.sort(key=lambda x: x["letzte_nachricht_am"], reverse=True)

        return konversationen

    def ungelesene_nachrichten_zaehlen(self, user_id: int) -> int:
        """Zählt ungelesene Nachrichten für einen Benutzer"""
        return self.db.query(Nachricht).filter(
            Nachricht.empfaenger_user_id == user_id,
            Nachricht.gelesen == False,
            Nachricht.geloescht == False
        ).count()

    def nachrichten_als_gelesen_markieren(self, konversation_id: str, user_id: int) -> int:
        """Markiert alle Nachrichten einer Konversation als gelesen"""
        nachrichten = self.db.query(Nachricht).filter(
            Nachricht.konversation_id == konversation_id,
            Nachricht.empfaenger_user_id == user_id,
            Nachricht.gelesen == False
        ).all()

        for nachricht in nachrichten:
            nachricht.gelesen = True
            nachricht.gelesen_am = datetime.now()

        self.db.flush()
        return len(nachrichten)

    def nachricht_loeschen(self, nachricht_id: int, user_id: int) -> bool:
        """Löscht eine Nachricht (soft delete)"""
        nachricht = self.db.query(Nachricht).get(nachricht_id)

        if nachricht and nachricht.absender_user_id == user_id:
            nachricht.geloescht = True
            self.db.flush()
            return True

        return False

    def nachrichten_fuer_projekt(self, projekt_id: int, limit: int = 50) -> List[Nachricht]:
        """Holt alle Nachrichten für ein Projekt"""
        return self.db.query(Nachricht).filter(
            Nachricht.projekt_id == projekt_id,
            Nachricht.geloescht == False
        ).order_by(Nachricht.erstellt_am.desc()).limit(limit).all()

    def suche_nachrichten(self, user_id: int, suchbegriff: str) -> List[Nachricht]:
        """Sucht in Nachrichten eines Benutzers"""
        from sqlalchemy import or_

        return self.db.query(Nachricht).filter(
            or_(
                Nachricht.absender_user_id == user_id,
                Nachricht.empfaenger_user_id == user_id
            ),
            Nachricht.geloescht == False,
            or_(
                Nachricht.inhalt.ilike(f"%{suchbegriff}%"),
                Nachricht.betreff.ilike(f"%{suchbegriff}%")
            )
        ).order_by(Nachricht.erstellt_am.desc()).limit(50).all()
