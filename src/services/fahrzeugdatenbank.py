"""
Fahrzeugdatenbank mit Neupreisen und Fahrzeugdaten
"""
from typing import Dict, List, Optional, Tuple
from decimal import Decimal


class FahrzeugDatenbank:
    """
    Datenbank mit Fahrzeuginformationen für Berechnungen.

    Enthält Neupreise, Fahrzeuggruppen für Nutzungsausfall,
    und typische Werte für verschiedene Berechnungen.
    """

    # Fahrzeugdaten: Hersteller -> Modelle -> Varianten
    FAHRZEUGE = {
        "Audi": {
            "A1": {
                "neupreis_basis": 22000,
                "varianten": {
                    "25 TFSI": 22000,
                    "30 TFSI": 24500,
                    "35 TFSI": 27500,
                    "S1": 35000,
                },
                "nutzungsausfall_gruppe": "B",
                "segment": "Kleinwagen",
            },
            "A3": {
                "neupreis_basis": 29000,
                "varianten": {
                    "30 TFSI": 29000,
                    "35 TFSI": 32500,
                    "35 TDI": 35000,
                    "S3": 52000,
                    "RS3": 62000,
                },
                "nutzungsausfall_gruppe": "C",
                "segment": "Kompaktklasse",
            },
            "A4": {
                "neupreis_basis": 39000,
                "varianten": {
                    "35 TFSI": 39000,
                    "40 TFSI": 43000,
                    "45 TFSI": 48000,
                    "40 TDI": 45000,
                    "S4": 62000,
                    "RS4": 85000,
                },
                "nutzungsausfall_gruppe": "D",
                "segment": "Mittelklasse",
            },
            "A6": {
                "neupreis_basis": 54000,
                "varianten": {
                    "40 TDI": 54000,
                    "45 TFSI": 58000,
                    "50 TDI": 65000,
                    "S6": 78000,
                    "RS6": 120000,
                },
                "nutzungsausfall_gruppe": "E",
                "segment": "Obere Mittelklasse",
            },
            "A8": {
                "neupreis_basis": 95000,
                "varianten": {
                    "50 TDI": 95000,
                    "55 TFSI": 105000,
                    "60 TFSI": 130000,
                    "S8": 145000,
                },
                "nutzungsausfall_gruppe": "F",
                "segment": "Oberklasse",
            },
            "Q3": {
                "neupreis_basis": 35000,
                "varianten": {
                    "35 TFSI": 35000,
                    "40 TFSI": 40000,
                    "35 TDI": 38000,
                    "RS Q3": 58000,
                },
                "nutzungsausfall_gruppe": "SUV_KLEIN",
                "segment": "Kompakt-SUV",
            },
            "Q5": {
                "neupreis_basis": 50000,
                "varianten": {
                    "40 TDI": 50000,
                    "45 TFSI": 55000,
                    "50 TDI": 60000,
                    "SQ5": 72000,
                },
                "nutzungsausfall_gruppe": "SUV_MITTEL",
                "segment": "Mittelklasse-SUV",
            },
            "Q7": {
                "neupreis_basis": 72000,
                "varianten": {
                    "45 TDI": 72000,
                    "50 TDI": 78000,
                    "55 TFSI": 85000,
                    "SQ7": 98000,
                },
                "nutzungsausfall_gruppe": "SUV_GROSS",
                "segment": "Oberklasse-SUV",
            },
        },
        "BMW": {
            "1er": {
                "neupreis_basis": 29500,
                "varianten": {
                    "116i": 29500,
                    "118i": 32000,
                    "120i": 36000,
                    "M135i": 52000,
                },
                "nutzungsausfall_gruppe": "C",
                "segment": "Kompaktklasse",
            },
            "3er": {
                "neupreis_basis": 42000,
                "varianten": {
                    "318i": 42000,
                    "320i": 46000,
                    "330i": 52000,
                    "320d": 48000,
                    "M340i": 62000,
                    "M3": 85000,
                },
                "nutzungsausfall_gruppe": "D",
                "segment": "Mittelklasse",
            },
            "5er": {
                "neupreis_basis": 55000,
                "varianten": {
                    "520i": 55000,
                    "530i": 62000,
                    "540i": 72000,
                    "520d": 58000,
                    "M550i": 85000,
                    "M5": 120000,
                },
                "nutzungsausfall_gruppe": "E",
                "segment": "Obere Mittelklasse",
            },
            "7er": {
                "neupreis_basis": 100000,
                "varianten": {
                    "740i": 100000,
                    "750i": 120000,
                    "M760i": 180000,
                },
                "nutzungsausfall_gruppe": "F",
                "segment": "Oberklasse",
            },
            "X1": {
                "neupreis_basis": 38000,
                "varianten": {
                    "sDrive18i": 38000,
                    "xDrive20i": 42000,
                    "xDrive20d": 45000,
                },
                "nutzungsausfall_gruppe": "SUV_KLEIN",
                "segment": "Kompakt-SUV",
            },
            "X3": {
                "neupreis_basis": 52000,
                "varianten": {
                    "xDrive20i": 52000,
                    "xDrive30i": 58000,
                    "xDrive20d": 55000,
                    "M40i": 72000,
                    "X3 M": 88000,
                },
                "nutzungsausfall_gruppe": "SUV_MITTEL",
                "segment": "Mittelklasse-SUV",
            },
            "X5": {
                "neupreis_basis": 75000,
                "varianten": {
                    "xDrive40i": 75000,
                    "xDrive40d": 80000,
                    "M50i": 98000,
                    "X5 M": 135000,
                },
                "nutzungsausfall_gruppe": "SUV_GROSS",
                "segment": "Oberklasse-SUV",
            },
        },
        "Mercedes-Benz": {
            "A-Klasse": {
                "neupreis_basis": 32000,
                "varianten": {
                    "A 180": 32000,
                    "A 200": 35000,
                    "A 250": 42000,
                    "AMG A 35": 52000,
                    "AMG A 45": 62000,
                },
                "nutzungsausfall_gruppe": "C",
                "segment": "Kompaktklasse",
            },
            "C-Klasse": {
                "neupreis_basis": 45000,
                "varianten": {
                    "C 180": 45000,
                    "C 200": 48000,
                    "C 300": 55000,
                    "C 220d": 50000,
                    "AMG C 43": 68000,
                    "AMG C 63": 88000,
                },
                "nutzungsausfall_gruppe": "D",
                "segment": "Mittelklasse",
            },
            "E-Klasse": {
                "neupreis_basis": 55000,
                "varianten": {
                    "E 200": 55000,
                    "E 300": 62000,
                    "E 450": 75000,
                    "E 220d": 58000,
                    "AMG E 53": 85000,
                    "AMG E 63": 118000,
                },
                "nutzungsausfall_gruppe": "E",
                "segment": "Obere Mittelklasse",
            },
            "S-Klasse": {
                "neupreis_basis": 110000,
                "varianten": {
                    "S 350d": 110000,
                    "S 450": 120000,
                    "S 500": 135000,
                    "S 580": 155000,
                    "AMG S 63": 195000,
                },
                "nutzungsausfall_gruppe": "F",
                "segment": "Oberklasse",
            },
            "GLA": {
                "neupreis_basis": 38000,
                "varianten": {
                    "GLA 180": 38000,
                    "GLA 200": 42000,
                    "GLA 250": 48000,
                    "AMG GLA 35": 55000,
                    "AMG GLA 45": 65000,
                },
                "nutzungsausfall_gruppe": "SUV_KLEIN",
                "segment": "Kompakt-SUV",
            },
            "GLC": {
                "neupreis_basis": 52000,
                "varianten": {
                    "GLC 200": 52000,
                    "GLC 300": 58000,
                    "GLC 220d": 55000,
                    "AMG GLC 43": 72000,
                    "AMG GLC 63": 98000,
                },
                "nutzungsausfall_gruppe": "SUV_MITTEL",
                "segment": "Mittelklasse-SUV",
            },
            "GLE": {
                "neupreis_basis": 72000,
                "varianten": {
                    "GLE 300d": 72000,
                    "GLE 450": 82000,
                    "GLE 580": 105000,
                    "AMG GLE 53": 95000,
                    "AMG GLE 63": 145000,
                },
                "nutzungsausfall_gruppe": "SUV_GROSS",
                "segment": "Oberklasse-SUV",
            },
        },
        "Volkswagen": {
            "Polo": {
                "neupreis_basis": 19000,
                "varianten": {
                    "1.0 TSI 80": 19000,
                    "1.0 TSI 95": 21000,
                    "1.0 TSI 110": 23500,
                    "GTI": 30000,
                },
                "nutzungsausfall_gruppe": "B",
                "segment": "Kleinwagen",
            },
            "Golf": {
                "neupreis_basis": 28000,
                "varianten": {
                    "1.0 TSI": 28000,
                    "1.5 TSI": 30000,
                    "2.0 TDI": 34000,
                    "GTI": 42000,
                    "GTD": 44000,
                    "R": 52000,
                },
                "nutzungsausfall_gruppe": "C",
                "segment": "Kompaktklasse",
            },
            "Passat": {
                "neupreis_basis": 38000,
                "varianten": {
                    "1.5 TSI": 38000,
                    "2.0 TSI": 42000,
                    "2.0 TDI": 40000,
                    "GTE": 48000,
                },
                "nutzungsausfall_gruppe": "D",
                "segment": "Mittelklasse",
            },
            "T-Roc": {
                "neupreis_basis": 26000,
                "varianten": {
                    "1.0 TSI": 26000,
                    "1.5 TSI": 29000,
                    "2.0 TDI": 32000,
                    "R": 48000,
                },
                "nutzungsausfall_gruppe": "SUV_KLEIN",
                "segment": "Kompakt-SUV",
            },
            "Tiguan": {
                "neupreis_basis": 35000,
                "varianten": {
                    "1.5 TSI": 35000,
                    "2.0 TSI": 40000,
                    "2.0 TDI": 38000,
                    "R": 55000,
                },
                "nutzungsausfall_gruppe": "SUV_MITTEL",
                "segment": "Mittelklasse-SUV",
            },
            "Touareg": {
                "neupreis_basis": 62000,
                "varianten": {
                    "3.0 V6 TDI": 62000,
                    "3.0 V6 TSI": 68000,
                    "R": 85000,
                },
                "nutzungsausfall_gruppe": "SUV_GROSS",
                "segment": "Oberklasse-SUV",
            },
        },
        "Porsche": {
            "911": {
                "neupreis_basis": 115000,
                "varianten": {
                    "Carrera": 115000,
                    "Carrera S": 135000,
                    "Carrera 4S": 145000,
                    "Turbo": 195000,
                    "Turbo S": 230000,
                    "GT3": 180000,
                },
                "nutzungsausfall_gruppe": "H",
                "segment": "Sportwagen",
            },
            "Cayenne": {
                "neupreis_basis": 82000,
                "varianten": {
                    "Cayenne": 82000,
                    "Cayenne S": 105000,
                    "Cayenne GTS": 125000,
                    "Cayenne Turbo": 155000,
                    "Cayenne Turbo S": 195000,
                },
                "nutzungsausfall_gruppe": "SUV_GROSS",
                "segment": "Luxus-SUV",
            },
            "Macan": {
                "neupreis_basis": 62000,
                "varianten": {
                    "Macan": 62000,
                    "Macan S": 72000,
                    "Macan GTS": 85000,
                    "Macan Turbo": 98000,
                },
                "nutzungsausfall_gruppe": "SUV_MITTEL",
                "segment": "Sport-SUV",
            },
        },
    }

    # Wertverlust-Tabelle (prozentual nach Jahren)
    WERTVERLUST = {
        1: 0.75,   # Nach 1 Jahr: 75% des Neupreises
        2: 0.65,   # Nach 2 Jahren: 65%
        3: 0.55,   # Nach 3 Jahren: 55%
        4: 0.47,   # Nach 4 Jahren: 47%
        5: 0.40,   # Nach 5 Jahren: 40%
        6: 0.34,   # Nach 6 Jahren: 34%
        7: 0.29,   # Nach 7 Jahren: 29%
        8: 0.25,   # Nach 8 Jahren: 25%
        9: 0.22,   # Nach 9 Jahren: 22%
        10: 0.19,  # Nach 10 Jahren: 19%
    }

    def get_hersteller(self) -> List[str]:
        """Gibt alle Hersteller zurück"""
        return list(self.FAHRZEUGE.keys())

    def get_modelle(self, hersteller: str) -> List[str]:
        """Gibt alle Modelle eines Herstellers zurück"""
        if hersteller not in self.FAHRZEUGE:
            return []
        return list(self.FAHRZEUGE[hersteller].keys())

    def get_varianten(self, hersteller: str, modell: str) -> Dict[str, int]:
        """Gibt alle Varianten eines Modells mit Preisen zurück"""
        if hersteller not in self.FAHRZEUGE:
            return {}
        if modell not in self.FAHRZEUGE[hersteller]:
            return {}
        return self.FAHRZEUGE[hersteller][modell].get("varianten", {})

    def get_fahrzeugdaten(self, hersteller: str, modell: str) -> Optional[Dict]:
        """Gibt die Daten eines Fahrzeugs zurück"""
        if hersteller not in self.FAHRZEUGE:
            return None
        if modell not in self.FAHRZEUGE[hersteller]:
            return None
        return self.FAHRZEUGE[hersteller][modell]

    def berechne_zeitwert(
        self,
        neupreis: Decimal,
        alter_jahre: int,
        laufleistung_km: int,
        zustand: str = "normal"
    ) -> Dict:
        """
        Berechnet den ungefähren Zeitwert eines Fahrzeugs.

        Args:
            neupreis: Neupreis des Fahrzeugs
            alter_jahre: Alter in Jahren
            laufleistung_km: Laufleistung in km
            zustand: Zustand (gut, normal, schlecht)

        Returns:
            Dictionary mit Berechnungsergebnis
        """
        # Basis-Wertverlust nach Alter
        if alter_jahre in self.WERTVERLUST:
            basis_faktor = Decimal(str(self.WERTVERLUST[alter_jahre]))
        elif alter_jahre > 10:
            basis_faktor = Decimal("0.15")  # Unter 10 Jahren: 15%
        else:
            basis_faktor = Decimal("1.0")  # Neufahrzeug

        # Laufleistungs-Korrektur (15.000 km/Jahr ist Standard)
        standard_km = alter_jahre * 15000
        km_differenz = laufleistung_km - standard_km

        if km_differenz > 0:
            # Mehr gefahren als Standard -> Abzug
            km_faktor = Decimal("1.0") - Decimal(str(km_differenz / 100000 * 0.1))
        else:
            # Weniger gefahren als Standard -> Zuschlag
            km_faktor = Decimal("1.0") + Decimal(str(abs(km_differenz) / 100000 * 0.05))

        km_faktor = max(Decimal("0.7"), min(Decimal("1.2"), km_faktor))

        # Zustands-Korrektur
        zustand_faktoren = {
            "sehr_gut": Decimal("1.1"),
            "gut": Decimal("1.05"),
            "normal": Decimal("1.0"),
            "schlecht": Decimal("0.9"),
            "sehr_schlecht": Decimal("0.75"),
        }
        zustand_faktor = zustand_faktoren.get(zustand, Decimal("1.0"))

        # Zeitwert berechnen
        zeitwert = (neupreis * basis_faktor * km_faktor * zustand_faktor).quantize(Decimal("1"))

        return {
            "neupreis": neupreis,
            "alter_jahre": alter_jahre,
            "laufleistung_km": laufleistung_km,
            "basis_faktor": float(basis_faktor),
            "km_faktor": float(km_faktor),
            "zustand_faktor": float(zustand_faktor),
            "zeitwert": zeitwert,
            "wertverlust_prozent": round((1 - float(zeitwert / neupreis)) * 100, 1),
        }

    def suche_fahrzeug(self, suchbegriff: str) -> List[Dict]:
        """
        Sucht nach Fahrzeugen basierend auf einem Suchbegriff.

        Args:
            suchbegriff: Suchbegriff (Hersteller, Modell oder Variante)

        Returns:
            Liste der gefundenen Fahrzeuge
        """
        ergebnisse = []
        suchbegriff = suchbegriff.lower()

        for hersteller, modelle in self.FAHRZEUGE.items():
            for modell, daten in modelle.items():
                # Prüfen ob Hersteller oder Modell passt
                if suchbegriff in hersteller.lower() or suchbegriff in modell.lower():
                    ergebnisse.append({
                        "hersteller": hersteller,
                        "modell": modell,
                        "neupreis_basis": daten["neupreis_basis"],
                        "segment": daten["segment"],
                        "nutzungsausfall_gruppe": daten["nutzungsausfall_gruppe"],
                    })
                else:
                    # Prüfen ob Variante passt
                    for variante in daten.get("varianten", {}).keys():
                        if suchbegriff in variante.lower():
                            ergebnisse.append({
                                "hersteller": hersteller,
                                "modell": modell,
                                "variante": variante,
                                "neupreis": daten["varianten"][variante],
                                "segment": daten["segment"],
                            })
                            break

        return ergebnisse


def get_fahrzeugdatenbank() -> FahrzeugDatenbank:
    """Factory-Funktion für die Fahrzeugdatenbank"""
    return FahrzeugDatenbank()
