"""
Email-Parser Service
Parst .eml und .msg Dateien und extrahiert Metadaten
"""

import os
import email
import json
import hashlib
from datetime import datetime
from email import policy
from email.parser import BytesParser
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field

from src.config.settings import get_settings


@dataclass
class EmailAnhang:
    """Repräsentiert einen Email-Anhang"""
    dateiname: str
    content_type: str
    groesse: int
    daten: bytes
    content_id: Optional[str] = None


@dataclass
class GeparsteEmail:
    """Ergebnis des Email-Parsings"""
    message_id: str
    betreff: str
    von_email: str
    von_name: str
    an_emails: List[str]
    an_namen: List[str]
    cc_emails: List[str]
    bcc_emails: List[str]
    gesendet_am: Optional[datetime]
    text_plain: str
    text_html: str
    in_reply_to: Optional[str]
    references: List[str]
    anhaenge: List[EmailAnhang] = field(default_factory=list)
    raw_headers: Dict[str, str] = field(default_factory=dict)


class EmailParserService:
    """
    Service zum Parsen von Email-Dateien (.eml, .msg)

    Unterstützte Formate:
    - .eml (RFC 5322)
    - .msg (Microsoft Outlook) - erfordert 'extract-msg' Paket
    """

    def __init__(self):
        self.settings = get_settings()

    def parse_datei(self, dateipfad: str) -> Tuple[Optional[GeparsteEmail], str]:
        """
        Parst eine Email-Datei.

        Args:
            dateipfad: Pfad zur .eml oder .msg Datei

        Returns:
            Tuple aus (GeparsteEmail, Fehlermeldung)
        """
        if not os.path.exists(dateipfad):
            return None, f"Datei nicht gefunden: {dateipfad}"

        _, ext = os.path.splitext(dateipfad.lower())

        if ext == '.eml':
            return self._parse_eml(dateipfad)
        elif ext == '.msg':
            return self._parse_msg(dateipfad)
        else:
            return None, f"Nicht unterstütztes Format: {ext}"

    def parse_bytes(
        self,
        daten: bytes,
        dateiname: str
    ) -> Tuple[Optional[GeparsteEmail], str]:
        """
        Parst Email-Daten aus Bytes.

        Args:
            daten: Die Email-Bytes
            dateiname: Original-Dateiname für Format-Erkennung

        Returns:
            Tuple aus (GeparsteEmail, Fehlermeldung)
        """
        _, ext = os.path.splitext(dateiname.lower())

        if ext == '.eml':
            return self._parse_eml_bytes(daten)
        elif ext == '.msg':
            return self._parse_msg_bytes(daten)
        else:
            return None, f"Nicht unterstütztes Format: {ext}"

    def _parse_eml(self, dateipfad: str) -> Tuple[Optional[GeparsteEmail], str]:
        """Parst eine .eml Datei"""
        try:
            with open(dateipfad, 'rb') as f:
                return self._parse_eml_bytes(f.read())
        except Exception as e:
            return None, f"Fehler beim Lesen der Datei: {str(e)}"

    def _parse_eml_bytes(self, daten: bytes) -> Tuple[Optional[GeparsteEmail], str]:
        """Parst .eml Bytes"""
        try:
            msg = BytesParser(policy=policy.default).parsebytes(daten)
            return self._extrahiere_email_daten(msg), ""
        except Exception as e:
            return None, f"Fehler beim Parsen: {str(e)}"

    def _parse_msg(self, dateipfad: str) -> Tuple[Optional[GeparsteEmail], str]:
        """Parst eine .msg Datei (Outlook)"""
        try:
            import extract_msg
            msg = extract_msg.Message(dateipfad)
            return self._extrahiere_msg_daten(msg), ""
        except ImportError:
            return None, "extract-msg Paket nicht installiert. Bitte: pip install extract-msg"
        except Exception as e:
            return None, f"Fehler beim Parsen der MSG-Datei: {str(e)}"

    def _parse_msg_bytes(self, daten: bytes) -> Tuple[Optional[GeparsteEmail], str]:
        """Parst .msg Bytes"""
        try:
            import extract_msg
            import tempfile

            # MSG muss als Datei gelesen werden
            with tempfile.NamedTemporaryFile(suffix='.msg', delete=False) as f:
                f.write(daten)
                temp_path = f.name

            try:
                msg = extract_msg.Message(temp_path)
                result = self._extrahiere_msg_daten(msg)
                return result, ""
            finally:
                os.unlink(temp_path)

        except ImportError:
            return None, "extract-msg Paket nicht installiert"
        except Exception as e:
            return None, f"Fehler beim Parsen: {str(e)}"

    def _extrahiere_email_daten(self, msg) -> GeparsteEmail:
        """Extrahiert Daten aus einem email.message.Message Objekt"""

        # Message-ID
        message_id = msg.get('Message-ID', '')
        if not message_id:
            # Generiere eine falls nicht vorhanden
            content_hash = hashlib.md5(str(msg).encode()).hexdigest()[:16]
            message_id = f"<generated-{content_hash}@import>"

        # Absender
        von = msg.get('From', '')
        von_name, von_email = self._parse_adresse(von)

        # Empfänger
        an_liste = msg.get_all('To', [])
        an_emails, an_namen = self._parse_adressen_liste(an_liste)

        cc_liste = msg.get_all('Cc', [])
        cc_emails, _ = self._parse_adressen_liste(cc_liste)

        bcc_liste = msg.get_all('Bcc', [])
        bcc_emails, _ = self._parse_adressen_liste(bcc_liste)

        # Betreff
        betreff = msg.get('Subject', '(Kein Betreff)')

        # Datum
        datum_str = msg.get('Date', '')
        gesendet_am = self._parse_datum(datum_str)

        # Thread-Referenzen
        in_reply_to = msg.get('In-Reply-To', '')
        references_str = msg.get('References', '')
        references = references_str.split() if references_str else []

        # Inhalt
        text_plain = ""
        text_html = ""
        anhaenge = []

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get('Content-Disposition', ''))

                if 'attachment' in content_disposition:
                    # Anhang
                    anhang = self._extrahiere_anhang(part)
                    if anhang:
                        anhaenge.append(anhang)
                elif content_type == 'text/plain':
                    text_plain = self._decode_payload(part)
                elif content_type == 'text/html':
                    text_html = self._decode_payload(part)
        else:
            content_type = msg.get_content_type()
            if content_type == 'text/plain':
                text_plain = self._decode_payload(msg)
            elif content_type == 'text/html':
                text_html = self._decode_payload(msg)

        # Raw Headers
        raw_headers = {k: str(v) for k, v in msg.items()}

        return GeparsteEmail(
            message_id=message_id,
            betreff=betreff,
            von_email=von_email,
            von_name=von_name,
            an_emails=an_emails,
            an_namen=an_namen,
            cc_emails=cc_emails,
            bcc_emails=bcc_emails,
            gesendet_am=gesendet_am,
            text_plain=text_plain,
            text_html=text_html,
            in_reply_to=in_reply_to,
            references=references,
            anhaenge=anhaenge,
            raw_headers=raw_headers
        )

    def _extrahiere_msg_daten(self, msg) -> GeparsteEmail:
        """Extrahiert Daten aus einem extract_msg.Message Objekt"""

        # Message-ID
        message_id = msg.messageId or ""
        if not message_id:
            content_hash = hashlib.md5(str(msg.body or "").encode()).hexdigest()[:16]
            message_id = f"<generated-{content_hash}@import>"

        # Absender
        von_name = msg.senderName or ""
        von_email = msg.senderEmail or msg.sender or ""

        # Empfänger
        an_str = msg.to or ""
        an_emails, an_namen = self._parse_adressen_liste([an_str] if an_str else [])

        cc_str = msg.cc or ""
        cc_emails, _ = self._parse_adressen_liste([cc_str] if cc_str else [])

        bcc_str = msg.bcc or ""
        bcc_emails, _ = self._parse_adressen_liste([bcc_str] if bcc_str else [])

        # Betreff
        betreff = msg.subject or "(Kein Betreff)"

        # Datum
        gesendet_am = msg.date

        # Inhalt
        text_plain = msg.body or ""
        text_html = msg.htmlBody or ""

        # Anhänge
        anhaenge = []
        for attachment in msg.attachments:
            try:
                anhaenge.append(EmailAnhang(
                    dateiname=attachment.longFilename or attachment.shortFilename or "anhang",
                    content_type=attachment.mimetype or "application/octet-stream",
                    groesse=len(attachment.data) if attachment.data else 0,
                    daten=attachment.data or b"",
                    content_id=attachment.cid
                ))
            except Exception:
                pass

        return GeparsteEmail(
            message_id=message_id,
            betreff=betreff,
            von_email=von_email,
            von_name=von_name,
            an_emails=an_emails,
            an_namen=an_namen,
            cc_emails=cc_emails,
            bcc_emails=bcc_emails,
            gesendet_am=gesendet_am,
            text_plain=text_plain,
            text_html=text_html,
            in_reply_to="",
            references=[],
            anhaenge=anhaenge,
            raw_headers={}
        )

    def _parse_adresse(self, adresse: str) -> Tuple[str, str]:
        """Parst eine Email-Adresse in Name und Email"""
        import re

        adresse = str(adresse).strip()
        if not adresse:
            return "", ""

        # Format: "Name <email@example.com>"
        match = re.match(r'^"?([^"<]*)"?\s*<([^>]+)>$', adresse)
        if match:
            return match.group(1).strip(), match.group(2).strip()

        # Nur Email
        if '@' in adresse:
            return "", adresse

        return adresse, ""

    def _parse_adressen_liste(self, adressen: List) -> Tuple[List[str], List[str]]:
        """Parst eine Liste von Adressen"""
        emails = []
        namen = []

        for addr in adressen:
            # Kann mehrere kommagetrennte Adressen enthalten
            for single in str(addr).split(','):
                name, email = self._parse_adresse(single)
                if email:
                    emails.append(email)
                    namen.append(name)

        return emails, namen

    def _parse_datum(self, datum_str: str) -> Optional[datetime]:
        """Parst ein Email-Datum"""
        if not datum_str:
            return None

        try:
            from email.utils import parsedate_to_datetime
            return parsedate_to_datetime(datum_str)
        except Exception:
            pass

        # Fallback-Formate
        formate = [
            "%a, %d %b %Y %H:%M:%S %z",
            "%d %b %Y %H:%M:%S %z",
            "%Y-%m-%d %H:%M:%S",
        ]

        for fmt in formate:
            try:
                return datetime.strptime(datum_str.strip(), fmt)
            except ValueError:
                continue

        return None

    def _decode_payload(self, part) -> str:
        """Dekodiert den Payload eines Email-Parts"""
        try:
            payload = part.get_payload(decode=True)
            if payload:
                # Versuche verschiedene Encodings
                for encoding in ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']:
                    try:
                        return payload.decode(encoding)
                    except (UnicodeDecodeError, AttributeError):
                        continue
            return str(part.get_payload())
        except Exception:
            return ""

    def _extrahiere_anhang(self, part) -> Optional[EmailAnhang]:
        """Extrahiert einen Anhang aus einem Email-Part"""
        try:
            dateiname = part.get_filename()
            if not dateiname:
                return None

            daten = part.get_payload(decode=True)
            if not daten:
                return None

            return EmailAnhang(
                dateiname=dateiname,
                content_type=part.get_content_type(),
                groesse=len(daten),
                daten=daten,
                content_id=part.get('Content-ID')
            )
        except Exception:
            return None


# Singleton
_parser = None


def get_email_parser() -> EmailParserService:
    """Gibt die Singleton-Instanz des EmailParserService zurück"""
    global _parser
    if _parser is None:
        _parser = EmailParserService()
    return _parser
