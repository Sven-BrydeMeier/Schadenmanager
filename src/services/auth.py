"""
Authentifizierungsservice mit 2FA-Unterstützung (SMS und TOTP)
"""
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Tuple

import bcrypt
import pyotp
from sqlalchemy.orm import Session

from src.models import User, Rollen
from src.config.settings import get_settings


class AuthService:
    """Service für Authentifizierung und 2FA"""

    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()

    # ==================== Passwort-Funktionen ====================

    def hash_passwort(self, passwort: str) -> str:
        """Hasht ein Passwort mit bcrypt"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(passwort.encode('utf-8'), salt).decode('utf-8')

    def verifiziere_passwort(self, passwort: str, passwort_hash: str) -> bool:
        """Überprüft ein Passwort gegen den Hash"""
        try:
            return bcrypt.checkpw(
                passwort.encode('utf-8'),
                passwort_hash.encode('utf-8')
            )
        except Exception:
            return False

    def passwort_ist_stark(self, passwort: str) -> Tuple[bool, str]:
        """
        Prüft ob ein Passwort den Sicherheitsanforderungen entspricht.

        Returns:
            Tuple aus (ist_gueltig, fehlermeldung)
        """
        if len(passwort) < self.settings.password_min_length:
            return False, f"Passwort muss mindestens {self.settings.password_min_length} Zeichen lang sein"

        if not any(c.isupper() for c in passwort):
            return False, "Passwort muss mindestens einen Großbuchstaben enthalten"

        if not any(c.islower() for c in passwort):
            return False, "Passwort muss mindestens einen Kleinbuchstaben enthalten"

        if not any(c.isdigit() for c in passwort):
            return False, "Passwort muss mindestens eine Zahl enthalten"

        return True, ""

    # ==================== Benutzer-Funktionen ====================

    def benutzer_erstellen(
        self,
        email: str,
        passwort: str,
        rolle: Rollen,
        vorname: str = None,
        nachname: str = None,
        telefonnummer: str = None,
        organisation_id: int = None
    ) -> Tuple[Optional[User], str]:
        """
        Erstellt einen neuen Benutzer.

        Returns:
            Tuple aus (User oder None, Fehlermeldung)
        """
        # Prüfe ob E-Mail bereits existiert
        existing = self.db.query(User).filter(User.email == email.lower()).first()
        if existing:
            return None, "E-Mail-Adresse ist bereits registriert"

        # Passwort validieren
        ist_stark, fehler = self.passwort_ist_stark(passwort)
        if not ist_stark:
            return None, fehler

        user = User(
            email=email.lower(),
            passwort_hash=self.hash_passwort(passwort),
            rolle=rolle,
            vorname=vorname,
            nachname=nachname,
            telefonnummer=telefonnummer,
            organisation_id=organisation_id,
            aktiv=True
        )

        self.db.add(user)
        self.db.flush()

        return user, ""

    def benutzer_authentifizieren(self, email: str, passwort: str) -> Tuple[Optional[User], str]:
        """
        Authentifiziert einen Benutzer mit E-Mail und Passwort.
        Prüft NICHT 2FA - das muss separat erfolgen.

        Returns:
            Tuple aus (User oder None, Fehlermeldung)
        """
        user = self.db.query(User).filter(User.email == email.lower()).first()

        if not user:
            return None, "Ungültige E-Mail-Adresse oder Passwort"

        if not user.aktiv:
            return None, "Dieses Konto ist deaktiviert"

        if not self.verifiziere_passwort(passwort, user.passwort_hash):
            return None, "Ungültige E-Mail-Adresse oder Passwort"

        return user, ""

    def login_abschliessen(self, user: User) -> None:
        """Aktualisiert den letzten Login-Zeitstempel"""
        user.letzter_login = datetime.utcnow()
        self.db.flush()

    # ==================== 2FA TOTP-Funktionen ====================

    def generiere_totp_secret(self) -> str:
        """Generiert ein neues TOTP-Secret für 2FA"""
        return pyotp.random_base32()

    def get_totp_uri(self, user: User, secret: str) -> str:
        """Generiert die TOTP-URI für QR-Code-Generierung"""
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(
            name=user.email,
            issuer_name=self.settings.app_name
        )

    def aktiviere_totp(self, user: User, secret: str, code: str) -> Tuple[bool, str]:
        """
        Aktiviert TOTP-2FA für einen Benutzer nach Verifizierung des Codes.

        Args:
            user: Der Benutzer
            secret: Das TOTP-Secret
            code: Der vom Benutzer eingegebene Code zur Verifizierung

        Returns:
            Tuple aus (erfolgreich, fehlermeldung)
        """
        totp = pyotp.TOTP(secret)

        if not totp.verify(code, valid_window=1):
            return False, "Ungültiger Verifizierungscode"

        user.totp_secret = secret
        user.zwei_faktor_aktiviert = True
        self.db.flush()

        return True, ""

    def verifiziere_totp(self, user: User, code: str) -> bool:
        """
        Verifiziert einen TOTP-Code für einen Benutzer.

        Args:
            user: Der Benutzer
            code: Der TOTP-Code

        Returns:
            True wenn der Code gültig ist
        """
        if not user.totp_secret:
            return False

        totp = pyotp.TOTP(user.totp_secret)
        return totp.verify(code, valid_window=1)

    # ==================== 2FA SMS-Funktionen ====================

    def generiere_sms_code(self) -> str:
        """Generiert einen 6-stelligen SMS-Verifizierungscode"""
        return ''.join([str(secrets.randbelow(10)) for _ in range(6)])

    def sende_sms_code(self, telefonnummer: str, code: str) -> Tuple[bool, str]:
        """
        Sendet einen SMS-Verifizierungscode.

        In der Produktionsumgebung wird Twilio verwendet.
        Im Debug-Modus wird der Code nur geloggt.

        Returns:
            Tuple aus (erfolgreich, fehlermeldung)
        """
        settings = self.settings

        if settings.debug:
            # Im Debug-Modus: Code ausgeben statt SMS senden
            print(f"[DEBUG] SMS-Code für {telefonnummer}: {code}")
            return True, ""

        # Twilio-Integration
        if not all([settings.twilio_account_sid, settings.twilio_auth_token, settings.twilio_phone_number]):
            return False, "SMS-Dienst nicht konfiguriert"

        try:
            from twilio.rest import Client

            client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
            message = client.messages.create(
                body=f"Ihr Verifizierungscode für {settings.app_name}: {code}",
                from_=settings.twilio_phone_number,
                to=telefonnummer
            )
            return True, ""

        except Exception as e:
            return False, f"SMS konnte nicht gesendet werden: {str(e)}"

    # ==================== Einladungs-Funktionen ====================

    def generiere_einladungstoken(self) -> str:
        """Generiert einen sicheren Einladungstoken"""
        return secrets.token_urlsafe(32)

    def erstelle_einladung(
        self,
        email: str,
        rolle: Rollen,
        gueltig_tage: int = 7
    ) -> Tuple[Optional[User], str]:
        """
        Erstellt eine Benutzereinladung.

        Returns:
            Tuple aus (User mit Einladungstoken oder None, Token oder Fehlermeldung)
        """
        # Prüfe ob E-Mail bereits existiert
        existing = self.db.query(User).filter(User.email == email.lower()).first()
        if existing and existing.aktiv:
            return None, "E-Mail-Adresse ist bereits registriert"

        if existing:
            # Bestehende inaktive Einladung aktualisieren
            user = existing
        else:
            # Neuen Benutzer mit temporärem Passwort anlegen
            user = User(
                email=email.lower(),
                passwort_hash="EINLADUNG_PENDING",
                rolle=rolle,
                aktiv=False
            )
            self.db.add(user)

        token = self.generiere_einladungstoken()
        user.einladungs_token = token
        user.einladung_gueltig_bis = datetime.utcnow() + timedelta(days=gueltig_tage)

        self.db.flush()

        return user, token

    def einladung_annehmen(
        self,
        token: str,
        passwort: str,
        vorname: str = None,
        nachname: str = None,
        telefonnummer: str = None
    ) -> Tuple[Optional[User], str]:
        """
        Nimmt eine Einladung an und aktiviert den Benutzer.

        Returns:
            Tuple aus (User oder None, Fehlermeldung)
        """
        user = self.db.query(User).filter(User.einladungs_token == token).first()

        if not user:
            return None, "Ungültiger Einladungslink"

        if user.einladung_gueltig_bis and user.einladung_gueltig_bis < datetime.utcnow():
            return None, "Einladungslink ist abgelaufen"

        # Passwort validieren
        ist_stark, fehler = self.passwort_ist_stark(passwort)
        if not ist_stark:
            return None, fehler

        # Benutzer aktivieren
        user.passwort_hash = self.hash_passwort(passwort)
        user.vorname = vorname
        user.nachname = nachname
        user.telefonnummer = telefonnummer
        user.aktiv = True
        user.einladungs_token = None
        user.einladung_gueltig_bis = None

        self.db.flush()

        return user, ""


# Session-basierte 2FA-Codes (für SMS-Verifizierung)
_pending_sms_codes = {}


def speichere_sms_code(user_id: int, code: str, gueltig_minuten: int = 5) -> None:
    """Speichert einen SMS-Code temporär für die Verifizierung"""
    _pending_sms_codes[user_id] = {
        "code": code,
        "gueltig_bis": datetime.utcnow() + timedelta(minutes=gueltig_minuten)
    }


def verifiziere_sms_code(user_id: int, code: str) -> bool:
    """Verifiziert einen SMS-Code"""
    eintrag = _pending_sms_codes.get(user_id)

    if not eintrag:
        return False

    if eintrag["gueltig_bis"] < datetime.utcnow():
        del _pending_sms_codes[user_id]
        return False

    if eintrag["code"] != code:
        return False

    # Code nach erfolgreicher Verifizierung löschen
    del _pending_sms_codes[user_id]
    return True
