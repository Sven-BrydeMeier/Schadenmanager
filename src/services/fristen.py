"""
Fristenwarnsystem Service
Überwachung von Verjährungs- und Klagefristen mit E-Mail-Benachrichtigung
"""
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
from enum import Enum
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Enum as SQLEnum, Date
from sqlalchemy.orm import relationship
from src.models.base import Base


class FristTyp(str, Enum):
    """Typen von Fristen"""
    VERJAEHRUNG = "VERJAEHRUNG"
    KLAGEFRIST = "KLAGEFRIST"
    BERUFUNGSFRIST = "BERUFUNGSFRIST"
    WIDERSPRUCHSFRIST = "WIDERSPRUCHSFRIST"
    STELLUNGNAHME = "STELLUNGNAHME"
    ZAHLUNG = "ZAHLUNG"
    GUTACHTEN = "GUTACHTEN"
    REGULIERUNG = "REGULIERUNG"
    RECHTSMITTEL = "RECHTSMITTEL"
    SONSTIGE = "SONSTIGE"


class FristPrioritaet(str, Enum):
    """Priorität einer Frist"""
    NIEDRIG = "NIEDRIG"
    NORMAL = "NORMAL"
    HOCH = "HOCH"
    KRITISCH = "KRITISCH"


class FristStatus(str, Enum):
    """Status einer Frist"""
    OFFEN = "OFFEN"
    WARNUNG = "WARNUNG"
    KRITISCH = "KRITISCH"
    ERLEDIGT = "ERLEDIGT"
    VERSTRICHEN = "VERSTRICHEN"


class Frist(Base):
    """Model für Fristen"""
    __tablename__ = "frist"

    id = Column(Integer, primary_key=True)

    # Projekt-Zuordnung
    projekt_id = Column(Integer, ForeignKey("unfallprojekt.id"), nullable=False)
    projekt = relationship("UnfallProjekt", backref="fristen")

    # Frist-Daten
    bezeichnung = Column(String(200), nullable=False)
    beschreibung = Column(Text)
    frist_typ = Column(SQLEnum(FristTyp), default=FristTyp.SONSTIGE)
    prioritaet = Column(SQLEnum(FristPrioritaet), default=FristPrioritaet.NORMAL)
    status = Column(SQLEnum(FristStatus), default=FristStatus.OFFEN)

    # Datum
    frist_datum = Column(Date, nullable=False)
    urspruengliches_datum = Column(Date)  # Falls verlängert

    # Berechnung
    berechnet_ab = Column(Date)  # Startdatum für Fristberechnung
    frist_tage = Column(Integer)  # Fristtage (z.B. 3 Jahre = 1095 Tage)

    # Warnung
    warnung_tage_vorher = Column(Integer, default=30)
    zweite_warnung_tage = Column(Integer, default=7)

    # Benachrichtigungen
    erste_warnung_gesendet = Column(Boolean, default=False)
    erste_warnung_am = Column(DateTime)
    zweite_warnung_gesendet = Column(Boolean, default=False)
    zweite_warnung_am = Column(DateTime)

    # Erledigung
    erledigt = Column(Boolean, default=False)
    erledigt_am = Column(DateTime)
    erledigt_von_user_id = Column(Integer, ForeignKey("user.id"))
    erledigt_notiz = Column(Text)

    # Verantwortlich
    verantwortlich_user_id = Column(Integer, ForeignKey("user.id"))

    # Metadaten
    erstellt_von_user_id = Column(Integer, ForeignKey("user.id"))
    erstellt_am = Column(DateTime, default=datetime.now)
    aktualisiert_am = Column(DateTime, onupdate=datetime.now)

    @property
    def tage_bis_frist(self) -> int:
        """Berechnet Tage bis zur Frist"""
        if self.frist_datum:
            return (self.frist_datum - date.today()).days
        return 0

    @property
    def ist_ueberfaellig(self) -> bool:
        """Prüft ob die Frist überschritten ist"""
        return self.tage_bis_frist < 0 and not self.erledigt

    @property
    def aktueller_status(self) -> FristStatus:
        """Berechnet den aktuellen Status"""
        if self.erledigt:
            return FristStatus.ERLEDIGT

        tage = self.tage_bis_frist

        if tage < 0:
            return FristStatus.VERSTRICHEN
        elif tage <= 7:
            return FristStatus.KRITISCH
        elif tage <= 30:
            return FristStatus.WARNUNG
        else:
            return FristStatus.OFFEN

    @property
    def status_anzeige(self) -> str:
        """Anzeigetext für Status"""
        status = self.aktueller_status
        return {
            FristStatus.OFFEN: "🟢 Offen",
            FristStatus.WARNUNG: "🟡 Warnung",
            FristStatus.KRITISCH: "🔴 Kritisch",
            FristStatus.ERLEDIGT: "✅ Erledigt",
            FristStatus.VERSTRICHEN: "⛔ Verstrichen"
        }.get(status, "Unbekannt")

    @property
    def typ_anzeige(self) -> str:
        """Anzeigetext für Fristtyp"""
        return {
            FristTyp.VERJAEHRUNG: "⏰ Verjährung",
            FristTyp.KLAGEFRIST: "⚖️ Klagefrist",
            FristTyp.BERUFUNGSFRIST: "📜 Berufungsfrist",
            FristTyp.WIDERSPRUCHSFRIST: "✋ Widerspruchsfrist",
            FristTyp.STELLUNGNAHME: "📝 Stellungnahme",
            FristTyp.ZAHLUNG: "💶 Zahlungsfrist",
            FristTyp.GUTACHTEN: "📋 Gutachtenfrist",
            FristTyp.REGULIERUNG: "🏢 Regulierungsfrist",
            FristTyp.RECHTSMITTEL: "⚖️ Rechtsmittelfrist",
            FristTyp.SONSTIGE: "📌 Sonstige"
        }.get(self.frist_typ, "Frist")


class FristenService:
    """Service für Fristenverwaltung und -überwachung"""

    # Standard-Fristdauern (in Tagen)
    STANDARD_FRISTEN = {
        FristTyp.VERJAEHRUNG: 1095,  # 3 Jahre
        FristTyp.KLAGEFRIST: 30,
        FristTyp.BERUFUNGSFRIST: 30,
        FristTyp.WIDERSPRUCHSFRIST: 14,
        FristTyp.STELLUNGNAHME: 14,
        FristTyp.ZAHLUNG: 14,
        FristTyp.REGULIERUNG: 42,  # 6 Wochen
        FristTyp.RECHTSMITTEL: 30
    }

    def __init__(self, db_session):
        self.db = db_session

    def frist_erstellen(
        self,
        projekt_id: int,
        bezeichnung: str,
        frist_datum: date,
        frist_typ: FristTyp = FristTyp.SONSTIGE,
        prioritaet: FristPrioritaet = FristPrioritaet.NORMAL,
        beschreibung: Optional[str] = None,
        verantwortlich_user_id: Optional[int] = None,
        warnung_tage_vorher: int = 30,
        erstellt_von_user_id: Optional[int] = None
    ) -> Frist:
        """Erstellt eine neue Frist"""
        frist = Frist(
            projekt_id=projekt_id,
            bezeichnung=bezeichnung,
            beschreibung=beschreibung,
            frist_typ=frist_typ,
            prioritaet=prioritaet,
            frist_datum=frist_datum,
            verantwortlich_user_id=verantwortlich_user_id,
            warnung_tage_vorher=warnung_tage_vorher,
            erstellt_von_user_id=erstellt_von_user_id
        )

        self.db.add(frist)
        self.db.flush()

        return frist

    def berechne_verjaehrungsfrist(
        self,
        projekt_id: int,
        unfall_datum: date,
        erstellt_von_user_id: Optional[int] = None
    ) -> Frist:
        """Berechnet und erstellt die Verjährungsfrist für einen Unfallschaden"""
        # Verjährung beginnt am Ende des Jahres, in dem der Anspruch entstanden ist
        jahresende = date(unfall_datum.year, 12, 31)

        # 3 Jahre Verjährungsfrist
        verjaehrung_datum = date(jahresende.year + 3, 12, 31)

        return self.frist_erstellen(
            projekt_id=projekt_id,
            bezeichnung=f"Verjährung Schadensersatzansprüche",
            frist_datum=verjaehrung_datum,
            frist_typ=FristTyp.VERJAEHRUNG,
            prioritaet=FristPrioritaet.KRITISCH,
            beschreibung=f"Verjährung der Schadensersatzansprüche aus dem Unfall vom {unfall_datum.strftime('%d.%m.%Y')}. Die regelmäßige Verjährungsfrist beträgt 3 Jahre (§ 195 BGB) und beginnt am Ende des Jahres, in dem der Anspruch entstanden ist (§ 199 BGB).",
            warnung_tage_vorher=90,  # 3 Monate vorher warnen
            erstellt_von_user_id=erstellt_von_user_id
        )

    def fristen_fuer_projekt(self, projekt_id: int, nur_offene: bool = False) -> List[Frist]:
        """Holt alle Fristen für ein Projekt"""
        query = self.db.query(Frist).filter(Frist.projekt_id == projekt_id)

        if nur_offene:
            query = query.filter(Frist.erledigt == False)

        return query.order_by(Frist.frist_datum).all()

    def kritische_fristen(self, tage: int = 30, user_id: Optional[int] = None) -> List[Frist]:
        """Holt alle kritischen Fristen der nächsten X Tage"""
        grenze = date.today() + timedelta(days=tage)

        query = self.db.query(Frist).filter(
            Frist.frist_datum <= grenze,
            Frist.frist_datum >= date.today(),
            Frist.erledigt == False
        )

        if user_id:
            query = query.filter(Frist.verantwortlich_user_id == user_id)

        return query.order_by(Frist.frist_datum).all()

    def ueberfaellige_fristen(self) -> List[Frist]:
        """Holt alle überfälligen Fristen"""
        return self.db.query(Frist).filter(
            Frist.frist_datum < date.today(),
            Frist.erledigt == False
        ).order_by(Frist.frist_datum).all()

    def frist_erledigen(
        self,
        frist_id: int,
        user_id: int,
        notiz: Optional[str] = None
    ) -> Optional[Frist]:
        """Markiert eine Frist als erledigt"""
        frist = self.db.query(Frist).get(frist_id)

        if frist:
            frist.erledigt = True
            frist.erledigt_am = datetime.now()
            frist.erledigt_von_user_id = user_id
            frist.erledigt_notiz = notiz
            frist.status = FristStatus.ERLEDIGT
            self.db.flush()

        return frist

    def frist_verlaengern(
        self,
        frist_id: int,
        neues_datum: date,
        grund: Optional[str] = None
    ) -> Optional[Frist]:
        """Verlängert eine Frist"""
        frist = self.db.query(Frist).get(frist_id)

        if frist:
            if not frist.urspruengliches_datum:
                frist.urspruengliches_datum = frist.frist_datum

            frist.frist_datum = neues_datum

            if grund:
                frist.beschreibung = f"{frist.beschreibung or ''}\n\nVerlängert: {grund}"

            # Warnungen zurücksetzen
            frist.erste_warnung_gesendet = False
            frist.zweite_warnung_gesendet = False

            self.db.flush()

        return frist

    def pruefe_und_sende_warnungen(self) -> List[Dict[str, Any]]:
        """Prüft alle Fristen und sendet ggf. Warnungen"""
        gesendete_warnungen = []
        heute = date.today()

        offene_fristen = self.db.query(Frist).filter(
            Frist.erledigt == False,
            Frist.frist_datum >= heute
        ).all()

        for frist in offene_fristen:
            tage_bis = frist.tage_bis_frist

            # Erste Warnung
            if (not frist.erste_warnung_gesendet and
                tage_bis <= frist.warnung_tage_vorher):

                warnung = self._sende_warnung(frist, "erste")
                if warnung:
                    frist.erste_warnung_gesendet = True
                    frist.erste_warnung_am = datetime.now()
                    gesendete_warnungen.append(warnung)

            # Zweite Warnung
            if (not frist.zweite_warnung_gesendet and
                frist.zweite_warnung_tage and
                tage_bis <= frist.zweite_warnung_tage):

                warnung = self._sende_warnung(frist, "zweite")
                if warnung:
                    frist.zweite_warnung_gesendet = True
                    frist.zweite_warnung_am = datetime.now()
                    gesendete_warnungen.append(warnung)

        self.db.flush()
        return gesendete_warnungen

    def _sende_warnung(self, frist: Frist, warnung_typ: str) -> Optional[Dict[str, Any]]:
        """Sendet eine Fristwarnung (intern - würde E-Mail-Service nutzen)"""
        warnung = {
            "frist_id": frist.id,
            "projekt_id": frist.projekt_id,
            "bezeichnung": frist.bezeichnung,
            "frist_datum": frist.frist_datum.isoformat(),
            "tage_bis": frist.tage_bis_frist,
            "warnung_typ": warnung_typ,
            "verantwortlich_user_id": frist.verantwortlich_user_id,
            "prioritaet": frist.prioritaet.value,
            "gesendet_am": datetime.now().isoformat()
        }

        # Hier würde der E-Mail-Service aufgerufen werden
        # email_service.sende_fristwarnung(warnung)

        return warnung

    def fristen_uebersicht(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Erstellt eine Übersicht aller Fristen"""
        query = self.db.query(Frist)

        if user_id:
            query = query.filter(Frist.verantwortlich_user_id == user_id)

        alle_fristen = query.all()
        heute = date.today()

        return {
            "gesamt": len(alle_fristen),
            "offen": len([f for f in alle_fristen if not f.erledigt]),
            "erledigt": len([f for f in alle_fristen if f.erledigt]),
            "ueberfaellig": len([f for f in alle_fristen if f.ist_ueberfaellig]),
            "kritisch_7_tage": len([f for f in alle_fristen if not f.erledigt and 0 <= f.tage_bis_frist <= 7]),
            "warnung_30_tage": len([f for f in alle_fristen if not f.erledigt and 7 < f.tage_bis_frist <= 30]),
            "naechste_frist": min([f for f in alle_fristen if not f.erledigt], key=lambda x: x.frist_datum, default=None)
        }

    def erstelle_standard_fristen(
        self,
        projekt_id: int,
        unfall_datum: date,
        erstellt_von_user_id: Optional[int] = None
    ) -> List[Frist]:
        """Erstellt Standard-Fristen für ein neues Projekt"""
        fristen = []

        # Verjährungsfrist
        fristen.append(self.berechne_verjaehrungsfrist(
            projekt_id, unfall_datum, erstellt_von_user_id
        ))

        # Regulierungsfrist (6 Wochen nach Schadenmeldung)
        regulierung_datum = date.today() + timedelta(days=42)
        fristen.append(self.frist_erstellen(
            projekt_id=projekt_id,
            bezeichnung="Regulierungsfrist der Versicherung",
            frist_datum=regulierung_datum,
            frist_typ=FristTyp.REGULIERUNG,
            prioritaet=FristPrioritaet.NORMAL,
            beschreibung="Die Versicherung hat in der Regel 4-6 Wochen Zeit zur Regulierung nach vollständiger Schadenmeldung.",
            warnung_tage_vorher=7,
            erstellt_von_user_id=erstellt_von_user_id
        ))

        return fristen
