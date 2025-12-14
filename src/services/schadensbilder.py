"""
Schadensbilder-Galerie Service
Organisierte Bildverwaltung für Unfallfotos
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
import json
import os
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from src.models.base import Base


class BildKategorie(str, Enum):
    """Kategorien für Schadensbilder"""
    UNFALLORT = "UNFALLORT"
    FAHRZEUG_VORNE = "FAHRZEUG_VORNE"
    FAHRZEUG_HINTEN = "FAHRZEUG_HINTEN"
    FAHRZEUG_LINKS = "FAHRZEUG_LINKS"
    FAHRZEUG_RECHTS = "FAHRZEUG_RECHTS"
    SCHADEN_DETAIL = "SCHADEN_DETAIL"
    INNENRAUM = "INNENRAUM"
    MOTORRAUM = "MOTORRAUM"
    VORHER = "VORHER"
    NACHHER = "NACHHER"
    REPARATUR = "REPARATUR"
    GUTACHTEN = "GUTACHTEN"
    SONSTIGES = "SONSTIGES"


class Schadensbild(Base):
    """Model für Schadensbilder"""
    __tablename__ = "schadensbild"

    id = Column(Integer, primary_key=True)

    # Projekt-Zuordnung
    projekt_id = Column(Integer, ForeignKey("unfallprojekt.id"), nullable=False)
    projekt = relationship("UnfallProjekt", backref="schadensbilder")

    # Dokument-Referenz (wenn über Dokumentensystem hochgeladen)
    dokument_id = Column(Integer, ForeignKey("dokument.id"))

    # Bild-Daten
    dateiname = Column(String(255), nullable=False)
    original_dateiname = Column(String(255))
    dateipfad = Column(String(500), nullable=False)
    thumbnail_pfad = Column(String(500))
    dateityp = Column(String(50))  # image/jpeg, image/png, etc.
    dateigroesse = Column(Integer)  # in Bytes

    # Kategorisierung
    kategorie = Column(SQLEnum(BildKategorie), default=BildKategorie.SONSTIGES)
    beschreibung = Column(Text)
    tags = Column(String(500))  # Komma-separierte Tags

    # Position/Reihenfolge
    sortierung = Column(Integer, default=0)

    # Aufnahmedaten
    aufnahme_datum = Column(DateTime)
    aufnahme_ort = Column(String(200))
    gps_koordinaten = Column(String(50))  # lat,lon

    # EXIF-Daten (JSON)
    exif_daten_json = Column(Text)

    # Markierungen auf dem Bild (JSON)
    markierungen_json = Column(Text)

    # Verknüpfung
    ist_vorher_bild = Column(Boolean, default=False)
    nachher_bild_id = Column(Integer, ForeignKey("schadensbild.id"))

    # Metadaten
    hochgeladen_von_user_id = Column(Integer, ForeignKey("user.id"))
    erstellt_am = Column(DateTime, default=datetime.now)
    aktualisiert_am = Column(DateTime, onupdate=datetime.now)

    @property
    def kategorie_anzeige(self) -> str:
        """Anzeigetext für Kategorie"""
        return {
            BildKategorie.UNFALLORT: "📍 Unfallort",
            BildKategorie.FAHRZEUG_VORNE: "🚗 Fahrzeug vorne",
            BildKategorie.FAHRZEUG_HINTEN: "🚗 Fahrzeug hinten",
            BildKategorie.FAHRZEUG_LINKS: "🚗 Fahrzeug links",
            BildKategorie.FAHRZEUG_RECHTS: "🚗 Fahrzeug rechts",
            BildKategorie.SCHADEN_DETAIL: "🔍 Schadensdetail",
            BildKategorie.INNENRAUM: "🪑 Innenraum",
            BildKategorie.MOTORRAUM: "⚙️ Motorraum",
            BildKategorie.VORHER: "⬅️ Vorher",
            BildKategorie.NACHHER: "➡️ Nachher",
            BildKategorie.REPARATUR: "🔧 Reparatur",
            BildKategorie.GUTACHTEN: "📋 Gutachten",
            BildKategorie.SONSTIGES: "📷 Sonstiges"
        }.get(self.kategorie, "📷 Bild")

    @property
    def exif_daten(self) -> Dict[str, Any]:
        """Parsed die EXIF-Daten"""
        try:
            return json.loads(self.exif_daten_json) if self.exif_daten_json else {}
        except json.JSONDecodeError:
            return {}

    @exif_daten.setter
    def exif_daten(self, wert: Dict[str, Any]):
        """Speichert EXIF-Daten als JSON"""
        self.exif_daten_json = json.dumps(wert)

    @property
    def markierungen(self) -> List[Dict[str, Any]]:
        """Parsed die Markierungen"""
        try:
            return json.loads(self.markierungen_json) if self.markierungen_json else []
        except json.JSONDecodeError:
            return []

    @markierungen.setter
    def markierungen(self, wert: List[Dict[str, Any]]):
        """Speichert Markierungen als JSON"""
        self.markierungen_json = json.dumps(wert)

    @property
    def dateigroesse_anzeige(self) -> str:
        """Formatierte Dateigröße"""
        if not self.dateigroesse:
            return "-"
        if self.dateigroesse < 1024:
            return f"{self.dateigroesse} B"
        elif self.dateigroesse < 1024 * 1024:
            return f"{self.dateigroesse / 1024:.1f} KB"
        else:
            return f"{self.dateigroesse / 1024 / 1024:.1f} MB"


class SchadensbilderService:
    """Service für Schadensbilder-Verwaltung"""

    ERLAUBTE_DATEITYPEN = [
        "image/jpeg", "image/jpg", "image/png",
        "image/gif", "image/webp", "image/bmp"
    ]

    def __init__(self, db_session):
        self.db = db_session

    def bild_hinzufuegen(
        self,
        projekt_id: int,
        dateiname: str,
        dateipfad: str,
        kategorie: BildKategorie = BildKategorie.SONSTIGES,
        beschreibung: Optional[str] = None,
        hochgeladen_von_user_id: Optional[int] = None,
        **kwargs
    ) -> Schadensbild:
        """Fügt ein neues Schadensbild hinzu"""
        # Dateigröße ermitteln
        dateigroesse = None
        if os.path.exists(dateipfad):
            dateigroesse = os.path.getsize(dateipfad)

        # Dateityp ermitteln
        import mimetypes
        dateityp, _ = mimetypes.guess_type(dateiname)

        bild = Schadensbild(
            projekt_id=projekt_id,
            dateiname=dateiname,
            original_dateiname=dateiname,
            dateipfad=dateipfad,
            dateityp=dateityp,
            dateigroesse=dateigroesse,
            kategorie=kategorie,
            beschreibung=beschreibung,
            hochgeladen_von_user_id=hochgeladen_von_user_id,
            **kwargs
        )

        self.db.add(bild)
        self.db.flush()

        return bild

    def bilder_fuer_projekt(
        self,
        projekt_id: int,
        kategorie: Optional[BildKategorie] = None
    ) -> List[Schadensbild]:
        """Holt alle Bilder für ein Projekt"""
        query = self.db.query(Schadensbild).filter(
            Schadensbild.projekt_id == projekt_id
        )

        if kategorie:
            query = query.filter(Schadensbild.kategorie == kategorie)

        return query.order_by(
            Schadensbild.kategorie,
            Schadensbild.sortierung,
            Schadensbild.erstellt_am
        ).all()

    def bilder_nach_kategorie(self, projekt_id: int) -> Dict[BildKategorie, List[Schadensbild]]:
        """Gruppiert Bilder nach Kategorie"""
        bilder = self.bilder_fuer_projekt(projekt_id)

        gruppiert = {}
        for bild in bilder:
            if bild.kategorie not in gruppiert:
                gruppiert[bild.kategorie] = []
            gruppiert[bild.kategorie].append(bild)

        return gruppiert

    def bild_kategorisieren(
        self,
        bild_id: int,
        kategorie: BildKategorie,
        beschreibung: Optional[str] = None
    ) -> Optional[Schadensbild]:
        """Kategorisiert ein Bild"""
        bild = self.db.query(Schadensbild).get(bild_id)

        if bild:
            bild.kategorie = kategorie
            if beschreibung:
                bild.beschreibung = beschreibung
            bild.aktualisiert_am = datetime.now()
            self.db.flush()

        return bild

    def markierung_hinzufuegen(
        self,
        bild_id: int,
        x: int,
        y: int,
        text: str,
        farbe: str = "#ff0000"
    ) -> Optional[Schadensbild]:
        """Fügt eine Markierung zu einem Bild hinzu"""
        bild = self.db.query(Schadensbild).get(bild_id)

        if bild:
            markierungen = bild.markierungen
            markierungen.append({
                "id": len(markierungen) + 1,
                "x": x,
                "y": y,
                "text": text,
                "farbe": farbe
            })
            bild.markierungen = markierungen
            bild.aktualisiert_am = datetime.now()
            self.db.flush()

        return bild

    def vorher_nachher_verknuepfen(
        self,
        vorher_bild_id: int,
        nachher_bild_id: int
    ) -> bool:
        """Verknüpft ein Vorher- mit einem Nachher-Bild"""
        vorher_bild = self.db.query(Schadensbild).get(vorher_bild_id)
        nachher_bild = self.db.query(Schadensbild).get(nachher_bild_id)

        if vorher_bild and nachher_bild:
            vorher_bild.ist_vorher_bild = True
            vorher_bild.nachher_bild_id = nachher_bild_id
            vorher_bild.kategorie = BildKategorie.VORHER
            nachher_bild.kategorie = BildKategorie.NACHHER
            self.db.flush()
            return True

        return False

    def bild_loeschen(self, bild_id: int, auch_datei: bool = False) -> bool:
        """Löscht ein Schadensbild"""
        bild = self.db.query(Schadensbild).get(bild_id)

        if bild:
            if auch_datei and os.path.exists(bild.dateipfad):
                os.remove(bild.dateipfad)
                if bild.thumbnail_pfad and os.path.exists(bild.thumbnail_pfad):
                    os.remove(bild.thumbnail_pfad)

            self.db.delete(bild)
            self.db.flush()
            return True

        return False

    def sortierung_aktualisieren(self, bild_ids: List[int]) -> bool:
        """Aktualisiert die Sortierung der Bilder"""
        for index, bild_id in enumerate(bild_ids):
            bild = self.db.query(Schadensbild).get(bild_id)
            if bild:
                bild.sortierung = index

        self.db.flush()
        return True

    def galerie_statistik(self, projekt_id: int) -> Dict[str, Any]:
        """Erstellt Statistiken zur Bildergalerie"""
        bilder = self.bilder_fuer_projekt(projekt_id)

        gesamt_groesse = sum(b.dateigroesse or 0 for b in bilder)
        kategorien = {}

        for bild in bilder:
            kat = bild.kategorie.value
            if kat not in kategorien:
                kategorien[kat] = 0
            kategorien[kat] += 1

        return {
            "anzahl_bilder": len(bilder),
            "gesamt_groesse": gesamt_groesse,
            "gesamt_groesse_anzeige": self._formatiere_groesse(gesamt_groesse),
            "nach_kategorie": kategorien,
            "vorher_nachher_paare": len([b for b in bilder if b.ist_vorher_bild])
        }

    def _formatiere_groesse(self, bytes_wert: int) -> str:
        """Formatiert Bytes in lesbare Größe"""
        if bytes_wert < 1024:
            return f"{bytes_wert} B"
        elif bytes_wert < 1024 * 1024:
            return f"{bytes_wert / 1024:.1f} KB"
        elif bytes_wert < 1024 * 1024 * 1024:
            return f"{bytes_wert / 1024 / 1024:.1f} MB"
        else:
            return f"{bytes_wert / 1024 / 1024 / 1024:.1f} GB"

    def importiere_von_dokument(
        self,
        dokument_id: int,
        kategorie: BildKategorie = BildKategorie.SONSTIGES
    ) -> Optional[Schadensbild]:
        """Importiert ein Bild aus dem Dokumentensystem"""
        from src.models import Dokument

        dokument = self.db.query(Dokument).get(dokument_id)

        if not dokument:
            return None

        # Prüfe ob es ein Bild ist
        import mimetypes
        dateityp, _ = mimetypes.guess_type(dokument.original_dateiname)

        if dateityp not in self.ERLAUBTE_DATEITYPEN:
            return None

        bild = Schadensbild(
            projekt_id=dokument.projekt_id,
            dokument_id=dokument.id,
            dateiname=dokument.original_dateiname,
            original_dateiname=dokument.original_dateiname,
            dateipfad=dokument.dateipfad,
            dateityp=dateityp,
            kategorie=kategorie,
            hochgeladen_von_user_id=dokument.hochgeladen_von_user_id
        )

        self.db.add(bild)
        self.db.flush()

        return bild
