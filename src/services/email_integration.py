"""
E-Mail-Integration Service
Automatische E-Mail-Verarbeitung und Zuordnung zu Projekten
"""
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum
import json
import re
import hashlib
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from src.models.base import Base


class EmailStatus(str, Enum):
    """Status einer E-Mail"""
    NEU = "NEU"
    ZUGEORDNET = "ZUGEORDNET"
    BEARBEITET = "BEARBEITET"
    ARCHIVIERT = "ARCHIVIERT"
    SPAM = "SPAM"


class EmailRichtung(str, Enum):
    """Richtung der E-Mail"""
    EINGANG = "EINGANG"
    AUSGANG = "AUSGANG"


class EmailPrioritaet(str, Enum):
    """Priorität einer E-Mail"""
    NIEDRIG = "NIEDRIG"
    NORMAL = "NORMAL"
    HOCH = "HOCH"
    DRINGEND = "DRINGEND"


class EmailKonto(Base):
    """Model für E-Mail-Konten"""
    __tablename__ = "email_konto"

    id = Column(Integer, primary_key=True)

    # Konto-Daten
    bezeichnung = Column(String(100), nullable=False)
    email_adresse = Column(String(200), nullable=False, unique=True)

    # Server-Einstellungen (verschlüsselt speichern in Produktion!)
    imap_server = Column(String(200))
    imap_port = Column(Integer, default=993)
    smtp_server = Column(String(200))
    smtp_port = Column(Integer, default=587)
    benutzername = Column(String(200))
    passwort_hash = Column(String(500))  # In Produktion verschlüsseln!

    # Einstellungen
    ssl_aktiviert = Column(Boolean, default=True)
    auto_abruf = Column(Boolean, default=True)
    abruf_intervall_minuten = Column(Integer, default=5)

    # Status
    aktiv = Column(Boolean, default=True)
    letzter_abruf = Column(DateTime)
    letzte_fehler_meldung = Column(Text)

    # Besitzer
    user_id = Column(Integer, ForeignKey("user.id"))

    # Metadaten
    erstellt_am = Column(DateTime, default=datetime.now)


class Email(Base):
    """Model für E-Mails"""
    __tablename__ = "email"

    id = Column(Integer, primary_key=True)

    # E-Mail-Konto
    konto_id = Column(Integer, ForeignKey("email_konto.id"))

    # Projekt-Zuordnung
    projekt_id = Column(Integer, ForeignKey("unfallprojekt.id"))
    projekt = relationship("UnfallProjekt", backref="emails")

    # E-Mail-Daten
    message_id = Column(String(500), unique=True)  # Unique Message-ID
    richtung = Column(SQLEnum(EmailRichtung), default=EmailRichtung.EINGANG)
    status = Column(SQLEnum(EmailStatus), default=EmailStatus.NEU)
    prioritaet = Column(SQLEnum(EmailPrioritaet), default=EmailPrioritaet.NORMAL)

    # Header
    von = Column(String(500), nullable=False)
    an = Column(Text)  # Kann mehrere Empfänger haben
    cc = Column(Text)
    bcc = Column(Text)
    betreff = Column(String(500))

    # Inhalt
    text_inhalt = Column(Text)
    html_inhalt = Column(Text)

    # Anhänge (JSON-Array)
    _anhaenge = Column("anhaenge", Text)

    # Datum
    gesendet_am = Column(DateTime)
    empfangen_am = Column(DateTime)

    # Verarbeitung
    gelesen = Column(Boolean, default=False)
    gelesen_am = Column(DateTime)
    beantwortet = Column(Boolean, default=False)
    beantwortet_am = Column(DateTime)

    # Automatische Zuordnung
    auto_zugeordnet = Column(Boolean, default=False)
    zuordnung_konfidenz = Column(Integer)  # 0-100%
    zuordnung_grund = Column(String(200))

    # Thread
    thread_id = Column(String(500))
    antwort_auf_id = Column(Integer, ForeignKey("email.id"))

    # Datei-Import (für .eml/.msg Drag & Drop)
    original_dateiname = Column(String(255))
    dateipfad = Column(String(500))
    dateigroesse = Column(Integer)
    storage_provider = Column(String(50), default="local")
    storage_key = Column(String(500))
    importiert_via = Column(String(50))  # "IMAP", "DRAG_DROP", "UPLOAD"

    # KI-Verarbeitung
    ki_zusammenfassung = Column(Text)
    ki_kategorie = Column(String(100))
    ki_aktenzeichen_erkannt = Column(String(100))
    ki_verarbeitet = Column(Boolean, default=False)
    ki_verarbeitet_am = Column(DateTime)

    # Hochgeladen von
    hochgeladen_von_user_id = Column(Integer, ForeignKey("user.id"))

    # Metadaten
    erstellt_am = Column(DateTime, default=datetime.now)

    @property
    def anhaenge(self) -> List[Dict]:
        if self._anhaenge:
            return json.loads(self._anhaenge)
        return []

    @anhaenge.setter
    def anhaenge(self, value: List[Dict]):
        self._anhaenge = json.dumps(value)

    @property
    def empfaenger_liste(self) -> List[str]:
        """Liste aller Empfänger"""
        if self.an:
            return [e.strip() for e in self.an.split(",")]
        return []


class EmailVorlage(Base):
    """Model für E-Mail-Vorlagen"""
    __tablename__ = "email_vorlage"

    id = Column(Integer, primary_key=True)

    # Vorlage
    bezeichnung = Column(String(200), nullable=False)
    kategorie = Column(String(100))
    betreff_vorlage = Column(String(500))
    text_vorlage = Column(Text)
    html_vorlage = Column(Text)

    # Platzhalter (JSON-Array)
    _platzhalter = Column("platzhalter", Text)

    # Status
    aktiv = Column(Boolean, default=True)

    # Metadaten
    erstellt_von_user_id = Column(Integer, ForeignKey("user.id"))
    erstellt_am = Column(DateTime, default=datetime.now)

    @property
    def platzhalter(self) -> List[str]:
        if self._platzhalter:
            return json.loads(self._platzhalter)
        return []

    @platzhalter.setter
    def platzhalter(self, value: List[str]):
        self._platzhalter = json.dumps(value)


class EmailIntegrationService:
    """Service für E-Mail-Integration"""

    # Muster für automatische Zuordnung
    AKTENZEICHEN_MUSTER = [
        r'Az[.:]\s*(\d{4}[-/]\d+)',
        r'Aktenzeichen[:\s]+(\d{4}[-/]\d+)',
        r'Unser Zeichen[:\s]+(\d{4}[-/]\d+)',
        r'Schadensnummer[:\s]+(\S+)',
        r'Schadennummer[:\s]+(\S+)',
        r'VorgangNr[.:\s]+(\S+)',
    ]

    # Keywords für Prioritätserkennung
    DRINGEND_KEYWORDS = [
        'dringend', 'urgent', 'sofort', 'eilig', 'frist',
        'mahnung', 'letzte warnung', 'rechtsmittel'
    ]

    def __init__(self, db_session):
        self.db = db_session

    def konto_erstellen(
        self,
        bezeichnung: str,
        email_adresse: str,
        imap_server: str,
        smtp_server: str,
        benutzername: str,
        passwort: str,
        user_id: Optional[int] = None
    ) -> EmailKonto:
        """Erstellt ein neues E-Mail-Konto"""
        konto = EmailKonto(
            bezeichnung=bezeichnung,
            email_adresse=email_adresse,
            imap_server=imap_server,
            smtp_server=smtp_server,
            benutzername=benutzername,
            passwort_hash=self._hash_passwort(passwort),
            user_id=user_id
        )

        self.db.add(konto)
        self.db.flush()

        return konto

    def _hash_passwort(self, passwort: str) -> str:
        """Hasht ein Passwort (in Produktion: richtige Verschlüsselung verwenden!)"""
        return hashlib.sha256(passwort.encode()).hexdigest()

    def email_importieren(
        self,
        konto_id: int,
        von: str,
        an: str,
        betreff: str,
        text_inhalt: str,
        html_inhalt: Optional[str] = None,
        message_id: Optional[str] = None,
        gesendet_am: Optional[datetime] = None,
        anhaenge: Optional[List[Dict]] = None
    ) -> Email:
        """Importiert eine E-Mail und versucht automatische Zuordnung"""
        # Prüfe ob bereits vorhanden
        if message_id:
            existiert = self.db.query(Email).filter(
                Email.message_id == message_id
            ).first()
            if existiert:
                return existiert

        email = Email(
            konto_id=konto_id,
            von=von,
            an=an,
            betreff=betreff,
            text_inhalt=text_inhalt,
            html_inhalt=html_inhalt,
            message_id=message_id or self._generiere_message_id(),
            gesendet_am=gesendet_am,
            empfangen_am=datetime.now(),
            richtung=EmailRichtung.EINGANG
        )

        if anhaenge:
            email.anhaenge = anhaenge

        # Automatische Zuordnung versuchen
        zuordnung = self._versuche_auto_zuordnung(email)
        if zuordnung:
            email.projekt_id = zuordnung['projekt_id']
            email.auto_zugeordnet = True
            email.zuordnung_konfidenz = zuordnung['konfidenz']
            email.zuordnung_grund = zuordnung['grund']
            email.status = EmailStatus.ZUGEORDNET

        # Priorität erkennen
        email.prioritaet = self._erkenne_prioritaet(betreff, text_inhalt)

        self.db.add(email)
        self.db.flush()

        return email

    def _generiere_message_id(self) -> str:
        """Generiert eine eindeutige Message-ID"""
        import uuid
        return f"<{uuid.uuid4()}@schadenmanager.local>"

    def _versuche_auto_zuordnung(self, email: Email) -> Optional[Dict]:
        """Versucht eine E-Mail automatisch einem Projekt zuzuordnen"""
        from src.models import UnfallProjekt

        text = f"{email.betreff or ''} {email.text_inhalt or ''}"

        # 1. Suche nach Aktenzeichen im Text
        for muster in self.AKTENZEICHEN_MUSTER:
            match = re.search(muster, text, re.IGNORECASE)
            if match:
                aktenzeichen = match.group(1)
                projekt = self.db.query(UnfallProjekt).filter(
                    UnfallProjekt.aktenzeichen.ilike(f"%{aktenzeichen}%")
                ).first()

                if projekt:
                    return {
                        'projekt_id': projekt.id,
                        'konfidenz': 95,
                        'grund': f'Aktenzeichen gefunden: {aktenzeichen}'
                    }

        # 2. Suche nach E-Mail-Adresse des Absenders
        absender_email = self._extrahiere_email(email.von)
        if absender_email:
            # Suche in Beteiligte
            from src.models import Beteiligte
            beteiligter = self.db.query(Beteiligte).filter(
                Beteiligte.email == absender_email
            ).first()

            if beteiligter and beteiligter.projekt_id:
                return {
                    'projekt_id': beteiligter.projekt_id,
                    'konfidenz': 85,
                    'grund': f'Absender bekannt: {absender_email}'
                }

        # 3. Suche nach Kennzeichen
        kennzeichen_muster = r'[A-ZÄÖÜ]{1,3}[-\s]?[A-Z]{1,2}[-\s]?\d{1,4}'
        matches = re.findall(kennzeichen_muster, text)
        for kz in matches:
            kz_clean = kz.replace(' ', '-').upper()
            projekt = self.db.query(UnfallProjekt).filter(
                (UnfallProjekt.kennzeichen_mandant.ilike(f"%{kz_clean}%")) |
                (UnfallProjekt.kennzeichen_gegner.ilike(f"%{kz_clean}%"))
            ).first()

            if projekt:
                return {
                    'projekt_id': projekt.id,
                    'konfidenz': 70,
                    'grund': f'Kennzeichen gefunden: {kz_clean}'
                }

        return None

    def _extrahiere_email(self, von: str) -> Optional[str]:
        """Extrahiert E-Mail-Adresse aus Header"""
        match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', von)
        return match.group(0).lower() if match else None

    def _erkenne_prioritaet(self, betreff: str, inhalt: str) -> EmailPrioritaet:
        """Erkennt die Priorität einer E-Mail"""
        text = f"{betreff or ''} {inhalt or ''}".lower()

        for keyword in self.DRINGEND_KEYWORDS:
            if keyword in text:
                return EmailPrioritaet.DRINGEND

        if 'wichtig' in text or 'important' in text:
            return EmailPrioritaet.HOCH

        return EmailPrioritaet.NORMAL

    def email_manuell_zuordnen(
        self,
        email_id: int,
        projekt_id: int
    ) -> Optional[Email]:
        """Ordnet eine E-Mail manuell einem Projekt zu"""
        email = self.db.query(Email).get(email_id)

        if email:
            email.projekt_id = projekt_id
            email.auto_zugeordnet = False
            email.status = EmailStatus.ZUGEORDNET
            self.db.flush()

        return email

    def email_als_gelesen_markieren(self, email_id: int) -> Optional[Email]:
        """Markiert eine E-Mail als gelesen"""
        email = self.db.query(Email).get(email_id)

        if email:
            email.gelesen = True
            email.gelesen_am = datetime.now()
            self.db.flush()

        return email

    def emails_fuer_projekt(
        self,
        projekt_id: int,
        nur_ungelesen: bool = False
    ) -> List[Email]:
        """Holt alle E-Mails für ein Projekt"""
        query = self.db.query(Email).filter(Email.projekt_id == projekt_id)

        if nur_ungelesen:
            query = query.filter(Email.gelesen == False)

        return query.order_by(Email.empfangen_am.desc()).all()

    def unzugeordnete_emails(self) -> List[Email]:
        """Holt alle unzugeordneten E-Mails"""
        return self.db.query(Email).filter(
            Email.projekt_id == None,
            Email.status == EmailStatus.NEU
        ).order_by(Email.empfangen_am.desc()).all()

    def email_senden(
        self,
        konto_id: int,
        an: str,
        betreff: str,
        text_inhalt: str,
        projekt_id: Optional[int] = None,
        html_inhalt: Optional[str] = None,
        cc: Optional[str] = None,
        anhaenge: Optional[List[Dict]] = None
    ) -> Email:
        """Sendet eine E-Mail (Simulation - in Produktion SMTP verwenden)"""
        konto = self.db.query(EmailKonto).get(konto_id)

        email = Email(
            konto_id=konto_id,
            projekt_id=projekt_id,
            von=konto.email_adresse if konto else "system@schadenmanager.local",
            an=an,
            cc=cc,
            betreff=betreff,
            text_inhalt=text_inhalt,
            html_inhalt=html_inhalt,
            message_id=self._generiere_message_id(),
            richtung=EmailRichtung.AUSGANG,
            status=EmailStatus.BEARBEITET,
            gesendet_am=datetime.now()
        )

        if anhaenge:
            email.anhaenge = anhaenge

        self.db.add(email)
        self.db.flush()

        # Hier würde der eigentliche SMTP-Versand stattfinden
        # smtp_service.sende(email)

        return email

    def vorlage_erstellen(
        self,
        bezeichnung: str,
        betreff_vorlage: str,
        text_vorlage: str,
        kategorie: Optional[str] = None,
        erstellt_von_user_id: Optional[int] = None
    ) -> EmailVorlage:
        """Erstellt eine E-Mail-Vorlage"""
        # Extrahiere Platzhalter
        platzhalter = re.findall(r'\{\{(\w+)\}\}', f"{betreff_vorlage} {text_vorlage}")

        vorlage = EmailVorlage(
            bezeichnung=bezeichnung,
            kategorie=kategorie,
            betreff_vorlage=betreff_vorlage,
            text_vorlage=text_vorlage,
            erstellt_von_user_id=erstellt_von_user_id
        )
        vorlage.platzhalter = list(set(platzhalter))

        self.db.add(vorlage)
        self.db.flush()

        return vorlage

    def vorlage_anwenden(
        self,
        vorlage_id: int,
        werte: Dict[str, str]
    ) -> Dict[str, str]:
        """Wendet eine Vorlage mit Werten an"""
        vorlage = self.db.query(EmailVorlage).get(vorlage_id)

        if not vorlage:
            return {}

        betreff = vorlage.betreff_vorlage or ""
        text = vorlage.text_vorlage or ""

        for key, value in werte.items():
            betreff = betreff.replace(f"{{{{{key}}}}}", str(value))
            text = text.replace(f"{{{{{key}}}}}", str(value))

        return {
            'betreff': betreff,
            'text': text
        }

    def alle_vorlagen(self, kategorie: Optional[str] = None) -> List[EmailVorlage]:
        """Holt alle E-Mail-Vorlagen"""
        query = self.db.query(EmailVorlage).filter(EmailVorlage.aktiv == True)

        if kategorie:
            query = query.filter(EmailVorlage.kategorie == kategorie)

        return query.order_by(EmailVorlage.bezeichnung).all()

    def email_statistik(self, projekt_id: Optional[int] = None) -> Dict[str, Any]:
        """Erstellt eine E-Mail-Statistik"""
        query = self.db.query(Email)

        if projekt_id:
            query = query.filter(Email.projekt_id == projekt_id)

        alle_emails = query.all()

        return {
            'gesamt': len(alle_emails),
            'eingang': len([e for e in alle_emails if e.richtung == EmailRichtung.EINGANG]),
            'ausgang': len([e for e in alle_emails if e.richtung == EmailRichtung.AUSGANG]),
            'ungelesen': len([e for e in alle_emails if not e.gelesen and e.richtung == EmailRichtung.EINGANG]),
            'unzugeordnet': len([e for e in alle_emails if not e.projekt_id]),
            'dringend': len([e for e in alle_emails if e.prioritaet == EmailPrioritaet.DRINGEND and not e.gelesen])
        }

    def importiere_email_datei(
        self,
        datei_bytes: bytes,
        dateiname: str,
        user_id: int,
        projekt_id: Optional[int] = None
    ) -> Tuple[Optional['Email'], str]:
        """
        Importiert eine Email aus einer .eml oder .msg Datei.

        Args:
            datei_bytes: Die Datei-Bytes
            dateiname: Original-Dateiname
            user_id: ID des hochladenden Users
            projekt_id: Optionale Projekt-Zuordnung

        Returns:
            Tuple aus (Email-Objekt, Fehlermeldung)
        """
        from src.services.email_parser import get_email_parser
        from src.storage import get_storage_backend, generate_storage_key
        from src.config.settings import get_settings

        parser = get_email_parser()
        settings = get_settings()

        # Email parsen
        geparste_email, fehler = parser.parse_bytes(datei_bytes, dateiname)

        if fehler:
            return None, fehler

        # Prüfen ob bereits importiert
        existiert = self.db.query(Email).filter(
            Email.message_id == geparste_email.message_id
        ).first()

        if existiert:
            return existiert, "Email bereits importiert"

        # Email-Datei speichern
        storage = get_storage_backend()

        storage_key = generate_storage_key(
            projekt_id=projekt_id or 0,
            kategorie="emails",
            dateiname=dateiname
        )

        try:
            storage.put_bytes(storage_key, datei_bytes, "message/rfc822")
        except Exception as e:
            return None, f"Fehler beim Speichern: {str(e)}"

        # Email-Objekt erstellen
        von_str = f"{geparste_email.von_name} <{geparste_email.von_email}>" if geparste_email.von_name else geparste_email.von_email

        email_obj = Email(
            projekt_id=projekt_id,
            message_id=geparste_email.message_id,
            von=von_str,
            an=", ".join(geparste_email.an_emails),
            cc=", ".join(geparste_email.cc_emails) if geparste_email.cc_emails else None,
            betreff=geparste_email.betreff,
            text_inhalt=geparste_email.text_plain,
            html_inhalt=geparste_email.text_html,
            gesendet_am=geparste_email.gesendet_am,
            empfangen_am=datetime.now(),
            richtung=EmailRichtung.EINGANG,
            status=EmailStatus.ZUGEORDNET if projekt_id else EmailStatus.NEU,
            original_dateiname=dateiname,
            dateigroesse=len(datei_bytes),
            storage_provider=settings.storage_backend,
            storage_key=storage_key,
            importiert_via="DRAG_DROP",
            hochgeladen_von_user_id=user_id,
            thread_id=geparste_email.in_reply_to or geparste_email.message_id
        )

        # Anhänge als JSON speichern
        if geparste_email.anhaenge:
            anhaenge_info = []
            for anh in geparste_email.anhaenge:
                anhang_key = generate_storage_key(
                    projekt_id=projekt_id or 0,
                    kategorie="email_anhaenge",
                    dateiname=anh.dateiname
                )
                try:
                    storage.put_bytes(anhang_key, anh.daten, anh.content_type)
                    anhaenge_info.append({
                        "dateiname": anh.dateiname,
                        "content_type": anh.content_type,
                        "groesse": anh.groesse,
                        "storage_key": anhang_key
                    })
                except Exception:
                    pass

            email_obj.anhaenge = anhaenge_info

        # Priorität erkennen
        email_obj.prioritaet = self._erkenne_prioritaet(
            geparste_email.betreff,
            geparste_email.text_plain
        )

        # Automatische Zuordnung versuchen
        if not projekt_id:
            zuordnung = self._versuche_auto_zuordnung(email_obj)
            if zuordnung:
                email_obj.projekt_id = zuordnung['projekt_id']
                email_obj.auto_zugeordnet = True
                email_obj.zuordnung_konfidenz = zuordnung['konfidenz']
                email_obj.zuordnung_grund = zuordnung['grund']
                email_obj.status = EmailStatus.ZUGEORDNET

        self.db.add(email_obj)
        self.db.flush()

        return email_obj, ""

    def emails_fuer_projekt_gruppiert(
        self,
        projekt_id: int
    ) -> Dict[str, List['Email']]:
        """
        Holt alle Emails für ein Projekt, gruppiert nach Thread.

        Args:
            projekt_id: ID des Projekts

        Returns:
            Dict mit thread_id als Key und Liste von Emails als Value
        """
        emails = self.db.query(Email).filter(
            Email.projekt_id == projekt_id
        ).order_by(
            Email.gesendet_am.desc()
        ).all()

        threads = {}
        for email in emails:
            thread_id = email.thread_id or email.message_id or str(email.id)
            if thread_id not in threads:
                threads[thread_id] = []
            threads[thread_id].append(email)

        return threads

    def suche_emails(
        self,
        projekt_id: Optional[int] = None,
        suchbegriff: Optional[str] = None,
        von: Optional[str] = None,
        an: Optional[str] = None,
        nur_ungelesen: bool = False,
        nur_mit_anhaengen: bool = False,
        von_datum: Optional[datetime] = None,
        bis_datum: Optional[datetime] = None,
        limit: int = 50
    ) -> List['Email']:
        """
        Sucht Emails mit verschiedenen Filtern.
        """
        query = self.db.query(Email)

        if projekt_id:
            query = query.filter(Email.projekt_id == projekt_id)

        if suchbegriff:
            search = f"%{suchbegriff}%"
            query = query.filter(
                (Email.betreff.ilike(search)) |
                (Email.text_inhalt.ilike(search))
            )

        if von:
            query = query.filter(Email.von.ilike(f"%{von}%"))

        if an:
            query = query.filter(Email.an.ilike(f"%{an}%"))

        if nur_ungelesen:
            query = query.filter(Email.gelesen == False)

        if nur_mit_anhaengen:
            query = query.filter(Email._anhaenge.isnot(None))

        if von_datum:
            query = query.filter(Email.gesendet_am >= von_datum)

        if bis_datum:
            query = query.filter(Email.gesendet_am <= bis_datum)

        return query.order_by(Email.gesendet_am.desc()).limit(limit).all()


# Standard-Vorlagen
STANDARD_VORLAGEN = [
    {
        'bezeichnung': 'Schadenmeldung an Versicherung',
        'kategorie': 'Versicherung',
        'betreff': 'Schadenmeldung - Az. {{aktenzeichen}} - Unfall vom {{unfalldatum}}',
        'text': '''Sehr geehrte Damen und Herren,

hiermit zeigen wir an, dass wir die Interessen unseres Mandanten {{mandant_name}} vertreten.

Am {{unfalldatum}} kam es zu einem Verkehrsunfall, an dem unser Mandant mit seinem Fahrzeug ({{kennzeichen}}) beteiligt war.

Wir bitten um:
- Anerkennung der Haftung dem Grunde nach
- Mitteilung der Deckungssumme
- Benennung des zuständigen Sachbearbeiters

Mit freundlichen Grüßen
{{absender_name}}'''
    },
    {
        'bezeichnung': 'Zahlungserinnerung',
        'kategorie': 'Mahnung',
        'betreff': 'Zahlungserinnerung - Az. {{aktenzeichen}}',
        'text': '''Sehr geehrte Damen und Herren,

in vorbezeichneter Angelegenheit erinnern wir an den ausstehenden Betrag von {{betrag}} EUR.

Bitte überweisen Sie den Betrag bis zum {{frist_datum}} auf unser Konto.

Mit freundlichen Grüßen
{{absender_name}}'''
    },
    {
        'bezeichnung': 'Anforderung Gutachten',
        'kategorie': 'Gutachter',
        'betreff': 'Gutachtenauftrag - {{kennzeichen}} - Unfall vom {{unfalldatum}}',
        'text': '''Sehr geehrte Damen und Herren,

wir beauftragen Sie mit der Erstellung eines Schadensgutachtens für folgendes Fahrzeug:

Fahrzeug: {{fahrzeug}}
Kennzeichen: {{kennzeichen}}
Halter: {{mandant_name}}
Unfalldatum: {{unfalldatum}}

Bitte setzen Sie sich zur Terminvereinbarung mit unserem Mandanten in Verbindung:
{{mandant_telefon}}

Mit freundlichen Grüßen
{{absender_name}}'''
    }
]
