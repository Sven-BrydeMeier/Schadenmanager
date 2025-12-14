"""
Gutachten-Plausibilitätsprüfung Service
Automatische Prüfung von Kfz-Gutachten auf Unstimmigkeiten und Fehler
"""
from datetime import datetime, date
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum
from decimal import Decimal
import json
import re
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Enum as SQLEnum, Numeric, Date
from sqlalchemy.orm import relationship
from src.models.base import Base


class PruefungsSchwere(str, Enum):
    """Schweregrad einer Auffälligkeit"""
    INFO = "INFO"           # Hinweis/Information
    WARNUNG = "WARNUNG"     # Sollte geprüft werden
    KRITISCH = "KRITISCH"   # Muss geprüft werden
    FEHLER = "FEHLER"       # Offensichtlicher Fehler


class PruefungsKategorie(str, Enum):
    """Kategorien der Prüfung"""
    FAHRZEUGDATEN = "FAHRZEUGDATEN"
    WERTERMITTLUNG = "WERTERMITTLUNG"
    REPARATURKOSTEN = "REPARATURKOSTEN"
    STUNDENVERRECHNUNGSSAETZE = "STUNDENVERRECHNUNGSSAETZE"
    ERSATZTEILE = "ERSATZTEILE"
    LACKIERUNG = "LACKIERUNG"
    MERKANTILER_MINDERWERT = "MERKANTILER_MINDERWERT"
    NUTZUNGSAUSFALL = "NUTZUNGSAUSFALL"
    RESTWERT = "RESTWERT"
    TOTALSCHADEN = "TOTALSCHADEN"
    FORMALES = "FORMALES"
    PLAUSIBILITAET = "PLAUSIBILITAET"


class GutachtenPruefung(Base):
    """Model für Gutachten-Plausibilitätsprüfungen"""
    __tablename__ = "gutachten_pruefung"

    id = Column(Integer, primary_key=True)

    # Projekt-Zuordnung
    projekt_id = Column(Integer, ForeignKey("unfallprojekt.id"), nullable=False)
    projekt = relationship("UnfallProjekt", backref="gutachten_pruefungen")

    # Gutachten-Referenz
    dokument_id = Column(Integer, ForeignKey("dokument.id"))
    gutachten_nr = Column(String(100))
    gutachter_name = Column(String(200))
    gutachten_datum = Column(Date)

    # Eingabedaten (aus Gutachten extrahiert)
    _gutachten_daten = Column("gutachten_daten", Text)

    # Prüfungsergebnis
    pruefung_am = Column(DateTime, default=datetime.now)
    geprueft_von_user_id = Column(Integer, ForeignKey("user.id"))

    # Ergebnis-Zusammenfassung
    anzahl_fehler = Column(Integer, default=0)
    anzahl_warnungen = Column(Integer, default=0)
    anzahl_hinweise = Column(Integer, default=0)
    gesamtbewertung = Column(String(50))  # UNAUFFAELLIG, PRUEFENSWERT, AUFFAELLIG

    # Detaillierte Ergebnisse
    _pruefungsergebnisse = Column("pruefungsergebnisse", Text)

    # Anmerkungen
    anwalt_kommentar = Column(Text)

    # Metadaten
    erstellt_am = Column(DateTime, default=datetime.now)
    aktualisiert_am = Column(DateTime, onupdate=datetime.now)

    @property
    def gutachten_daten(self) -> Dict[str, Any]:
        if self._gutachten_daten:
            return json.loads(self._gutachten_daten)
        return {}

    @gutachten_daten.setter
    def gutachten_daten(self, value: Dict[str, Any]):
        self._gutachten_daten = json.dumps(value, default=str)

    @property
    def pruefungsergebnisse(self) -> List[Dict]:
        if self._pruefungsergebnisse:
            return json.loads(self._pruefungsergebnisse)
        return []

    @pruefungsergebnisse.setter
    def pruefungsergebnisse(self, value: List[Dict]):
        self._pruefungsergebnisse = json.dumps(value, default=str)


class GutachtenPlausibilitaetService:
    """Service für Gutachten-Plausibilitätsprüfung"""

    # Referenzwerte für Stundenverrechnungssätze (EUR/Stunde) - Stand 2024
    REFERENZ_STUNDENSAETZE = {
        'karosserie': {'min': 95, 'max': 180, 'durchschnitt': 135},
        'mechanik': {'min': 90, 'max': 170, 'durchschnitt': 125},
        'elektrik': {'min': 95, 'max': 175, 'durchschnitt': 130},
        'lackierung': {'min': 100, 'max': 190, 'durchschnitt': 145},
        'freie_werkstatt': {'min': 60, 'max': 120, 'durchschnitt': 85}
    }

    # Referenzwerte für Lackierung (EUR/Lackierpunkt)
    REFERENZ_LACKIERUNG = {
        'lackmaterial_pro_lp': {'min': 1.50, 'max': 4.50, 'durchschnitt': 2.80},
        'arbeitszeit_pro_lp_minuten': {'min': 4, 'max': 8, 'durchschnitt': 5.5}
    }

    # Merkantiler Minderwert - Referenzwerte nach Halbgewachs
    MINDERWERT_FAKTOREN = {
        'alter_monate_max': 60,  # Nach 5 Jahren meist kein Minderwert
        'km_max': 100000,        # Über 100.000 km meist kein Minderwert
        'prozent_von_reparatur_max': 30,
        'prozent_von_wbw_max': 10
    }

    # Nutzungsausfall-Referenzwerte (nach Sanden/Danner/Küppersbusch)
    NUTZUNGSAUSFALL_GRUPPEN = {
        'A': {'min': 23, 'max': 29},
        'B': {'min': 29, 'max': 35},
        'C': {'min': 35, 'max': 41},
        'D': {'min': 41, 'max': 50},
        'E': {'min': 50, 'max': 59},
        'F': {'min': 59, 'max': 65},
        'G': {'min': 65, 'max': 79},
        'H': {'min': 79, 'max': 89},
        'J': {'min': 89, 'max': 103},
        'K': {'min': 103, 'max': 119},
        'L': {'min': 119, 'max': 175}
    }

    # Wertminderungsgrenzen für Totalschaden
    TOTALSCHADEN_GRENZE_PROZENT = 130  # 130%-Regel

    def __init__(self, db_session):
        self.db = db_session

    def pruefung_durchfuehren(
        self,
        projekt_id: int,
        gutachten_daten: Dict[str, Any],
        dokument_id: Optional[int] = None,
        geprueft_von_user_id: Optional[int] = None
    ) -> GutachtenPruefung:
        """Führt eine vollständige Plausibilitätsprüfung durch"""
        pruefung = GutachtenPruefung(
            projekt_id=projekt_id,
            dokument_id=dokument_id,
            gutachten_nr=gutachten_daten.get('gutachten_nr'),
            gutachter_name=gutachten_daten.get('gutachter_name'),
            geprueft_von_user_id=geprueft_von_user_id
        )

        if gutachten_daten.get('gutachten_datum'):
            if isinstance(gutachten_daten['gutachten_datum'], str):
                try:
                    pruefung.gutachten_datum = datetime.strptime(
                        gutachten_daten['gutachten_datum'], '%Y-%m-%d'
                    ).date()
                except:
                    pass
            else:
                pruefung.gutachten_datum = gutachten_daten['gutachten_datum']

        pruefung.gutachten_daten = gutachten_daten

        # Alle Prüfungen durchführen
        ergebnisse = []

        # 1. Fahrzeugdaten prüfen
        ergebnisse.extend(self._pruefe_fahrzeugdaten(gutachten_daten))

        # 2. Wertermittlung prüfen
        ergebnisse.extend(self._pruefe_wertermittlung(gutachten_daten))

        # 3. Reparaturkosten prüfen
        ergebnisse.extend(self._pruefe_reparaturkosten(gutachten_daten))

        # 4. Stundenverrechnungssätze prüfen
        ergebnisse.extend(self._pruefe_stundensaetze(gutachten_daten))

        # 5. Ersatzteilpreise prüfen
        ergebnisse.extend(self._pruefe_ersatzteile(gutachten_daten))

        # 6. Lackierung prüfen
        ergebnisse.extend(self._pruefe_lackierung(gutachten_daten))

        # 7. Merkantilen Minderwert prüfen
        ergebnisse.extend(self._pruefe_merkantilen_minderwert(gutachten_daten))

        # 8. Nutzungsausfall prüfen
        ergebnisse.extend(self._pruefe_nutzungsausfall(gutachten_daten))

        # 9. Restwert prüfen
        ergebnisse.extend(self._pruefe_restwert(gutachten_daten))

        # 10. Totalschaden-Grenze prüfen
        ergebnisse.extend(self._pruefe_totalschaden(gutachten_daten))

        # 11. Formale Prüfung
        ergebnisse.extend(self._pruefe_formal(gutachten_daten))

        # 12. Allgemeine Plausibilität
        ergebnisse.extend(self._pruefe_allgemeine_plausibilitaet(gutachten_daten))

        # Ergebnisse speichern
        pruefung.pruefungsergebnisse = ergebnisse

        # Zusammenfassung erstellen
        pruefung.anzahl_fehler = len([e for e in ergebnisse if e['schwere'] == PruefungsSchwere.FEHLER.value])
        pruefung.anzahl_warnungen = len([e for e in ergebnisse if e['schwere'] in [PruefungsSchwere.KRITISCH.value, PruefungsSchwere.WARNUNG.value]])
        pruefung.anzahl_hinweise = len([e for e in ergebnisse if e['schwere'] == PruefungsSchwere.INFO.value])

        # Gesamtbewertung
        if pruefung.anzahl_fehler > 0:
            pruefung.gesamtbewertung = "AUFFAELLIG"
        elif pruefung.anzahl_warnungen > 2:
            pruefung.gesamtbewertung = "PRUEFENSWERT"
        elif pruefung.anzahl_warnungen > 0:
            pruefung.gesamtbewertung = "LEICHT_AUFFAELLIG"
        else:
            pruefung.gesamtbewertung = "UNAUFFAELLIG"

        self.db.add(pruefung)
        self.db.flush()

        return pruefung

    def _erstelle_ergebnis(
        self,
        kategorie: PruefungsKategorie,
        schwere: PruefungsSchwere,
        titel: str,
        beschreibung: str,
        details: Optional[Dict] = None
    ) -> Dict:
        """Erstellt ein Prüfungsergebnis"""
        return {
            'kategorie': kategorie.value,
            'schwere': schwere.value,
            'titel': titel,
            'beschreibung': beschreibung,
            'details': details or {}
        }

    def _pruefe_fahrzeugdaten(self, daten: Dict) -> List[Dict]:
        """Prüft die Fahrzeugdaten auf Plausibilität"""
        ergebnisse = []

        # Kilometerstand vs. Alter
        ez = daten.get('erstzulassung')
        km = daten.get('kilometerstand')

        if ez and km:
            if isinstance(ez, str):
                try:
                    ez_date = datetime.strptime(ez, '%Y-%m-%d').date()
                except:
                    ez_date = None
            else:
                ez_date = ez

            if ez_date:
                alter_monate = (date.today().year - ez_date.year) * 12 + (date.today().month - ez_date.month)
                erwartete_km = alter_monate * 1250  # ca. 15.000 km/Jahr

                if km > erwartete_km * 2:
                    ergebnisse.append(self._erstelle_ergebnis(
                        PruefungsKategorie.FAHRZEUGDATEN,
                        PruefungsSchwere.INFO,
                        "Hohe Laufleistung",
                        f"Der Kilometerstand ({km:,} km) ist deutlich höher als der Durchschnitt ({erwartete_km:,} km für dieses Alter).",
                        {'km': km, 'erwartet': erwartete_km, 'alter_monate': alter_monate}
                    ))
                elif km < erwartete_km * 0.3:
                    ergebnisse.append(self._erstelle_ergebnis(
                        PruefungsKategorie.FAHRZEUGDATEN,
                        PruefungsSchwere.WARNUNG,
                        "Ungewöhnlich niedrige Laufleistung",
                        f"Der Kilometerstand ({km:,} km) ist auffällig niedrig. Prüfen Sie auf Tachomanipulation.",
                        {'km': km, 'erwartet': erwartete_km}
                    ))

        return ergebnisse

    def _pruefe_wertermittlung(self, daten: Dict) -> List[Dict]:
        """Prüft die Wertermittlung"""
        ergebnisse = []

        wbw = daten.get('wiederbeschaffungswert', 0)
        restwert = daten.get('restwert', 0)
        neupreis = daten.get('neupreis', 0)

        # Verhältnis WBW zu Neupreis
        if wbw and neupreis and neupreis > 0:
            verhaeltnis = wbw / neupreis * 100

            ez = daten.get('erstzulassung')
            if ez:
                if isinstance(ez, str):
                    try:
                        ez_date = datetime.strptime(ez, '%Y-%m-%d').date()
                    except:
                        ez_date = None
                else:
                    ez_date = ez

                if ez_date:
                    alter_monate = (date.today().year - ez_date.year) * 12

                    # Erwarteter Wertverlust ca. 1-2% pro Monat im ersten Jahr
                    if alter_monate < 12 and verhaeltnis > 95:
                        ergebnisse.append(self._erstelle_ergebnis(
                            PruefungsKategorie.WERTERMITTLUNG,
                            PruefungsSchwere.WARNUNG,
                            "WBW sehr hoch im Verhältnis zum Neupreis",
                            f"Bei einem Fahrzeugalter von {alter_monate} Monaten erscheint ein WBW von {verhaeltnis:.1f}% des Neupreises ungewöhnlich hoch.",
                            {'wbw': wbw, 'neupreis': neupreis, 'verhaeltnis': verhaeltnis}
                        ))

        # Verhältnis Restwert zu WBW
        if wbw and restwert and wbw > 0:
            restwert_prozent = restwert / wbw * 100

            if restwert_prozent < 5:
                ergebnisse.append(self._erstelle_ergebnis(
                    PruefungsKategorie.RESTWERT,
                    PruefungsSchwere.WARNUNG,
                    "Sehr niedriger Restwert",
                    f"Der Restwert ({restwert:,.2f} EUR = {restwert_prozent:.1f}% des WBW) erscheint sehr niedrig. Prüfen Sie die Restwertermittlung.",
                    {'restwert': restwert, 'wbw': wbw, 'prozent': restwert_prozent}
                ))
            elif restwert_prozent > 40:
                ergebnisse.append(self._erstelle_ergebnis(
                    PruefungsKategorie.RESTWERT,
                    PruefungsSchwere.INFO,
                    "Hoher Restwert",
                    f"Der Restwert ({restwert:,.2f} EUR = {restwert_prozent:.1f}% des WBW) ist relativ hoch.",
                    {'restwert': restwert, 'wbw': wbw, 'prozent': restwert_prozent}
                ))

        return ergebnisse

    def _pruefe_reparaturkosten(self, daten: Dict) -> List[Dict]:
        """Prüft die Reparaturkosten"""
        ergebnisse = []

        reparaturkosten = daten.get('reparaturkosten_netto', 0)
        wbw = daten.get('wiederbeschaffungswert', 0)
        lohnkosten = daten.get('lohnkosten', 0)
        ersatzteilkosten = daten.get('ersatzteilkosten', 0)
        lackierkosten = daten.get('lackierkosten', 0)

        # Verhältnis Reparaturkosten zu WBW
        if reparaturkosten and wbw and wbw > 0:
            verhaeltnis = reparaturkosten / wbw * 100

            if verhaeltnis > 100 and verhaeltnis <= 130:
                ergebnisse.append(self._erstelle_ergebnis(
                    PruefungsKategorie.REPARATURKOSTEN,
                    PruefungsSchwere.INFO,
                    "Reparaturkosten über 100% des WBW",
                    f"Die Reparaturkosten ({reparaturkosten:,.2f} EUR = {verhaeltnis:.1f}% des WBW) liegen über dem Wiederbeschaffungswert, aber unter der 130%-Grenze (Integritätsinteresse möglich).",
                    {'reparaturkosten': reparaturkosten, 'wbw': wbw, 'prozent': verhaeltnis}
                ))

        # Verhältnis Lohn zu Material
        if lohnkosten and ersatzteilkosten and ersatzteilkosten > 0:
            lohn_material_verhaeltnis = lohnkosten / ersatzteilkosten

            if lohn_material_verhaeltnis > 2:
                ergebnisse.append(self._erstelle_ergebnis(
                    PruefungsKategorie.REPARATURKOSTEN,
                    PruefungsSchwere.WARNUNG,
                    "Hoher Lohnanteil",
                    f"Das Verhältnis Lohn ({lohnkosten:,.2f} EUR) zu Material ({ersatzteilkosten:,.2f} EUR) ist ungewöhnlich hoch ({lohn_material_verhaeltnis:.1f}:1).",
                    {'lohnkosten': lohnkosten, 'ersatzteilkosten': ersatzteilkosten, 'verhaeltnis': lohn_material_verhaeltnis}
                ))
            elif lohn_material_verhaeltnis < 0.3:
                ergebnisse.append(self._erstelle_ergebnis(
                    PruefungsKategorie.REPARATURKOSTEN,
                    PruefungsSchwere.WARNUNG,
                    "Niedriger Lohnanteil",
                    f"Das Verhältnis Lohn ({lohnkosten:,.2f} EUR) zu Material ({ersatzteilkosten:,.2f} EUR) ist ungewöhnlich niedrig ({lohn_material_verhaeltnis:.1f}:1).",
                    {'lohnkosten': lohnkosten, 'ersatzteilkosten': ersatzteilkosten}
                ))

        return ergebnisse

    def _pruefe_stundensaetze(self, daten: Dict) -> List[Dict]:
        """Prüft die Stundenverrechnungssätze"""
        ergebnisse = []

        stundensaetze = daten.get('stundensaetze', {})
        werkstatt_typ = daten.get('werkstatt_typ', 'markenwerkstatt')

        referenz = self.REFERENZ_STUNDENSAETZE.get(
            'freie_werkstatt' if werkstatt_typ == 'freie_werkstatt' else 'karosserie'
        )

        for bereich, satz in stundensaetze.items():
            ref = self.REFERENZ_STUNDENSAETZE.get(bereich, referenz)

            if satz > ref['max']:
                ergebnisse.append(self._erstelle_ergebnis(
                    PruefungsKategorie.STUNDENVERRECHNUNGSSAETZE,
                    PruefungsSchwere.WARNUNG,
                    f"Hoher Stundensatz ({bereich})",
                    f"Der Stundensatz für {bereich} ({satz:.2f} EUR) liegt über dem Referenzbereich (max. {ref['max']:.2f} EUR).",
                    {'bereich': bereich, 'satz': satz, 'max': ref['max']}
                ))
            elif satz < ref['min']:
                ergebnisse.append(self._erstelle_ergebnis(
                    PruefungsKategorie.STUNDENVERRECHNUNGSSAETZE,
                    PruefungsSchwere.INFO,
                    f"Niedriger Stundensatz ({bereich})",
                    f"Der Stundensatz für {bereich} ({satz:.2f} EUR) liegt unter dem üblichen Bereich (min. {ref['min']:.2f} EUR).",
                    {'bereich': bereich, 'satz': satz, 'min': ref['min']}
                ))

        return ergebnisse

    def _pruefe_ersatzteile(self, daten: Dict) -> List[Dict]:
        """Prüft die Ersatzteilpreise"""
        ergebnisse = []

        ersatzteile = daten.get('ersatzteile', [])
        upe_aufschlag = daten.get('upe_aufschlag', 0)

        # UPE-Aufschlag prüfen
        if upe_aufschlag:
            if upe_aufschlag > 20:
                ergebnisse.append(self._erstelle_ergebnis(
                    PruefungsKategorie.ERSATZTEILE,
                    PruefungsSchwere.WARNUNG,
                    "Hoher UPE-Aufschlag",
                    f"Der UPE-Aufschlag ({upe_aufschlag}%) ist höher als üblich (max. 15-20%).",
                    {'upe_aufschlag': upe_aufschlag}
                ))
            elif upe_aufschlag < 10:
                ergebnisse.append(self._erstelle_ergebnis(
                    PruefungsKategorie.ERSATZTEILE,
                    PruefungsSchwere.INFO,
                    "Niedriger UPE-Aufschlag",
                    f"Der UPE-Aufschlag ({upe_aufschlag}%) ist niedrig. Prüfen Sie, ob Originalteile kalkuliert wurden.",
                    {'upe_aufschlag': upe_aufschlag}
                ))

        # Kleinteile-Pauschale
        kleinteile = daten.get('kleinteile_pauschale', 0)
        ersatzteilkosten = daten.get('ersatzteilkosten', 0)

        if kleinteile and ersatzteilkosten and ersatzteilkosten > 0:
            kleinteile_prozent = kleinteile / ersatzteilkosten * 100

            if kleinteile_prozent > 5:
                ergebnisse.append(self._erstelle_ergebnis(
                    PruefungsKategorie.ERSATZTEILE,
                    PruefungsSchwere.WARNUNG,
                    "Hohe Kleinteile-Pauschale",
                    f"Die Kleinteile-Pauschale ({kleinteile:,.2f} EUR = {kleinteile_prozent:.1f}%) erscheint hoch.",
                    {'kleinteile': kleinteile, 'prozent': kleinteile_prozent}
                ))

        return ergebnisse

    def _pruefe_lackierung(self, daten: Dict) -> List[Dict]:
        """Prüft die Lackierkosten"""
        ergebnisse = []

        lackierpunkte = daten.get('lackierpunkte', 0)
        lackmaterial = daten.get('lackmaterial', 0)
        lackierzeit_stunden = daten.get('lackierzeit_stunden', 0)

        if lackierpunkte and lackierpunkte > 0:
            # Lackmaterial pro Lackierpunkt
            if lackmaterial:
                material_pro_lp = lackmaterial / lackierpunkte
                ref = self.REFERENZ_LACKIERUNG['lackmaterial_pro_lp']

                if material_pro_lp > ref['max']:
                    ergebnisse.append(self._erstelle_ergebnis(
                        PruefungsKategorie.LACKIERUNG,
                        PruefungsSchwere.WARNUNG,
                        "Hohe Lackmaterialkosten",
                        f"Die Lackmaterialkosten pro LP ({material_pro_lp:.2f} EUR) liegen über dem Referenzwert (max. {ref['max']:.2f} EUR).",
                        {'material_pro_lp': material_pro_lp, 'max': ref['max']}
                    ))

            # Arbeitszeit pro Lackierpunkt
            if lackierzeit_stunden:
                minuten_pro_lp = (lackierzeit_stunden * 60) / lackierpunkte
                ref = self.REFERENZ_LACKIERUNG['arbeitszeit_pro_lp_minuten']

                if minuten_pro_lp > ref['max']:
                    ergebnisse.append(self._erstelle_ergebnis(
                        PruefungsKategorie.LACKIERUNG,
                        PruefungsSchwere.WARNUNG,
                        "Hohe Lackierzeit",
                        f"Die Lackierzeit pro LP ({minuten_pro_lp:.1f} Min.) liegt über dem Referenzwert (max. {ref['max']} Min.).",
                        {'minuten_pro_lp': minuten_pro_lp, 'max': ref['max']}
                    ))

        return ergebnisse

    def _pruefe_merkantilen_minderwert(self, daten: Dict) -> List[Dict]:
        """Prüft den merkantilen Minderwert"""
        ergebnisse = []

        minderwert = daten.get('merkantiler_minderwert', 0)
        wbw = daten.get('wiederbeschaffungswert', 0)
        reparaturkosten = daten.get('reparaturkosten_netto', 0)
        km = daten.get('kilometerstand', 0)

        ez = daten.get('erstzulassung')
        alter_monate = 0
        if ez:
            if isinstance(ez, str):
                try:
                    ez_date = datetime.strptime(ez, '%Y-%m-%d').date()
                    alter_monate = (date.today().year - ez_date.year) * 12
                except:
                    pass
            else:
                alter_monate = (date.today().year - ez.year) * 12

        # Prüfen ob Minderwert angesetzt werden sollte
        if minderwert == 0:
            if alter_monate < self.MINDERWERT_FAKTOREN['alter_monate_max'] and km < self.MINDERWERT_FAKTOREN['km_max']:
                ergebnisse.append(self._erstelle_ergebnis(
                    PruefungsKategorie.MERKANTILER_MINDERWERT,
                    PruefungsSchwere.WARNUNG,
                    "Kein merkantiler Minderwert angesetzt",
                    f"Bei einem Fahrzeugalter von {alter_monate} Monaten und {km:,} km sollte ein merkantiler Minderwert geprüft werden.",
                    {'alter_monate': alter_monate, 'km': km}
                ))
        else:
            # Höhe des Minderwerts prüfen
            if reparaturkosten and reparaturkosten > 0:
                prozent_von_reparatur = minderwert / reparaturkosten * 100
                if prozent_von_reparatur > self.MINDERWERT_FAKTOREN['prozent_von_reparatur_max']:
                    ergebnisse.append(self._erstelle_ergebnis(
                        PruefungsKategorie.MERKANTILER_MINDERWERT,
                        PruefungsSchwere.WARNUNG,
                        "Hoher merkantiler Minderwert",
                        f"Der merkantile Minderwert ({minderwert:,.2f} EUR = {prozent_von_reparatur:.1f}% der Reparaturkosten) erscheint hoch.",
                        {'minderwert': minderwert, 'prozent': prozent_von_reparatur}
                    ))

            if wbw and wbw > 0:
                prozent_von_wbw = minderwert / wbw * 100
                if prozent_von_wbw > self.MINDERWERT_FAKTOREN['prozent_von_wbw_max']:
                    ergebnisse.append(self._erstelle_ergebnis(
                        PruefungsKategorie.MERKANTILER_MINDERWERT,
                        PruefungsSchwere.WARNUNG,
                        "Merkantiler Minderwert über 10% des WBW",
                        f"Der merkantile Minderwert ({minderwert:,.2f} EUR = {prozent_von_wbw:.1f}% des WBW) übersteigt 10% des Wiederbeschaffungswertes.",
                        {'minderwert': minderwert, 'prozent': prozent_von_wbw}
                    ))

        return ergebnisse

    def _pruefe_nutzungsausfall(self, daten: Dict) -> List[Dict]:
        """Prüft den Nutzungsausfall"""
        ergebnisse = []

        nutzungsausfall_tag = daten.get('nutzungsausfall_pro_tag', 0)
        nutzungsausfall_gruppe = daten.get('nutzungsausfall_gruppe', '')
        reparaturdauer_tage = daten.get('reparaturdauer_tage', 0)

        if nutzungsausfall_tag and nutzungsausfall_gruppe:
            ref = self.NUTZUNGSAUSFALL_GRUPPEN.get(nutzungsausfall_gruppe.upper())

            if ref:
                if nutzungsausfall_tag > ref['max']:
                    ergebnisse.append(self._erstelle_ergebnis(
                        PruefungsKategorie.NUTZUNGSAUSFALL,
                        PruefungsSchwere.WARNUNG,
                        "Nutzungsausfall zu hoch",
                        f"Der Nutzungsausfall ({nutzungsausfall_tag:.2f} EUR/Tag) liegt über dem Höchstwert für Gruppe {nutzungsausfall_gruppe} (max. {ref['max']} EUR).",
                        {'betrag': nutzungsausfall_tag, 'gruppe': nutzungsausfall_gruppe, 'max': ref['max']}
                    ))
                elif nutzungsausfall_tag < ref['min']:
                    ergebnisse.append(self._erstelle_ergebnis(
                        PruefungsKategorie.NUTZUNGSAUSFALL,
                        PruefungsSchwere.INFO,
                        "Nutzungsausfall niedrig",
                        f"Der Nutzungsausfall ({nutzungsausfall_tag:.2f} EUR/Tag) liegt unter dem Mindestwert für Gruppe {nutzungsausfall_gruppe} (min. {ref['min']} EUR).",
                        {'betrag': nutzungsausfall_tag, 'gruppe': nutzungsausfall_gruppe, 'min': ref['min']}
                    ))

        # Reparaturdauer prüfen
        if reparaturdauer_tage:
            reparaturkosten = daten.get('reparaturkosten_netto', 0)

            # Faustformel: ca. 1.000-2.000 EUR Reparaturkosten pro Tag
            if reparaturkosten and reparaturkosten > 0:
                kosten_pro_tag = reparaturkosten / reparaturdauer_tage

                if kosten_pro_tag < 500:
                    ergebnisse.append(self._erstelle_ergebnis(
                        PruefungsKategorie.NUTZUNGSAUSFALL,
                        PruefungsSchwere.WARNUNG,
                        "Lange Reparaturdauer",
                        f"Die Reparaturdauer ({reparaturdauer_tage} Tage) erscheint im Verhältnis zu den Reparaturkosten ({reparaturkosten:,.2f} EUR) lang.",
                        {'tage': reparaturdauer_tage, 'kosten': reparaturkosten, 'kosten_pro_tag': kosten_pro_tag}
                    ))

        return ergebnisse

    def _pruefe_restwert(self, daten: Dict) -> List[Dict]:
        """Prüft den Restwert"""
        ergebnisse = []

        restwert = daten.get('restwert', 0)
        restwert_methode = daten.get('restwert_methode', '')

        if restwert:
            # Prüfen ob Restwertbörse genutzt wurde
            if not restwert_methode or restwert_methode.lower() not in ['restwertboerse', 'börse', 'online']:
                ergebnisse.append(self._erstelle_ergebnis(
                    PruefungsKategorie.RESTWERT,
                    PruefungsSchwere.INFO,
                    "Restwertermittlung prüfen",
                    "Es sollte geprüft werden, ob der Restwert über eine Restwertbörse ermittelt wurde (höherer Restwert möglich).",
                    {'restwert': restwert, 'methode': restwert_methode}
                ))

        return ergebnisse

    def _pruefe_totalschaden(self, daten: Dict) -> List[Dict]:
        """Prüft die Totalschaden-Bewertung"""
        ergebnisse = []

        wbw = daten.get('wiederbeschaffungswert', 0)
        restwert = daten.get('restwert', 0)
        reparaturkosten = daten.get('reparaturkosten_netto', 0)
        ist_totalschaden = daten.get('totalschaden', False)

        if wbw and reparaturkosten:
            grenze = wbw * self.TOTALSCHADEN_GRENZE_PROZENT / 100
            ist_wirtschaftlich_totalschaden = reparaturkosten > grenze

            if ist_wirtschaftlich_totalschaden and not ist_totalschaden:
                ergebnisse.append(self._erstelle_ergebnis(
                    PruefungsKategorie.TOTALSCHADEN,
                    PruefungsSchwere.KRITISCH,
                    "Wirtschaftlicher Totalschaden nicht erkannt",
                    f"Die Reparaturkosten ({reparaturkosten:,.2f} EUR) übersteigen die 130%-Grenze ({grenze:,.2f} EUR), aber das Gutachten weist keinen Totalschaden aus.",
                    {'reparaturkosten': reparaturkosten, 'grenze': grenze, 'wbw': wbw}
                ))
            elif not ist_wirtschaftlich_totalschaden and ist_totalschaden:
                ergebnisse.append(self._erstelle_ergebnis(
                    PruefungsKategorie.TOTALSCHADEN,
                    PruefungsSchwere.WARNUNG,
                    "Totalschaden möglicherweise zu Unrecht festgestellt",
                    f"Die Reparaturkosten ({reparaturkosten:,.2f} EUR) liegen unter der 130%-Grenze ({grenze:,.2f} EUR). Prüfen Sie die Totalschaden-Feststellung.",
                    {'reparaturkosten': reparaturkosten, 'grenze': grenze}
                ))

            # Abrechnungsbetrag bei Totalschaden
            if ist_totalschaden and restwert:
                abrechnungsbetrag = wbw - restwert
                if abrechnungsbetrag < reparaturkosten and reparaturkosten <= grenze:
                    ergebnisse.append(self._erstelle_ergebnis(
                        PruefungsKategorie.TOTALSCHADEN,
                        PruefungsSchwere.INFO,
                        "Reparatur möglicherweise wirtschaftlicher",
                        f"Bei Reparatur würden {reparaturkosten:,.2f} EUR erstattet, bei Totalschadenabrechnung nur {abrechnungsbetrag:,.2f} EUR (WBW - Restwert).",
                        {'reparatur': reparaturkosten, 'abrechnung': abrechnungsbetrag}
                    ))

        return ergebnisse

    def _pruefe_formal(self, daten: Dict) -> List[Dict]:
        """Prüft formale Aspekte"""
        ergebnisse = []

        # Pflichtangaben prüfen
        pflichtfelder = [
            ('gutachter_name', 'Gutachter-Name'),
            ('gutachten_datum', 'Gutachten-Datum'),
            ('kennzeichen', 'Kennzeichen'),
            ('fahrgestellnummer', 'Fahrgestellnummer'),
            ('erstzulassung', 'Erstzulassung'),
            ('kilometerstand', 'Kilometerstand'),
            ('wiederbeschaffungswert', 'Wiederbeschaffungswert')
        ]

        fehlende = []
        for feld, bezeichnung in pflichtfelder:
            if not daten.get(feld):
                fehlende.append(bezeichnung)

        if fehlende:
            ergebnisse.append(self._erstelle_ergebnis(
                PruefungsKategorie.FORMALES,
                PruefungsSchwere.WARNUNG,
                "Fehlende Pflichtangaben",
                f"Folgende Angaben fehlen im Gutachten: {', '.join(fehlende)}",
                {'fehlende_felder': fehlende}
            ))

        # Gutachten-Alter prüfen
        gutachten_datum = daten.get('gutachten_datum')
        if gutachten_datum:
            if isinstance(gutachten_datum, str):
                try:
                    g_date = datetime.strptime(gutachten_datum, '%Y-%m-%d').date()
                except:
                    g_date = None
            else:
                g_date = gutachten_datum

            if g_date:
                alter_tage = (date.today() - g_date).days
                if alter_tage > 180:
                    ergebnisse.append(self._erstelle_ergebnis(
                        PruefungsKategorie.FORMALES,
                        PruefungsSchwere.WARNUNG,
                        "Veraltetes Gutachten",
                        f"Das Gutachten ist {alter_tage} Tage alt. Aktuelle Marktwerte könnten abweichen.",
                        {'alter_tage': alter_tage}
                    ))

        return ergebnisse

    def _pruefe_allgemeine_plausibilitaet(self, daten: Dict) -> List[Dict]:
        """Prüft allgemeine Plausibilität"""
        ergebnisse = []

        # Rechenprobe: Summe der Einzelpositionen = Gesamtsumme?
        lohnkosten = daten.get('lohnkosten', 0)
        ersatzteilkosten = daten.get('ersatzteilkosten', 0)
        lackierkosten = daten.get('lackierkosten', 0)
        sonstige_kosten = daten.get('sonstige_kosten', 0)
        reparaturkosten = daten.get('reparaturkosten_netto', 0)

        if lohnkosten or ersatzteilkosten or lackierkosten:
            summe_einzeln = lohnkosten + ersatzteilkosten + lackierkosten + sonstige_kosten

            if reparaturkosten and abs(summe_einzeln - reparaturkosten) > 10:
                differenz = reparaturkosten - summe_einzeln
                ergebnisse.append(self._erstelle_ergebnis(
                    PruefungsKategorie.PLAUSIBILITAET,
                    PruefungsSchwere.WARNUNG,
                    "Rechenfehler bei Reparaturkosten",
                    f"Die Summe der Einzelpositionen ({summe_einzeln:,.2f} EUR) weicht von den Gesamtreparaturkosten ({reparaturkosten:,.2f} EUR) ab. Differenz: {differenz:,.2f} EUR",
                    {'summe': summe_einzeln, 'gesamt': reparaturkosten, 'differenz': differenz}
                ))

        return ergebnisse

    def pruefungen_fuer_projekt(self, projekt_id: int) -> List[GutachtenPruefung]:
        """Holt alle Prüfungen für ein Projekt"""
        return self.db.query(GutachtenPruefung).filter(
            GutachtenPruefung.projekt_id == projekt_id
        ).order_by(GutachtenPruefung.pruefung_am.desc()).all()

    def anwalt_kommentar_speichern(
        self,
        pruefung_id: int,
        kommentar: str
    ) -> Optional[GutachtenPruefung]:
        """Speichert einen Anwaltskommentar zur Prüfung"""
        pruefung = self.db.query(GutachtenPruefung).get(pruefung_id)

        if pruefung:
            pruefung.anwalt_kommentar = kommentar
            self.db.flush()

        return pruefung

    def generiere_pruefbericht(self, pruefung_id: int) -> str:
        """Generiert einen Prüfbericht als Text"""
        pruefung = self.db.query(GutachtenPruefung).get(pruefung_id)

        if not pruefung:
            return "Prüfung nicht gefunden"

        bericht = f"""
GUTACHTEN-PLAUSIBILITÄTSPRÜFUNG
================================

Gutachten-Nr.: {pruefung.gutachten_nr or '-'}
Gutachter: {pruefung.gutachter_name or '-'}
Gutachten-Datum: {pruefung.gutachten_datum.strftime('%d.%m.%Y') if pruefung.gutachten_datum else '-'}
Prüfung am: {pruefung.pruefung_am.strftime('%d.%m.%Y %H:%M') if pruefung.pruefung_am else '-'}

GESAMTBEWERTUNG: {pruefung.gesamtbewertung}
- Fehler: {pruefung.anzahl_fehler}
- Warnungen: {pruefung.anzahl_warnungen}
- Hinweise: {pruefung.anzahl_hinweise}

DETAILS:
"""
        for ergebnis in pruefung.pruefungsergebnisse:
            icon = {
                'FEHLER': '❌',
                'KRITISCH': '⚠️',
                'WARNUNG': '⚡',
                'INFO': 'ℹ️'
            }.get(ergebnis['schwere'], '•')

            bericht += f"""
{icon} [{ergebnis['kategorie']}] {ergebnis['titel']}
   {ergebnis['beschreibung']}
"""

        if pruefung.anwalt_kommentar:
            bericht += f"""
ANWALTSKOMMENTAR:
{pruefung.anwalt_kommentar}
"""

        return bericht
