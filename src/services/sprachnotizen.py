"""
Sprachnotizen/Diktierfunktion Service
Audio-Aufnahme und Transkription für Fallnotizen
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
import json
import base64
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Enum as SQLEnum, Float
from sqlalchemy.orm import relationship
from src.models.base import Base


class SprachnotizStatus(str, Enum):
    """Status einer Sprachnotiz"""
    AUFGENOMMEN = "AUFGENOMMEN"
    TRANSKRIBIERT = "TRANSKRIBIERT"
    VERIFIZIERT = "VERIFIZIERT"
    ARCHIVIERT = "ARCHIVIERT"


class SprachnotizKategorie(str, Enum):
    """Kategorien für Sprachnotizen"""
    TELEFONAT = "TELEFONAT"
    BESPRECHUNG = "BESPRECHUNG"
    DIKTAT = "DIKTAT"
    NOTIZ = "NOTIZ"
    ZEUGENBEFRAGUNG = "ZEUGENBEFRAGUNG"
    ORTSTERMIN = "ORTSTERMIN"
    SONSTIGE = "SONSTIGE"


class Sprachnotiz(Base):
    """Model für Sprachnotizen"""
    __tablename__ = "sprachnotiz"

    id = Column(Integer, primary_key=True)

    # Projekt-Zuordnung
    projekt_id = Column(Integer, ForeignKey("unfallprojekt.id"), nullable=False)
    projekt = relationship("UnfallProjekt", backref="sprachnotizen")

    # Notiz-Daten
    titel = Column(String(200), nullable=False)
    kategorie = Column(SQLEnum(SprachnotizKategorie), default=SprachnotizKategorie.NOTIZ)
    status = Column(SQLEnum(SprachnotizStatus), default=SprachnotizStatus.AUFGENOMMEN)

    # Audio
    audio_format = Column(String(20), default="webm")  # webm, mp3, wav
    audio_daten = Column(Text)  # Base64-kodiert
    dauer_sekunden = Column(Float)

    # Transkription
    transkription = Column(Text)
    transkription_automatisch = Column(Boolean, default=False)
    transkription_am = Column(DateTime)
    transkription_konfidenz = Column(Float)  # 0-1

    # Manuelle Bearbeitung
    bearbeitet_text = Column(Text)
    bearbeitet_am = Column(DateTime)
    bearbeitet_von_user_id = Column(Integer, ForeignKey("user.id"))

    # Metadaten
    aufgenommen_am = Column(DateTime, default=datetime.now)
    aufgenommen_von_user_id = Column(Integer, ForeignKey("user.id"))

    # Tags (JSON-Array)
    _tags = Column("tags", Text)

    @property
    def tags(self) -> List[str]:
        if self._tags:
            return json.loads(self._tags)
        return []

    @tags.setter
    def tags(self, value: List[str]):
        self._tags = json.dumps(value)

    @property
    def finaler_text(self) -> str:
        """Gibt den finalen Text zurück (bearbeitet oder transkribiert)"""
        return self.bearbeitet_text or self.transkription or ""

    @property
    def dauer_anzeige(self) -> str:
        """Formatierte Dauer-Anzeige"""
        if not self.dauer_sekunden:
            return "0:00"
        minuten = int(self.dauer_sekunden // 60)
        sekunden = int(self.dauer_sekunden % 60)
        return f"{minuten}:{sekunden:02d}"


class SprachnotizService:
    """Service für Sprachnotizen"""

    def __init__(self, db_session):
        self.db = db_session

    def notiz_erstellen(
        self,
        projekt_id: int,
        titel: str,
        audio_daten: str,  # Base64-kodiert
        audio_format: str = "webm",
        dauer_sekunden: Optional[float] = None,
        kategorie: SprachnotizKategorie = SprachnotizKategorie.NOTIZ,
        aufgenommen_von_user_id: Optional[int] = None,
        tags: Optional[List[str]] = None
    ) -> Sprachnotiz:
        """Erstellt eine neue Sprachnotiz"""
        notiz = Sprachnotiz(
            projekt_id=projekt_id,
            titel=titel,
            audio_daten=audio_daten,
            audio_format=audio_format,
            dauer_sekunden=dauer_sekunden,
            kategorie=kategorie,
            aufgenommen_von_user_id=aufgenommen_von_user_id
        )

        if tags:
            notiz.tags = tags

        self.db.add(notiz)
        self.db.flush()

        return notiz

    def transkribieren(
        self,
        notiz_id: int,
        transkription: str,
        automatisch: bool = True,
        konfidenz: Optional[float] = None
    ) -> Optional[Sprachnotiz]:
        """Fügt eine Transkription hinzu"""
        notiz = self.db.query(Sprachnotiz).get(notiz_id)

        if notiz:
            notiz.transkription = transkription
            notiz.transkription_automatisch = automatisch
            notiz.transkription_am = datetime.now()
            notiz.transkription_konfidenz = konfidenz
            notiz.status = SprachnotizStatus.TRANSKRIBIERT
            self.db.flush()

        return notiz

    def text_bearbeiten(
        self,
        notiz_id: int,
        text: str,
        user_id: int
    ) -> Optional[Sprachnotiz]:
        """Bearbeitet den transkribierten Text"""
        notiz = self.db.query(Sprachnotiz).get(notiz_id)

        if notiz:
            notiz.bearbeitet_text = text
            notiz.bearbeitet_am = datetime.now()
            notiz.bearbeitet_von_user_id = user_id
            notiz.status = SprachnotizStatus.VERIFIZIERT
            self.db.flush()

        return notiz

    def notizen_fuer_projekt(
        self,
        projekt_id: int,
        kategorie: Optional[SprachnotizKategorie] = None
    ) -> List[Sprachnotiz]:
        """Holt alle Sprachnotizen für ein Projekt"""
        query = self.db.query(Sprachnotiz).filter(
            Sprachnotiz.projekt_id == projekt_id
        )

        if kategorie:
            query = query.filter(Sprachnotiz.kategorie == kategorie)

        return query.order_by(Sprachnotiz.aufgenommen_am.desc()).all()

    def suche_in_transkriptionen(
        self,
        suchbegriff: str,
        projekt_id: Optional[int] = None
    ) -> List[Sprachnotiz]:
        """Sucht in Transkriptionen"""
        query = self.db.query(Sprachnotiz).filter(
            (Sprachnotiz.transkription.ilike(f"%{suchbegriff}%")) |
            (Sprachnotiz.bearbeitet_text.ilike(f"%{suchbegriff}%"))
        )

        if projekt_id:
            query = query.filter(Sprachnotiz.projekt_id == projekt_id)

        return query.order_by(Sprachnotiz.aufgenommen_am.desc()).all()

    def notiz_loeschen(self, notiz_id: int) -> bool:
        """Löscht eine Sprachnotiz"""
        notiz = self.db.query(Sprachnotiz).get(notiz_id)

        if notiz:
            self.db.delete(notiz)
            self.db.flush()
            return True

        return False

    def audio_herunterladen(self, notiz_id: int) -> Optional[Dict[str, Any]]:
        """Gibt Audio-Daten zum Download zurück"""
        notiz = self.db.query(Sprachnotiz).get(notiz_id)

        if notiz and notiz.audio_daten:
            return {
                'daten': base64.b64decode(notiz.audio_daten),
                'format': notiz.audio_format,
                'dateiname': f"sprachnotiz_{notiz.id}.{notiz.audio_format}"
            }

        return None

    def statistik(self, projekt_id: Optional[int] = None) -> Dict[str, Any]:
        """Erstellt eine Statistik der Sprachnotizen"""
        query = self.db.query(Sprachnotiz)

        if projekt_id:
            query = query.filter(Sprachnotiz.projekt_id == projekt_id)

        notizen = query.all()

        gesamt_dauer = sum(n.dauer_sekunden or 0 for n in notizen)

        return {
            'gesamt': len(notizen),
            'transkribiert': len([n for n in notizen if n.transkription]),
            'verifiziert': len([n for n in notizen if n.status == SprachnotizStatus.VERIFIZIERT]),
            'gesamt_dauer_minuten': round(gesamt_dauer / 60, 1),
            'nach_kategorie': self._zaehle_nach_kategorie(notizen)
        }

    def _zaehle_nach_kategorie(self, notizen: List[Sprachnotiz]) -> Dict[str, int]:
        """Zählt Notizen nach Kategorie"""
        zaehler = {}
        for n in notizen:
            kat = n.kategorie.value if n.kategorie else 'SONSTIGE'
            zaehler[kat] = zaehler.get(kat, 0) + 1
        return zaehler

    def simuliere_transkription(self, audio_text: str) -> str:
        """
        Simuliert eine Transkription
        In Produktion: Integration mit Speech-to-Text API (Google, AWS, Azure, Whisper)
        """
        # Simulierte Transkription - in Produktion würde hier eine echte API aufgerufen
        return f"[Automatische Transkription]\n\n{audio_text}\n\n[Ende der Transkription]"

    def text_zu_notiz_konvertieren(
        self,
        projekt_id: int,
        titel: str,
        text: str,
        kategorie: SprachnotizKategorie = SprachnotizKategorie.DIKTAT,
        erstellt_von_user_id: Optional[int] = None
    ) -> Sprachnotiz:
        """Erstellt eine Text-Notiz ohne Audio (für manuelle Eingabe)"""
        notiz = Sprachnotiz(
            projekt_id=projekt_id,
            titel=titel,
            kategorie=kategorie,
            status=SprachnotizStatus.VERIFIZIERT,
            bearbeitet_text=text,
            bearbeitet_am=datetime.now(),
            bearbeitet_von_user_id=erstellt_von_user_id,
            aufgenommen_von_user_id=erstellt_von_user_id
        )

        self.db.add(notiz)
        self.db.flush()

        return notiz


# Vorlagen für Diktat-Textbausteine
DIKTAT_VORLAGEN = {
    'telefonat_eingang': '''Telefonat am {datum} um {uhrzeit}
Gesprächspartner: {partner}
Thema: {thema}

Inhalt:
{inhalt}

Vereinbarungen/To-Dos:
{todos}
''',

    'zeugenbefragung': '''Zeugenbefragung am {datum}
Zeuge: {zeuge}
Ort: {ort}

Aussage:
{aussage}

Bemerkungen:
{bemerkungen}
''',

    'ortstermin': '''Ortstermin am {datum}
Unfallort: {ort}
Anwesende: {anwesende}

Feststellungen:
{feststellungen}

Fotos aufgenommen: {fotos}
''',

    'besprechung': '''Besprechung am {datum}
Teilnehmer: {teilnehmer}
Thema: {thema}

Besprochene Punkte:
{punkte}

Ergebnis/Beschlüsse:
{ergebnis}

Nächste Schritte:
{schritte}
'''
}
