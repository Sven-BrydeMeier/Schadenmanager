"""
Ermittlungsakte-Service
Verwaltung von Ermittlungsakten der Staatsanwaltschaft
"""
import os
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass

from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean, Enum as SQLEnum
from sqlalchemy.orm import relationship

from src.models.base import Base
from src.models import Dokument, DokumentTyp, UnfallProjekt, User
from src.config.settings import get_settings


class ErmittlungsakteStatus(str, Enum):
    """Status der Ermittlungsakte"""
    ANGEFORDERT = "angefordert"
    EINGEGANGEN = "eingegangen"
    IN_BEARBEITUNG = "in_bearbeitung"
    AUSGEWERTET = "ausgewertet"
    ARCHIVIERT = "archiviert"


class Ermittlungsakte(Base):
    """Ermittlungsakte von der Staatsanwaltschaft"""
    __tablename__ = "ermittlungsakte"

    id = Column(Integer, primary_key=True)

    # Zuordnung
    unfallprojekt_id = Column(Integer, ForeignKey("unfallprojekt.id"), nullable=False)

    # Staatsanwaltschaft
    staatsanwaltschaft = Column(String(255))  # Name der StA
    aktenzeichen_sta = Column(String(100))  # Aktenzeichen bei der StA
    sachbearbeiter_sta = Column(String(255))

    # Anforderung
    angefordert_am = Column(DateTime)
    angefordert_von_user_id = Column(Integer, ForeignKey("user.id"))
    anforderungsschreiben_dok_id = Column(Integer, ForeignKey("dokument.id"))

    # Eingang
    eingegangen_am = Column(DateTime)
    dokument_id = Column(Integer, ForeignKey("dokument.id"))  # Die Akte als PDF
    seitenanzahl = Column(Integer)

    # Status
    status = Column(SQLEnum(ErmittlungsakteStatus), default=ErmittlungsakteStatus.ANGEFORDERT)

    # Auswertung
    zusammenfassung = Column(Text)  # KI-generierte Zusammenfassung
    unfallhergang_extrakt = Column(Text)  # Extrahierter Unfallhergang
    verursacher_info = Column(Text)  # Informationen zum Verursacher
    zeugenaussagen = Column(Text)  # Zusammenfassung Zeugenaussagen
    polizeibericht_extrakt = Column(Text)  # Extrakt aus Polizeibericht
    wichtige_blattzahlen = Column(Text)  # JSON mit wichtigen Seitenbereichen

    # Timestamps
    erstellt_am = Column(DateTime, default=datetime.utcnow)
    aktualisiert_am = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    projekt = relationship("UnfallProjekt", backref="ermittlungsakten")
    angefordert_von = relationship("User", foreign_keys=[angefordert_von_user_id])
    dokument = relationship("Dokument", foreign_keys=[dokument_id])
    anforderungsschreiben = relationship("Dokument", foreign_keys=[anforderungsschreiben_dok_id])


class ErmittlungsakteWeitergabe(Base):
    """Protokoll der Weitergabe von Ermittlungsakten"""
    __tablename__ = "ermittlungsakte_weitergabe"

    id = Column(Integer, primary_key=True)

    # Zuordnung
    ermittlungsakte_id = Column(Integer, ForeignKey("ermittlungsakte.id"), nullable=False)
    weitergegeben_von_user_id = Column(Integer, ForeignKey("user.id"), nullable=False)

    # Empfänger
    empfaenger_typ = Column(String(50))  # VERSICHERUNG_EIGEN, VERSICHERUNG_GEGNER, ANWALT_GEGNER, etc.
    empfaenger_name = Column(String(255))
    empfaenger_email = Column(String(255))
    empfaenger_user_id = Column(Integer, ForeignKey("user.id"))

    # Was wurde weitergegeben
    komplett = Column(Boolean, default=False)  # Gesamte Akte
    blattzahlen_von = Column(Integer)  # Von Seite
    blattzahlen_bis = Column(Integer)  # Bis Seite
    ausgewaehlte_bereiche = Column(Text)  # JSON mit spezifischen Bereichen

    # Begleittext
    anschreiben = Column(Text)
    verwendungszweck = Column(Text)

    # Timestamps
    erstellt_am = Column(DateTime, default=datetime.utcnow)

    # Relationships
    ermittlungsakte = relationship("Ermittlungsakte", backref="weitergaben")
    weitergegeben_von = relationship("User", foreign_keys=[weitergegeben_von_user_id])
    empfaenger_user = relationship("User", foreign_keys=[empfaenger_user_id])


@dataclass
class SeitenBereich:
    """Definiert einen Seitenbereich der Akte"""
    von: int
    bis: int
    bezeichnung: str
    beschreibung: Optional[str] = None


class ErmittlungsakteService:
    """Service für Ermittlungsakten-Verwaltung"""

    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()

    def anforderung_erstellen(
        self,
        projekt_id: int,
        user_id: int,
        staatsanwaltschaft: str,
        aktenzeichen_sta: str,
        sachbearbeiter_sta: Optional[str] = None
    ) -> Tuple[bool, str, Optional[Ermittlungsakte]]:
        """
        Erstellt eine Anforderung für eine Ermittlungsakte.

        Args:
            projekt_id: ID des Projekts
            user_id: ID des anfordernden Users
            staatsanwaltschaft: Name der Staatsanwaltschaft
            aktenzeichen_sta: Aktenzeichen bei der StA
            sachbearbeiter_sta: Optional - Sachbearbeiter

        Returns:
            Tuple (Erfolg, Nachricht, Ermittlungsakte)
        """
        projekt = self.db.query(UnfallProjekt).filter(
            UnfallProjekt.id == projekt_id
        ).first()

        if not projekt:
            return False, "Projekt nicht gefunden", None

        # Prüfen ob bereits eine Akte angefordert wurde
        bestehende = self.db.query(Ermittlungsakte).filter(
            Ermittlungsakte.unfallprojekt_id == projekt_id,
            Ermittlungsakte.aktenzeichen_sta == aktenzeichen_sta
        ).first()

        if bestehende:
            return False, "Für dieses Aktenzeichen wurde bereits eine Akte angefordert", bestehende

        akte = Ermittlungsakte(
            unfallprojekt_id=projekt_id,
            staatsanwaltschaft=staatsanwaltschaft,
            aktenzeichen_sta=aktenzeichen_sta,
            sachbearbeiter_sta=sachbearbeiter_sta,
            angefordert_am=datetime.now(),
            angefordert_von_user_id=user_id,
            status=ErmittlungsakteStatus.ANGEFORDERT
        )

        self.db.add(akte)
        self.db.flush()

        return True, "Anforderung erstellt", akte

    def generiere_anforderungsschreiben(
        self,
        akte: Ermittlungsakte
    ) -> str:
        """
        Generiert ein Anforderungsschreiben für die Ermittlungsakte.

        Args:
            akte: Die Ermittlungsakte

        Returns:
            Text des Anforderungsschreibens
        """
        projekt = akte.projekt
        user = akte.angefordert_von

        schreiben = f"""
{user.vorname} {user.nachname}
Rechtsanwalt
{datetime.now().strftime('%d.%m.%Y')}

An die
{akte.staatsanwaltschaft}

Aktenzeichen: {akte.aktenzeichen_sta}
{f"z. Hd. {akte.sachbearbeiter_sta}" if akte.sachbearbeiter_sta else ""}

Betreff: Antrag auf Akteneinsicht gem. § 406e StPO
         Unser Zeichen: {projekt.aktenzeichen or projekt.projektnummer}

Sehr geehrte Damen und Herren,

in vorbezeichneter Sache zeige ich an, dass ich den/die Geschädigte/n

    [Name des Mandanten]
    [Anschrift]

rechtsanwaltlich vertrete. Ordnungsgemäße Bevollmächtigung wird anwaltlich versichert.

Namens und in Vollmacht meines/meiner Mandanten/Mandantin beantrage ich hiermit

    Akteneinsicht gemäß § 406e StPO

zur Prüfung und Durchsetzung zivilrechtlicher Schadensersatzansprüche.

Ich bitte um Übersendung der Ermittlungsakte in Kopie an meine Kanzleiadresse.

Sollte das Verfahren noch nicht abgeschlossen sein, bitte ich um Mitteilung des aktuellen Verfahrensstands.

Für Rückfragen stehe ich gerne zur Verfügung.

Mit freundlichen Grüßen


{user.vorname} {user.nachname}
Rechtsanwalt
"""
        return schreiben

    def akte_importieren(
        self,
        ermittlungsakte_id: int,
        dokument_id: int,
        seitenanzahl: Optional[int] = None
    ) -> Tuple[bool, str]:
        """
        Importiert eine eingegangene Ermittlungsakte.

        Args:
            ermittlungsakte_id: ID der Ermittlungsakte
            dokument_id: ID des hochgeladenen Dokuments
            seitenanzahl: Anzahl der Seiten

        Returns:
            Tuple (Erfolg, Nachricht)
        """
        akte = self.db.query(Ermittlungsakte).filter(
            Ermittlungsakte.id == ermittlungsakte_id
        ).first()

        if not akte:
            return False, "Ermittlungsakte nicht gefunden"

        dokument = self.db.query(Dokument).filter(
            Dokument.id == dokument_id
        ).first()

        if not dokument:
            return False, "Dokument nicht gefunden"

        akte.dokument_id = dokument_id
        akte.eingegangen_am = datetime.now()
        akte.seitenanzahl = seitenanzahl
        akte.status = ErmittlungsakteStatus.EINGEGANGEN

        self.db.flush()

        return True, "Ermittlungsakte erfolgreich importiert"

    def akte_auswerten(
        self,
        ermittlungsakte_id: int,
        zusammenfassung: str,
        unfallhergang_extrakt: str,
        verursacher_info: str,
        zeugenaussagen: Optional[str] = None,
        polizeibericht_extrakt: Optional[str] = None,
        wichtige_bereiche: Optional[List[SeitenBereich]] = None
    ) -> Tuple[bool, str]:
        """
        Speichert die Auswertung einer Ermittlungsakte.

        Args:
            ermittlungsakte_id: ID der Ermittlungsakte
            zusammenfassung: Allgemeine Zusammenfassung
            unfallhergang_extrakt: Extrakt zum Unfallhergang
            verursacher_info: Informationen zum Verursacher
            zeugenaussagen: Optional - Zeugenaussagen
            polizeibericht_extrakt: Optional - Polizeibericht
            wichtige_bereiche: Optional - Liste wichtiger Seitenbereiche

        Returns:
            Tuple (Erfolg, Nachricht)
        """
        akte = self.db.query(Ermittlungsakte).filter(
            Ermittlungsakte.id == ermittlungsakte_id
        ).first()

        if not akte:
            return False, "Ermittlungsakte nicht gefunden"

        akte.zusammenfassung = zusammenfassung
        akte.unfallhergang_extrakt = unfallhergang_extrakt
        akte.verursacher_info = verursacher_info
        akte.zeugenaussagen = zeugenaussagen
        akte.polizeibericht_extrakt = polizeibericht_extrakt

        if wichtige_bereiche:
            akte.wichtige_blattzahlen = json.dumps([
                {
                    "von": b.von,
                    "bis": b.bis,
                    "bezeichnung": b.bezeichnung,
                    "beschreibung": b.beschreibung
                }
                for b in wichtige_bereiche
            ], ensure_ascii=False)

        akte.status = ErmittlungsakteStatus.AUSGEWERTET
        self.db.flush()

        return True, "Auswertung gespeichert"

    def ki_zusammenfassung_erstellen(
        self,
        ermittlungsakte_id: int
    ) -> Tuple[bool, str, Dict]:
        """
        Erstellt eine KI-basierte Zusammenfassung der Ermittlungsakte.
        (Vereinfachte Version - würde normalerweise OCR + KI nutzen)

        Args:
            ermittlungsakte_id: ID der Ermittlungsakte

        Returns:
            Tuple (Erfolg, Nachricht, Zusammenfassung-Dict)
        """
        akte = self.db.query(Ermittlungsakte).filter(
            Ermittlungsakte.id == ermittlungsakte_id
        ).first()

        if not akte or not akte.dokument:
            return False, "Ermittlungsakte oder Dokument nicht gefunden", {}

        # In einer echten Implementierung würde hier:
        # 1. OCR auf das PDF angewendet
        # 2. Der Text mit KI analysiert
        # 3. Relevante Informationen extrahiert

        # Vereinfachte Platzhalter-Zusammenfassung
        zusammenfassung = {
            "unfallhergang": "Der Unfallhergang wird nach Analyse der Ermittlungsakte wie folgt zusammengefasst: [KI-Analyse erforderlich]",
            "verursacher": "Informationen zum Unfallverursacher: [KI-Analyse erforderlich]",
            "zeugen": "Zusammenfassung der Zeugenaussagen: [KI-Analyse erforderlich]",
            "polizeibericht": "Wesentliche Punkte aus dem Polizeibericht: [KI-Analyse erforderlich]",
            "empfehlung": "Basierend auf der Aktenlage wird empfohlen: [KI-Analyse erforderlich]",
            "wichtige_seiten": [
                {"von": 1, "bis": 10, "bezeichnung": "Polizeibericht", "beschreibung": "Unfallaufnahme"},
                {"von": 11, "bis": 20, "bezeichnung": "Zeugenvernehmungen", "beschreibung": "Aussagen der Unfallzeugen"},
                {"von": 21, "bis": 30, "bezeichnung": "Skizzen/Fotos", "beschreibung": "Unfallskizze und Lichtbilder"}
            ]
        }

        return True, "Zusammenfassung erstellt (KI-Analyse empfohlen)", zusammenfassung

    def weitergabe_erstellen(
        self,
        ermittlungsakte_id: int,
        user_id: int,
        empfaenger_typ: str,
        empfaenger_name: str,
        empfaenger_email: Optional[str] = None,
        empfaenger_user_id: Optional[int] = None,
        komplett: bool = False,
        blattzahlen_von: Optional[int] = None,
        blattzahlen_bis: Optional[int] = None,
        ausgewaehlte_bereiche: Optional[List[Dict]] = None,
        anschreiben: Optional[str] = None,
        verwendungszweck: Optional[str] = None
    ) -> Tuple[bool, str, Optional[ErmittlungsakteWeitergabe]]:
        """
        Erstellt eine Weitergabe der Ermittlungsakte.

        Args:
            ermittlungsakte_id: ID der Ermittlungsakte
            user_id: ID des weiterleitenden Users
            empfaenger_typ: Typ des Empfängers
            empfaenger_name: Name des Empfängers
            empfaenger_email: Optional - E-Mail
            empfaenger_user_id: Optional - User-ID wenn interner Empfänger
            komplett: Gesamte Akte
            blattzahlen_von: Von Seite (wenn nicht komplett)
            blattzahlen_bis: Bis Seite (wenn nicht komplett)
            ausgewaehlte_bereiche: Optional - Spezifische Bereiche
            anschreiben: Optional - Begleittext
            verwendungszweck: Optional - Verwendungszweck

        Returns:
            Tuple (Erfolg, Nachricht, Weitergabe-Objekt)
        """
        akte = self.db.query(Ermittlungsakte).filter(
            Ermittlungsakte.id == ermittlungsakte_id
        ).first()

        if not akte:
            return False, "Ermittlungsakte nicht gefunden", None

        if not akte.dokument_id:
            return False, "Ermittlungsakte wurde noch nicht importiert", None

        weitergabe = ErmittlungsakteWeitergabe(
            ermittlungsakte_id=ermittlungsakte_id,
            weitergegeben_von_user_id=user_id,
            empfaenger_typ=empfaenger_typ,
            empfaenger_name=empfaenger_name,
            empfaenger_email=empfaenger_email,
            empfaenger_user_id=empfaenger_user_id,
            komplett=komplett,
            blattzahlen_von=blattzahlen_von,
            blattzahlen_bis=blattzahlen_bis,
            ausgewaehlte_bereiche=json.dumps(ausgewaehlte_bereiche) if ausgewaehlte_bereiche else None,
            anschreiben=anschreiben,
            verwendungszweck=verwendungszweck
        )

        self.db.add(weitergabe)
        self.db.flush()

        return True, "Weitergabe protokolliert", weitergabe

    def generiere_verwendungstext(
        self,
        akte: Ermittlungsakte,
        verwendungszweck: str = "versicherung"
    ) -> str:
        """
        Generiert einen Text zur Verwendung gegenüber Versicherungen/Unfallgegner.

        Args:
            akte: Die Ermittlungsakte
            verwendungszweck: Art der Verwendung

        Returns:
            Formulierter Text
        """
        if not akte.unfallhergang_extrakt:
            return "Bitte werten Sie die Ermittlungsakte zunächst aus."

        if verwendungszweck == "versicherung":
            return f"""
Bezugnehmend auf die beigefügte Ermittlungsakte der {akte.staatsanwaltschaft}
(Az.: {akte.aktenzeichen_sta}) ergibt sich folgender Sachverhalt:

UNFALLHERGANG:
{akte.unfallhergang_extrakt}

VERURSACHER:
{akte.verursacher_info}

{f"ZEUGENAUSSAGEN:{chr(10)}{akte.zeugenaussagen}" if akte.zeugenaussagen else ""}

Die Ermittlungsakte belegt eindeutig die Haftung Ihres Versicherungsnehmers.
Wir fordern Sie daher auf, die geltend gemachten Ansprüche nunmehr vollständig zu regulieren.
"""
        elif verwendungszweck == "gegner":
            return f"""
Zur Untermauerung unserer Forderungen verweisen wir auf die Ermittlungsakte
der {akte.staatsanwaltschaft} (Az.: {akte.aktenzeichen_sta}).

Aus der Akte ergibt sich zweifelsfrei:
{akte.unfallhergang_extrakt}

{akte.verursacher_info}

Wir fordern Sie auf, die Haftung anzuerkennen und unsere Ansprüche zu erfüllen.
"""
        else:
            return akte.zusammenfassung or "Keine Zusammenfassung verfügbar"

    def get_ermittlungsakten(
        self,
        projekt_id: Optional[int] = None
    ) -> List[Ermittlungsakte]:
        """Holt alle Ermittlungsakten"""
        query = self.db.query(Ermittlungsakte)

        if projekt_id:
            query = query.filter(Ermittlungsakte.unfallprojekt_id == projekt_id)

        return query.order_by(Ermittlungsakte.erstellt_am.desc()).all()

    def get_weitergaben(
        self,
        ermittlungsakte_id: int
    ) -> List[ErmittlungsakteWeitergabe]:
        """Holt alle Weitergaben einer Ermittlungsakte"""
        return self.db.query(ErmittlungsakteWeitergabe).filter(
            ErmittlungsakteWeitergabe.ermittlungsakte_id == ermittlungsakte_id
        ).order_by(ErmittlungsakteWeitergabe.erstellt_am.desc()).all()


def get_ermittlungsakte_service(db: Session) -> ErmittlungsakteService:
    """Factory-Funktion für den Ermittlungsakte-Service"""
    return ErmittlungsakteService(db)
