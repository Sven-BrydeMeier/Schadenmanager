"""
Schadensrechner für Nutzungsausfall und Merkantilen Minderwert
"""
from typing import Optional, Dict, Tuple
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP


class NutzungsausfallRechner:
    """
    Berechnet den Nutzungsausfall basierend auf Fahrzeugklasse und Ausfallzeit.

    Die Nutzungsausfallentschädigung wird nach der Tabelle von Sanden/Danner/Küppersbusch
    berechnet. Die Fahrzeuge werden in Gruppen eingeteilt.
    """

    # Nutzungsausfallentschädigung pro Tag nach Fahrzeuggruppen (Stand 2024)
    # Basiert auf der Tabelle Sanden/Danner/Küppersbusch
    TAGESSAETZE = {
        "A": 23,    # Kleinstwagen (z.B. Smart, Twingo)
        "B": 29,    # Kleinwagen (z.B. Polo, Corsa, Fiesta)
        "C": 35,    # Untere Mittelklasse (z.B. Golf, Focus, Astra)
        "D": 43,    # Mittelklasse (z.B. Passat, A4, 3er)
        "E": 50,    # Obere Mittelklasse (z.B. E-Klasse, 5er, A6)
        "F": 59,    # Oberklasse (z.B. S-Klasse, 7er, A8)
        "G": 65,    # Luxusklasse
        "H": 79,    # Sportwagen
        "J": 119,   # Hochwertige Sportwagen
        "K": 175,   # Luxus-Sportwagen
        "L": 38,    # Kombi untere Mittelklasse
        "M": 50,    # Kombi Mittelklasse
        "N": 59,    # Kombi obere Mittelklasse
        "SUV_KLEIN": 43,   # Kompakt-SUV
        "SUV_MITTEL": 59,  # Mittel-SUV
        "SUV_GROSS": 79,   # Groß-SUV/Luxus-SUV
    }

    # Fahrzeugzuordnung zu Gruppen (beispielhaft, kann erweitert werden)
    FAHRZEUG_GRUPPEN = {
        # Kleinstwagen (A)
        "smart": "A", "twingo": "A", "up": "A", "aygo": "A", "c1": "A",

        # Kleinwagen (B)
        "polo": "B", "corsa": "B", "fiesta": "B", "clio": "B", "ibiza": "B",
        "fabia": "B", "yaris": "B", "micra": "B", "i20": "B", "swift": "B",

        # Untere Mittelklasse (C)
        "golf": "C", "focus": "C", "astra": "C", "leon": "C", "megane": "C",
        "octavia": "C", "civic": "C", "corolla": "C", "i30": "C", "3": "C",

        # Mittelklasse (D)
        "passat": "D", "a4": "D", "3er": "D", "c-klasse": "D", "mondeo": "D",
        "superb": "D", "accord": "D", "camry": "D", "sonata": "D",

        # Obere Mittelklasse (E)
        "e-klasse": "E", "5er": "E", "a6": "E", "xf": "E", "talisman": "E",

        # Oberklasse (F)
        "s-klasse": "F", "7er": "F", "a8": "F", "xj": "F", "panamera": "F",

        # Sportwagen (H)
        "911": "H", "cayman": "H", "boxster": "H", "z4": "H", "tt": "H",
        "mx-5": "H", "mustang": "H", "camaro": "H",

        # SUV
        "tiguan": "SUV_MITTEL", "rav4": "SUV_MITTEL", "qashqai": "SUV_MITTEL",
        "q5": "SUV_MITTEL", "x3": "SUV_MITTEL", "glc": "SUV_MITTEL",
        "q7": "SUV_GROSS", "x5": "SUV_GROSS", "gle": "SUV_GROSS",
        "cayenne": "SUV_GROSS", "range rover": "SUV_GROSS",
        "t-roc": "SUV_KLEIN", "t-cross": "SUV_KLEIN", "captur": "SUV_KLEIN",
    }

    def ermittle_fahrzeuggruppe(self, modell: str) -> str:
        """
        Ermittelt die Fahrzeuggruppe basierend auf dem Modellnamen.

        Args:
            modell: Modellbezeichnung des Fahrzeugs

        Returns:
            Fahrzeuggruppe (A-K, L-N, SUV_*)
        """
        modell_lower = modell.lower().strip()

        for key, gruppe in self.FAHRZEUG_GRUPPEN.items():
            if key in modell_lower:
                return gruppe

        # Standard: Mittelklasse
        return "C"

    def berechne_nutzungsausfall(
        self,
        fahrzeuggruppe: str,
        ausfall_tage: int,
        reparatur_tage: Optional[int] = None,
        wiederbeschaffung_tage: Optional[int] = None
    ) -> Dict:
        """
        Berechnet den Nutzungsausfall.

        Args:
            fahrzeuggruppe: Gruppe des Fahrzeugs (A-K, L-N, SUV_*)
            ausfall_tage: Anzahl der Ausfalltage
            reparatur_tage: Optional - Tage für Reparatur
            wiederbeschaffung_tage: Optional - Tage für Wiederbeschaffung

        Returns:
            Dictionary mit Berechnungsdetails
        """
        tagessatz = self.TAGESSAETZE.get(fahrzeuggruppe.upper(), self.TAGESSAETZE["C"])

        # Bei Totalschaden: Wiederbeschaffungsdauer (i.d.R. 14 Tage)
        if wiederbeschaffung_tage:
            ausfall_tage = min(ausfall_tage, wiederbeschaffung_tage)

        # Bei Reparatur: Reparaturdauer + ggf. Wartezeit
        if reparatur_tage:
            ausfall_tage = min(ausfall_tage, reparatur_tage)

        gesamt = Decimal(tagessatz * ausfall_tage).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        return {
            "fahrzeuggruppe": fahrzeuggruppe,
            "tagessatz": Decimal(tagessatz),
            "ausfall_tage": ausfall_tage,
            "gesamt_betrag": gesamt,
            "hinweis": self._get_hinweis(fahrzeuggruppe)
        }

    def _get_hinweis(self, gruppe: str) -> str:
        """Gibt einen Hinweistext zur Fahrzeuggruppe zurück"""
        hinweise = {
            "A": "Kleinstwagen (Smart, Twingo, etc.)",
            "B": "Kleinwagen (Polo, Corsa, etc.)",
            "C": "Kompaktklasse (Golf, Focus, etc.)",
            "D": "Mittelklasse (Passat, A4, 3er, etc.)",
            "E": "Obere Mittelklasse (E-Klasse, 5er, A6, etc.)",
            "F": "Oberklasse (S-Klasse, 7er, A8, etc.)",
            "G": "Luxusklasse",
            "H": "Sportwagen",
            "J": "Hochwertige Sportwagen",
            "K": "Luxus-Sportwagen",
            "SUV_KLEIN": "Kompakt-SUV",
            "SUV_MITTEL": "Mittelklasse-SUV",
            "SUV_GROSS": "Oberklasse-SUV",
        }
        return hinweise.get(gruppe, "Standardgruppe")


class MerkantilerMinderwertRechner:
    """
    Berechnet den merkantilen Minderwert nach verschiedenen Methoden.

    Der merkantile Minderwert ist die Wertminderung eines Fahrzeugs,
    die trotz fachgerechter Reparatur aufgrund des "Makels" eines
    Unfallfahrzeugs verbleibt.
    """

    def berechne_alle_methoden(
        self,
        wiederbeschaffungswert: Decimal,
        reparaturkosten: Decimal,
        fahrzeugalter_monate: int,
        laufleistung_km: int
    ) -> Dict:
        """
        Berechnet den merkantilen Minderwert nach allen gängigen Methoden.

        Args:
            wiederbeschaffungswert: Wiederbeschaffungswert vor dem Unfall
            reparaturkosten: Netto-Reparaturkosten
            fahrzeugalter_monate: Alter des Fahrzeugs in Monaten
            laufleistung_km: Laufleistung in Kilometern

        Returns:
            Dictionary mit Ergebnissen aller Berechnungsmethoden
        """
        ergebnisse = {
            "ruhkopf_sahm": self.methode_ruhkopf_sahm(
                wiederbeschaffungswert, reparaturkosten, fahrzeugalter_monate
            ),
            "halbgewachs": self.methode_halbgewachs(
                wiederbeschaffungswert, reparaturkosten
            ),
            "dvgt": self.methode_dvgt(
                wiederbeschaffungswert, reparaturkosten, fahrzeugalter_monate, laufleistung_km
            ),
            "empfehlung": None
        }

        # Empfehlung: Mittelwert der Methoden
        werte = [
            ergebnisse["ruhkopf_sahm"]["minderwert"],
            ergebnisse["halbgewachs"]["minderwert"],
            ergebnisse["dvgt"]["minderwert"]
        ]
        mittelwert = sum(werte) / len(werte)
        ergebnisse["empfehlung"] = Decimal(mittelwert).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        return ergebnisse

    def methode_ruhkopf_sahm(
        self,
        wiederbeschaffungswert: Decimal,
        reparaturkosten: Decimal,
        fahrzeugalter_monate: int
    ) -> Dict:
        """
        Berechnung nach der Methode Ruhkopf/Sahm.

        Formel: Minderwert = (Reparaturkosten × Wiederbeschaffungswert) / (Reparaturkosten + Wiederbeschaffungswert) × Faktor

        Der Faktor ist abhängig vom Fahrzeugalter.
        """
        if wiederbeschaffungswert <= 0:
            return {"minderwert": Decimal("0"), "faktor": 0, "hinweis": "Ungültiger Wiederbeschaffungswert"}

        # Altersfaktoren
        if fahrzeugalter_monate <= 12:
            faktor = 1.0
        elif fahrzeugalter_monate <= 24:
            faktor = 0.9
        elif fahrzeugalter_monate <= 36:
            faktor = 0.8
        elif fahrzeugalter_monate <= 48:
            faktor = 0.7
        elif fahrzeugalter_monate <= 60:
            faktor = 0.6
        elif fahrzeugalter_monate <= 72:
            faktor = 0.5
        else:
            faktor = 0.3  # Sehr alte Fahrzeuge: geringer Minderwert

        # Berechnung
        zaehler = float(reparaturkosten) * float(wiederbeschaffungswert)
        nenner = float(reparaturkosten) + float(wiederbeschaffungswert)

        if nenner == 0:
            minderwert = Decimal("0")
        else:
            minderwert = Decimal(zaehler / nenner * faktor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        return {
            "minderwert": minderwert,
            "faktor": faktor,
            "methode": "Ruhkopf/Sahm",
            "hinweis": f"Altersfaktor: {faktor} (Fahrzeugalter: {fahrzeugalter_monate} Monate)"
        }

    def methode_halbgewachs(
        self,
        wiederbeschaffungswert: Decimal,
        reparaturkosten: Decimal
    ) -> Dict:
        """
        Berechnung nach der Methode Halbgewachs.

        Formel: Minderwert = Reparaturkosten × Faktor (5-10% der Reparaturkosten)

        Der Faktor liegt typischerweise zwischen 0.05 und 0.10.
        """
        # Standardfaktor: 7.5%
        faktor = Decimal("0.075")

        # Höherer Faktor bei teuren Fahrzeugen
        if wiederbeschaffungswert > 50000:
            faktor = Decimal("0.10")
        elif wiederbeschaffungswert > 30000:
            faktor = Decimal("0.085")

        minderwert = (reparaturkosten * faktor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        return {
            "minderwert": minderwert,
            "faktor": float(faktor),
            "methode": "Halbgewachs",
            "hinweis": f"Faktor: {float(faktor)*100}% der Reparaturkosten"
        }

    def methode_dvgt(
        self,
        wiederbeschaffungswert: Decimal,
        reparaturkosten: Decimal,
        fahrzeugalter_monate: int,
        laufleistung_km: int
    ) -> Dict:
        """
        Berechnung nach DVGT (Deutscher Verband der Gutachter für Technik).

        Berücksichtigt zusätzlich die Laufleistung.
        """
        if wiederbeschaffungswert <= 0:
            return {"minderwert": Decimal("0"), "hinweis": "Ungültiger Wiederbeschaffungswert"}

        # Basisberechnung: Prozent vom Wiederbeschaffungswert
        reparatur_anteil = float(reparaturkosten) / float(wiederbeschaffungswert)

        # Grundfaktor basierend auf Reparaturumfang
        if reparatur_anteil < 0.1:
            grund_faktor = 0.02
        elif reparatur_anteil < 0.2:
            grund_faktor = 0.03
        elif reparatur_anteil < 0.3:
            grund_faktor = 0.04
        elif reparatur_anteil < 0.5:
            grund_faktor = 0.05
        else:
            grund_faktor = 0.06

        # Altersfaktor (reduziert Minderwert bei älteren Fahrzeugen)
        alter_faktor = max(0.3, 1.0 - (fahrzeugalter_monate / 120))

        # Laufleistungsfaktor (reduziert Minderwert bei hoher Laufleistung)
        km_faktor = max(0.3, 1.0 - (laufleistung_km / 200000))

        # Gesamtfaktor
        gesamt_faktor = grund_faktor * alter_faktor * km_faktor

        minderwert = Decimal(float(wiederbeschaffungswert) * gesamt_faktor).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        return {
            "minderwert": minderwert,
            "grund_faktor": grund_faktor,
            "alter_faktor": round(alter_faktor, 3),
            "km_faktor": round(km_faktor, 3),
            "gesamt_faktor": round(gesamt_faktor, 4),
            "methode": "DVGT",
            "hinweis": f"Berücksichtigt Alter ({fahrzeugalter_monate} Mon.) und Laufleistung ({laufleistung_km:,} km)"
        }

    def pruefe_anspruch(
        self,
        fahrzeugalter_monate: int,
        laufleistung_km: int,
        wiederbeschaffungswert: Decimal
    ) -> Tuple[bool, str]:
        """
        Prüft, ob grundsätzlich ein Anspruch auf merkantilen Minderwert besteht.

        Nach Rechtsprechung entfällt der Anspruch i.d.R. bei:
        - Fahrzeugalter > 5-7 Jahre
        - Laufleistung > 100.000-150.000 km
        - Wiederbeschaffungswert < 4.000-5.000 EUR

        Returns:
            Tuple aus (Anspruch besteht, Begründung)
        """
        gruende = []
        anspruch = True

        if fahrzeugalter_monate > 84:  # > 7 Jahre
            gruende.append(f"Fahrzeugalter ({fahrzeugalter_monate // 12} Jahre) überschreitet typische Grenze")
            anspruch = False

        if laufleistung_km > 150000:
            gruende.append(f"Laufleistung ({laufleistung_km:,} km) überschreitet typische Grenze")
            anspruch = False

        if wiederbeschaffungswert < 4000:
            gruende.append(f"Wiederbeschaffungswert ({float(wiederbeschaffungswert):.2f} EUR) zu gering")
            anspruch = False

        if anspruch:
            return True, "Anspruch auf merkantilen Minderwert besteht grundsätzlich."
        else:
            return False, "Anspruch fraglich: " + "; ".join(gruende)


def get_nutzungsausfall_rechner() -> NutzungsausfallRechner:
    """Factory-Funktion für den Nutzungsausfallrechner"""
    return NutzungsausfallRechner()


def get_minderwert_rechner() -> MerkantilerMinderwertRechner:
    """Factory-Funktion für den Minderwertrechner"""
    return MerkantilerMinderwertRechner()
