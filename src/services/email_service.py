"""
E-Mail-Benachrichtigungsdienst für den Schadenmanager
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List, Tuple
from datetime import datetime
from jinja2 import Template

from src.config.settings import get_settings


class EmailService:
    """Service für E-Mail-Versand"""

    def __init__(self):
        self.settings = get_settings()

    def _get_smtp_connection(self):
        """Erstellt eine SMTP-Verbindung"""
        try:
            if self.settings.smtp_use_tls:
                server = smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port)
                server.starttls()
            else:
                server = smtplib.SMTP_SSL(self.settings.smtp_host, self.settings.smtp_port)

            if self.settings.smtp_username and self.settings.smtp_password:
                server.login(self.settings.smtp_username, self.settings.smtp_password)

            return server
        except Exception as e:
            print(f"SMTP-Verbindungsfehler: {e}")
            return None

    def sende_email(
        self,
        empfaenger: str,
        betreff: str,
        inhalt_html: str,
        inhalt_text: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Sendet eine E-Mail.

        Args:
            empfaenger: E-Mail-Adresse des Empfängers
            betreff: Betreff der E-Mail
            inhalt_html: HTML-Inhalt der E-Mail
            inhalt_text: Optional - Plaintext-Version

        Returns:
            Tuple aus (Erfolg, Fehlermeldung)
        """
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"[Schadenmanager] {betreff}"
            msg['From'] = self.settings.smtp_from_email
            msg['To'] = empfaenger

            # Plaintext-Version
            if inhalt_text:
                part1 = MIMEText(inhalt_text, 'plain', 'utf-8')
                msg.attach(part1)

            # HTML-Version
            part2 = MIMEText(inhalt_html, 'html', 'utf-8')
            msg.attach(part2)

            server = self._get_smtp_connection()
            if not server:
                return False, "SMTP-Verbindung fehlgeschlagen"

            server.sendmail(
                self.settings.smtp_from_email,
                empfaenger,
                msg.as_string()
            )
            server.quit()

            return True, None

        except Exception as e:
            return False, str(e)

    def sende_benachrichtigung(
        self,
        empfaenger: str,
        typ: str,
        daten: dict
    ) -> Tuple[bool, Optional[str]]:
        """
        Sendet eine formatierte Benachrichtigung.

        Args:
            empfaenger: E-Mail-Adresse
            typ: Typ der Benachrichtigung (siehe TEMPLATES)
            daten: Daten für das Template

        Returns:
            Tuple aus (Erfolg, Fehlermeldung)
        """
        template = BENACHRICHTIGUNGS_TEMPLATES.get(typ)
        if not template:
            return False, f"Unbekannter Benachrichtigungstyp: {typ}"

        betreff = Template(template['betreff']).render(**daten)
        inhalt_html = Template(template['html']).render(**daten)
        inhalt_text = Template(template['text']).render(**daten) if 'text' in template else None

        return self.sende_email(empfaenger, betreff, inhalt_html, inhalt_text)


# E-Mail-Templates für verschiedene Benachrichtigungstypen
BENACHRICHTIGUNGS_TEMPLATES = {
    'neues_dokument': {
        'betreff': 'Neues Dokument in Akte {{ aktenzeichen }}',
        'html': '''
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background-color: #1e40af; color: white; padding: 20px; text-align: center;">
                <h1 style="margin: 0;">Schadenmanager</h1>
            </div>
            <div style="padding: 20px; background-color: #f8fafc;">
                <h2>Neues Dokument hochgeladen</h2>
                <p>In der Akte <strong>{{ aktenzeichen }}</strong> wurde ein neues Dokument hochgeladen:</p>
                <div style="background-color: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 15px; margin: 15px 0;">
                    <p><strong>Dokumenttyp:</strong> {{ dokument_typ }}</p>
                    <p><strong>Dateiname:</strong> {{ dateiname }}</p>
                    <p><strong>Hochgeladen von:</strong> {{ hochgeladen_von }}</p>
                    <p><strong>Datum:</strong> {{ datum }}</p>
                </div>
                <p>Bitte prüfen Sie das Dokument und erteilen Sie ggf. die Freigabe.</p>
                <a href="{{ link }}" style="display: inline-block; background-color: #1e40af; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; margin-top: 10px;">Zum Dokument</a>
            </div>
            <div style="padding: 15px; text-align: center; color: #64748b; font-size: 12px;">
                <p>Diese E-Mail wurde automatisch vom Schadenmanager versendet.</p>
            </div>
        </body>
        </html>
        ''',
        'text': '''
Neues Dokument in Akte {{ aktenzeichen }}

In der Akte {{ aktenzeichen }} wurde ein neues Dokument hochgeladen:

Dokumenttyp: {{ dokument_typ }}
Dateiname: {{ dateiname }}
Hochgeladen von: {{ hochgeladen_von }}
Datum: {{ datum }}

Bitte prüfen Sie das Dokument und erteilen Sie ggf. die Freigabe.
        '''
    },

    'status_aenderung': {
        'betreff': 'Statusänderung in Akte {{ aktenzeichen }}',
        'html': '''
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background-color: #1e40af; color: white; padding: 20px; text-align: center;">
                <h1 style="margin: 0;">Schadenmanager</h1>
            </div>
            <div style="padding: 20px; background-color: #f8fafc;">
                <h2>Projektstatus geändert</h2>
                <p>Der Status der Akte <strong>{{ aktenzeichen }}</strong> wurde geändert:</p>
                <div style="background-color: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 15px; margin: 15px 0;">
                    <p><strong>Alter Status:</strong> {{ alter_status }}</p>
                    <p><strong>Neuer Status:</strong> {{ neuer_status }}</p>
                    <p><strong>Geändert von:</strong> {{ geaendert_von }}</p>
                    <p><strong>Datum:</strong> {{ datum }}</p>
                </div>
                <a href="{{ link }}" style="display: inline-block; background-color: #1e40af; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; margin-top: 10px;">Zum Projekt</a>
            </div>
        </body>
        </html>
        ''',
        'text': '''
Statusänderung in Akte {{ aktenzeichen }}

Der Status der Akte {{ aktenzeichen }} wurde geändert:

Alter Status: {{ alter_status }}
Neuer Status: {{ neuer_status }}
Geändert von: {{ geaendert_von }}
Datum: {{ datum }}
        '''
    },

    'meilenstein_erreicht': {
        'betreff': 'Meilenstein erreicht in Akte {{ aktenzeichen }}',
        'html': '''
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background-color: #1e40af; color: white; padding: 20px; text-align: center;">
                <h1 style="margin: 0;">Schadenmanager</h1>
            </div>
            <div style="padding: 20px; background-color: #f8fafc;">
                <h2 style="color: #16a34a;">Meilenstein erreicht!</h2>
                <p>In der Akte <strong>{{ aktenzeichen }}</strong> wurde ein Meilenstein erreicht:</p>
                <div style="background-color: #dcfce7; border: 1px solid #16a34a; border-radius: 8px; padding: 15px; margin: 15px 0;">
                    <p style="font-size: 18px; font-weight: bold; color: #16a34a;">{{ meilenstein_name }}</p>
                    <p>{{ meilenstein_beschreibung }}</p>
                </div>
                <a href="{{ link }}" style="display: inline-block; background-color: #1e40af; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; margin-top: 10px;">Zum Projekt</a>
            </div>
        </body>
        </html>
        ''',
        'text': '''
Meilenstein erreicht in Akte {{ aktenzeichen }}

In der Akte {{ aktenzeichen }} wurde ein Meilenstein erreicht:

{{ meilenstein_name }}
{{ meilenstein_beschreibung }}
        '''
    },

    'frist_erinnerung': {
        'betreff': 'Frist-Erinnerung: {{ frist_name }} ({{ aktenzeichen }})',
        'html': '''
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background-color: #dc2626; color: white; padding: 20px; text-align: center;">
                <h1 style="margin: 0;">Schadenmanager - Frist-Erinnerung</h1>
            </div>
            <div style="padding: 20px; background-color: #fef2f2;">
                <h2 style="color: #dc2626;">Frist läuft ab!</h2>
                <p>Für die Akte <strong>{{ aktenzeichen }}</strong> steht eine Frist bevor:</p>
                <div style="background-color: white; border: 2px solid #dc2626; border-radius: 8px; padding: 15px; margin: 15px 0;">
                    <p style="font-size: 18px; font-weight: bold;">{{ frist_name }}</p>
                    <p><strong>Fällig am:</strong> {{ faellig_am }}</p>
                    <p><strong>Verbleibend:</strong> {{ tage_verbleibend }} Tag(e)</p>
                    {% if notiz %}
                    <p><strong>Notiz:</strong> {{ notiz }}</p>
                    {% endif %}
                </div>
                <a href="{{ link }}" style="display: inline-block; background-color: #dc2626; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; margin-top: 10px;">Zum Projekt</a>
            </div>
        </body>
        </html>
        ''',
        'text': '''
FRIST-ERINNERUNG: {{ frist_name }}

Für die Akte {{ aktenzeichen }} steht eine Frist bevor:

{{ frist_name }}
Fällig am: {{ faellig_am }}
Verbleibend: {{ tage_verbleibend }} Tag(e)
{% if notiz %}Notiz: {{ notiz }}{% endif %}
        '''
    },

    'freigabe_erteilt': {
        'betreff': 'Dokument freigegeben in Akte {{ aktenzeichen }}',
        'html': '''
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background-color: #1e40af; color: white; padding: 20px; text-align: center;">
                <h1 style="margin: 0;">Schadenmanager</h1>
            </div>
            <div style="padding: 20px; background-color: #f8fafc;">
                <h2 style="color: #16a34a;">Dokument freigegeben</h2>
                <p>In der Akte <strong>{{ aktenzeichen }}</strong> wurde ein Dokument freigegeben:</p>
                <div style="background-color: #dcfce7; border: 1px solid #16a34a; border-radius: 8px; padding: 15px; margin: 15px 0;">
                    <p><strong>Dokumenttyp:</strong> {{ dokument_typ }}</p>
                    <p><strong>Dateiname:</strong> {{ dateiname }}</p>
                    <p><strong>Freigegeben von:</strong> {{ freigegeben_von }}</p>
                    <p><strong>Datum:</strong> {{ datum }}</p>
                </div>
                <p>Das Dokument ist nun für alle Beteiligten sichtbar.</p>
            </div>
        </body>
        </html>
        ''',
        'text': '''
Dokument freigegeben in Akte {{ aktenzeichen }}

In der Akte {{ aktenzeichen }} wurde ein Dokument freigegeben:

Dokumenttyp: {{ dokument_typ }}
Dateiname: {{ dateiname }}
Freigegeben von: {{ freigegeben_von }}
Datum: {{ datum }}

Das Dokument ist nun für alle Beteiligten sichtbar.
        '''
    },

    'neue_kostenposition': {
        'betreff': 'Neue Kostenposition in Akte {{ aktenzeichen }}',
        'html': '''
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background-color: #1e40af; color: white; padding: 20px; text-align: center;">
                <h1 style="margin: 0;">Schadenmanager</h1>
            </div>
            <div style="padding: 20px; background-color: #f8fafc;">
                <h2>Neue Kostenposition erfasst</h2>
                <p>In der Akte <strong>{{ aktenzeichen }}</strong> wurde eine neue Kostenposition erfasst:</p>
                <div style="background-color: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 15px; margin: 15px 0;">
                    <p><strong>Position:</strong> {{ position_name }}</p>
                    <p><strong>Betrag (gefordert):</strong> {{ betrag_gefordert }} EUR</p>
                    <p><strong>Erfasst von:</strong> {{ erfasst_von }}</p>
                </div>
                <a href="{{ link }}" style="display: inline-block; background-color: #1e40af; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; margin-top: 10px;">Zur Kostenübersicht</a>
            </div>
        </body>
        </html>
        ''',
        'text': '''
Neue Kostenposition in Akte {{ aktenzeichen }}

In der Akte {{ aktenzeichen }} wurde eine neue Kostenposition erfasst:

Position: {{ position_name }}
Betrag (gefordert): {{ betrag_gefordert }} EUR
Erfasst von: {{ erfasst_von }}
        '''
    }
}


def get_email_service() -> EmailService:
    """Factory-Funktion für den E-Mail-Service"""
    return EmailService()
