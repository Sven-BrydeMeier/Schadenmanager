"""
KI-Textanalyse Service
Automatische Analyse von Gutachten, Kürzungsschreiben und anderen Dokumenten
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
import json
import re
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from src.models.base import Base


class AnalyseTyp(str, Enum):
    """Typen von Analysen"""
    GUTACHTEN = "GUTACHTEN"
    KUERZUNGSSCHREIBEN = "KUERZUNGSSCHREIBEN"
    ANSPRUCHSSCHREIBEN = "ANSPRUCHSSCHREIBEN"
    URTEIL = "URTEIL"
    POLIZEIBERICHT = "POLIZEIBERICHT"
    KORRESPONDENZ = "KORRESPONDENZ"
    ALLGEMEIN = "ALLGEMEIN"


class DokumentAnalyse(Base):
    """Model für Dokumentenanalysen"""
    __tablename__ = "dokument_analyse"

    id = Column(Integer, primary_key=True)

    # Dokument-Zuordnung
    dokument_id = Column(Integer, ForeignKey("dokument.id"), nullable=False)

    # Projekt-Zuordnung
    projekt_id = Column(Integer, ForeignKey("unfallprojekt.id"))

    # Analyse-Daten
    analyse_typ = Column(SQLEnum(AnalyseTyp), default=AnalyseTyp.ALLGEMEIN)
    zusammenfassung = Column(Text)

    # Extrahierte Daten (JSON)
    extrahierte_daten_json = Column(Text)

    # Schlüsselwörter und Erkenntnisse
    schluesselwoerter = Column(Text)  # Komma-separiert
    erkannte_betraege_json = Column(Text)  # JSON-Liste von Beträgen
    erkannte_daten_json = Column(Text)  # JSON-Liste von Daten

    # Bei Kürzungsschreiben
    kuerzungspositionen_json = Column(Text)  # JSON der Kürzungen
    kuerzungsgruende = Column(Text)

    # Bei Gutachten
    gutachten_ergebnis = Column(Text)
    schadenshoehe = Column(String(50))
    reparaturdauer = Column(String(50))

    # Handlungsempfehlungen
    empfehlungen = Column(Text)

    # Metadaten
    erstellt_von_user_id = Column(Integer, ForeignKey("user.id"))
    erstellt_am = Column(DateTime, default=datetime.now)

    @property
    def extrahierte_daten(self) -> Dict[str, Any]:
        """Parsed die extrahierten Daten"""
        try:
            return json.loads(self.extrahierte_daten_json) if self.extrahierte_daten_json else {}
        except json.JSONDecodeError:
            return {}

    @extrahierte_daten.setter
    def extrahierte_daten(self, wert: Dict[str, Any]):
        self.extrahierte_daten_json = json.dumps(wert)

    @property
    def erkannte_betraege(self) -> List[Dict[str, Any]]:
        try:
            return json.loads(self.erkannte_betraege_json) if self.erkannte_betraege_json else []
        except json.JSONDecodeError:
            return []

    @erkannte_betraege.setter
    def erkannte_betraege(self, wert: List[Dict[str, Any]]):
        self.erkannte_betraege_json = json.dumps(wert)

    @property
    def kuerzungspositionen(self) -> List[Dict[str, Any]]:
        try:
            return json.loads(self.kuerzungspositionen_json) if self.kuerzungspositionen_json else []
        except json.JSONDecodeError:
            return []

    @kuerzungspositionen.setter
    def kuerzungspositionen(self, wert: List[Dict[str, Any]]):
        self.kuerzungspositionen_json = json.dumps(wert)


class KIAnalyseService:
    """Service für KI-basierte Textanalyse"""

    # Schlüsselwörter für Dokumenttyp-Erkennung
    GUTACHTEN_KEYWORDS = [
        "gutachten", "sachverständig", "wiederbeschaffungswert", "reparaturkosten",
        "restwert", "wertminderung", "nutzungsausfall", "reparaturdauer",
        "fahrzeugbewertung", "schadensbild", "kalkulation"
    ]

    KUERZUNG_KEYWORDS = [
        "kürzung", "ablehnung", "nicht erstattungsfähig", "überhöht",
        "nicht nachvollziehbar", "abzug", "minderung", "erstattung abgelehnt",
        "regulierung", "schadenersatz", "nicht begründet"
    ]

    # Muster für Betragsextraktion
    BETRAG_PATTERN = r'(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)\s*(?:EUR|€|Euro)'

    # Muster für Datumsextraktion
    DATUM_PATTERN = r'(\d{1,2})[./](\d{1,2})[./](\d{2,4})'

    def __init__(self, db_session):
        self.db = db_session

    def analysiere_dokument(
        self,
        dokument_id: int,
        text_inhalt: str,
        projekt_id: Optional[int] = None,
        erstellt_von_user_id: Optional[int] = None
    ) -> DokumentAnalyse:
        """Analysiert ein Dokument und extrahiert relevante Informationen"""

        # Dokumenttyp erkennen
        analyse_typ = self._erkenne_dokumenttyp(text_inhalt)

        # Beträge extrahieren
        betraege = self._extrahiere_betraege(text_inhalt)

        # Daten extrahieren
        daten = self._extrahiere_daten(text_inhalt)

        # Schlüsselwörter extrahieren
        schluesselwoerter = self._extrahiere_schluesselwoerter(text_inhalt)

        # Zusammenfassung generieren
        zusammenfassung = self._generiere_zusammenfassung(text_inhalt, analyse_typ)

        # Spezifische Analyse je nach Typ
        kuerzungspositionen = []
        kuerzungsgruende = None
        gutachten_ergebnis = None
        schadenshoehe = None
        reparaturdauer = None
        empfehlungen = None

        if analyse_typ == AnalyseTyp.KUERZUNGSSCHREIBEN:
            kuerzungspositionen = self._analysiere_kuerzungen(text_inhalt)
            kuerzungsgruende = self._extrahiere_kuerzungsgruende(text_inhalt)
            empfehlungen = self._generiere_kuerzungs_empfehlungen(kuerzungspositionen)

        elif analyse_typ == AnalyseTyp.GUTACHTEN:
            gutachten_daten = self._analysiere_gutachten(text_inhalt)
            gutachten_ergebnis = gutachten_daten.get("ergebnis")
            schadenshoehe = gutachten_daten.get("schadenshoehe")
            reparaturdauer = gutachten_daten.get("reparaturdauer")
            empfehlungen = self._generiere_gutachten_empfehlungen(gutachten_daten)

        # Analyse speichern
        analyse = DokumentAnalyse(
            dokument_id=dokument_id,
            projekt_id=projekt_id,
            analyse_typ=analyse_typ,
            zusammenfassung=zusammenfassung,
            schluesselwoerter=", ".join(schluesselwoerter),
            kuerzungsgruende=kuerzungsgruende,
            gutachten_ergebnis=gutachten_ergebnis,
            schadenshoehe=schadenshoehe,
            reparaturdauer=reparaturdauer,
            empfehlungen=empfehlungen,
            erstellt_von_user_id=erstellt_von_user_id
        )

        analyse.erkannte_betraege = betraege
        analyse.kuerzungspositionen = kuerzungspositionen

        self.db.add(analyse)
        self.db.flush()

        return analyse

    def _erkenne_dokumenttyp(self, text: str) -> AnalyseTyp:
        """Erkennt den Dokumenttyp anhand von Schlüsselwörtern"""
        text_lower = text.lower()

        gutachten_score = sum(1 for kw in self.GUTACHTEN_KEYWORDS if kw in text_lower)
        kuerzung_score = sum(1 for kw in self.KUERZUNG_KEYWORDS if kw in text_lower)

        if gutachten_score > kuerzung_score and gutachten_score >= 3:
            return AnalyseTyp.GUTACHTEN
        elif kuerzung_score > gutachten_score and kuerzung_score >= 2:
            return AnalyseTyp.KUERZUNGSSCHREIBEN
        elif "polizei" in text_lower or "unfallbericht" in text_lower:
            return AnalyseTyp.POLIZEIBERICHT
        elif "urteil" in text_lower or "beschluss" in text_lower:
            return AnalyseTyp.URTEIL
        elif "anspruch" in text_lower and "schaden" in text_lower:
            return AnalyseTyp.ANSPRUCHSSCHREIBEN

        return AnalyseTyp.ALLGEMEIN

    def _extrahiere_betraege(self, text: str) -> List[Dict[str, Any]]:
        """Extrahiert alle Geldbeträge aus dem Text"""
        betraege = []

        for match in re.finditer(self.BETRAG_PATTERN, text):
            betrag_str = match.group(1).replace(".", "").replace(",", ".")
            try:
                betrag = float(betrag_str)

                # Kontext finden (50 Zeichen vor und nach)
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                kontext = text[start:end].strip()

                betraege.append({
                    "betrag": betrag,
                    "original": match.group(0),
                    "kontext": kontext
                })
            except ValueError:
                pass

        return betraege

    def _extrahiere_daten(self, text: str) -> List[str]:
        """Extrahiert alle Datumsangaben aus dem Text"""
        daten = []

        for match in re.finditer(self.DATUM_PATTERN, text):
            tag, monat, jahr = match.groups()
            if len(jahr) == 2:
                jahr = "20" + jahr if int(jahr) < 50 else "19" + jahr
            daten.append(f"{tag}.{monat}.{jahr}")

        return list(set(daten))

    def _extrahiere_schluesselwoerter(self, text: str) -> List[str]:
        """Extrahiert relevante Schlüsselwörter"""
        text_lower = text.lower()
        gefunden = []

        alle_keywords = self.GUTACHTEN_KEYWORDS + self.KUERZUNG_KEYWORDS + [
            "totalschaden", "wirtschaftlicher totalschaden", "reparaturwürdig",
            "haftpflicht", "kasko", "vollkasko", "selbstbeteiligung",
            "mietwagen", "nutzungsentschädigung", "schmerzensgeld",
            "heilbehandlung", "arbeitsunfähigkeit", "haushaltsführung"
        ]

        for kw in alle_keywords:
            if kw in text_lower:
                gefunden.append(kw)

        return gefunden[:20]  # Max 20 Keywords

    def _generiere_zusammenfassung(self, text: str, typ: AnalyseTyp) -> str:
        """Generiert eine kurze Zusammenfassung des Dokuments"""
        # Erste Sätze extrahieren (max 500 Zeichen)
        saetze = text.split(".")
        zusammenfassung_teile = []
        laenge = 0

        for satz in saetze[:10]:
            satz = satz.strip()
            if len(satz) > 20 and laenge + len(satz) < 500:
                zusammenfassung_teile.append(satz)
                laenge += len(satz)

        basis_zusammenfassung = ". ".join(zusammenfassung_teile) + "." if zusammenfassung_teile else ""

        typ_info = {
            AnalyseTyp.GUTACHTEN: "Dieses Dokument ist ein Schadensgutachten.",
            AnalyseTyp.KUERZUNGSSCHREIBEN: "Dieses Dokument ist ein Kürzungsschreiben der Versicherung.",
            AnalyseTyp.ANSPRUCHSSCHREIBEN: "Dieses Dokument ist ein Anspruchsschreiben.",
            AnalyseTyp.POLIZEIBERICHT: "Dieses Dokument ist ein Polizeibericht.",
            AnalyseTyp.URTEIL: "Dieses Dokument ist ein Gerichtsurteil oder Beschluss.",
            AnalyseTyp.ALLGEMEIN: "Dokumenttyp nicht eindeutig erkannt."
        }.get(typ, "")

        return f"{typ_info}\n\n{basis_zusammenfassung}"

    def _analysiere_kuerzungen(self, text: str) -> List[Dict[str, Any]]:
        """Analysiert Kürzungspositionen aus einem Kürzungsschreiben"""
        kuerzungen = []
        text_lower = text.lower()

        # Typische Kürzungskategorien
        kategorien = [
            ("reparaturkosten", ["reparaturkosten", "reparatur"]),
            ("mietwagenkosten", ["mietwagen", "ersatzfahrzeug"]),
            ("nutzungsausfall", ["nutzungsausfall", "nutzungsentschädigung"]),
            ("gutachterkosten", ["gutachterkosten", "sachverständigenkosten"]),
            ("anwaltskosten", ["anwaltskosten", "rechtsanwaltskosten"]),
            ("abschleppkosten", ["abschleppkosten", "bergen"]),
            ("wertminderung", ["wertminderung", "merkantiler minderwert"]),
            ("ummeldungskosten", ["ummeldung", "zulassung"]),
            ("kostenpauschale", ["kostenpauschale", "auslagenpauschale"])
        ]

        for kategorie, keywords in kategorien:
            for kw in keywords:
                if kw in text_lower:
                    # Versuche Betrag in der Nähe zu finden
                    idx = text_lower.find(kw)
                    umgebung = text[max(0, idx-100):min(len(text), idx+200)]

                    betrag_match = re.search(self.BETRAG_PATTERN, umgebung)
                    betrag = None
                    if betrag_match:
                        try:
                            betrag = float(betrag_match.group(1).replace(".", "").replace(",", "."))
                        except ValueError:
                            pass

                    kuerzungen.append({
                        "kategorie": kategorie,
                        "betrag": betrag,
                        "kontext": umgebung.strip()
                    })
                    break

        return kuerzungen

    def _extrahiere_kuerzungsgruende(self, text: str) -> str:
        """Extrahiert die Begründungen für Kürzungen"""
        gruende = []
        text_lower = text.lower()

        grund_patterns = [
            "überhöht", "nicht erforderlich", "nicht nachvollziehbar",
            "nicht erstattungsfähig", "nicht vereinbart", "unangemessen",
            "nicht belegt", "nicht nachgewiesen", "ortsüblich überschritten"
        ]

        for pattern in grund_patterns:
            if pattern in text_lower:
                gruende.append(pattern)

        return ", ".join(gruende) if gruende else None

    def _generiere_kuerzungs_empfehlungen(self, kuerzungen: List[Dict[str, Any]]) -> str:
        """Generiert Empfehlungen für den Umgang mit Kürzungen"""
        if not kuerzungen:
            return "Keine konkreten Kürzungspositionen erkannt."

        empfehlungen = ["### Handlungsempfehlungen\n"]

        for kuerzung in kuerzungen:
            kat = kuerzung.get("kategorie", "")

            if kat == "reparaturkosten":
                empfehlungen.append("- **Reparaturkosten**: Kostenvoranschlag der Werkstatt mit Gutachten vergleichen. Bei Differenzen detaillierte Aufstellung anfordern.")
            elif kat == "mietwagenkosten":
                empfehlungen.append("- **Mietwagenkosten**: Schwacke/Fraunhofer-Liste prüfen. Ggf. günstigeres Angebot dokumentieren oder Nutzungsausfall geltend machen.")
            elif kat == "nutzungsausfall":
                empfehlungen.append("- **Nutzungsausfall**: Fahrzeugklasse nach Sanden/Danner prüfen. Tatsächliche Ausfallzeit dokumentieren.")
            elif kat == "gutachterkosten":
                empfehlungen.append("- **Gutachterkosten**: BVSK-Honorarbefragung heranziehen. Rechnung auf Angemessenheit prüfen.")
            elif kat == "wertminderung":
                empfehlungen.append("- **Wertminderung**: Bei Ablehnung: Fahrzeugalter, Laufleistung und Reparaturumfang argumentativ darlegen.")

        empfehlungen.append("\n**Generelle Empfehlung**: Kürzungsschreiben detailliert beantworten und für jeden Punkt Gegenargumente mit Belegen vorbringen.")

        return "\n".join(empfehlungen)

    def _analysiere_gutachten(self, text: str) -> Dict[str, Any]:
        """Analysiert ein Schadensgutachten"""
        ergebnis = {}
        text_lower = text.lower()

        # Schadenshöhe suchen
        for keyword in ["reparaturkosten", "schadenshöhe", "gesamtschaden"]:
            if keyword in text_lower:
                idx = text_lower.find(keyword)
                umgebung = text[idx:min(len(text), idx+200)]
                betrag_match = re.search(self.BETRAG_PATTERN, umgebung)
                if betrag_match:
                    ergebnis["schadenshoehe"] = betrag_match.group(0)
                    break

        # Reparaturdauer suchen
        dauer_pattern = r'(\d+)\s*(?:Arbeitstage?|Tage?|AT)'
        dauer_match = re.search(dauer_pattern, text, re.IGNORECASE)
        if dauer_match:
            ergebnis["reparaturdauer"] = f"{dauer_match.group(1)} Arbeitstage"

        # Totalschaden erkennen
        if "totalschaden" in text_lower or "wirtschaftlicher totalschaden" in text_lower:
            ergebnis["ergebnis"] = "Wirtschaftlicher Totalschaden"
        elif "reparaturwürdig" in text_lower:
            ergebnis["ergebnis"] = "Reparaturwürdig"

        return ergebnis

    def _generiere_gutachten_empfehlungen(self, gutachten_daten: Dict[str, Any]) -> str:
        """Generiert Empfehlungen basierend auf Gutachten-Daten"""
        empfehlungen = ["### Handlungsempfehlungen\n"]

        if gutachten_daten.get("ergebnis") == "Wirtschaftlicher Totalschaden":
            empfehlungen.append("- Wiederbeschaffungswert und Restwert prüfen")
            empfehlungen.append("- Restwertangebote über Restwertbörse einholen")
            empfehlungen.append("- Nutzungsausfallentschädigung für Wiederbeschaffungszeitraum geltend machen")
        else:
            empfehlungen.append("- Reparaturfreigabe bei Werkstatt einholen")
            empfehlungen.append("- Mietwagen oder Nutzungsausfall für Reparaturdauer")
            empfehlungen.append("- Wertminderung prüfen (bei Fahrzeugen < 5 Jahre oder < 100.000 km)")

        return "\n".join(empfehlungen)

    def analysen_fuer_projekt(self, projekt_id: int) -> List[DokumentAnalyse]:
        """Holt alle Analysen für ein Projekt"""
        return self.db.query(DokumentAnalyse).filter(
            DokumentAnalyse.projekt_id == projekt_id
        ).order_by(DokumentAnalyse.erstellt_am.desc()).all()

    def analyse_fuer_dokument(self, dokument_id: int) -> Optional[DokumentAnalyse]:
        """Holt die Analyse für ein Dokument"""
        return self.db.query(DokumentAnalyse).filter(
            DokumentAnalyse.dokument_id == dokument_id
        ).first()
