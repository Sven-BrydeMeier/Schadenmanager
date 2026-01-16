"""
RA-Micro Aktengestalter PDF Parser
Extrahiert Daten aus RA-Micro PDF-Akten für den Schadenmanager

Analysiert:
- Aktenvorblatt (Beteiligte, Aktenzeichen, Gegenstandswert)
- Bookmarks zur Dokumententrennung
- Schadenskosten und Kostenpositionen
- Gutachten-Informationen
"""
from __future__ import annotations

import io
import re
import json
from dataclasses import dataclass, asdict, field
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

import pdfplumber

# Regex-Pattern
DATE_RE = re.compile(r"\b(\d{1,2})\.(\d{1,2})\.(\d{4})\b")
AZ_RE = re.compile(r"\b(\d{1,5}/\d{2})\b")
EUR_RE = re.compile(r"(?<!\d)(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)(?:\s?€|\s*EUR)\b", re.IGNORECASE)
EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_RE = re.compile(r"\b0\d{1,5}(?:[ /-]?\d{2,}){2,}\b")
MOBILE_RE = re.compile(r"\b01\d{1,4}(?:[ /-]?\d{2,}){2,}\b")
PLZ_CITY_RE = re.compile(r"\b(\d{5})\s+([A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß .-]+)\b")
STREET_RE = re.compile(
    r"\b([A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß .-]+(?:straße|str\.|weg|platz|allee|ring|damm|gasse|berg|ufer))\s+(\d+[A-Za-z]?)\b",
    re.IGNORECASE,
)
KENNZEICHEN_RE = re.compile(r"\b([A-ZÄÖÜ]{1,3})[- ]?([A-Z]{1,2})[- ]?(\d{1,4})\b")
IBAN_RE = re.compile(r"\b(DE\d{2}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{2})\b", re.IGNORECASE)

# Keywords für Aktenvorblatt-Erkennung
COVER_KEYWORDS_ALL = ["GEGNER", "AUFTRAGGEBER"]
COVER_KEYWORDS_ANY = ["Aktennr", "Aktenzeichen", "GEGENSTANDSWERT", "FRISTEN", "MANDANT"]

# Keywords für Schadenfall-spezifische Erkennung
SCHADEN_KEYWORDS = [
    "Unfall", "Schaden", "Verkehrsunfall", "Gutachten", "Reparatur",
    "Haftpflicht", "Kasko", "Schadensersatz", "Nutzungsausfall",
    "Mietwagen", "Wertminderung", "merkantil"
]


class BeteiligterTyp(str, Enum):
    MANDANT = "MANDANT"
    UNFALLGEGNER = "UNFALLGEGNER"
    VERSICHERUNG_GEGNER = "VERSICHERUNG_GEGNER"
    VERSICHERUNG_EIGEN = "VERSICHERUNG_EIGEN"
    WERKSTATT = "WERKSTATT"
    GUTACHTER = "GUTACHTER"
    SONSTIG = "SONSTIG"


@dataclass
class Beteiligter:
    """Beteiligte Person/Organisation aus der Akte"""
    typ: BeteiligterTyp
    name: Optional[str] = None
    vorname: Optional[str] = None
    firma: Optional[str] = None
    strasse: Optional[str] = None
    plz: Optional[str] = None
    ort: Optional[str] = None
    telefon: List[str] = field(default_factory=list)
    mobil: List[str] = field(default_factory=list)
    fax: List[str] = field(default_factory=list)
    email: List[str] = field(default_factory=list)
    iban: Optional[str] = None
    kennzeichen: Optional[str] = None
    versicherungsnummer: Optional[str] = None
    raw_text: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["typ"] = self.typ.value
        return d


@dataclass
class Kostenposition:
    """Extrahierte Kostenposition"""
    kategorie: str
    beschreibung: str
    betrag: float
    brutto: bool = True
    seite: Optional[int] = None
    raw_text: Optional[str] = None


@dataclass
class DokumentSegment:
    """Ein Dokumentsegment aus dem PDF"""
    titel: str
    start_seite: int
    end_seite: int
    typ: Optional[str] = None
    bookmark_titel: Optional[str] = None


@dataclass
class RAMicroAkteErgebnis:
    """Ergebnis der RA-Micro Akten-Analyse"""
    aktenzeichen: Optional[str] = None
    aktenzeichen_nummer: Optional[int] = None
    aktenzeichen_jahr: Optional[int] = None
    kurzbezeichnung: Optional[str] = None
    unfalldatum: Optional[date] = None
    unfallort: Optional[str] = None
    gegenstandswert: Optional[float] = None
    beteiligte: List[Beteiligter] = field(default_factory=list)
    kostenpositionen: List[Kostenposition] = field(default_factory=list)
    dokument_segmente: List[DokumentSegment] = field(default_factory=list)
    cover_page_index: Optional[int] = None
    seitenzahl: int = 0
    fehler: List[str] = field(default_factory=list)
    raw_cover_text: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "aktenzeichen": self.aktenzeichen,
            "aktenzeichen_nummer": self.aktenzeichen_nummer,
            "aktenzeichen_jahr": self.aktenzeichen_jahr,
            "kurzbezeichnung": self.kurzbezeichnung,
            "unfalldatum": self.unfalldatum.isoformat() if self.unfalldatum else None,
            "unfallort": self.unfallort,
            "gegenstandswert": self.gegenstandswert,
            "beteiligte": [b.to_dict() for b in self.beteiligte],
            "kostenpositionen": [asdict(k) for k in self.kostenpositionen],
            "dokument_segmente": [asdict(d) for d in self.dokument_segmente],
            "cover_page_index": self.cover_page_index,
            "seitenzahl": self.seitenzahl,
            "fehler": self.fehler,
        }


def _parse_date(text: str) -> Optional[date]:
    """Parst ein deutsches Datum"""
    m = DATE_RE.search(text)
    if not m:
        return None
    day, month, year = map(int, m.groups())
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _eur_to_float(s: str) -> float:
    """Konvertiert deutschen Währungsstring zu float"""
    s = s.strip()
    s = s.replace(".", "").replace(" ", "")
    s = s.replace(",", ".")
    return float(s)


def _normalize_spaces(text: str) -> str:
    """Normalisiert Whitespace"""
    text = text.replace("\u00a0", " ")
    text = "\n".join(" ".join(line.split()) for line in text.splitlines())
    return text.strip()


def _extract_block(text: str, start_label: str, end_labels: List[str]) -> Optional[str]:
    """Extrahiert einen Textblock zwischen Labels"""
    start = text.find(start_label)
    if start < 0:
        return None
    sub = text[start:]
    end_positions = []
    for el in end_labels:
        p = sub.find(el)
        if p > 0:
            end_positions.append(p)
    end = min(end_positions) if end_positions else len(sub)
    return sub[:end].strip()


def _extract_address(block: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Extrahiert Adresse aus einem Textblock"""
    street = None
    plz = None
    ort = None
    for line in block.splitlines():
        if street is None:
            m = STREET_RE.search(line)
            if m:
                street = f"{m.group(1)} {m.group(2)}"
        if plz is None:
            m2 = PLZ_CITY_RE.search(line)
            if m2:
                plz, ort = m2.group(1), m2.group(2).strip()
    return street, plz, ort


def _extract_contacts(block: str) -> Dict[str, List[str]]:
    """Extrahiert Kontaktdaten aus einem Textblock"""
    emails = sorted(set(EMAIL_RE.findall(block)))
    phones = sorted(set(PHONE_RE.findall(block)))
    mobiles = sorted(set(MOBILE_RE.findall(block)))
    fax = []
    for line in block.splitlines():
        if "fax" in line.lower():
            fax.extend(PHONE_RE.findall(line))
    fax = sorted(set(fax))
    phones = [p for p in phones if p not in mobiles]
    return {"email": emails, "telefon": phones, "mobil": mobiles, "fax": fax}


def _extract_name_from_block(block: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Extrahiert Name/Vorname/Firma aus Block"""
    lines = [l.strip() for l in block.splitlines() if l.strip()]
    firma = None
    name = None
    vorname = None

    for line in lines:
        # Firma-Keywords
        if any(kw in line for kw in ["GmbH", "mbH", "AG", "KG", "OHG", "e.K.", "UG"]):
            firma = line.split(" Tel")[0].split(" Fax")[0].strip(" :")
            continue

        # Normale Namen (Nachname, Vorname oder Vorname Nachname)
        if len(line) >= 3 and not line.lower().startswith(("adressnr", "tel", "fax", "e-mail", "email", "mobil")):
            clean = line.split(" Tel")[0].split(" Fax")[0].strip(" :")
            if "," in clean:
                parts = clean.split(",")
                name = parts[0].strip()
                vorname = parts[1].strip() if len(parts) > 1 else None
            elif " " in clean and not firma:
                parts = clean.split()
                if len(parts) == 2:
                    vorname = parts[0]
                    name = parts[1]
                elif len(parts) > 2:
                    vorname = parts[0]
                    name = " ".join(parts[1:])
            elif not name:
                name = clean
            break

    return name, vorname, firma


class RAMicroParser:
    """Parser für RA-Micro Aktengestalter PDFs"""

    def __init__(self, enable_ocr: bool = False, ocr_dpi: int = 300):
        self.enable_ocr = enable_ocr
        self.ocr_dpi = ocr_dpi
        self._pytesseract = None

        if enable_ocr:
            try:
                import pytesseract
                self._pytesseract = pytesseract
            except ImportError:
                pass

    def parse(self, pdf_bytes: bytes, filename: Optional[str] = None) -> RAMicroAkteErgebnis:
        """
        Parst ein RA-Micro PDF und extrahiert alle relevanten Daten.

        Args:
            pdf_bytes: PDF-Datei als Bytes
            filename: Optional - Dateiname für zusätzliche Metadaten

        Returns:
            RAMicroAkteErgebnis mit allen extrahierten Daten
        """
        ergebnis = RAMicroAkteErgebnis()

        try:
            # Text seitenweise extrahieren
            pages = self._extract_pages(pdf_bytes)
            ergebnis.seitenzahl = len(pages)

            if not pages:
                ergebnis.fehler.append("Keine Seiten im PDF gefunden")
                return ergebnis

            # Bookmarks für Dokumententrennung extrahieren
            bookmarks = self._extract_bookmarks(pdf_bytes)
            if bookmarks:
                ergebnis.dokument_segmente = self._bookmarks_to_segments(bookmarks, len(pages))

            # Aktenvorblatt finden
            cover_idx = self._find_cover_page(pages)
            ergebnis.cover_page_index = cover_idx

            if cover_idx is not None:
                cover_text = pages[cover_idx]
                ergebnis.raw_cover_text = cover_text
                self._parse_cover_page(cover_text, ergebnis)

            # Gesamttext für weitere Analyse
            full_text = "\n".join(pages)

            # Kostenpositionen extrahieren
            self._extract_costs(pages, ergebnis)

            # Unfalldatum und -ort suchen
            self._extract_unfall_info(full_text, ergebnis)

            # Aktenzeichen aus Dateiname (Fallback)
            if not ergebnis.aktenzeichen and filename:
                m = re.search(r"\b(\d{1,5})[-_/](\d{2})\b", filename)
                if m:
                    ergebnis.aktenzeichen = f"{m.group(1)}/{m.group(2)}"
                    self._parse_aktenzeichen(ergebnis.aktenzeichen, ergebnis)

        except Exception as e:
            ergebnis.fehler.append(f"Parse-Fehler: {str(e)}")

        return ergebnis

    def _extract_pages(self, pdf_bytes: bytes) -> List[str]:
        """Extrahiert Text seitenweise aus PDF"""
        pages = []

        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                txt = page.extract_text() or ""
                txt = _normalize_spaces(txt)

                # OCR-Fallback wenn Text zu kurz
                if self._pytesseract and len(txt) < 40:
                    try:
                        pil_img = page.to_image(resolution=self.ocr_dpi).original
                        ocr_txt = self._pytesseract.image_to_string(pil_img, lang="deu")
                        txt = _normalize_spaces(ocr_txt or "")
                    except Exception:
                        pass

                pages.append(txt)

        return pages

    def _extract_bookmarks(self, pdf_bytes: bytes) -> List[Dict[str, Any]]:
        """Extrahiert Bookmarks/Outline aus PDF"""
        bookmarks = []

        try:
            import fitz  # PyMuPDF

            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            toc = doc.get_toc()

            for item in toc:
                level, title, page = item
                bookmarks.append({
                    "level": level,
                    "title": title,
                    "page": page
                })

            doc.close()
        except ImportError:
            pass  # PyMuPDF nicht verfügbar
        except Exception:
            pass

        return bookmarks

    def _bookmarks_to_segments(self, bookmarks: List[Dict], total_pages: int) -> List[DokumentSegment]:
        """Konvertiert Bookmarks in Dokument-Segmente"""
        segments = []

        for i, bm in enumerate(bookmarks):
            start = bm["page"]
            end = bookmarks[i + 1]["page"] - 1 if i + 1 < len(bookmarks) else total_pages

            # Dokumenttyp aus Titel ableiten
            titel = bm["title"]
            typ = self._detect_document_type(titel)

            segments.append(DokumentSegment(
                titel=titel,
                start_seite=start,
                end_seite=end,
                typ=typ,
                bookmark_titel=titel
            ))

        return segments

    def _detect_document_type(self, titel: str) -> Optional[str]:
        """Erkennt Dokumenttyp aus Bookmark-Titel"""
        titel_lower = titel.lower()

        type_mappings = [
            (["gutachten", "schadensgutachten", "kfz-gutachten"], "GUTACHTEN"),
            (["rechnung", "werkstattrechnung", "reparaturrechnung"], "RECHNUNG"),
            (["kürzung", "kuerzung", "regulierung"], "KUERZUNGSSCHREIBEN"),
            (["anspruch", "forderung", "geltendmachung"], "ANSPRUCHSSCHREIBEN"),
            (["vollmacht"], "VOLLMACHT"),
            (["versicherung", "schadenmeldung"], "VERSICHERUNGSSCHREIBEN"),
            (["fahrzeugschein", "zulassung"], "FAHRZEUGSCHEIN"),
            (["polizei", "unfallbericht"], "POLIZEIBERICHT"),
            (["foto", "bild", "lichtbild"], "FOTOS"),
            (["vorblatt", "akte", "deckblatt"], "AKTENVORBLATT"),
        ]

        for keywords, doc_type in type_mappings:
            if any(kw in titel_lower for kw in keywords):
                return doc_type

        return "SONSTIG"

    def _find_cover_page(self, pages: List[str]) -> Optional[int]:
        """Findet das Aktenvorblatt"""
        # Erst am Ende suchen (üblich bei RA-Micro)
        for idx in range(len(pages) - 1, -1, -1):
            t = pages[idx]
            if all(k in t for k in COVER_KEYWORDS_ALL) and any(k in t for k in COVER_KEYWORDS_ANY):
                return idx

        # Dann am Anfang
        for idx, t in enumerate(pages):
            if all(k in t for k in COVER_KEYWORDS_ALL) and any(k in t for k in COVER_KEYWORDS_ANY):
                return idx

        # Fallback: Seite mit "Aktenvorblatt" oder "Deckblatt"
        for idx, t in enumerate(pages):
            if "aktenvorblatt" in t.lower() or "deckblatt" in t.lower():
                return idx

        return None

    def _parse_cover_page(self, cover_text: str, ergebnis: RAMicroAkteErgebnis):
        """Parst das Aktenvorblatt"""

        # Aktenzeichen
        m = re.search(r"Aktennr\.?:?\s*([0-9]{1,5}/[0-9]{2})", cover_text)
        if m:
            ergebnis.aktenzeichen = m.group(1)
        else:
            m2 = AZ_RE.search(cover_text)
            if m2:
                ergebnis.aktenzeichen = m2.group(1)

        if ergebnis.aktenzeichen:
            self._parse_aktenzeichen(ergebnis.aktenzeichen, ergebnis)

        # Kurzbezeichnung
        m3 = re.search(r"\b(.+?\./\.\s*.+?)\b", cover_text)
        if m3:
            ergebnis.kurzbezeichnung = m3.group(1).strip()

        # Gegenstandswert
        gw_match = re.search(r"GEGENSTANDSWERT:?\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)\s*(?:€|EUR)?", cover_text, re.IGNORECASE)
        if gw_match:
            try:
                ergebnis.gegenstandswert = _eur_to_float(gw_match.group(1))
            except ValueError:
                pass

        # Beteiligte extrahieren
        self._extract_parties(cover_text, ergebnis)

    def _parse_aktenzeichen(self, az: str, ergebnis: RAMicroAkteErgebnis):
        """Parst Aktenzeichen in Nummer und Jahr"""
        if "/" in az:
            parts = az.split("/")
            try:
                ergebnis.aktenzeichen_nummer = int(parts[0])
                jahr = int(parts[1])
                ergebnis.aktenzeichen_jahr = 2000 + jahr if jahr < 100 else jahr
            except ValueError:
                pass

    def _extract_parties(self, cover_text: str, ergebnis: RAMicroAkteErgebnis):
        """Extrahiert Beteiligte aus dem Aktenvorblatt"""

        # Verschiedene Label-Varianten für Mandant
        mandant_labels = [
            "AUFTRAGGEBER:", "AUFTRAGGEBER", "MANDANT:", "MANDANT",
            "GESCHÄDIGTER:", "GESCHÄDIGTER", "GESCHAEDIGTER:", "GESCHAEDIGTER",
            "KLÄGER:", "KLÄGER", "KLAEGER:", "KLAEGER",
            "ANTRAGSTELLER:", "ANTRAGSTELLER"
        ]

        mandant_block = None
        for label in mandant_labels:
            mandant_block = _extract_block(
                cover_text,
                label,
                end_labels=["GEGNERVERTRETER:", "GEGNER:", "VERSICHERUNG:", "UNFALLGEGNER:",
                           "SCHÄDIGER:", "SCHAEDIGER:", "BEKLAGTER:", "ANTRAGSGEGNER:"]
            )
            if mandant_block and len(mandant_block) > 20:
                break

        if mandant_block:
            beteiligter = self._parse_party_block(mandant_block, BeteiligterTyp.MANDANT)
            if beteiligter:
                ergebnis.beteiligte.append(beteiligter)

        # Verschiedene Label-Varianten für Gegner
        gegner_labels = [
            "GEGNER:", "GEGNER", "UNFALLGEGNER:", "UNFALLGEGNER",
            "SCHÄDIGER:", "SCHÄDIGER", "SCHAEDIGER:", "SCHAEDIGER",
            "BEKLAGTER:", "BEKLAGTER", "ANTRAGSGEGNER:", "ANTRAGSGEGNER",
            "UNFALLVERURSACHER:", "UNFALLVERURSACHER"
        ]

        gegner_block = None
        for label in gegner_labels:
            gegner_block = _extract_block(
                cover_text,
                label,
                end_labels=["GEGNERVERTRETER:", "GEGENSTANDSWERT:", "VERSICHERUNG:",
                           "RECHTSSCHUTZ:", "TERMINE:", "FRISTEN:", "HAFTPFLICHT:",
                           "GEGNERISCHE VERSICHERUNG:", "KFZHAFTPFLICHT:"]
            )
            if gegner_block and len(gegner_block) > 10:
                break

        if gegner_block:
            beteiligter = self._parse_party_block(gegner_block, BeteiligterTyp.UNFALLGEGNER)
            if beteiligter:
                ergebnis.beteiligte.append(beteiligter)

        # Verschiedene Label-Varianten für Versicherung
        vers_labels = [
            "VERSICHERUNG:", "VERSICHERUNG", "GEGNERISCHE VERSICHERUNG:",
            "HAFTPFLICHTVERSICHERUNG:", "HAFTPFLICHT:", "KFZ-HAFTPFLICHT:",
            "KFZHAFTPFLICHT:", "VERS.:", "VERS:"
        ]

        vers_block = None
        for label in vers_labels:
            vers_block = _extract_block(
                cover_text,
                label,
                end_labels=["RECHTSSCHUTZ:", "TERMINE:", "FRISTEN:", "GEGENSTANDSWERT:",
                           "SACHBEARBEITER:", "SCHADENNUMMER:", "AKTENZEICHEN:"]
            )
            if vers_block and len(vers_block) > 10:
                break

        if vers_block:
            beteiligter = self._parse_party_block(vers_block, BeteiligterTyp.VERSICHERUNG_GEGNER)
            if beteiligter:
                ergebnis.beteiligte.append(beteiligter)

        # Fallback: Suche nach bekannten Versicherungsnamen im Text
        if not any(b.typ == BeteiligterTyp.VERSICHERUNG_GEGNER for b in ergebnis.beteiligte):
            versicherungen = self._find_insurance_names(cover_text)
            if versicherungen:
                for vers_name in versicherungen[:1]:  # Nur erste gefundene
                    ergebnis.beteiligte.append(Beteiligter(
                        typ=BeteiligterTyp.VERSICHERUNG_GEGNER,
                        firma=vers_name,
                        raw_text=vers_name
                    ))

    def _find_insurance_names(self, text: str) -> List[str]:
        """Sucht nach bekannten Versicherungsnamen im Text"""
        bekannte_versicherungen = [
            "Allianz", "HUK-COBURG", "HUK COBURG", "DEVK", "AXA", "Generali",
            "ERGO", "Zurich", "HDI", "VHV", "LVM", "R+V", "Provinzial",
            "Württembergische", "Debeka", "Gothaer", "Nürnberger", "Cosmos",
            "Signal Iduna", "ADAC", "Arag", "Roland", "DA Direkt", "CosmosDirekt",
            "Verti", "Friday", "Kravag", "Itzehoer", "WGV", "Sparkassen"
        ]

        gefunden = []
        text_lower = text.lower()

        for vers in bekannte_versicherungen:
            if vers.lower() in text_lower:
                # Versuche vollständigen Namen zu finden
                pattern = re.compile(rf"({re.escape(vers)}[A-Za-zÄÖÜäöüß\s\-]*(?:Versicherung|AG|SE)?)", re.IGNORECASE)
                match = pattern.search(text)
                if match:
                    gefunden.append(match.group(1).strip())
                else:
                    gefunden.append(vers)

        return gefunden

    def _parse_party_block(self, block: str, typ: BeteiligterTyp) -> Optional[Beteiligter]:
        """Parst einen Beteiligten-Block"""
        name, vorname, firma = _extract_name_from_block(block)
        strasse, plz, ort = _extract_address(block)
        contacts = _extract_contacts(block)

        # Kennzeichen
        kennzeichen = None
        kz_match = KENNZEICHEN_RE.search(block)
        if kz_match:
            kennzeichen = f"{kz_match.group(1)}-{kz_match.group(2)} {kz_match.group(3)}"

        # IBAN
        iban = None
        iban_match = IBAN_RE.search(block)
        if iban_match:
            iban = iban_match.group(1).replace(" ", "")

        # Versicherungsnummer
        vers_nr = None
        vers_match = re.search(r"(?:Vers\.?-?Nr\.?|Schadennr\.?|Schaden-Nr\.?):?\s*([A-Z0-9/-]+)", block, re.IGNORECASE)
        if vers_match:
            vers_nr = vers_match.group(1)

        if not name and not firma:
            return None

        return Beteiligter(
            typ=typ,
            name=name,
            vorname=vorname,
            firma=firma,
            strasse=strasse,
            plz=plz,
            ort=ort,
            telefon=contacts["telefon"],
            mobil=contacts["mobil"],
            fax=contacts["fax"],
            email=contacts["email"],
            iban=iban,
            kennzeichen=kennzeichen,
            versicherungsnummer=vers_nr,
            raw_text=block.strip()
        )

    def _extract_costs(self, pages: List[str], ergebnis: RAMicroAkteErgebnis):
        """Extrahiert Kostenpositionen aus allen Seiten"""

        kosten_keywords = {
            "REPARATUR": ["reparatur", "instandsetzung", "werkstatt"],
            "GUTACHTEN": ["gutachten", "sachverständig", "bewertung"],
            "MIETWAGEN": ["mietwagen", "ersatzfahrzeug", "leihwagen"],
            "NUTZUNGSAUSFALL": ["nutzungsausfall", "nutzungsentschädigung"],
            "WERTMINDERUNG": ["wertminderung", "merkantil", "minderwert"],
            "ABSCHLEPPEN": ["abschlepp", "bergen", "transport"],
            "KOSTENPAUSCHALE": ["kostenpauschale", "auslagenpauschale", "pauschale"],
            "RECHTSANWALT": ["rechtsanwalt", "anwaltskosten", "gebühren"],
            "SONSTIG": []
        }

        for seite_nr, text in enumerate(pages, start=1):
            for eur_match in EUR_RE.finditer(text):
                try:
                    betrag = _eur_to_float(eur_match.group(1))

                    # Kontext (umgebende Zeile)
                    start = max(0, eur_match.start() - 100)
                    end = min(len(text), eur_match.end() + 50)
                    kontext = text[start:end].replace("\n", " ")

                    # Kategorie bestimmen
                    kategorie = "SONSTIG"
                    kontext_lower = kontext.lower()
                    for kat, keywords in kosten_keywords.items():
                        if any(kw in kontext_lower for kw in keywords):
                            kategorie = kat
                            break

                    # Beschreibung extrahieren
                    beschreibung = kontext.strip()
                    if len(beschreibung) > 100:
                        beschreibung = beschreibung[:100] + "..."

                    # Nur sinnvolle Beträge (> 1€, < 1.000.000€)
                    if 1 < betrag < 1000000:
                        ergebnis.kostenpositionen.append(Kostenposition(
                            kategorie=kategorie,
                            beschreibung=beschreibung,
                            betrag=betrag,
                            seite=seite_nr,
                            raw_text=kontext
                        ))

                except ValueError:
                    continue

    def _extract_unfall_info(self, full_text: str, ergebnis: RAMicroAkteErgebnis):
        """Extrahiert Unfalldatum und -ort"""

        # Unfalldatum
        unfall_date_patterns = [
            r"Unfall(?:datum|tag)?:?\s*(\d{1,2}\.\d{1,2}\.\d{4})",
            r"Verkehrsunfall\s+(?:vom\s+)?(\d{1,2}\.\d{1,2}\.\d{4})",
            r"Unfall\s+(?:vom\s+)?(\d{1,2}\.\d{1,2}\.\d{4})",
            r"Schadensereignis:?\s*(\d{1,2}\.\d{1,2}\.\d{4})",
        ]

        for pattern in unfall_date_patterns:
            m = re.search(pattern, full_text, re.IGNORECASE)
            if m:
                ergebnis.unfalldatum = _parse_date(m.group(1))
                if ergebnis.unfalldatum:
                    break

        # Unfallort
        ort_patterns = [
            r"Unfallort:?\s*([^\n,]+)",
            r"Schadensort:?\s*([^\n,]+)",
            r"Ort des Unfalls:?\s*([^\n,]+)",
        ]

        for pattern in ort_patterns:
            m = re.search(pattern, full_text, re.IGNORECASE)
            if m:
                ergebnis.unfallort = m.group(1).strip()
                if ergebnis.unfallort:
                    break


def parse_ramicro_pdf(pdf_bytes: bytes, filename: Optional[str] = None) -> RAMicroAkteErgebnis:
    """
    Convenience-Funktion zum Parsen eines RA-Micro PDFs.

    Args:
        pdf_bytes: PDF-Datei als Bytes
        filename: Optional - Dateiname

    Returns:
        RAMicroAkteErgebnis mit allen extrahierten Daten
    """
    parser = RAMicroParser()
    return parser.parse(pdf_bytes, filename)


def split_pdf_by_bookmarks(pdf_bytes: bytes) -> List[Tuple[str, bytes]]:
    """
    Splittet ein PDF anhand der Bookmarks in einzelne Dokumente.

    Args:
        pdf_bytes: PDF-Datei als Bytes

    Returns:
        Liste von (titel, pdf_bytes) Tupeln
    """
    try:
        import fitz  # PyMuPDF

        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        toc = doc.get_toc()

        if not toc:
            # Keine Bookmarks - komplettes PDF zurückgeben
            return [("Komplette Akte", pdf_bytes)]

        segments = []

        for i, item in enumerate(toc):
            level, title, start_page = item
            end_page = toc[i + 1][2] - 1 if i + 1 < len(toc) else len(doc)

            # Neues PDF für dieses Segment erstellen
            new_doc = fitz.open()
            new_doc.insert_pdf(doc, from_page=start_page - 1, to_page=end_page - 1)

            segment_bytes = new_doc.tobytes()
            new_doc.close()

            segments.append((title, segment_bytes))

        doc.close()
        return segments

    except ImportError:
        return [("Komplette Akte", pdf_bytes)]
    except Exception:
        return [("Komplette Akte", pdf_bytes)]
