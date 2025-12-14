"""
Automatische Dokumentenklassifizierung
Klassifiziert Dokumente anhand von Mustern, Keywords und OCR-Text
"""
import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

from sqlalchemy.orm import Session

from src.models import Dokument, DokumentTyp


@dataclass
class KlassifizierungsErgebnis:
    """Ergebnis einer Dokumentenklassifizierung"""
    dokument_typ: DokumentTyp
    konfidenz: float  # 0.0 - 1.0
    erkannte_merkmale: List[str]
    empfehlung: str


# Klassifizierungsregeln für jeden Dokumenttyp
KLASSIFIZIERUNGS_REGELN = {
    DokumentTyp.GUTACHTEN: {
        "keywords": [
            "gutachten", "sachverständig", "bewertung", "reparaturkosten",
            "wiederbeschaffungswert", "restwert", "merkantiler minderwert",
            "schadenkalkulation", "stundenverrechnungssatz", "lackierung",
            "fahrzeugbewertung", "technische daten", "schaden-nr",
            "dekra", "tüv", "gtü", "küs", "fsb"
        ],
        "muster": [
            r"gutachten.{0,20}nr\.?\s*:?\s*\d+",
            r"wiederbeschaffungswert\s*:?\s*[\d\.,]+\s*(?:€|eur)",
            r"restwert\s*:?\s*[\d\.,]+\s*(?:€|eur)",
            r"reparaturkosten\s*:?\s*[\d\.,]+\s*(?:€|eur)",
            r"merkantiler\s+minderwert",
            r"lohnkosten|materialkosten|lackierkosten"
        ],
        "dateiname_muster": [
            r"gutachten", r"expertise", r"bewertung", r"SV[\-_]"
        ],
        "gewicht": 1.0
    },

    DokumentTyp.FAHRZEUGSCHEIN: {
        "keywords": [
            "zulassungsbescheinigung", "fahrzeugschein", "teil i",
            "halter", "zulassungsstelle", "kennzeichen", "hersteller",
            "typ", "variante", "version", "erstzulassung",
            "fzg-id-nr", "kraftfahrt-bundesamt"
        ],
        "muster": [
            r"zulassungsbescheinigung\s+teil\s+i",
            r"fahrzeug-identifizierungsnummer",
            r"vin\s*:?\s*[A-Z0-9]{17}",
            r"kennzeichen\s*:?\s*[A-ZÄÖÜ]{1,3}[\-\s][A-Z]{1,2}\s*\d{1,4}",
            r"erstzulassung\s*:?\s*\d{2}[\./]\d{2}[\./]\d{4}"
        ],
        "dateiname_muster": [
            r"fahrzeugschein", r"zulassungsbescheinigung", r"fzs", r"teil.?i"
        ],
        "gewicht": 1.2
    },

    DokumentTyp.PERSONALAUSWEIS: {
        "keywords": [
            "personalausweis", "identity card", "ausweisnummer",
            "staatsangehörigkeit", "geburtsort", "geburtsdatum",
            "gültig bis", "ausweisbehörde", "bundesrepublik deutschland"
        ],
        "muster": [
            r"personalausweis",
            r"identity\s*card",
            r"ausweisnummer\s*:?\s*[A-Z0-9]+",
            r"gültig\s+bis\s*:?\s*\d{2}[\./]\d{2}[\./]\d{4}"
        ],
        "dateiname_muster": [
            r"ausweis", r"perso", r"id[\-_]?card"
        ],
        "gewicht": 1.0
    },

    DokumentTyp.RECHNUNG: {
        "keywords": [
            "rechnung", "invoice", "rechnungsnummer", "rechnungsbetrag",
            "mwst", "mehrwertsteuer", "ust", "netto", "brutto",
            "zahlbar bis", "zahlungsziel", "bankverbindung", "iban",
            "steuernummer", "ust-id"
        ],
        "muster": [
            r"rechnung\s*(?:nr\.?|nummer)\s*:?\s*\d+",
            r"rechnungsbetrag\s*:?\s*[\d\.,]+\s*(?:€|eur)",
            r"mwst\s*:?\s*19\s*%|7\s*%",
            r"gesamtbetrag\s*:?\s*[\d\.,]+\s*(?:€|eur)",
            r"zahlbar\s+bis\s*:?\s*\d{2}[\./]\d{2}[\./]\d{4}"
        ],
        "dateiname_muster": [
            r"rechnung", r"invoice", r"rg[\-_]?\d+"
        ],
        "gewicht": 1.0
    },

    DokumentTyp.VERSICHERUNGSSCHREIBEN: {
        "keywords": [
            "versicherung", "schadennummer", "versicherungsschein",
            "police", "deckungszusage", "regulierung",
            "versicherungsnehmer", "versicherungsfall", "prämie",
            "selbstbeteiligung", "vollkasko", "teilkasko", "haftpflicht"
        ],
        "muster": [
            r"schaden(?:s)?(?:nummer|nr\.?)\s*:?\s*[A-Z0-9\-]+",
            r"versicherungsschein(?:nummer|nr\.?)?\s*:?\s*[A-Z0-9\-]+",
            r"deckung(?:szusage|sbestätigung)",
            r"(?:huk|allianz|axa|generali|zurich|vgh|devk|ergo)"
        ],
        "dateiname_muster": [
            r"versicherung", r"police", r"schreiben[\-_]vers"
        ],
        "gewicht": 1.0
    },

    DokumentTyp.KUERZUNGSSCHREIBEN: {
        "keywords": [
            "kürzung", "abzug", "nicht erstattungsfähig",
            "ablehnung", "wir können nicht", "leider müssen wir",
            "beanstanden", "einwände", "nicht anerkennen",
            "minderung", "reduktion"
        ],
        "muster": [
            r"kürzung\s*:?\s*[\d\.,]+\s*(?:€|eur)",
            r"nicht\s+erstattungsfähig",
            r"abzug\s+(?:von|in\s+höhe\s+von)\s*[\d\.,]+",
            r"(?:können|müssen)\s+wir\s+(?:leider\s+)?(?:nicht|ablehnen)"
        ],
        "dateiname_muster": [
            r"kürzung", r"ablehnung", r"abzug"
        ],
        "gewicht": 1.1
    },

    DokumentTyp.ANSPRUCHSSCHREIBEN: {
        "keywords": [
            "anspruch", "forderung", "schadensersatz", "geltend machen",
            "erstattung", "regulierung", "zahlung", "innerhalb von",
            "auffordern", "anspruchsschreiben", "haftpflichtanspruch"
        ],
        "muster": [
            r"anspruch(?:s)?schreiben",
            r"(?:geltend|machen|fordern)\s+wir\s+(?:hiermit)?",
            r"forderung\s*:?\s*[\d\.,]+\s*(?:€|eur)",
            r"innerhalb\s+von\s+\d+\s+(?:tagen|wochen)"
        ],
        "dateiname_muster": [
            r"anspruch", r"forderung", r"schaden(?:s)?ersatz"
        ],
        "gewicht": 1.0
    },

    DokumentTyp.VOLLMACHT: {
        "keywords": [
            "vollmacht", "bevollmächtigen", "vertretung", "ermächtigen",
            "rechtsanwalt", "kanzlei", "mandant", "rechtsvertretung",
            "im namen und", "für mich zu handeln"
        ],
        "muster": [
            r"vollmacht",
            r"bevollmächtig(?:en|e|t)",
            r"ermächtig(?:en|e|t)\s+(?:hiermit)?",
            r"(?:herrn|frau)\s+rechtsanwalt",
            r"mich\s+(?:zu\s+)?vertreten"
        ],
        "dateiname_muster": [
            r"vollmacht"
        ],
        "gewicht": 1.2
    }
}


class DokumentenKlassifizierung:
    """Service für automatische Dokumentenklassifizierung"""

    def __init__(self, db: Session):
        self.db = db

    def klassifiziere(
        self,
        dokument: Dokument,
        ocr_text: Optional[str] = None
    ) -> KlassifizierungsErgebnis:
        """
        Klassifiziert ein Dokument automatisch.

        Args:
            dokument: Das zu klassifizierende Dokument
            ocr_text: Optional - OCR-Text (sonst wird dokument.ocr_text verwendet)

        Returns:
            KlassifizierungsErgebnis
        """
        text = (ocr_text or dokument.ocr_text or "").lower()
        dateiname = (dokument.original_dateiname or "").lower()

        ergebnisse = []

        for dok_typ, regeln in KLASSIFIZIERUNGS_REGELN.items():
            konfidenz = 0.0
            erkannte_merkmale = []

            # Keywords prüfen
            for keyword in regeln["keywords"]:
                if keyword in text:
                    konfidenz += 0.1
                    erkannte_merkmale.append(f"Keyword: {keyword}")

            # Muster prüfen
            for muster in regeln["muster"]:
                if re.search(muster, text, re.IGNORECASE):
                    konfidenz += 0.2
                    erkannte_merkmale.append(f"Muster: {muster[:30]}...")

            # Dateiname prüfen
            for muster in regeln["dateiname_muster"]:
                if re.search(muster, dateiname, re.IGNORECASE):
                    konfidenz += 0.15
                    erkannte_merkmale.append(f"Dateiname: {muster}")

            # Gewichtung anwenden
            konfidenz *= regeln["gewicht"]

            # Normalisieren auf max 1.0
            konfidenz = min(konfidenz, 1.0)

            if konfidenz > 0:
                ergebnisse.append({
                    "typ": dok_typ,
                    "konfidenz": konfidenz,
                    "merkmale": erkannte_merkmale
                })

        # Nach Konfidenz sortieren
        ergebnisse.sort(key=lambda x: x["konfidenz"], reverse=True)

        if ergebnisse:
            bestes = ergebnisse[0]
            empfehlung = self._generiere_empfehlung(bestes["konfidenz"])

            return KlassifizierungsErgebnis(
                dokument_typ=bestes["typ"],
                konfidenz=bestes["konfidenz"],
                erkannte_merkmale=bestes["merkmale"],
                empfehlung=empfehlung
            )
        else:
            return KlassifizierungsErgebnis(
                dokument_typ=DokumentTyp.SONSTIG,
                konfidenz=0.0,
                erkannte_merkmale=[],
                empfehlung="Keine automatische Klassifizierung möglich - bitte manuell prüfen"
            )

    def klassifiziere_batch(
        self,
        dokumente: List[Dokument]
    ) -> Dict[int, KlassifizierungsErgebnis]:
        """
        Klassifiziert mehrere Dokumente.

        Args:
            dokumente: Liste der zu klassifizierenden Dokumente

        Returns:
            Dictionary mit Dokument-ID als Key und Ergebnis als Value
        """
        ergebnisse = {}

        for dok in dokumente:
            ergebnisse[dok.id] = self.klassifiziere(dok)

        return ergebnisse

    def auto_klassifiziere_und_speichere(
        self,
        dokument: Dokument,
        min_konfidenz: float = 0.6
    ) -> Tuple[bool, str]:
        """
        Klassifiziert ein Dokument und speichert das Ergebnis.

        Args:
            dokument: Das zu klassifizierende Dokument
            min_konfidenz: Mindest-Konfidenz für automatisches Speichern

        Returns:
            Tuple (Erfolg, Nachricht)
        """
        ergebnis = self.klassifiziere(dokument)

        if ergebnis.konfidenz >= min_konfidenz:
            dokument.dokument_typ = ergebnis.dokument_typ
            self.db.flush()
            return True, f"Dokument als '{ergebnis.dokument_typ.value}' klassifiziert (Konfidenz: {ergebnis.konfidenz:.0%})"
        else:
            return False, f"Konfidenz zu niedrig ({ergebnis.konfidenz:.0%}). Vorschlag: {ergebnis.dokument_typ.value}"

    def _generiere_empfehlung(self, konfidenz: float) -> str:
        """Generiert eine Empfehlung basierend auf der Konfidenz"""
        if konfidenz >= 0.8:
            return "Hohe Übereinstimmung - automatische Klassifizierung empfohlen"
        elif konfidenz >= 0.6:
            return "Gute Übereinstimmung - Klassifizierung wahrscheinlich korrekt"
        elif konfidenz >= 0.4:
            return "Mittlere Übereinstimmung - manuelle Prüfung empfohlen"
        else:
            return "Niedrige Übereinstimmung - manuelle Klassifizierung erforderlich"


def get_klassifizierungs_service(db: Session) -> DokumentenKlassifizierung:
    """Factory-Funktion für den Klassifizierungs-Service"""
    return DokumentenKlassifizierung(db)
