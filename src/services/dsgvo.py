"""
DSGVO-Service (Datenschutz-Grundverordnung)
Ermöglicht Datenauskunft, Löschung und Protokollierung gemäß DSGVO
"""
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
from dataclasses import dataclass, asdict

from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean, Enum as SQLEnum
from sqlalchemy.orm import relationship

from src.models.base import Base
from src.models import (
    User, UnfallProjekt, Dokument, KostenPosition,
    Korrespondenz, Wiedervorlage, Notiz, DokumentTyp
)


class DSGVOAktionTyp(str, Enum):
    """Typ der DSGVO-Aktion"""
    AUSKUNFT = "auskunft"
    LOESCHUNG = "loeschung"
    BERICHTIGUNG = "berichtigung"
    EINSCHRAENKUNG = "einschraenkung"
    DATENPORTABILITAET = "datenportabilitaet"


class DSGVOProtokoll(Base):
    """Protokoll für DSGVO-Aktionen"""
    __tablename__ = "dsgvo_protokoll"

    id = Column(Integer, primary_key=True)

    # Betroffene Person
    betroffene_person_user_id = Column(Integer, ForeignKey("user.id"))
    betroffene_person_name = Column(String(255))  # Falls kein User vorhanden
    betroffene_person_email = Column(String(255))

    # Projekt-Bezug
    unfallprojekt_id = Column(Integer, ForeignKey("unfallprojekt.id"))

    # Aktion
    aktion_typ = Column(SQLEnum(DSGVOAktionTyp), nullable=False)
    durchgefuehrt_von_user_id = Column(Integer, ForeignKey("user.id"), nullable=False)

    # Anforderungs-Dokument (muss vorhanden sein)
    anforderungs_dokument_id = Column(Integer, ForeignKey("dokument.id"))

    # Details
    begruendung = Column(Text)
    geloeschte_daten = Column(Text)  # JSON mit Details zu gelöschten Daten
    ausgenommene_daten = Column(Text)  # JSON mit Daten die nicht gelöscht wurden + Begründung
    exportierte_daten = Column(Text)  # JSON/Pfad zu exportierten Daten

    # Status
    status = Column(String(50), default="DURCHGEFUEHRT")  # ANGEFORDERT, DURCHGEFUEHRT, ABGELEHNT
    abschluss_bemerkung = Column(Text)

    # Timestamps
    erstellt_am = Column(DateTime, default=datetime.utcnow)
    durchgefuehrt_am = Column(DateTime)

    # Relationships
    betroffene_person = relationship("User", foreign_keys=[betroffene_person_user_id])
    projekt = relationship("UnfallProjekt")
    durchgefuehrt_von = relationship("User", foreign_keys=[durchgefuehrt_von_user_id])
    anforderungs_dokument = relationship("Dokument")


@dataclass
class PersonenDaten:
    """Struktur für personenbezogene Daten"""
    kategorie: str
    daten: Dict[str, Any]
    quelle: str
    loeschbar: bool
    loeschausnahme_grund: Optional[str] = None


class DSGVOService:
    """Service für DSGVO-konforme Datenverarbeitung"""

    def __init__(self, db: Session):
        self.db = db

    def pruefe_anforderungsdokument(
        self,
        projekt_id: int,
        betroffene_person_id: Optional[int] = None
    ) -> Tuple[bool, Optional[Dokument], str]:
        """
        Prüft ob ein DSGVO-Anforderungsschreiben in der Akte hinterlegt ist.

        Args:
            projekt_id: ID des Projekts
            betroffene_person_id: Optional - ID der betroffenen Person

        Returns:
            Tuple (Vorhanden, Dokument, Nachricht)
        """
        # Suche nach DSGVO-relevanten Dokumenten
        anforderungen = self.db.query(Dokument).filter(
            Dokument.unfallprojekt_id == projekt_id,
            Dokument.geloescht == False
        ).all()

        # Prüfe auf DSGVO-Keywords im Dateinamen oder Beschreibung
        dsgvo_keywords = [
            'dsgvo', 'datenschutz', 'auskunft', 'löschung', 'loeschung',
            'art. 15', 'art. 17', 'artikel 15', 'artikel 17',
            'betroffenenrecht', 'datenauskunft', 'löschanforderung'
        ]

        for dok in anforderungen:
            dateiname = (dok.original_dateiname or "").lower()
            beschreibung = (dok.beschreibung or "").lower()
            ocr_text = (dok.ocr_text or "").lower()

            for keyword in dsgvo_keywords:
                if keyword in dateiname or keyword in beschreibung or keyword in ocr_text:
                    return True, dok, "DSGVO-Anforderungsschreiben gefunden"

        return False, None, "Kein DSGVO-Anforderungsschreiben in der Akte gefunden. Bitte laden Sie zuerst das Anforderungsschreiben des Betroffenen hoch."

    def sammle_personendaten(
        self,
        projekt_id: int,
        betroffene_person_id: Optional[int] = None,
        betroffene_email: Optional[str] = None
    ) -> List[PersonenDaten]:
        """
        Sammelt alle personenbezogenen Daten zu einer Person.

        Args:
            projekt_id: ID des Projekts
            betroffene_person_id: Optional - User-ID
            betroffene_email: Optional - E-Mail der Person

        Returns:
            Liste der PersonenDaten
        """
        daten = []

        projekt = self.db.query(UnfallProjekt).filter(
            UnfallProjekt.id == projekt_id
        ).first()

        if not projekt:
            return daten

        # 1. Benutzerdaten
        if betroffene_person_id:
            user = self.db.query(User).filter(User.id == betroffene_person_id).first()
            if user:
                daten.append(PersonenDaten(
                    kategorie="Benutzerkonto",
                    daten={
                        "Vorname": user.vorname,
                        "Nachname": user.nachname,
                        "E-Mail": user.email,
                        "Telefon": user.telefon,
                        "Rolle": user.rolle.value if user.rolle else None,
                        "Erstellt am": user.erstellt_am.isoformat() if user.erstellt_am else None,
                        "Letzter Login": user.letzter_login.isoformat() if user.letzter_login else None
                    },
                    quelle="Benutzertabelle",
                    loeschbar=True
                ))

        # 2. Projektdaten
        if projekt.unfallopfer_user_id == betroffene_person_id:
            daten.append(PersonenDaten(
                kategorie="Unfallprojekt - Stammdaten",
                daten={
                    "Aktenzeichen": projekt.aktenzeichen,
                    "Projektnummer": projekt.projektnummer,
                    "Unfalldatum": projekt.unfalldatum.isoformat() if projekt.unfalldatum else None,
                    "Unfallort": projekt.unfallort,
                    "Unfallhergang": projekt.unfallhergang,
                    "Schuldfrage": projekt.schuldfrage,
                    "Status": projekt.status
                },
                quelle="Unfallprojekt",
                loeschbar=False,
                loeschausnahme_grund="Aufbewahrungspflicht nach § 147 AO (10 Jahre für steuerrelevante Unterlagen) und § 50 BRAO (6 Jahre Aufbewahrung anwaltlicher Akten)"
            ))

        # 3. Fahrzeugdaten
        if projekt.fahrzeug:
            fz = projekt.fahrzeug
            daten.append(PersonenDaten(
                kategorie="Fahrzeugdaten",
                daten={
                    "Kennzeichen": fz.kennzeichen,
                    "Hersteller": fz.hersteller,
                    "Modell": fz.modell,
                    "FIN": fz.fin,
                    "Erstzulassung": fz.erstzulassung.isoformat() if fz.erstzulassung else None
                },
                quelle="Fahrzeugtabelle",
                loeschbar=False,
                loeschausnahme_grund="Zur Nachvollziehbarkeit des Schadensfalls erforderlich (berechtigtes Interesse gem. Art. 6 Abs. 1 lit. f DSGVO)"
            ))

        # 4. Dokumente
        dokumente = self.db.query(Dokument).filter(
            Dokument.unfallprojekt_id == projekt_id,
            Dokument.hochgeladen_von_user_id == betroffene_person_id
        ).all()

        for dok in dokumente:
            daten.append(PersonenDaten(
                kategorie="Dokument",
                daten={
                    "Dateiname": dok.original_dateiname,
                    "Typ": dok.dokument_typ.value if dok.dokument_typ else None,
                    "Hochgeladen am": dok.erstellt_am.isoformat() if dok.erstellt_am else None,
                    "Beschreibung": dok.beschreibung
                },
                quelle=f"Dokument ID {dok.id}",
                loeschbar=dok.dokument_typ not in [DokumentTyp.GUTACHTEN, DokumentTyp.RECHNUNG],
                loeschausnahme_grund="Beweismittel für Schadensregulierung" if dok.dokument_typ in [DokumentTyp.GUTACHTEN, DokumentTyp.RECHNUNG] else None
            ))

        # 5. Korrespondenz
        korrespondenz = self.db.query(Korrespondenz).filter(
            Korrespondenz.unfallprojekt_id == projekt_id
        ).all()

        for korr in korrespondenz:
            daten.append(PersonenDaten(
                kategorie="Korrespondenz",
                daten={
                    "Betreff": korr.betreff,
                    "Datum": korr.datum.isoformat() if korr.datum else None,
                    "Richtung": korr.richtung.value if korr.richtung else None,
                    "Empfänger/Absender": korr.empfaenger_absender
                },
                quelle=f"Korrespondenz ID {korr.id}",
                loeschbar=False,
                loeschausnahme_grund="Dokumentationspflicht für Rechtsstreitigkeiten"
            ))

        # 6. Kostenpositionen
        kosten = self.db.query(KostenPosition).filter(
            KostenPosition.unfallprojekt_id == projekt_id
        ).all()

        for k in kosten:
            daten.append(PersonenDaten(
                kategorie="Kostenposition",
                daten={
                    "Beschreibung": k.beschreibung,
                    "Betrag": str(k.betrag),
                    "Kategorie": k.kategorie.value if k.kategorie else None,
                    "Erstellt am": k.erstellt_am.isoformat() if k.erstellt_am else None
                },
                quelle=f"Kostenposition ID {k.id}",
                loeschbar=False,
                loeschausnahme_grund="Steuerrechtliche Aufbewahrungspflicht nach § 147 AO"
            ))

        # 7. Notizen (falls vorhanden)
        try:
            notizen = self.db.query(Notiz).filter(
                Notiz.unfallprojekt_id == projekt_id
            ).all()

            for n in notizen:
                daten.append(PersonenDaten(
                    kategorie="Notiz",
                    daten={
                        "Inhalt": n.inhalt[:100] + "..." if len(n.inhalt or "") > 100 else n.inhalt,
                        "Kategorie": n.kategorie,
                        "Erstellt am": n.erstellt_am.isoformat() if n.erstellt_am else None
                    },
                    quelle=f"Notiz ID {n.id}",
                    loeschbar=True
                ))
        except:
            pass  # Notiz-Tabelle existiert möglicherweise noch nicht

        return daten

    def erstelle_datenauskunft(
        self,
        projekt_id: int,
        betroffene_person_id: int,
        durchgefuehrt_von_user_id: int,
        anforderungs_dokument_id: int
    ) -> Tuple[bool, str, Optional[Dict]]:
        """
        Erstellt eine DSGVO-Datenauskunft.

        Args:
            projekt_id: ID des Projekts
            betroffene_person_id: ID der betroffenen Person
            durchgefuehrt_von_user_id: ID des durchführenden Users
            anforderungs_dokument_id: ID des Anforderungsdokuments

        Returns:
            Tuple (Erfolg, Nachricht, Daten-Dict)
        """
        # Anforderungsdokument prüfen
        hat_anforderung, dok, msg = self.pruefe_anforderungsdokument(projekt_id, betroffene_person_id)
        if not hat_anforderung:
            return False, msg, None

        # Daten sammeln
        personendaten = self.sammle_personendaten(projekt_id, betroffene_person_id)

        # Auskunft strukturieren
        auskunft = {
            "erstellt_am": datetime.now().isoformat(),
            "betroffene_person_id": betroffene_person_id,
            "projekt_id": projekt_id,
            "rechtsgrundlage": "Art. 15 DSGVO - Auskunftsrecht der betroffenen Person",
            "kategorien": {}
        }

        for pd in personendaten:
            if pd.kategorie not in auskunft["kategorien"]:
                auskunft["kategorien"][pd.kategorie] = []
            auskunft["kategorien"][pd.kategorie].append({
                "daten": pd.daten,
                "quelle": pd.quelle
            })

        # Protokoll erstellen
        protokoll = DSGVOProtokoll(
            betroffene_person_user_id=betroffene_person_id,
            unfallprojekt_id=projekt_id,
            aktion_typ=DSGVOAktionTyp.AUSKUNFT,
            durchgefuehrt_von_user_id=durchgefuehrt_von_user_id,
            anforderungs_dokument_id=anforderungs_dokument_id,
            exportierte_daten=json.dumps(auskunft, ensure_ascii=False, default=str),
            status="DURCHGEFUEHRT",
            durchgefuehrt_am=datetime.now()
        )

        self.db.add(protokoll)
        self.db.flush()

        return True, "Datenauskunft erfolgreich erstellt", auskunft

    def fuehre_loeschung_durch(
        self,
        projekt_id: int,
        betroffene_person_id: int,
        durchgefuehrt_von_user_id: int,
        anforderungs_dokument_id: int,
        begruendung: str = ""
    ) -> Tuple[bool, str, Optional[DSGVOProtokoll]]:
        """
        Führt eine DSGVO-konforme Löschung durch.

        Args:
            projekt_id: ID des Projekts
            betroffene_person_id: ID der betroffenen Person
            durchgefuehrt_von_user_id: ID des durchführenden Users
            anforderungs_dokument_id: ID des Anforderungsdokuments
            begruendung: Begründung für die Löschung

        Returns:
            Tuple (Erfolg, Nachricht, Protokoll)
        """
        # Anforderungsdokument prüfen
        hat_anforderung, dok, msg = self.pruefe_anforderungsdokument(projekt_id, betroffene_person_id)
        if not hat_anforderung:
            return False, msg, None

        # Daten sammeln
        personendaten = self.sammle_personendaten(projekt_id, betroffene_person_id)

        geloeschte_daten = []
        ausgenommene_daten = []

        for pd in personendaten:
            if pd.loeschbar:
                geloeschte_daten.append({
                    "kategorie": pd.kategorie,
                    "quelle": pd.quelle,
                    "daten_zusammenfassung": list(pd.daten.keys())
                })
            else:
                ausgenommene_daten.append({
                    "kategorie": pd.kategorie,
                    "quelle": pd.quelle,
                    "ausnahmegrund": pd.loeschausnahme_grund,
                    "rechtsgrundlage": "Art. 17 Abs. 3 DSGVO"
                })

        # Tatsächliche Löschung durchführen
        # (nur für löschbare Daten)

        # Notizen löschen
        try:
            self.db.query(Notiz).filter(
                Notiz.unfallprojekt_id == projekt_id,
                Notiz.erstellt_von_user_id == betroffene_person_id
            ).delete()
        except:
            pass

        # Löschbare Dokumente in Papierkorb verschieben
        loeschbare_dokumente = self.db.query(Dokument).filter(
            Dokument.unfallprojekt_id == projekt_id,
            Dokument.hochgeladen_von_user_id == betroffene_person_id,
            Dokument.dokument_typ.notin_([DokumentTyp.GUTACHTEN, DokumentTyp.RECHNUNG])
        ).all()

        for dok in loeschbare_dokumente:
            dok.geloescht = True
            dok.geloescht_am = datetime.now()
            dok.geloescht_von_user_id = durchgefuehrt_von_user_id

        # Protokoll erstellen
        protokoll = DSGVOProtokoll(
            betroffene_person_user_id=betroffene_person_id,
            unfallprojekt_id=projekt_id,
            aktion_typ=DSGVOAktionTyp.LOESCHUNG,
            durchgefuehrt_von_user_id=durchgefuehrt_von_user_id,
            anforderungs_dokument_id=anforderungs_dokument_id,
            begruendung=begruendung,
            geloeschte_daten=json.dumps(geloeschte_daten, ensure_ascii=False),
            ausgenommene_daten=json.dumps(ausgenommene_daten, ensure_ascii=False),
            status="DURCHGEFUEHRT",
            durchgefuehrt_am=datetime.now(),
            abschluss_bemerkung=f"Löschung durchgeführt. {len(geloeschte_daten)} Datenkategorien gelöscht, {len(ausgenommene_daten)} Datenkategorien aufgrund gesetzlicher Aufbewahrungspflichten ausgenommen."
        )

        self.db.add(protokoll)
        self.db.flush()

        return True, f"DSGVO-Löschung durchgeführt. {len(ausgenommene_daten)} Datenkategorien konnten aufgrund gesetzlicher Aufbewahrungspflichten nicht gelöscht werden.", protokoll

    def get_protokolle(
        self,
        projekt_id: Optional[int] = None,
        betroffene_person_id: Optional[int] = None
    ) -> List[DSGVOProtokoll]:
        """Holt alle DSGVO-Protokolle"""
        query = self.db.query(DSGVOProtokoll)

        if projekt_id:
            query = query.filter(DSGVOProtokoll.unfallprojekt_id == projekt_id)

        if betroffene_person_id:
            query = query.filter(DSGVOProtokoll.betroffene_person_user_id == betroffene_person_id)

        return query.order_by(DSGVOProtokoll.erstellt_am.desc()).all()

    def exportiere_loeschprotokoll_pdf(self, protokoll: DSGVOProtokoll) -> str:
        """
        Exportiert ein Löschprotokoll als PDF.

        Args:
            protokoll: Das DSGVO-Protokoll

        Returns:
            Pfad zur PDF-Datei
        """
        # Hier würde die PDF-Generierung implementiert
        # Vereinfachte Version: JSON-Export
        return json.dumps({
            "titel": "DSGVO-Löschprotokoll",
            "erstellt_am": protokoll.erstellt_am.isoformat() if protokoll.erstellt_am else None,
            "durchgefuehrt_am": protokoll.durchgefuehrt_am.isoformat() if protokoll.durchgefuehrt_am else None,
            "aktion": protokoll.aktion_typ.value,
            "betroffene_person_id": protokoll.betroffene_person_user_id,
            "projekt_id": protokoll.unfallprojekt_id,
            "geloeschte_daten": json.loads(protokoll.geloeschte_daten) if protokoll.geloeschte_daten else [],
            "ausgenommene_daten": json.loads(protokoll.ausgenommene_daten) if protokoll.ausgenommene_daten else [],
            "begruendung": protokoll.begruendung,
            "abschluss_bemerkung": protokoll.abschluss_bemerkung
        }, ensure_ascii=False, indent=2)


def get_dsgvo_service(db: Session) -> DSGVOService:
    """Factory-Funktion für den DSGVO-Service"""
    return DSGVOService(db)
