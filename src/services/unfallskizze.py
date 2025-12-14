"""
Unfallskizze-Tool Service
Grafische Darstellung des Unfallhergangs
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
import json
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from src.models.base import Base


class SkizzenElementTyp(str, Enum):
    """Typen von Skizzenelementen"""
    FAHRZEUG = "FAHRZEUG"
    STRASSE = "STRASSE"
    KREUZUNG = "KREUZUNG"
    FUSSGAENGER = "FUSSGAENGER"
    RADFAHRER = "RADFAHRER"
    AMPEL = "AMPEL"
    SCHILD = "SCHILD"
    MARKIERUNG = "MARKIERUNG"
    PFEIL = "PFEIL"
    TEXT = "TEXT"
    BAUM = "BAUM"
    GEBAEUDE = "GEBAEUDE"


class Unfallskizze(Base):
    """Model für Unfallskizzen"""
    __tablename__ = "unfallskizze"

    id = Column(Integer, primary_key=True)

    # Projekt-Zuordnung
    projekt_id = Column(Integer, ForeignKey("unfallprojekt.id"), nullable=False)
    projekt = relationship("UnfallProjekt", backref="unfallskizzen")

    # Skizzen-Daten
    titel = Column(String(200), default="Unfallskizze")
    beschreibung = Column(Text)

    # Canvas-Daten (JSON)
    canvas_breite = Column(Integer, default=800)
    canvas_hoehe = Column(Integer, default=600)
    elemente_json = Column(Text, default="[]")  # JSON-Array der Elemente
    hintergrund_farbe = Column(String(20), default="#f5f5f5")

    # Export
    svg_export = Column(Text)  # SVG-Export für PDF
    png_pfad = Column(String(500))  # Pfad zum PNG-Export

    # Version
    version = Column(Integer, default=1)

    # Metadaten
    erstellt_von_user_id = Column(Integer, ForeignKey("user.id"))
    erstellt_am = Column(DateTime, default=datetime.now)
    aktualisiert_am = Column(DateTime, onupdate=datetime.now)

    @property
    def elemente(self) -> List[Dict[str, Any]]:
        """Parsed die Elemente aus JSON"""
        try:
            return json.loads(self.elemente_json) if self.elemente_json else []
        except json.JSONDecodeError:
            return []

    @elemente.setter
    def elemente(self, wert: List[Dict[str, Any]]):
        """Speichert Elemente als JSON"""
        self.elemente_json = json.dumps(wert)


class UnfallskizzeService:
    """Service für Unfallskizzen-Verwaltung"""

    # Vordefinierte Fahrzeugformen (SVG-Pfade)
    FAHRZEUG_FORMEN = {
        "pkw": {
            "breite": 40,
            "hoehe": 80,
            "farbe": "#3498db",
            "form": "rect"
        },
        "lkw": {
            "breite": 50,
            "hoehe": 120,
            "farbe": "#e74c3c",
            "form": "rect"
        },
        "motorrad": {
            "breite": 20,
            "hoehe": 50,
            "farbe": "#f39c12",
            "form": "rect"
        },
        "fahrrad": {
            "breite": 15,
            "hoehe": 40,
            "farbe": "#27ae60",
            "form": "rect"
        },
        "fussgaenger": {
            "breite": 15,
            "hoehe": 15,
            "farbe": "#9b59b6",
            "form": "circle"
        }
    }

    # Straßenelemente
    STRASSEN_ELEMENTE = {
        "strasse_gerade": {
            "breite": 100,
            "hoehe": 300,
            "farbe": "#7f8c8d"
        },
        "kreuzung": {
            "breite": 150,
            "hoehe": 150,
            "farbe": "#7f8c8d"
        },
        "einmuendung": {
            "breite": 100,
            "hoehe": 100,
            "farbe": "#7f8c8d"
        }
    }

    def __init__(self, db_session):
        self.db = db_session

    def skizze_erstellen(
        self,
        projekt_id: int,
        titel: str = "Unfallskizze",
        beschreibung: Optional[str] = None,
        erstellt_von_user_id: Optional[int] = None
    ) -> Unfallskizze:
        """Erstellt eine neue Unfallskizze"""
        skizze = Unfallskizze(
            projekt_id=projekt_id,
            titel=titel,
            beschreibung=beschreibung,
            erstellt_von_user_id=erstellt_von_user_id
        )
        self.db.add(skizze)
        self.db.flush()
        return skizze

    def skizzen_fuer_projekt(self, projekt_id: int) -> List[Unfallskizze]:
        """Holt alle Skizzen für ein Projekt"""
        return self.db.query(Unfallskizze).filter(
            Unfallskizze.projekt_id == projekt_id
        ).order_by(Unfallskizze.erstellt_am.desc()).all()

    def element_hinzufuegen(
        self,
        skizze_id: int,
        element_typ: SkizzenElementTyp,
        x: int,
        y: int,
        eigenschaften: Optional[Dict[str, Any]] = None
    ) -> Unfallskizze:
        """Fügt ein Element zur Skizze hinzu"""
        skizze = self.db.query(Unfallskizze).get(skizze_id)
        if not skizze:
            raise ValueError("Skizze nicht gefunden")

        elemente = skizze.elemente
        neues_element = {
            "id": len(elemente) + 1,
            "typ": element_typ.value,
            "x": x,
            "y": y,
            "rotation": 0,
            **(eigenschaften or {})
        }

        # Standard-Eigenschaften je nach Typ
        if element_typ == SkizzenElementTyp.FAHRZEUG:
            fahrzeug_typ = eigenschaften.get("fahrzeug_typ", "pkw") if eigenschaften else "pkw"
            form_daten = self.FAHRZEUG_FORMEN.get(fahrzeug_typ, self.FAHRZEUG_FORMEN["pkw"])
            neues_element.update({
                "breite": form_daten["breite"],
                "hoehe": form_daten["hoehe"],
                "farbe": eigenschaften.get("farbe", form_daten["farbe"]) if eigenschaften else form_daten["farbe"],
                "form": form_daten["form"],
                "label": eigenschaften.get("label", "") if eigenschaften else ""
            })

        elif element_typ == SkizzenElementTyp.STRASSE:
            neues_element.update({
                "breite": eigenschaften.get("breite", 100) if eigenschaften else 100,
                "hoehe": eigenschaften.get("hoehe", 300) if eigenschaften else 300,
                "farbe": "#7f8c8d",
                "spuranzahl": eigenschaften.get("spuranzahl", 2) if eigenschaften else 2
            })

        elif element_typ == SkizzenElementTyp.PFEIL:
            neues_element.update({
                "laenge": eigenschaften.get("laenge", 50) if eigenschaften else 50,
                "farbe": eigenschaften.get("farbe", "#e74c3c") if eigenschaften else "#e74c3c",
                "gestrichelt": eigenschaften.get("gestrichelt", False) if eigenschaften else False
            })

        elif element_typ == SkizzenElementTyp.TEXT:
            neues_element.update({
                "text": eigenschaften.get("text", "Text") if eigenschaften else "Text",
                "schriftgroesse": eigenschaften.get("schriftgroesse", 14) if eigenschaften else 14,
                "farbe": eigenschaften.get("farbe", "#000000") if eigenschaften else "#000000"
            })

        elemente.append(neues_element)
        skizze.elemente = elemente
        skizze.version += 1
        skizze.aktualisiert_am = datetime.now()
        self.db.flush()

        return skizze

    def element_aktualisieren(
        self,
        skizze_id: int,
        element_id: int,
        eigenschaften: Dict[str, Any]
    ) -> Unfallskizze:
        """Aktualisiert ein Element"""
        skizze = self.db.query(Unfallskizze).get(skizze_id)
        if not skizze:
            raise ValueError("Skizze nicht gefunden")

        elemente = skizze.elemente
        for element in elemente:
            if element.get("id") == element_id:
                element.update(eigenschaften)
                break

        skizze.elemente = elemente
        skizze.version += 1
        skizze.aktualisiert_am = datetime.now()
        self.db.flush()

        return skizze

    def element_loeschen(self, skizze_id: int, element_id: int) -> Unfallskizze:
        """Löscht ein Element"""
        skizze = self.db.query(Unfallskizze).get(skizze_id)
        if not skizze:
            raise ValueError("Skizze nicht gefunden")

        elemente = [e for e in skizze.elemente if e.get("id") != element_id]
        skizze.elemente = elemente
        skizze.version += 1
        skizze.aktualisiert_am = datetime.now()
        self.db.flush()

        return skizze

    def generiere_svg(self, skizze: Unfallskizze) -> str:
        """Generiert SVG aus der Skizze"""
        svg_parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{skizze.canvas_breite}" height="{skizze.canvas_hoehe}">',
            f'<rect width="100%" height="100%" fill="{skizze.hintergrund_farbe}"/>',
            '<defs>',
            '<marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">',
            '<polygon points="0 0, 10 3.5, 0 7" fill="#e74c3c"/>',
            '</marker>',
            '</defs>'
        ]

        for element in skizze.elemente:
            svg_parts.append(self._element_zu_svg(element))

        svg_parts.append('</svg>')
        return '\n'.join(svg_parts)

    def _element_zu_svg(self, element: Dict[str, Any]) -> str:
        """Konvertiert ein Element zu SVG"""
        typ = element.get("typ")
        x = element.get("x", 0)
        y = element.get("y", 0)
        rotation = element.get("rotation", 0)

        transform = f'transform="rotate({rotation} {x} {y})"' if rotation else ""

        if typ == "FAHRZEUG":
            breite = element.get("breite", 40)
            hoehe = element.get("hoehe", 80)
            farbe = element.get("farbe", "#3498db")
            label = element.get("label", "")

            svg = f'''<g {transform}>
                <rect x="{x - breite/2}" y="{y - hoehe/2}" width="{breite}" height="{hoehe}"
                      fill="{farbe}" stroke="#2c3e50" stroke-width="2" rx="5"/>
                <text x="{x}" y="{y}" text-anchor="middle" dominant-baseline="middle"
                      fill="white" font-size="12">{label}</text>
            </g>'''
            return svg

        elif typ == "STRASSE":
            breite = element.get("breite", 100)
            hoehe = element.get("hoehe", 300)

            svg = f'''<g {transform}>
                <rect x="{x - breite/2}" y="{y - hoehe/2}" width="{breite}" height="{hoehe}"
                      fill="#7f8c8d" stroke="#5d6d7e" stroke-width="1"/>
                <line x1="{x}" y1="{y - hoehe/2}" x2="{x}" y2="{y + hoehe/2}"
                      stroke="white" stroke-width="2" stroke-dasharray="20,10"/>
            </g>'''
            return svg

        elif typ == "PFEIL":
            laenge = element.get("laenge", 50)
            farbe = element.get("farbe", "#e74c3c")
            gestrichelt = element.get("gestrichelt", False)
            dash = 'stroke-dasharray="5,5"' if gestrichelt else ""

            svg = f'''<line x1="{x}" y1="{y}" x2="{x + laenge}" y2="{y}"
                      stroke="{farbe}" stroke-width="3" {dash}
                      marker-end="url(#arrowhead)" {transform}/>'''
            return svg

        elif typ == "TEXT":
            text = element.get("text", "")
            schriftgroesse = element.get("schriftgroesse", 14)
            farbe = element.get("farbe", "#000000")

            svg = f'''<text x="{x}" y="{y}" fill="{farbe}" font-size="{schriftgroesse}"
                      {transform}>{text}</text>'''
            return svg

        elif typ == "AMPEL":
            svg = f'''<g {transform}>
                <rect x="{x - 10}" y="{y - 30}" width="20" height="60" fill="#2c3e50" rx="3"/>
                <circle cx="{x}" cy="{y - 20}" r="6" fill="#e74c3c"/>
                <circle cx="{x}" cy="{y}" r="6" fill="#f39c12"/>
                <circle cx="{x}" cy="{y + 20}" r="6" fill="#27ae60"/>
            </g>'''
            return svg

        elif typ == "FUSSGAENGER":
            farbe = element.get("farbe", "#9b59b6")
            svg = f'<circle cx="{x}" cy="{y}" r="8" fill="{farbe}" {transform}/>'
            return svg

        return ""

    def skizze_loeschen(self, skizze_id: int) -> bool:
        """Löscht eine Skizze"""
        skizze = self.db.query(Unfallskizze).get(skizze_id)
        if skizze:
            self.db.delete(skizze)
            self.db.flush()
            return True
        return False

    def erstelle_standard_kreuzung_skizze(
        self,
        projekt_id: int,
        erstellt_von_user_id: Optional[int] = None
    ) -> Unfallskizze:
        """Erstellt eine Standard-Kreuzungsskizze als Vorlage"""
        skizze = self.skizze_erstellen(
            projekt_id=projekt_id,
            titel="Kreuzung - Vorlage",
            beschreibung="Vorkonfigurierte Kreuzungsskizze",
            erstellt_von_user_id=erstellt_von_user_id
        )

        # Straßen hinzufügen
        elemente = [
            # Vertikale Straße
            {"id": 1, "typ": "STRASSE", "x": 400, "y": 300, "breite": 100, "hoehe": 600, "rotation": 0},
            # Horizontale Straße
            {"id": 2, "typ": "STRASSE", "x": 400, "y": 300, "breite": 100, "hoehe": 800, "rotation": 90},
        ]

        skizze.elemente = elemente
        self.db.flush()

        return skizze
