"""
Serienbriefe/Vorlagen-System Service
Dokumentenvorlagen mit Platzhaltern und Serienbrief-Funktion
"""
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from enum import Enum
import json
import re
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from src.models.base import Base


class VorlageKategorie(str, Enum):
    """Kategorien für Vorlagen"""
    ANSCHREIBEN = "ANSCHREIBEN"
    MAHNUNG = "MAHNUNG"
    ANFRAGE = "ANFRAGE"
    MITTEILUNG = "MITTEILUNG"
    VOLLMACHT = "VOLLMACHT"
    RECHNUNG = "RECHNUNG"
    KLAGE = "KLAGE"
    VERGLEICH = "VERGLEICH"
    SONSTIGE = "SONSTIGE"


class VorlageFormat(str, Enum):
    """Ausgabeformate"""
    DOCX = "DOCX"
    PDF = "PDF"
    HTML = "HTML"
    TXT = "TXT"


class Dokumentvorlage(Base):
    """Model für Dokumentvorlagen"""
    __tablename__ = "dokumentvorlage"

    id = Column(Integer, primary_key=True)

    # Vorlage
    bezeichnung = Column(String(200), nullable=False)
    kategorie = Column(SQLEnum(VorlageKategorie), default=VorlageKategorie.SONSTIGE)
    beschreibung = Column(Text)

    # Inhalt
    betreff_vorlage = Column(String(500))
    inhalt_vorlage = Column(Text, nullable=False)

    # Format-Einstellungen
    standard_format = Column(SQLEnum(VorlageFormat), default=VorlageFormat.DOCX)

    # Platzhalter (automatisch erkannt)
    _platzhalter = Column("platzhalter", Text)

    # Status
    aktiv = Column(Boolean, default=True)
    ist_system_vorlage = Column(Boolean, default=False)

    # Metadaten
    erstellt_von_user_id = Column(Integer, ForeignKey("user.id"))
    erstellt_am = Column(DateTime, default=datetime.now)
    aktualisiert_am = Column(DateTime, onupdate=datetime.now)

    @property
    def platzhalter(self) -> List[str]:
        if self._platzhalter:
            return json.loads(self._platzhalter)
        return []

    @platzhalter.setter
    def platzhalter(self, value: List[str]):
        self._platzhalter = json.dumps(value)


class GeneriertesDokument(Base):
    """Model für generierte Dokumente"""
    __tablename__ = "generiertes_dokument"

    id = Column(Integer, primary_key=True)

    # Referenzen
    vorlage_id = Column(Integer, ForeignKey("dokumentvorlage.id"))
    projekt_id = Column(Integer, ForeignKey("unfallprojekt.id"))
    projekt = relationship("UnfallProjekt", backref="generierte_dokumente")

    # Dokument
    bezeichnung = Column(String(200), nullable=False)
    betreff = Column(String(500))
    inhalt = Column(Text)
    format = Column(SQLEnum(VorlageFormat))

    # Verwendete Werte
    _verwendete_werte = Column("verwendete_werte", Text)

    # Versand
    versendet = Column(Boolean, default=False)
    versendet_am = Column(DateTime)
    versendet_an = Column(String(500))
    versand_art = Column(String(50))  # E-Mail, Post, Fax

    # Metadaten
    erstellt_von_user_id = Column(Integer, ForeignKey("user.id"))
    erstellt_am = Column(DateTime, default=datetime.now)

    @property
    def verwendete_werte(self) -> Dict[str, str]:
        if self._verwendete_werte:
            return json.loads(self._verwendete_werte)
        return {}

    @verwendete_werte.setter
    def verwendete_werte(self, value: Dict[str, str]):
        self._verwendete_werte = json.dumps(value)


class SerienbriefeService:
    """Service für Serienbriefe und Vorlagen"""

    # Standard-Platzhalter mit Beschreibungen
    STANDARD_PLATZHALTER = {
        # Projekt
        '{{aktenzeichen}}': 'Aktenzeichen des Projekts',
        '{{projektnummer}}': 'Projektnummer',
        '{{unfalldatum}}': 'Datum des Unfalls',
        '{{unfallort}}': 'Ort des Unfalls',

        # Mandant
        '{{mandant_name}}': 'Vollständiger Name des Mandanten',
        '{{mandant_vorname}}': 'Vorname des Mandanten',
        '{{mandant_nachname}}': 'Nachname des Mandanten',
        '{{mandant_anrede}}': 'Anrede (Herr/Frau)',
        '{{mandant_strasse}}': 'Straße und Hausnummer',
        '{{mandant_plz}}': 'Postleitzahl',
        '{{mandant_ort}}': 'Ort',
        '{{mandant_telefon}}': 'Telefonnummer',
        '{{mandant_email}}': 'E-Mail-Adresse',

        # Gegner/Versicherung
        '{{gegner_name}}': 'Name des Unfallgegners',
        '{{gegner_kennzeichen}}': 'Kennzeichen des Gegners',
        '{{versicherung_name}}': 'Name der gegnerischen Versicherung',
        '{{versicherung_schadennummer}}': 'Schadennummer der Versicherung',

        # Fahrzeug
        '{{kennzeichen}}': 'Kennzeichen des Mandantenfahrzeugs',
        '{{fahrzeug}}': 'Fahrzeugbezeichnung',

        # Beträge
        '{{gesamtschaden}}': 'Gesamtschadensumme',
        '{{forderung}}': 'Forderungsbetrag',
        '{{gezahlt}}': 'Bereits gezahlter Betrag',
        '{{offen}}': 'Offener Betrag',

        # Datum
        '{{heute}}': 'Heutiges Datum',
        '{{frist_datum}}': 'Fristdatum',

        # Kanzlei
        '{{kanzlei_name}}': 'Name der Kanzlei',
        '{{kanzlei_adresse}}': 'Adresse der Kanzlei',
        '{{sachbearbeiter}}': 'Name des Sachbearbeiters'
    }

    def __init__(self, db_session):
        self.db = db_session

    def vorlage_erstellen(
        self,
        bezeichnung: str,
        inhalt_vorlage: str,
        kategorie: VorlageKategorie = VorlageKategorie.SONSTIGE,
        betreff_vorlage: Optional[str] = None,
        beschreibung: Optional[str] = None,
        erstellt_von_user_id: Optional[int] = None
    ) -> Dokumentvorlage:
        """Erstellt eine neue Dokumentvorlage"""
        vorlage = Dokumentvorlage(
            bezeichnung=bezeichnung,
            kategorie=kategorie,
            beschreibung=beschreibung,
            betreff_vorlage=betreff_vorlage,
            inhalt_vorlage=inhalt_vorlage,
            erstellt_von_user_id=erstellt_von_user_id
        )

        # Platzhalter automatisch erkennen
        platzhalter = self._extrahiere_platzhalter(inhalt_vorlage)
        if betreff_vorlage:
            platzhalter.extend(self._extrahiere_platzhalter(betreff_vorlage))
        vorlage.platzhalter = list(set(platzhalter))

        self.db.add(vorlage)
        self.db.flush()

        return vorlage

    def _extrahiere_platzhalter(self, text: str) -> List[str]:
        """Extrahiert Platzhalter aus Text"""
        return re.findall(r'\{\{(\w+)\}\}', text)

    def vorlage_aktualisieren(
        self,
        vorlage_id: int,
        **kwargs
    ) -> Optional[Dokumentvorlage]:
        """Aktualisiert eine Vorlage"""
        vorlage = self.db.query(Dokumentvorlage).get(vorlage_id)

        if vorlage:
            for key, value in kwargs.items():
                if hasattr(vorlage, key):
                    setattr(vorlage, key, value)

            # Platzhalter neu extrahieren
            inhalt = kwargs.get('inhalt_vorlage', vorlage.inhalt_vorlage)
            betreff = kwargs.get('betreff_vorlage', vorlage.betreff_vorlage)
            platzhalter = self._extrahiere_platzhalter(inhalt or '')
            if betreff:
                platzhalter.extend(self._extrahiere_platzhalter(betreff))
            vorlage.platzhalter = list(set(platzhalter))

            self.db.flush()

        return vorlage

    def alle_vorlagen(
        self,
        kategorie: Optional[VorlageKategorie] = None,
        nur_aktive: bool = True
    ) -> List[Dokumentvorlage]:
        """Holt alle Vorlagen"""
        query = self.db.query(Dokumentvorlage)

        if nur_aktive:
            query = query.filter(Dokumentvorlage.aktiv == True)

        if kategorie:
            query = query.filter(Dokumentvorlage.kategorie == kategorie)

        return query.order_by(Dokumentvorlage.bezeichnung).all()

    def dokument_generieren(
        self,
        vorlage_id: int,
        projekt_id: int,
        werte: Optional[Dict[str, str]] = None,
        format: VorlageFormat = VorlageFormat.DOCX,
        erstellt_von_user_id: Optional[int] = None
    ) -> GeneriertesDokument:
        """Generiert ein Dokument aus einer Vorlage"""
        vorlage = self.db.query(Dokumentvorlage).get(vorlage_id)

        if not vorlage:
            raise ValueError("Vorlage nicht gefunden")

        # Werte aus Projekt laden und mit übergebenen Werten ergänzen
        projekt_werte = self._lade_projekt_werte(projekt_id)
        alle_werte = {**projekt_werte, **(werte or {})}

        # Platzhalter ersetzen
        betreff = self._ersetze_platzhalter(vorlage.betreff_vorlage or '', alle_werte)
        inhalt = self._ersetze_platzhalter(vorlage.inhalt_vorlage, alle_werte)

        # Dokument erstellen
        dokument = GeneriertesDokument(
            vorlage_id=vorlage_id,
            projekt_id=projekt_id,
            bezeichnung=f"{vorlage.bezeichnung} - {datetime.now().strftime('%d.%m.%Y')}",
            betreff=betreff,
            inhalt=inhalt,
            format=format,
            erstellt_von_user_id=erstellt_von_user_id
        )
        dokument.verwendete_werte = alle_werte

        self.db.add(dokument)
        self.db.flush()

        return dokument

    def _ersetze_platzhalter(self, text: str, werte: Dict[str, str]) -> str:
        """Ersetzt Platzhalter im Text"""
        for key, value in werte.items():
            platzhalter = f"{{{{{key}}}}}"
            text = text.replace(platzhalter, str(value) if value else '')

        return text

    def _lade_projekt_werte(self, projekt_id: int) -> Dict[str, str]:
        """Lädt Standard-Werte aus einem Projekt"""
        from src.models import UnfallProjekt

        projekt = self.db.query(UnfallProjekt).get(projekt_id)

        if not projekt:
            return {}

        werte = {
            'aktenzeichen': projekt.aktenzeichen or '',
            'projektnummer': projekt.projektnummer or '',
            'unfalldatum': projekt.unfalldatum.strftime('%d.%m.%Y') if projekt.unfalldatum else '',
            'unfallort': projekt.unfallort or '',
            'kennzeichen': projekt.kennzeichen_mandant or '',
            'gegner_kennzeichen': projekt.kennzeichen_gegner or '',
            'heute': date.today().strftime('%d.%m.%Y')
        }

        # Mandant laden
        if hasattr(projekt, 'beteiligte'):
            for b in projekt.beteiligte:
                if hasattr(b, 'rolle') and b.rolle and b.rolle.value == 'MANDANT':
                    werte['mandant_vorname'] = b.vorname or ''
                    werte['mandant_nachname'] = b.nachname or ''
                    werte['mandant_name'] = f"{b.vorname or ''} {b.nachname or ''}".strip()
                    werte['mandant_anrede'] = 'Herr' if getattr(b, 'anrede', '') == 'HERR' else 'Frau'
                    werte['mandant_strasse'] = b.strasse or ''
                    werte['mandant_plz'] = b.plz or ''
                    werte['mandant_ort'] = b.ort or ''
                    werte['mandant_telefon'] = b.telefon or ''
                    werte['mandant_email'] = b.email or ''
                    break

        # Forderung laden
        if hasattr(projekt, 'forderung') and projekt.forderung:
            werte['gesamtschaden'] = f"{float(projekt.forderung.gesamtforderung or 0):,.2f} EUR"
            werte['forderung'] = f"{float(projekt.forderung.gesamtforderung or 0):,.2f} EUR"
            werte['gezahlt'] = f"{float(projekt.forderung.bezahlt or 0):,.2f} EUR"
            werte['offen'] = f"{float(projekt.forderung.offen or 0):,.2f} EUR"

        return werte

    def serienbrief_generieren(
        self,
        vorlage_id: int,
        projekt_ids: List[int],
        zusaetzliche_werte: Optional[Dict[str, str]] = None,
        erstellt_von_user_id: Optional[int] = None
    ) -> List[GeneriertesDokument]:
        """Generiert Serienbriefe für mehrere Projekte"""
        dokumente = []

        for projekt_id in projekt_ids:
            try:
                dokument = self.dokument_generieren(
                    vorlage_id=vorlage_id,
                    projekt_id=projekt_id,
                    werte=zusaetzliche_werte,
                    erstellt_von_user_id=erstellt_von_user_id
                )
                dokumente.append(dokument)
            except Exception as e:
                # Fehler protokollieren, aber weitermachen
                print(f"Fehler bei Projekt {projekt_id}: {e}")

        return dokumente

    def generiere_vorschau(
        self,
        vorlage_id: int,
        projekt_id: int,
        werte: Optional[Dict[str, str]] = None
    ) -> Dict[str, str]:
        """Generiert eine Vorschau ohne zu speichern"""
        vorlage = self.db.query(Dokumentvorlage).get(vorlage_id)

        if not vorlage:
            return {'fehler': 'Vorlage nicht gefunden'}

        projekt_werte = self._lade_projekt_werte(projekt_id)
        alle_werte = {**projekt_werte, **(werte or {})}

        return {
            'betreff': self._ersetze_platzhalter(vorlage.betreff_vorlage or '', alle_werte),
            'inhalt': self._ersetze_platzhalter(vorlage.inhalt_vorlage, alle_werte),
            'fehlende_platzhalter': [p for p in vorlage.platzhalter if p not in alle_werte or not alle_werte[p]]
        }

    def dokumente_fuer_projekt(self, projekt_id: int) -> List[GeneriertesDokument]:
        """Holt alle generierten Dokumente für ein Projekt"""
        return self.db.query(GeneriertesDokument).filter(
            GeneriertesDokument.projekt_id == projekt_id
        ).order_by(GeneriertesDokument.erstellt_am.desc()).all()

    def als_versendet_markieren(
        self,
        dokument_id: int,
        empfaenger: str,
        versand_art: str = "E-Mail"
    ) -> Optional[GeneriertesDokument]:
        """Markiert ein Dokument als versendet"""
        dokument = self.db.query(GeneriertesDokument).get(dokument_id)

        if dokument:
            dokument.versendet = True
            dokument.versendet_am = datetime.now()
            dokument.versendet_an = empfaenger
            dokument.versand_art = versand_art
            self.db.flush()

        return dokument


# Standard-Vorlagen
STANDARD_VORLAGEN = [
    {
        'bezeichnung': 'Schadenmeldung an gegnerische Versicherung',
        'kategorie': VorlageKategorie.ANSCHREIBEN,
        'betreff': 'Schadenmeldung - Unfall vom {{unfalldatum}} - Ihr Versicherungsnehmer {{gegner_name}}',
        'inhalt': '''{{kanzlei_name}}
{{kanzlei_adresse}}

{{versicherung_name}}
{{versicherung_adresse}}

{{heute}}

Unser Zeichen: {{aktenzeichen}}
Unfalldatum: {{unfalldatum}}
Unfallort: {{unfallort}}

Sehr geehrte Damen und Herren,

wir zeigen an, dass wir die rechtlichen Interessen von

{{mandant_anrede}} {{mandant_name}}
{{mandant_strasse}}
{{mandant_plz}} {{mandant_ort}}

vertreten. Ordnungsgemäße Bevollmächtigung wird anwaltlich versichert.

Am {{unfalldatum}} kam es in {{unfallort}} zu einem Verkehrsunfall zwischen dem Fahrzeug unseres Mandanten (Kennzeichen: {{kennzeichen}}) und dem bei Ihnen versicherten Fahrzeug (Kennzeichen: {{gegner_kennzeichen}}).

Wir fordern Sie auf, die Haftung dem Grunde nach anzuerkennen und uns mitzuteilen, in welcher Höhe Deckungsschutz besteht.

Den entstandenen Schaden werden wir Ihnen nach Vorliegen des Gutachtens beziffern.

Mit freundlichen Grüßen

{{sachbearbeiter}}
'''
    },
    {
        'bezeichnung': 'Erste Mahnung',
        'kategorie': VorlageKategorie.MAHNUNG,
        'betreff': 'Mahnung - {{aktenzeichen}} - Unfall vom {{unfalldatum}}',
        'inhalt': '''{{kanzlei_name}}
{{kanzlei_adresse}}

{{versicherung_name}}

{{heute}}

Unser Zeichen: {{aktenzeichen}}

Sehr geehrte Damen und Herren,

in vorbezeichneter Angelegenheit erinnern wir an unsere Forderung in Höhe von {{forderung}}.

Trotz mehrfacher Aufforderung ist bisher kein Zahlungseingang zu verzeichnen.

Wir fordern Sie daher letztmalig auf, den offenen Betrag von {{offen}} bis zum {{frist_datum}} auf unser Konto zu überweisen.

Sollte bis dahin kein Zahlungseingang erfolgen, werden wir ohne weitere Ankündigung gerichtliche Schritte einleiten.

Mit freundlichen Grüßen

{{sachbearbeiter}}
'''
    },
    {
        'bezeichnung': 'Vollmacht',
        'kategorie': VorlageKategorie.VOLLMACHT,
        'betreff': 'Vollmacht',
        'inhalt': '''VOLLMACHT

Ich, {{mandant_name}}, wohnhaft in {{mandant_strasse}}, {{mandant_plz}} {{mandant_ort}},

erteile hiermit

{{kanzlei_name}}
{{kanzlei_adresse}}

Vollmacht, mich in der Angelegenheit

Verkehrsunfall vom {{unfalldatum}} in {{unfallort}}
Aktenzeichen: {{aktenzeichen}}

außergerichtlich und gerichtlich zu vertreten.

Die Vollmacht umfasst insbesondere:
- Die Geltendmachung und Durchsetzung sämtlicher Schadensersatzansprüche
- Die Führung von Verhandlungen
- Die Einholung von Auskünften
- Den Abschluss von Vergleichen
- Die Entgegennahme von Zahlungen

{{mandant_ort}}, den {{heute}}

_______________________________
{{mandant_name}}
'''
    }
]
