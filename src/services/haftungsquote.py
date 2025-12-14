"""
Haftungsquoten-Rechner Service
Automatische Einschätzung basierend auf Unfalltyp und BGH-Rechtsprechung
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from decimal import Decimal
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Numeric
from sqlalchemy.orm import relationship
from src.models.base import Base


class UnfallTyp(str, Enum):
    """Typen von Verkehrsunfällen"""
    AUFFAHRUNFALL = "AUFFAHRUNFALL"
    SPURWECHSEL = "SPURWECHSEL"
    VORFAHRT = "VORFAHRT"
    ABBIEGEN = "ABBIEGEN"
    RUECKWAERTS = "RUECKWAERTS"
    PARKPLATZ = "PARKPLATZ"
    KREUZUNG = "KREUZUNG"
    UEBERHOLEN = "UEBERHOLEN"
    TUER_OEFFNEN = "TUER_OEFFNEN"
    FUSSGAENGER = "FUSSGAENGER"
    WILDUNFALL = "WILDUNFALL"
    ALKOHOL = "ALKOHOL"
    GESCHWINDIGKEIT = "GESCHWINDIGKEIT"
    ROTLICHT = "ROTLICHT"
    KETTENREAKTION = "KETTENREAKTION"
    SONSTIGES = "SONSTIGES"


class HaftungsBerechnung(Base):
    """Model für Haftungsberechnungen"""
    __tablename__ = "haftungsberechnung"

    id = Column(Integer, primary_key=True)

    # Projekt-Zuordnung
    projekt_id = Column(Integer, ForeignKey("unfallprojekt.id"), nullable=False)
    projekt = relationship("UnfallProjekt", backref="haftungsberechnungen")

    # Unfalltyp
    unfall_typ = Column(String(50))
    unfall_beschreibung = Column(Text)

    # Beteiligte Faktoren (JSON als Text)
    faktoren_json = Column(Text)

    # Ergebnis
    haftungsquote_eigenes_fahrzeug = Column(Numeric(5, 2))  # 0-100%
    haftungsquote_gegner = Column(Numeric(5, 2))  # 0-100%
    begruendung = Column(Text)

    # Rechtsprechung
    relevante_urteile = Column(Text)  # JSON-Liste

    # Metadaten
    erstellt_von_user_id = Column(Integer, ForeignKey("user.id"))
    erstellt_am = Column(DateTime, default=datetime.now)


class HaftungsquoteService:
    """Service für Haftungsquoten-Berechnung"""

    # Basis-Haftungsquoten nach Unfalltyp (Erfahrungswerte)
    BASIS_HAFTUNG = {
        UnfallTyp.AUFFAHRUNFALL: {
            "auffahrender": 100,
            "vorausfahrender": 0,
            "beschreibung": "Der Auffahrende haftet grundsätzlich allein (BGH, Urteil vom 13.12.2016 - VI ZR 32/16)"
        },
        UnfallTyp.SPURWECHSEL: {
            "spurwechsler": 100,
            "geradeausfahrer": 0,
            "beschreibung": "Wer die Spur wechselt, muss sich vergewissern, dass dies gefahrlos möglich ist (§ 7 Abs. 5 StVO)"
        },
        UnfallTyp.VORFAHRT: {
            "wartepflichtiger": 100,
            "vorfahrtsberechtigter": 0,
            "beschreibung": "Der Wartepflichtige haftet grundsätzlich allein bei Vorfahrtsverletzung"
        },
        UnfallTyp.ABBIEGEN: {
            "abbiegender": 70,
            "geradeausfahrer": 30,
            "beschreibung": "Der Abbiegende hat erhöhte Sorgfaltspflichten (§ 9 StVO)"
        },
        UnfallTyp.RUECKWAERTS: {
            "rueckwaertsfahrer": 100,
            "anderer": 0,
            "beschreibung": "Rückwärtsfahren erfordert höchste Sorgfalt (§ 9 Abs. 5 StVO)"
        },
        UnfallTyp.PARKPLATZ: {
            "seite_a": 50,
            "seite_b": 50,
            "beschreibung": "Auf Parkplätzen gilt oft die 50/50-Haftung mangels klarer Vorfahrtsregeln"
        },
        UnfallTyp.KREUZUNG: {
            "rechts_vor_links_verletzender": 100,
            "von_rechts_kommender": 0,
            "beschreibung": "Rechts vor Links gilt, wenn keine anderen Regelungen (§ 8 StVO)"
        },
        UnfallTyp.UEBERHOLEN: {
            "ueberholender": 80,
            "ueberholter": 20,
            "beschreibung": "Der Überholende trägt erhöhte Verantwortung (§ 5 StVO)"
        },
        UnfallTyp.TUER_OEFFNEN: {
            "tuer_oeffnender": 100,
            "vorbeifahrender": 0,
            "beschreibung": "Wer eine Fahrzeugtür öffnet, muss den Verkehr beachten (§ 14 StVO)"
        },
        UnfallTyp.ROTLICHT: {
            "rotlichtfahrer": 100,
            "gruenlichtfahrer": 0,
            "beschreibung": "Rotlichtverstoß begründet volle Haftung"
        }
    }

    # Modifikatoren für die Haftungsquote
    MODIFIKATOREN = {
        "alkohol": {"beschreibung": "Alkoholeinfluss", "aenderung": 20},
        "geschwindigkeit": {"beschreibung": "Geschwindigkeitsüberschreitung", "aenderung": 15},
        "handy": {"beschreibung": "Handynutzung", "aenderung": 15},
        "kein_gurt": {"beschreibung": "Nicht angeschnallt", "aenderung": 10},
        "mangelhaftes_fahrzeug": {"beschreibung": "Mangelhafter Fahrzeugzustand", "aenderung": 10},
        "dunkelheit_ohne_licht": {"beschreibung": "Fahren ohne Licht bei Dunkelheit", "aenderung": 15},
        "kind": {"beschreibung": "Kind als Unfallbeteiligter (Schutzminderung)", "aenderung": -20},
        "betriebsgefahr": {"beschreibung": "Betriebsgefahr (§ 7 StVG)", "aenderung": 25},
        "unaufklaerbar": {"beschreibung": "Unaufklärbarer Unfallhergang", "aenderung": 0},
    }

    # Relevante BGH-Urteile
    RECHTSPRECHUNG = {
        UnfallTyp.AUFFAHRUNFALL: [
            {
                "gericht": "BGH",
                "aktenzeichen": "VI ZR 32/16",
                "datum": "13.12.2016",
                "leitsatz": "Anscheinsbeweis für Verschulden des Auffahrenden"
            },
            {
                "gericht": "BGH",
                "aktenzeichen": "VI ZR 138/11",
                "datum": "13.12.2011",
                "leitsatz": "Auffahrunfall auf der Autobahn - grundlose Vollbremsung des Vorausfahrenden kann Mithaftung begründen"
            }
        ],
        UnfallTyp.SPURWECHSEL: [
            {
                "gericht": "BGH",
                "aktenzeichen": "VI ZR 218/13",
                "datum": "08.04.2014",
                "leitsatz": "Erhöhte Sorgfaltspflicht beim Spurwechsel"
            }
        ],
        UnfallTyp.PARKPLATZ: [
            {
                "gericht": "BGH",
                "aktenzeichen": "VI ZR 6/12",
                "datum": "15.01.2013",
                "leitsatz": "Parkplatzsituation erfordert besondere Rücksichtnahme beider Beteiligter"
            }
        ],
        UnfallTyp.RUECKWAERTS: [
            {
                "gericht": "BGH",
                "aktenzeichen": "VI ZR 115/06",
                "datum": "26.09.2006",
                "leitsatz": "Rückwärtsfahrer haftet grundsätzlich allein"
            }
        ]
    }

    def __init__(self, db_session):
        self.db = db_session

    def berechne_haftungsquote(
        self,
        projekt_id: int,
        unfall_typ: UnfallTyp,
        ist_hauptverursacher: bool = False,
        zusatz_faktoren: Optional[List[str]] = None,
        beschreibung: Optional[str] = None,
        erstellt_von_user_id: Optional[int] = None
    ) -> HaftungsBerechnung:
        """Berechnet die Haftungsquote basierend auf Unfalltyp und Faktoren"""

        # Basis-Haftung
        basis = self.BASIS_HAFTUNG.get(unfall_typ, {
            "seite_a": 50,
            "seite_b": 50,
            "beschreibung": "Keine typische Konstellation - Einzelfallprüfung erforderlich"
        })

        # Startquote je nach Rolle
        if ist_hauptverursacher:
            eigene_quote = Decimal(str(list(basis.values())[0]))
        else:
            eigene_quote = Decimal(str(list(basis.values())[1]))

        # Modifikatoren anwenden
        modifikator_beschreibungen = []

        if zusatz_faktoren:
            for faktor in zusatz_faktoren:
                if faktor in self.MODIFIKATOREN:
                    mod = self.MODIFIKATOREN[faktor]
                    if ist_hauptverursacher:
                        eigene_quote = min(100, eigene_quote + mod["aenderung"])
                    else:
                        eigene_quote = min(100, max(0, eigene_quote + mod["aenderung"]))
                    modifikator_beschreibungen.append(
                        f"- {mod['beschreibung']}: {mod['aenderung']:+d}%"
                    )

        # Quote auf 0-100 begrenzen
        eigene_quote = max(0, min(100, eigene_quote))
        gegner_quote = 100 - eigene_quote

        # Begründung zusammenstellen
        begruendung = f"""
HAFTUNGSQUOTEN-BERECHNUNG

Unfalltyp: {self._unfall_typ_anzeige(unfall_typ)}

Basis-Einschätzung:
{basis.get('beschreibung', '')}

{"Angewendete Modifikatoren:" if modifikator_beschreibungen else "Keine zusätzlichen Modifikatoren."}
{chr(10).join(modifikator_beschreibungen)}

ERGEBNIS:
Haftungsquote eigenes Fahrzeug: {eigene_quote}%
Haftungsquote Unfallgegner: {gegner_quote}%

Hinweis: Diese Berechnung dient als Orientierung. Die endgültige
Haftungsverteilung hängt von den konkreten Umständen des Einzelfalls ab.
"""

        # Relevante Urteile
        urteile = self.RECHTSPRECHUNG.get(unfall_typ, [])
        import json

        # Berechnung speichern
        berechnung = HaftungsBerechnung(
            projekt_id=projekt_id,
            unfall_typ=unfall_typ.value,
            unfall_beschreibung=beschreibung,
            faktoren_json=json.dumps(zusatz_faktoren or []),
            haftungsquote_eigenes_fahrzeug=eigene_quote,
            haftungsquote_gegner=gegner_quote,
            begruendung=begruendung,
            relevante_urteile=json.dumps(urteile),
            erstellt_von_user_id=erstellt_von_user_id
        )

        self.db.add(berechnung)
        self.db.flush()

        return berechnung

    def berechnungen_fuer_projekt(self, projekt_id: int) -> List[HaftungsBerechnung]:
        """Holt alle Haftungsberechnungen für ein Projekt"""
        return self.db.query(HaftungsBerechnung).filter(
            HaftungsBerechnung.projekt_id == projekt_id
        ).order_by(HaftungsBerechnung.erstellt_am.desc()).all()

    def _unfall_typ_anzeige(self, typ: UnfallTyp) -> str:
        """Gibt den Anzeigetext für einen Unfalltyp zurück"""
        return {
            UnfallTyp.AUFFAHRUNFALL: "Auffahrunfall",
            UnfallTyp.SPURWECHSEL: "Spurwechselunfall",
            UnfallTyp.VORFAHRT: "Vorfahrtsverletzung",
            UnfallTyp.ABBIEGEN: "Abbiegeunfall",
            UnfallTyp.RUECKWAERTS: "Rückwärtsfahren",
            UnfallTyp.PARKPLATZ: "Parkplatzunfall",
            UnfallTyp.KREUZUNG: "Kreuzungsunfall",
            UnfallTyp.UEBERHOLEN: "Überholunfall",
            UnfallTyp.TUER_OEFFNEN: "Türöffnungsunfall",
            UnfallTyp.FUSSGAENGER: "Fußgängerunfall",
            UnfallTyp.WILDUNFALL: "Wildunfall",
            UnfallTyp.ALKOHOL: "Alkoholunfall",
            UnfallTyp.GESCHWINDIGKEIT: "Geschwindigkeitsunfall",
            UnfallTyp.ROTLICHT: "Rotlichtverstoß",
            UnfallTyp.KETTENREAKTION: "Kettenreaktion/Massenkarambolage",
            UnfallTyp.SONSTIGES: "Sonstiger Unfall"
        }.get(typ, "Unbekannt")

    def get_alle_unfalltypen(self) -> List[Dict[str, str]]:
        """Gibt alle Unfalltypen mit Beschreibung zurück"""
        return [
            {"wert": t.value, "anzeige": self._unfall_typ_anzeige(t)}
            for t in UnfallTyp
        ]

    def get_alle_modifikatoren(self) -> List[Dict[str, Any]]:
        """Gibt alle verfügbaren Modifikatoren zurück"""
        return [
            {
                "code": code,
                "beschreibung": mod["beschreibung"],
                "aenderung": mod["aenderung"]
            }
            for code, mod in self.MODIFIKATOREN.items()
        ]

    def suche_rechtsprechung(self, suchbegriff: str) -> List[Dict[str, Any]]:
        """Durchsucht die Rechtsprechungsdatenbank"""
        ergebnisse = []
        suchbegriff_lower = suchbegriff.lower()

        for typ, urteile in self.RECHTSPRECHUNG.items():
            for urteil in urteile:
                if (suchbegriff_lower in urteil.get("leitsatz", "").lower() or
                    suchbegriff_lower in urteil.get("aktenzeichen", "").lower()):
                    ergebnisse.append({
                        **urteil,
                        "unfalltyp": self._unfall_typ_anzeige(typ)
                    })

        return ergebnisse
