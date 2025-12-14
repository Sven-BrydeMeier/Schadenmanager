"""
Schmerzensgeldrechner basierend auf Verletzungsart und Heilungsdauer
"""
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Tuple
from datetime import date


class SchmerzensgeldRechner:
    """
    Berechnet Schmerzensgeld basierend auf verschiedenen Faktoren.

    Die Berechnung orientiert sich an der Rechtsprechung und
    einschlägigen Schmerzensgeldtabellen (z.B. Hacks/Wellner/Häcker).
    """

    # Basisbeträge nach Verletzungskategorie (Richtwerte in EUR)
    VERLETZUNGS_KATEGORIEN = {
        "hws_leicht": {
            "name": "HWS-Distorsion (leicht)",
            "beschreibung": "HWS-Schleudertrauma Grad I, Beschwerden bis 4 Wochen",
            "min_betrag": 300,
            "max_betrag": 1500,
            "basis": 800,
        },
        "hws_mittel": {
            "name": "HWS-Distorsion (mittel)",
            "beschreibung": "HWS-Schleudertrauma Grad II, Beschwerden 4-12 Wochen",
            "min_betrag": 1000,
            "max_betrag": 4000,
            "basis": 2500,
        },
        "hws_schwer": {
            "name": "HWS-Distorsion (schwer)",
            "beschreibung": "HWS-Schleudertrauma Grad III, dauerhafte Beschwerden",
            "min_betrag": 3000,
            "max_betrag": 15000,
            "basis": 7000,
        },
        "prellung_leicht": {
            "name": "Prellungen (leicht)",
            "beschreibung": "Leichte Prellungen, schnelle Heilung",
            "min_betrag": 200,
            "max_betrag": 1000,
            "basis": 500,
        },
        "prellung_schwer": {
            "name": "Prellungen (schwer)",
            "beschreibung": "Schwere Prellungen mit längerer Heilungsdauer",
            "min_betrag": 500,
            "max_betrag": 2500,
            "basis": 1200,
        },
        "schnittwunde": {
            "name": "Schnittwunden",
            "beschreibung": "Schnittwunden ohne bleibende Narben",
            "min_betrag": 300,
            "max_betrag": 1500,
            "basis": 700,
        },
        "narben_gesicht": {
            "name": "Narben im Gesicht",
            "beschreibung": "Sichtbare Narben im Gesichtsbereich",
            "min_betrag": 2000,
            "max_betrag": 25000,
            "basis": 8000,
        },
        "knochenbruch_einfach": {
            "name": "Knochenbruch (einfach)",
            "beschreibung": "Einfacher Bruch ohne Komplikationen",
            "min_betrag": 2000,
            "max_betrag": 8000,
            "basis": 4000,
        },
        "knochenbruch_kompliziert": {
            "name": "Knochenbruch (kompliziert)",
            "beschreibung": "Komplizierter Bruch mit OP, längere Heilung",
            "min_betrag": 5000,
            "max_betrag": 20000,
            "basis": 10000,
        },
        "knochenbruch_mehrfach": {
            "name": "Mehrfache Knochenbrüche",
            "beschreibung": "Mehrere Knochenbrüche",
            "min_betrag": 10000,
            "max_betrag": 50000,
            "basis": 25000,
        },
        "gehirnerschuetterung_leicht": {
            "name": "Gehirnerschütterung (leicht)",
            "beschreibung": "Leichte Gehirnerschütterung ohne Folgen",
            "min_betrag": 500,
            "max_betrag": 2500,
            "basis": 1200,
        },
        "gehirnerschuetterung_schwer": {
            "name": "Schädel-Hirn-Trauma",
            "beschreibung": "Schweres Schädel-Hirn-Trauma",
            "min_betrag": 10000,
            "max_betrag": 100000,
            "basis": 35000,
        },
        "wirbelsaeule_leicht": {
            "name": "Wirbelsäulenverletzung (leicht)",
            "beschreibung": "Leichte Wirbelsäulenverletzung",
            "min_betrag": 2000,
            "max_betrag": 10000,
            "basis": 5000,
        },
        "wirbelsaeule_schwer": {
            "name": "Wirbelsäulenverletzung (schwer)",
            "beschreibung": "Schwere Wirbelsäulenverletzung mit Dauerfolgen",
            "min_betrag": 15000,
            "max_betrag": 150000,
            "basis": 50000,
        },
        "querschnitt": {
            "name": "Querschnittslähmung",
            "beschreibung": "Querschnittslähmung (teil/vollständig)",
            "min_betrag": 150000,
            "max_betrag": 600000,
            "basis": 300000,
        },
        "innere_verletzungen": {
            "name": "Innere Verletzungen",
            "beschreibung": "Verletzungen innerer Organe",
            "min_betrag": 5000,
            "max_betrag": 50000,
            "basis": 15000,
        },
        "amputation_finger": {
            "name": "Amputation (Finger)",
            "beschreibung": "Verlust eines oder mehrerer Finger",
            "min_betrag": 5000,
            "max_betrag": 40000,
            "basis": 15000,
        },
        "amputation_gliedmasse": {
            "name": "Amputation (Gliedmaße)",
            "beschreibung": "Verlust einer Gliedmaße",
            "min_betrag": 50000,
            "max_betrag": 250000,
            "basis": 120000,
        },
        "psychisch_leicht": {
            "name": "Psychische Folgen (leicht)",
            "beschreibung": "Leichte psychische Beeinträchtigung, Angststörung",
            "min_betrag": 500,
            "max_betrag": 5000,
            "basis": 2000,
        },
        "psychisch_schwer": {
            "name": "Psychische Folgen (schwer)",
            "beschreibung": "PTBS, schwere Depression nach Unfall",
            "min_betrag": 5000,
            "max_betrag": 50000,
            "basis": 15000,
        },
        "todesfall": {
            "name": "Todesfall (Hinterbliebenengeld)",
            "beschreibung": "Hinterbliebenengeld bei Todesfall",
            "min_betrag": 10000,
            "max_betrag": 30000,
            "basis": 15000,
        },
    }

    # Faktoren für die Berechnung
    FAKTOREN = {
        "heilungsdauer": {
            "bis_1_woche": 0.7,
            "1_bis_4_wochen": 0.9,
            "1_bis_3_monate": 1.0,
            "3_bis_6_monate": 1.2,
            "6_bis_12_monate": 1.4,
            "ueber_12_monate": 1.6,
            "dauerhaft": 2.0,
        },
        "alter": {
            "kind": 1.3,        # Kinder bekommen tendenziell mehr
            "jung": 1.1,       # 18-30 Jahre
            "mittel": 1.0,     # 30-60 Jahre
            "aelter": 0.9,     # über 60 Jahre
        },
        "beruf_beeintraechtigung": {
            "keine": 1.0,
            "leicht": 1.1,
            "mittel": 1.2,
            "schwer": 1.4,
            "berufsunfaehig": 1.8,
        },
        "mitverschulden": {
            0: 1.0,
            10: 0.9,
            20: 0.8,
            30: 0.7,
            40: 0.6,
            50: 0.5,
        },
    }

    def get_verletzungskategorien(self) -> Dict:
        """Gibt alle Verletzungskategorien zurück"""
        return self.VERLETZUNGS_KATEGORIEN

    def berechne_schmerzensgeld(
        self,
        verletzungen: List[str],
        heilungsdauer: str = "1_bis_3_monate",
        alter_kategorie: str = "mittel",
        beruf_beeintraechtigung: str = "keine",
        mitverschulden_prozent: int = 0,
        krankenhausaufenthalt_tage: int = 0,
        operationen: int = 0,
        dauerfolgen: bool = False
    ) -> Dict:
        """
        Berechnet das Schmerzensgeld.

        Args:
            verletzungen: Liste der Verletzungskategorien
            heilungsdauer: Dauer der Heilung
            alter_kategorie: Alterskategorie des Geschädigten
            beruf_beeintraechtigung: Beeinträchtigung im Beruf
            mitverschulden_prozent: Mitverschulden des Geschädigten in %
            krankenhausaufenthalt_tage: Tage im Krankenhaus
            operationen: Anzahl der Operationen
            dauerfolgen: Ob Dauerfolgen vorliegen

        Returns:
            Dictionary mit Berechnungsergebnis
        """
        if not verletzungen:
            return {
                "basis_betrag": Decimal("0"),
                "faktoren": {},
                "gesamtfaktor": 1.0,
                "empfehlung_min": Decimal("0"),
                "empfehlung_max": Decimal("0"),
                "empfehlung": Decimal("0"),
                "verletzungen_details": [],
                "hinweise": ["Keine Verletzungen angegeben"]
            }

        # Basisbetrag berechnen (Summe der Einzelverletzungen mit Abzug für Mehrfachverletzungen)
        verletzungen_details = []
        basis_gesamt = Decimal("0")
        min_gesamt = Decimal("0")
        max_gesamt = Decimal("0")

        for i, verletzung in enumerate(verletzungen):
            if verletzung in self.VERLETZUNGS_KATEGORIEN:
                kat = self.VERLETZUNGS_KATEGORIEN[verletzung]
                # Bei mehreren Verletzungen: erste 100%, weitere mit Abschlag
                faktor = 1.0 if i == 0 else 0.5
                basis = Decimal(str(kat["basis"])) * Decimal(str(faktor))
                basis_gesamt += basis
                min_gesamt += Decimal(str(kat["min_betrag"])) * Decimal(str(faktor))
                max_gesamt += Decimal(str(kat["max_betrag"])) * Decimal(str(faktor))

                verletzungen_details.append({
                    "kategorie": verletzung,
                    "name": kat["name"],
                    "beschreibung": kat["beschreibung"],
                    "basis": float(basis),
                    "faktor": faktor,
                })

        # Faktoren anwenden
        faktoren_angewandt = {}

        # Heilungsdauer
        heilung_faktor = self.FAKTOREN["heilungsdauer"].get(heilungsdauer, 1.0)
        faktoren_angewandt["heilungsdauer"] = {
            "wert": heilung_faktor,
            "beschreibung": f"Heilungsdauer: {heilungsdauer.replace('_', ' ')}"
        }

        # Alter
        alter_faktor = self.FAKTOREN["alter"].get(alter_kategorie, 1.0)
        faktoren_angewandt["alter"] = {
            "wert": alter_faktor,
            "beschreibung": f"Alterskategorie: {alter_kategorie}"
        }

        # Beruf
        beruf_faktor = self.FAKTOREN["beruf_beeintraechtigung"].get(beruf_beeintraechtigung, 1.0)
        faktoren_angewandt["beruf"] = {
            "wert": beruf_faktor,
            "beschreibung": f"Berufliche Beeinträchtigung: {beruf_beeintraechtigung}"
        }

        # Krankenhausaufenthalt (+ 50€ pro Tag)
        kh_zuschlag = Decimal(str(krankenhausaufenthalt_tage * 50))
        if krankenhausaufenthalt_tage > 0:
            faktoren_angewandt["krankenhaus"] = {
                "wert": f"+{float(kh_zuschlag):.2f}€",
                "beschreibung": f"Krankenhausaufenthalt: {krankenhausaufenthalt_tage} Tage"
            }

        # Operationen (+ 500€ pro OP)
        op_zuschlag = Decimal(str(operationen * 500))
        if operationen > 0:
            faktoren_angewandt["operationen"] = {
                "wert": f"+{float(op_zuschlag):.2f}€",
                "beschreibung": f"Operationen: {operationen}"
            }

        # Dauerfolgen
        dauerfolgen_faktor = 1.5 if dauerfolgen else 1.0
        if dauerfolgen:
            faktoren_angewandt["dauerfolgen"] = {
                "wert": dauerfolgen_faktor,
                "beschreibung": "Dauerhafte Folgen"
            }

        # Mitverschulden
        mv_faktor = self.FAKTOREN["mitverschulden"].get(mitverschulden_prozent, 1.0 - mitverschulden_prozent/100)
        if mitverschulden_prozent > 0:
            faktoren_angewandt["mitverschulden"] = {
                "wert": mv_faktor,
                "beschreibung": f"Mitverschulden: {mitverschulden_prozent}%"
            }

        # Gesamtfaktor berechnen
        gesamtfaktor = heilung_faktor * alter_faktor * beruf_faktor * dauerfolgen_faktor * mv_faktor

        # Endbetrag berechnen
        empfehlung = (basis_gesamt * Decimal(str(gesamtfaktor)) + kh_zuschlag + op_zuschlag).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
        empfehlung_min = (min_gesamt * Decimal(str(gesamtfaktor * 0.8)) + kh_zuschlag + op_zuschlag).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
        empfehlung_max = (max_gesamt * Decimal(str(gesamtfaktor * 1.2)) + kh_zuschlag + op_zuschlag).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )

        # Hinweise generieren
        hinweise = []
        if dauerfolgen:
            hinweise.append("Bei Dauerfolgen kann das Schmerzensgeld deutlich höher ausfallen.")
        if mitverschulden_prozent > 0:
            hinweise.append(f"Das Schmerzensgeld wurde um {mitverschulden_prozent}% wegen Mitverschulden gekürzt.")
        if len(verletzungen) > 1:
            hinweise.append("Bei Mehrfachverletzungen werden weitere Verletzungen mit 50% angerechnet.")

        return {
            "basis_betrag": basis_gesamt,
            "faktoren": faktoren_angewandt,
            "gesamtfaktor": round(gesamtfaktor, 3),
            "empfehlung_min": empfehlung_min,
            "empfehlung_max": empfehlung_max,
            "empfehlung": empfehlung,
            "verletzungen_details": verletzungen_details,
            "hinweise": hinweise,
        }


def get_schmerzensgeld_rechner() -> SchmerzensgeldRechner:
    """Factory-Funktion für den Schmerzensgeldrechner"""
    return SchmerzensgeldRechner()
