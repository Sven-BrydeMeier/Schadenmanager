"""
OCR-Service für Dokumentenverarbeitung
"""
import os
import json
from typing import Optional, Dict, Any, Tuple
from datetime import datetime

from sqlalchemy.orm import Session

from src.models import Dokument, DokumentTyp
from src.config.settings import get_settings


class OCRService:
    """Service für OCR-Verarbeitung von Dokumenten"""

    def __init__(self):
        self.settings = get_settings()

    def verarbeite_bild(self, dateipfad: str) -> Tuple[Optional[str], str]:
        """
        Führt OCR auf einem Bild durch.

        Args:
            dateipfad: Pfad zur Bilddatei

        Returns:
            Tuple aus (OCR-Text oder None, Fehlermeldung)
        """
        if not os.path.exists(dateipfad):
            return None, "Datei nicht gefunden"

        try:
            import pytesseract
            from PIL import Image

            # Tesseract-Pfad setzen falls konfiguriert
            if self.settings.tesseract_cmd:
                pytesseract.pytesseract.tesseract_cmd = self.settings.tesseract_cmd

            # Bild laden und OCR durchführen
            image = Image.open(dateipfad)

            # OCR mit deutscher Sprache
            text = pytesseract.image_to_string(image, lang='deu')

            return text.strip(), ""

        except ImportError:
            return None, "pytesseract oder PIL nicht installiert"
        except Exception as e:
            return None, f"OCR-Fehler: {str(e)}"

    def verarbeite_pdf(self, dateipfad: str) -> Tuple[Optional[str], str]:
        """
        Führt OCR auf einem PDF durch.

        Args:
            dateipfad: Pfad zur PDF-Datei

        Returns:
            Tuple aus (OCR-Text oder None, Fehlermeldung)
        """
        if not os.path.exists(dateipfad):
            return None, "Datei nicht gefunden"

        try:
            import pytesseract
            from PIL import Image
            import pdf2image

            # PDF in Bilder konvertieren
            images = pdf2image.convert_from_path(dateipfad)

            # OCR auf jeder Seite durchführen
            texte = []
            for i, image in enumerate(images):
                text = pytesseract.image_to_string(image, lang='deu')
                texte.append(f"--- Seite {i + 1} ---\n{text}")

            return "\n\n".join(texte), ""

        except ImportError:
            return None, "pdf2image, pytesseract oder PIL nicht installiert"
        except Exception as e:
            return None, f"PDF-OCR-Fehler: {str(e)}"

    def verarbeite_dokument(self, dokument: Dokument, db: Session) -> Tuple[bool, str]:
        """
        Verarbeitet ein Dokument mit OCR.

        Args:
            dokument: Das zu verarbeitende Dokument
            db: Datenbank-Session

        Returns:
            Tuple aus (erfolgreich, fehlermeldung)
        """
        if not dokument.dateipfad:
            return False, "Kein Dateipfad angegeben"

        dateipfad = dokument.dateipfad
        dateiendung = os.path.splitext(dateipfad)[1].lower()

        if dateiendung == '.pdf':
            text, fehler = self.verarbeite_pdf(dateipfad)
        elif dateiendung in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp']:
            text, fehler = self.verarbeite_bild(dateipfad)
        else:
            return False, f"Nicht unterstütztes Dateiformat: {dateiendung}"

        if text is None:
            dokument.status = "FEHLER"
            return False, fehler

        dokument.ocr_text = text
        dokument.ocr_verarbeitet = True
        dokument.ocr_verarbeitet_am = datetime.utcnow()
        dokument.status = "OCR_ABGESCHLOSSEN"

        db.flush()
        return True, ""


class KIExtraktor:
    """Extrahiert strukturierte Daten aus OCR-Text mittels KI"""

    def __init__(self):
        self.settings = get_settings()

    def _get_prompt_fahrzeugschein(self, ocr_text: str) -> str:
        """Prompt für Fahrzeugschein-Extraktion"""
        return f"""Analysiere den folgenden OCR-Text eines deutschen Fahrzeugscheins (Zulassungsbescheinigung Teil I) und extrahiere die Daten als JSON.

OCR-Text:
{ocr_text}

Extrahiere folgende Felder (falls vorhanden):
- halter_name: Name des Fahrzeughalters
- halter_vorname: Vorname des Halters
- halter_strasse: Straße
- halter_hausnummer: Hausnummer
- halter_plz: Postleitzahl
- halter_ort: Ort
- fin: Fahrzeug-Identifizierungsnummer (17 Zeichen)
- kennzeichen: Amtliches Kennzeichen
- hersteller: Fahrzeughersteller
- modell: Fahrzeugmodell/Handelsbezeichnung
- hsn: Herstellerschlüsselnummer (4 Ziffern)
- tsn: Typschlüsselnummer (3 Zeichen)
- erstzulassung: Datum der Erstzulassung (Format: YYYY-MM-DD)
- hubraum: Hubraum in ccm
- leistung_kw: Leistung in kW
- kraftstoff: Kraftstoffart

Antworte NUR mit validem JSON ohne zusätzlichen Text."""

    def _get_prompt_personalausweis(self, ocr_text: str) -> str:
        """Prompt für Personalausweis-Extraktion"""
        return f"""Analysiere den folgenden OCR-Text eines deutschen Personalausweises und extrahiere die Daten als JSON.

OCR-Text:
{ocr_text}

Extrahiere folgende Felder (falls vorhanden):
- nachname: Familienname
- vorname: Vorname(n)
- geburtsdatum: Geburtsdatum (Format: YYYY-MM-DD)
- geburtsort: Geburtsort
- staatsangehoerigkeit: Staatsangehörigkeit
- ausweisnummer: Ausweisnummer
- gueltig_bis: Gültig bis (Format: YYYY-MM-DD)
- strasse: Wohnadresse Straße
- hausnummer: Hausnummer
- plz: Postleitzahl
- ort: Wohnort

Antworte NUR mit validem JSON ohne zusätzlichen Text."""

    def _get_prompt_gutachten(self, ocr_text: str) -> str:
        """Prompt für Gutachten-Extraktion"""
        return f"""Analysiere den folgenden OCR-Text eines Kfz-Schadensgutachtens und extrahiere die Daten als JSON.

OCR-Text:
{ocr_text}

Extrahiere folgende Felder (falls vorhanden):
- gutachten_nummer: Gutachtennummer/Aktenzeichen
- gutachten_datum: Datum des Gutachtens (Format: YYYY-MM-DD)
- gutachter_name: Name des Sachverständigen
- gutachter_firma: Firma/Büro des Sachverständigen

Fahrzeugdaten:
- kennzeichen: Amtliches Kennzeichen
- hersteller: Fahrzeughersteller
- modell: Fahrzeugmodell
- fin: Fahrzeug-Identifizierungsnummer
- erstzulassung: Erstzulassung
- km_stand: Kilometerstand

Schadensbewertung:
- reparaturkosten_netto: Reparaturkosten netto in EUR
- reparaturkosten_brutto: Reparaturkosten brutto in EUR
- wiederbeschaffungswert: Wiederbeschaffungswert in EUR
- restwert: Restwert in EUR
- wertminderung: Merkantile Wertminderung in EUR
- nutzungsausfall_tage: Geschätzte Reparaturdauer in Tagen
- nutzungsausfall_tagessatz: Nutzungsausfall-Tagessatz in EUR
- totalschaden: true/false

Schadenbeschreibung:
- schaden_beschreibung: Kurze Zusammenfassung der Schäden

Antworte NUR mit validem JSON ohne zusätzlichen Text."""

    def _get_prompt_rechnung(self, ocr_text: str) -> str:
        """Prompt für Rechnungs-Extraktion"""
        return f"""Analysiere den folgenden OCR-Text einer Rechnung und extrahiere die Daten als JSON.

OCR-Text:
{ocr_text}

Extrahiere folgende Felder (falls vorhanden):
- rechnungsnummer: Rechnungsnummer
- rechnungsdatum: Rechnungsdatum (Format: YYYY-MM-DD)
- aussteller_name: Name des Rechnungsstellers
- aussteller_adresse: Adresse des Rechnungsstellers

Beträge:
- betrag_netto: Nettobetrag in EUR
- mwst_satz: MwSt-Satz in %
- mwst_betrag: MwSt-Betrag in EUR
- betrag_brutto: Bruttobetrag in EUR

Positionen (als Array):
- positionen: [{{ "beschreibung": "...", "menge": 1, "einzelpreis": 0.00, "gesamtpreis": 0.00 }}]

Kategorie:
- kategorie: Eine von [REPARATUR, GUTACHTEN, ERSATZWAGEN, SONSTIG]

Antworte NUR mit validem JSON ohne zusätzlichen Text."""

    def _get_prompt_versicherungsschreiben(self, ocr_text: str) -> str:
        """Prompt für Versicherungsschreiben-Extraktion"""
        return f"""Analysiere den folgenden OCR-Text eines Versicherungsschreibens und extrahiere die Daten als JSON.

OCR-Text:
{ocr_text}

Extrahiere folgende Felder (falls vorhanden):
- versicherung_name: Name der Versicherung
- schadennummer: Schadennummer/Aktenzeichen der Versicherung
- unser_zeichen: Unser Zeichen/Aktenzeichen
- datum: Datum des Schreibens (Format: YYYY-MM-DD)
- betreff: Betreff des Schreibens

Falls es sich um ein Kürzungsschreiben/Regulierungsschreiben handelt:
- ist_kuerzung: true/false
- kuerzungen: [{{ "position": "...", "gefordert": 0.00, "anerkannt": 0.00, "gekuerzt": 0.00, "begruendung": "..." }}]
- gesamt_gefordert: Gesamtforderung in EUR
- gesamt_anerkannt: Anerkannter Gesamtbetrag in EUR

Falls Zahlungsankündigung:
- zahlungsbetrag: Angekündigter Zahlungsbetrag in EUR
- zahlung_an: Zahlungsempfänger

Antworte NUR mit validem JSON ohne zusätzlichen Text."""

    def extrahiere_daten(
        self,
        ocr_text: str,
        dokument_typ: DokumentTyp
    ) -> Tuple[Optional[Dict[str, Any]], str]:
        """
        Extrahiert strukturierte Daten aus OCR-Text mittels KI.

        Args:
            ocr_text: Der OCR-Text
            dokument_typ: Der Typ des Dokuments

        Returns:
            Tuple aus (extrahierte Daten als Dict oder None, Fehlermeldung)
        """
        # Prompt basierend auf Dokumenttyp wählen
        if dokument_typ == DokumentTyp.FAHRZEUGSCHEIN:
            prompt = self._get_prompt_fahrzeugschein(ocr_text)
        elif dokument_typ == DokumentTyp.PERSONALAUSWEIS:
            prompt = self._get_prompt_personalausweis(ocr_text)
        elif dokument_typ == DokumentTyp.GUTACHTEN:
            prompt = self._get_prompt_gutachten(ocr_text)
        elif dokument_typ == DokumentTyp.RECHNUNG:
            prompt = self._get_prompt_rechnung(ocr_text)
        elif dokument_typ in [DokumentTyp.VERSICHERUNGSSCHREIBEN, DokumentTyp.KUERZUNGSSCHREIBEN]:
            prompt = self._get_prompt_versicherungsschreiben(ocr_text)
        else:
            return None, "Nicht unterstützter Dokumenttyp für KI-Extraktion"

        # KI-API aufrufen
        try:
            if self.settings.ki_provider == "anthropic" and self.settings.anthropic_api_key:
                return self._call_anthropic(prompt)
            elif self.settings.openai_api_key:
                return self._call_openai(prompt)
            else:
                return None, "Keine KI-API konfiguriert"
        except Exception as e:
            return None, f"KI-Fehler: {str(e)}"

    def _call_openai(self, prompt: str) -> Tuple[Optional[Dict[str, Any]], str]:
        """Ruft die OpenAI API auf"""
        try:
            from openai import OpenAI

            client = OpenAI(api_key=self.settings.openai_api_key)

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Du bist ein Experte für die Extraktion strukturierter Daten aus OCR-Text. Antworte immer nur mit validem JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )

            result = response.choices[0].message.content
            return json.loads(result), ""

        except json.JSONDecodeError:
            return None, "KI-Antwort konnte nicht als JSON geparst werden"
        except Exception as e:
            return None, f"OpenAI-Fehler: {str(e)}"

    def _call_anthropic(self, prompt: str) -> Tuple[Optional[Dict[str, Any]], str]:
        """Ruft die Anthropic API auf"""
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=self.settings.anthropic_api_key)

            response = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=4096,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            result = response.content[0].text

            # JSON aus Antwort extrahieren
            if result.strip().startswith('{'):
                return json.loads(result), ""
            else:
                # Versuche JSON aus Markdown-Block zu extrahieren
                import re
                match = re.search(r'```(?:json)?\s*([\s\S]*?)```', result)
                if match:
                    return json.loads(match.group(1)), ""
                return None, "Keine JSON-Daten in KI-Antwort gefunden"

        except json.JSONDecodeError:
            return None, "KI-Antwort konnte nicht als JSON geparst werden"
        except Exception as e:
            return None, f"Anthropic-Fehler: {str(e)}"

    def verarbeite_dokument(self, dokument: Dokument, db: Session) -> Tuple[bool, str]:
        """
        Verarbeitet ein Dokument mit KI-Extraktion.

        Args:
            dokument: Das zu verarbeitende Dokument
            db: Datenbank-Session

        Returns:
            Tuple aus (erfolgreich, fehlermeldung)
        """
        if not dokument.ocr_text:
            return False, "Kein OCR-Text vorhanden. Bitte zuerst OCR durchführen."

        if not dokument.dokument_typ:
            return False, "Dokumenttyp nicht festgelegt"

        daten, fehler = self.extrahiere_daten(dokument.ocr_text, dokument.dokument_typ)

        if daten is None:
            return False, fehler

        dokument.ki_strukturierte_daten = json.dumps(daten, ensure_ascii=False, indent=2)
        dokument.ki_verarbeitet = True
        dokument.ki_verarbeitet_am = datetime.utcnow()
        dokument.status = "VERARBEITET"

        db.flush()
        return True, ""


# Singleton-Instanzen
_ocr_service = None
_ki_extraktor = None


def get_ocr_service() -> OCRService:
    """Gibt die Singleton-Instanz des OCR-Service zurück"""
    global _ocr_service
    if _ocr_service is None:
        _ocr_service = OCRService()
    return _ocr_service


def get_ki_extraktor() -> KIExtraktor:
    """Gibt die Singleton-Instanz des KI-Extraktors zurück"""
    global _ki_extraktor
    if _ki_extraktor is None:
        _ki_extraktor = KIExtraktor()
    return _ki_extraktor
