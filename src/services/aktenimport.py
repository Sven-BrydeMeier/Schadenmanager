"""
Aktenimport Service
Import von PDF-Akten mit automatischer Dokumententrennung und Beteiligten-Extraktion
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum
import json
import re
import secrets
import hashlib
import os
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Enum as SQLEnum, Float
from sqlalchemy.orm import relationship
from src.models.base import Base


class EinladungsStatus(str, Enum):
    """Status einer Einladung"""
    AUSSTEHEND = "AUSSTEHEND"
    VERSENDET = "VERSENDET"
    ANGENOMMEN = "ANGENOMMEN"
    ABGELAUFEN = "ABGELAUFEN"
    STORNIERT = "STORNIERT"


class BeteiligtenRolle(str, Enum):
    """Rolle eines Beteiligten im Verfahren"""
    GESCHAEDIGTER = "GESCHAEDIGTER"
    UNFALLVERURSACHER = "UNFALLVERURSACHER"
    VERSICHERUNG_GESCHAEDIGTER = "VERSICHERUNG_GESCHAEDIGTER"
    VERSICHERUNG_VERURSACHER = "VERSICHERUNG_VERURSACHER"
    GUTACHTER = "GUTACHTER"
    WERKSTATT = "WERKSTATT"
    ZEUGE = "ZEUGE"
    GEGNERISCHER_ANWALT = "GEGNERISCHER_ANWALT"
    SONSTIGER = "SONSTIGER"


class AktenImport(Base):
    """Model für importierte Akten"""
    __tablename__ = "akten_import"

    id = Column(Integer, primary_key=True)

    # Zuordnung zum Projekt
    projekt_id = Column(Integer, ForeignKey("unfallprojekt.id"), nullable=False)
    projekt = relationship("UnfallProjekt", backref="akten_importe")

    # Import-Metadaten
    original_dateiname = Column(String(255))
    original_dateipfad = Column(String(500))
    import_datum = Column(DateTime, default=datetime.now)
    importiert_von_user_id = Column(Integer, ForeignKey("user.id"))

    # Extrahierte Daten
    extrahiertes_aktenzeichen = Column(String(100))
    anzahl_seiten = Column(Integer, default=0)
    anzahl_dokumente = Column(Integer, default=0)

    # Inhaltsverzeichnis (JSON)
    _inhaltsverzeichnis = Column("inhaltsverzeichnis", Text)

    # Status
    import_abgeschlossen = Column(Boolean, default=False)
    fehler_meldung = Column(Text)

    @property
    def inhaltsverzeichnis(self) -> List[Dict]:
        if self._inhaltsverzeichnis:
            return json.loads(self._inhaltsverzeichnis)
        return []

    @inhaltsverzeichnis.setter
    def inhaltsverzeichnis(self, value: List[Dict]):
        self._inhaltsverzeichnis = json.dumps(value, default=str)


class AktenDokument(Base):
    """Einzelnes Dokument aus einer importierten Akte"""
    __tablename__ = "akten_dokument"

    id = Column(Integer, primary_key=True)

    # Zuordnung
    akten_import_id = Column(Integer, ForeignKey("akten_import.id"), nullable=False)
    akten_import = relationship("AktenImport", backref="dokumente")

    projekt_id = Column(Integer, ForeignKey("unfallprojekt.id"), nullable=False)
    dokument_id = Column(Integer, ForeignKey("dokument.id"))  # Referenz zum gespeicherten Dokument

    # Dokument-Metadaten
    position_im_inhaltsverzeichnis = Column(Integer)
    titel = Column(String(255))
    dokumenttyp = Column(String(100))
    seite_von = Column(Integer)
    seite_bis = Column(Integer)

    # Fortschritts-Tracking
    ist_meilenstein = Column(Boolean, default=False)
    fortschritt_prozent = Column(Float, default=0)  # Anteil am Gesamtfortschritt

    # Zeitstempel
    erstellt_am = Column(DateTime, default=datetime.now)


class AktenBeteiligter(Base):
    """Beteiligter einer Akte"""
    __tablename__ = "akten_beteiligter"

    id = Column(Integer, primary_key=True)

    # Zuordnung
    akten_import_id = Column(Integer, ForeignKey("akten_import.id"), nullable=False)
    akten_import = relationship("AktenImport", backref="beteiligte")

    projekt_id = Column(Integer, ForeignKey("unfallprojekt.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("user.id"))  # Verknüpfter User (falls vorhanden)

    # Beteiligtendaten
    rolle = Column(SQLEnum(BeteiligtenRolle), default=BeteiligtenRolle.SONSTIGER)
    name = Column(String(200))
    vorname = Column(String(100))
    email = Column(String(200))
    telefon = Column(String(50))
    adresse = Column(Text)

    # Aus PDF extrahiert
    extrahiert_aus_pdf = Column(Boolean, default=False)

    erstellt_am = Column(DateTime, default=datetime.now)


class DokumentFreigabe(Base):
    """Freigabe eines Dokuments für einen Beteiligten"""
    __tablename__ = "dokument_freigabe"

    id = Column(Integer, primary_key=True)

    # Zuordnungen
    akten_dokument_id = Column(Integer, ForeignKey("akten_dokument.id"), nullable=False)
    akten_dokument = relationship("AktenDokument", backref="freigaben")

    beteiligter_id = Column(Integer, ForeignKey("akten_beteiligter.id"), nullable=False)
    beteiligter = relationship("AktenBeteiligter", backref="dokument_freigaben")

    # Freigabe-Details
    freigegeben_am = Column(DateTime, default=datetime.now)
    freigegeben_von_user_id = Column(Integer, ForeignKey("user.id"))

    # Lesestatus
    gelesen_am = Column(DateTime)
    heruntergeladen_am = Column(DateTime)


class Einladung(Base):
    """Einladung für neue Beteiligte"""
    __tablename__ = "einladung"

    id = Column(Integer, primary_key=True)

    # Zuordnung
    projekt_id = Column(Integer, ForeignKey("unfallprojekt.id"), nullable=False)
    beteiligter_id = Column(Integer, ForeignKey("akten_beteiligter.id"), nullable=False)
    beteiligter = relationship("AktenBeteiligter", backref="einladungen")

    # Einladungsdaten
    email = Column(String(200), nullable=False)
    einladungscode = Column(String(100), unique=True, nullable=False)
    einmalpasswort = Column(String(100))  # Gehashed
    einmalpasswort_klartext = Column(String(20))  # Temporär für Anzeige, wird nach Versand gelöscht

    # Status
    status = Column(SQLEnum(EinladungsStatus), default=EinladungsStatus.AUSSTEHEND)
    erstellt_am = Column(DateTime, default=datetime.now)
    versendet_am = Column(DateTime)
    gueltig_bis = Column(DateTime)
    angenommen_am = Column(DateTime)

    # Erstellt von
    erstellt_von_user_id = Column(Integer, ForeignKey("user.id"))


class AktenImportService:
    """Service für den Import von PDF-Akten"""

    # Muster für Aktenzeichen-Erkennung
    AKTENZEICHEN_PATTERNS = [
        r'(?:Az\.?|Aktenzeichen|AZ|Geschäftszeichen)[:\s]*([A-Za-z0-9\-/\.]+)',
        r'(\d{1,3}\s*[A-Z]{1,2}\s*\d{1,5}/\d{2,4})',  # Gerichtsaktenzeichen
        r'(?:Schaden(?:s)?(?:-)?Nr\.?|Schadensnummer)[:\s]*([A-Za-z0-9\-/]+)',
        r'(?:Versicherungs(?:-)?Nr\.?)[:\s]*([A-Za-z0-9\-/]+)',
        r'(?:Unser\s+Zeichen|Ihr\s+Zeichen)[:\s]*([A-Za-z0-9\-/\.]+)'
    ]

    # Erweiterte Muster für Beteiligte im Aktenvorblatt
    BETEILIGTER_PATTERNS = {
        BeteiligtenRolle.GESCHAEDIGTER: [
            r'(?:Geschädigt(?:er|e)|Anspruchsteller|Kläger|Mandant(?:in)?)[:\s]*([^\n,;]+?)(?:\n|,|;|$)',
            r'(?:Auftraggeber)[:\s]*([^\n,;]+?)(?:\n|,|;|$)',
        ],
        BeteiligtenRolle.UNFALLVERURSACHER: [
            r'(?:Unfallverursacher|Schädiger|Beklagte(?:r)?|Unfallgegner)[:\s]*([^\n,;]+?)(?:\n|,|;|$)',
        ],
        BeteiligtenRolle.VERSICHERUNG_VERURSACHER: [
            r'(?:Haftpflichtversicherung|gegnerische\s+Versicherung|Versicherung\s+des\s+(?:Unfallgegners|Schädigers))[:\s]*([^\n,;]+?)(?:\n|,|;|$)',
            r'(?:Gegnerische\s+Haftpflicht)[:\s]*([^\n,;]+?)(?:\n|,|;|$)',
        ],
        BeteiligtenRolle.VERSICHERUNG_GESCHAEDIGTER: [
            r'(?:Eigene\s+Versicherung|Kaskoversicherung|Vollkasko|Teilkasko)[:\s]*([^\n,;]+?)(?:\n|,|;|$)',
        ],
        BeteiligtenRolle.GUTACHTER: [
            r'(?:Gutachter|Sachverständiger)[:\s]*([^\n,;]+?)(?:\n|,|;|$)',
        ],
        BeteiligtenRolle.WERKSTATT: [
            r'(?:Werkstatt|Reparaturbetrieb|Autohaus)[:\s]*([^\n,;]+?)(?:\n|,|;|$)',
        ],
        BeteiligtenRolle.GEGNERISCHER_ANWALT: [
            r'(?:Gegnerischer\s+(?:Anwalt|Rechtsanwalt)|Anwalt\s+des\s+(?:Gegners|Schädigers))[:\s]*([^\n,;]+?)(?:\n|,|;|$)',
        ],
        BeteiligtenRolle.ZEUGE: [
            r'(?:Zeuge(?:n)?)[:\s]*([^\n,;]+?)(?:\n|,|;|$)',
        ]
    }

    # Muster für Inhaltsverzeichnis-Einträge
    INHALTSVERZEICHNIS_PATTERNS = [
        # Format: "1. Gutachten ..... 5" oder "1. Gutachten ... Seite 5"
        r'^[\s]*(\d+)[\.\)]\s*([^\.…\d][^\n]+?)[\.…\s]+(?:Seite\s*)?(\d+)\s*$',
        # Format: "Anlage 1: Gutachten Seite 5-10"
        r'^[\s]*(?:Anlage\s*)?(\d+)[:\.\)]\s*([^\n]+?)\s+(?:Seite\s*)?(\d+)(?:\s*[-–]\s*(\d+))?\s*$',
        # Format: "Gutachten .............. 5"
        r'^[\s]*([A-Za-zäöüÄÖÜß][^\n\.…]+?)[\.…\s]{3,}(\d+)\s*$',
        # Format: "- Gutachten (Seite 5-10)"
        r'^[\s]*[-•]\s*([^\n\(]+?)\s*\((?:Seite\s*)?(\d+)(?:\s*[-–]\s*(\d+))?\)\s*$',
        # Format: "Blatt 5: Gutachten"
        r'^[\s]*(?:Blatt|Bl\.)\s*(\d+)[:\s]+([^\n]+?)\s*$',
    ]

    def __init__(self, db_session):
        self.db = db_session

    def importiere_akte(
        self,
        projekt_id: int,
        pdf_inhalt: bytes,
        dateiname: str,
        user_id: int
    ) -> AktenImport:
        """Importiert eine PDF-Akte und extrahiert Dokumente"""

        # Import-Eintrag erstellen
        akten_import = AktenImport(
            projekt_id=projekt_id,
            original_dateiname=dateiname,
            import_datum=datetime.now(),
            importiert_von_user_id=user_id
        )

        try:
            # PDF analysieren
            pdf_analyse = self._analysiere_pdf(pdf_inhalt)

            akten_import.anzahl_seiten = pdf_analyse.get('anzahl_seiten', 0)
            akten_import.extrahiertes_aktenzeichen = pdf_analyse.get('aktenzeichen')
            akten_import.inhaltsverzeichnis = pdf_analyse.get('inhaltsverzeichnis', [])

            self.db.add(akten_import)
            self.db.flush()

            # Dokumente aufteilen und speichern
            dokumente = self._extrahiere_dokumente(
                akten_import,
                pdf_inhalt,
                pdf_analyse
            )

            akten_import.anzahl_dokumente = len(dokumente)

            # Beteiligte aus Aktenvorblatt extrahieren
            beteiligte = self._extrahiere_beteiligte(
                akten_import,
                pdf_analyse.get('text_inhalt', ''),
                pdf_analyse.get('seiten_texte', [])
            )

            # Projekt aktualisieren wenn Aktenzeichen gefunden
            if akten_import.extrahiertes_aktenzeichen:
                from src.models import UnfallProjekt
                projekt = self.db.query(UnfallProjekt).get(projekt_id)
                if projekt and not projekt.aktenzeichen:
                    projekt.aktenzeichen = akten_import.extrahiertes_aktenzeichen

            akten_import.import_abgeschlossen = True

        except Exception as e:
            akten_import.fehler_meldung = str(e)
            akten_import.import_abgeschlossen = False

        self.db.add(akten_import)
        self.db.flush()

        return akten_import

    def _analysiere_pdf(self, pdf_inhalt: bytes) -> Dict[str, Any]:
        """Analysiert ein PDF und extrahiert Metadaten"""
        result = {
            'anzahl_seiten': 0,
            'aktenzeichen': None,
            'inhaltsverzeichnis': [],
            'text_inhalt': '',
            'lesezeichen': [],
            'seiten_texte': []  # Text pro Seite
        }

        try:
            import io

            try:
                import PyPDF2
                pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_inhalt))
                result['anzahl_seiten'] = len(pdf_reader.pages)

                # Text pro Seite extrahieren
                text_gesamt = ""
                seiten_texte = []
                for i, page in enumerate(pdf_reader.pages):
                    seiten_text = page.extract_text() or ""
                    seiten_texte.append({
                        'seite': i + 1,
                        'text': seiten_text
                    })
                    text_gesamt += f"\n--- Seite {i + 1} ---\n" + seiten_text

                result['text_inhalt'] = text_gesamt
                result['seiten_texte'] = seiten_texte

                # Lesezeichen/Outlines extrahieren (falls vorhanden)
                try:
                    if pdf_reader.outline:
                        result['lesezeichen'] = self._parse_lesezeichen(pdf_reader, pdf_reader.outline)
                except Exception as e:
                    result['lesezeichen'] = []

            except ImportError:
                # Fallback ohne PyPDF2
                result['anzahl_seiten'] = 1
                result['text_inhalt'] = ""
                result['seiten_texte'] = []

            # Aktenzeichen suchen
            for pattern in self.AKTENZEICHEN_PATTERNS:
                match = re.search(pattern, result['text_inhalt'], re.IGNORECASE)
                if match:
                    result['aktenzeichen'] = match.group(1).strip()
                    break

            # Inhaltsverzeichnis erstellen
            if result['lesezeichen'] and len(result['lesezeichen']) > 0:
                # Lesezeichen gefunden - diese verwenden
                result['inhaltsverzeichnis'] = self._lesezeichen_zu_inhaltsverzeichnis(
                    result['lesezeichen'],
                    result['anzahl_seiten']
                )
            else:
                # Versuche Inhaltsverzeichnis aus Text zu extrahieren
                result['inhaltsverzeichnis'] = self._extrahiere_inhaltsverzeichnis_aus_text(
                    result['text_inhalt'],
                    result['seiten_texte'],
                    result['anzahl_seiten']
                )

            # Wenn immer noch kein Inhaltsverzeichnis, seitenbasierte Analyse
            if not result['inhaltsverzeichnis']:
                result['inhaltsverzeichnis'] = self._analysiere_seiten_fuer_dokumente(
                    result['seiten_texte'],
                    result['anzahl_seiten']
                )

        except Exception as e:
            result['fehler'] = str(e)

        return result

    def _parse_lesezeichen(self, pdf_reader, outline, level: int = 0) -> List[Dict]:
        """Parsed PDF-Lesezeichen rekursiv mit Seitenzahl-Ermittlung"""
        result = []

        if isinstance(outline, list):
            for item in outline:
                result.extend(self._parse_lesezeichen(pdf_reader, item, level))
        else:
            try:
                titel = outline.title if hasattr(outline, 'title') else str(outline)

                # Seitenzahl ermitteln
                seite = 1
                if hasattr(outline, 'page'):
                    try:
                        # PyPDF2 3.x
                        page_obj = outline.page
                        if page_obj:
                            seite = pdf_reader.pages.index(page_obj) + 1
                    except:
                        try:
                            # Alternativer Ansatz
                            dest = pdf_reader.get_destination_page_number(outline)
                            seite = dest + 1 if dest is not None else 1
                        except:
                            seite = 1

                result.append({
                    'titel': titel,
                    'seite_von': seite,
                    'ebene': level
                })
            except:
                pass

        return result

    def _lesezeichen_zu_inhaltsverzeichnis(self, lesezeichen: List[Dict], anzahl_seiten: int) -> List[Dict]:
        """Konvertiert Lesezeichen zu einem Inhaltsverzeichnis mit Seitenbereichen"""
        if not lesezeichen:
            return []

        # Nach Seitenzahl sortieren
        lesezeichen_sortiert = sorted(lesezeichen, key=lambda x: x.get('seite_von', 1))

        inhaltsverzeichnis = []
        for i, lz in enumerate(lesezeichen_sortiert):
            typ = self._erkenne_dokumenttyp_aus_titel(lz.get('titel', ''))

            eintrag = {
                'position': i,
                'titel': lz.get('titel', f'Dokument {i + 1}'),
                'typ': typ,
                'seite_von': lz.get('seite_von', 1),
                'seite_bis': anzahl_seiten  # Wird unten korrigiert
            }

            # Seite bis = nächste Seite - 1
            if i + 1 < len(lesezeichen_sortiert):
                naechste_seite = lesezeichen_sortiert[i + 1].get('seite_von', anzahl_seiten)
                eintrag['seite_bis'] = max(eintrag['seite_von'], naechste_seite - 1)

            inhaltsverzeichnis.append(eintrag)

        return inhaltsverzeichnis

    def _erkenne_dokumenttyp_aus_titel(self, titel: str) -> str:
        """Erkennt den Dokumenttyp aus dem Titel"""
        titel_lower = titel.lower()

        typ_mapping = {
            'gutachten': 'GUTACHTEN',
            'kostenvoranschlag': 'KOSTENVORANSCHLAG',
            'rechnung': 'RECHNUNG',
            'kürzung': 'KUERZUNGSSCHREIBEN',
            'anspruch': 'ANSPRUCHSSCHREIBEN',
            'vollmacht': 'VOLLMACHT',
            'unfallbericht': 'UNFALLBERICHT',
            'polizei': 'POLIZEIBERICHT',
            'zeuge': 'ZEUGENAUSSAGE',
            'foto': 'FOTOS',
            'lichtbild': 'FOTOS',
            'korrespondenz': 'KORRESPONDENZ',
            'schreiben': 'KORRESPONDENZ',
            'versicherung': 'VERSICHERUNGSSCHREIBEN',
            'urteil': 'URTEIL',
            'beschluss': 'BESCHLUSS',
            'klage': 'KLAGESCHRIFT',
            'erwiderung': 'KLAGEERWIDERUNG',
            'fahrzeugschein': 'FAHRZEUGSCHEIN',
            'brief': 'KORRESPONDENZ',
            'anlage': 'ANLAGE',
            'nachweis': 'NACHWEIS'
        }

        for keyword, typ in typ_mapping.items():
            if keyword in titel_lower:
                return typ

        return 'SONSTIGES'

    def _finde_inhaltsverzeichnis_seite(self, seiten_texte: List[Dict]) -> Optional[int]:
        """Findet die Seite mit dem Inhaltsverzeichnis"""
        inhaltsverzeichnis_keywords = [
            r'inhaltsverzeichnis',
            r'inhalt\s*:',
            r'gliederung',
            r'übersicht',
            r'dokumentenverzeichnis',
            r'akteninhalt',
        ]

        for seiten_info in seiten_texte[:5]:  # Nur erste 5 Seiten prüfen
            text_lower = seiten_info['text'].lower()
            for keyword in inhaltsverzeichnis_keywords:
                if re.search(keyword, text_lower):
                    return seiten_info['seite']
        return None

    def _extrahiere_inhaltsverzeichnis_aus_text(
        self,
        text: str,
        seiten_texte: List[Dict],
        anzahl_seiten: int
    ) -> List[Dict]:
        """Extrahiert ein Inhaltsverzeichnis aus dem Text (sucht nach TOC-Struktur)"""

        # Zuerst Inhaltsverzeichnis-Seite finden
        toc_seite = self._finde_inhaltsverzeichnis_seite(seiten_texte)

        toc_text = ""
        if toc_seite:
            # Nur Text der Inhaltsverzeichnis-Seite(n) verwenden
            for seiten_info in seiten_texte:
                if seiten_info['seite'] >= toc_seite and seiten_info['seite'] <= toc_seite + 1:
                    toc_text += seiten_info['text'] + "\n"
        else:
            # Fallback: Ersten Teil des Dokuments durchsuchen
            for seiten_info in seiten_texte[:5]:
                toc_text += seiten_info['text'] + "\n"

        gefundene_eintraege = []

        # Zeilen einzeln verarbeiten für bessere Mustererkennung
        zeilen = toc_text.split('\n')

        for zeile in zeilen:
            zeile = zeile.strip()
            if not zeile or len(zeile) < 3:
                continue

            # Pattern 1: "1. Gutachten ..... 5" oder "1) Gutachten ... 5"
            match = re.match(r'^(\d+)[\.\)]\s*(.+?)[\.…\s]+(\d+)\s*$', zeile)
            if match:
                position = int(match.group(1))
                titel = match.group(2).strip().rstrip('.')
                seite = int(match.group(3))
                if 1 <= seite <= anzahl_seiten and len(titel) >= 2:
                    gefundene_eintraege.append({
                        'position': position,
                        'titel': titel,
                        'seite_von': seite
                    })
                continue

            # Pattern 2: "Gutachten .............. 5" (ohne Nummerierung)
            match = re.match(r'^([A-Za-zäöüÄÖÜß][^\.…\d]+?)\s*[\.…\s]{3,}(\d+)\s*$', zeile)
            if match:
                titel = match.group(1).strip()
                seite = int(match.group(2))
                if 1 <= seite <= anzahl_seiten and len(titel) >= 2:
                    gefundene_eintraege.append({
                        'position': len(gefundene_eintraege),
                        'titel': titel,
                        'seite_von': seite
                    })
                continue

            # Pattern 3: "Anlage 1: Gutachten Seite 5" oder "Anlage 1 Gutachten 5"
            match = re.match(r'^(?:Anlage\s*)?(\d+)[:\.\)]\s*(.+?)\s+(?:Seite\s*)?(\d+)(?:\s*[-–]\s*(\d+))?\s*$', zeile, re.IGNORECASE)
            if match:
                position = int(match.group(1))
                titel = match.group(2).strip()
                seite_von = int(match.group(3))
                seite_bis = int(match.group(4)) if match.group(4) else None
                if 1 <= seite_von <= anzahl_seiten and len(titel) >= 2:
                    eintrag = {
                        'position': position,
                        'titel': titel,
                        'seite_von': seite_von
                    }
                    if seite_bis and seite_bis <= anzahl_seiten:
                        eintrag['seite_bis_explizit'] = seite_bis
                    gefundene_eintraege.append(eintrag)
                continue

            # Pattern 4: "- Gutachten (Seite 5)" oder "• Gutachten (5-10)"
            match = re.match(r'^[-•→]\s*(.+?)\s*\((?:Seite\s*)?(\d+)(?:\s*[-–]\s*(\d+))?\)\s*$', zeile)
            if match:
                titel = match.group(1).strip()
                seite_von = int(match.group(2))
                seite_bis = int(match.group(3)) if match.group(3) else None
                if 1 <= seite_von <= anzahl_seiten and len(titel) >= 2:
                    eintrag = {
                        'position': len(gefundene_eintraege),
                        'titel': titel,
                        'seite_von': seite_von
                    }
                    if seite_bis and seite_bis <= anzahl_seiten:
                        eintrag['seite_bis_explizit'] = seite_bis
                    gefundene_eintraege.append(eintrag)
                continue

            # Pattern 5: "Seite 5-10: Gutachten" oder "S. 5: Gutachten"
            match = re.match(r'^(?:Seite|S\.)\s*(\d+)(?:\s*[-–]\s*(\d+))?[:\s]+(.+?)\s*$', zeile, re.IGNORECASE)
            if match:
                seite_von = int(match.group(1))
                seite_bis = int(match.group(2)) if match.group(2) else None
                titel = match.group(3).strip()
                if 1 <= seite_von <= anzahl_seiten and len(titel) >= 2:
                    eintrag = {
                        'position': len(gefundene_eintraege),
                        'titel': titel,
                        'seite_von': seite_von
                    }
                    if seite_bis and seite_bis <= anzahl_seiten:
                        eintrag['seite_bis_explizit'] = seite_bis
                    gefundene_eintraege.append(eintrag)
                continue

            # Pattern 6: "Blatt 5-10 Gutachten" (typisch für Gerichtsakten)
            match = re.match(r'^(?:Blatt|Bl\.?)\s*(\d+)(?:\s*[-–]\s*(\d+))?[:\s]+(.+?)\s*$', zeile, re.IGNORECASE)
            if match:
                seite_von = int(match.group(1))
                seite_bis = int(match.group(2)) if match.group(2) else None
                titel = match.group(3).strip()
                if 1 <= seite_von <= anzahl_seiten and len(titel) >= 2:
                    eintrag = {
                        'position': len(gefundene_eintraege),
                        'titel': titel,
                        'seite_von': seite_von
                    }
                    if seite_bis and seite_bis <= anzahl_seiten:
                        eintrag['seite_bis_explizit'] = seite_bis
                    gefundene_eintraege.append(eintrag)

        # Wenn keine strukturierten Einträge gefunden, erweiterte Suche
        if not gefundene_eintraege:
            gefundene_eintraege = self._erweiterte_toc_suche(toc_text, anzahl_seiten)

        # Nach Seitenzahl sortieren
        gefundene_eintraege = sorted(gefundene_eintraege, key=lambda x: x['seite_von'])

        # Duplikate entfernen (gleiche Startseite)
        unique_eintraege = []
        seen_seiten = set()
        for eintrag in gefundene_eintraege:
            if eintrag['seite_von'] not in seen_seiten:
                unique_eintraege.append(eintrag)
                seen_seiten.add(eintrag['seite_von'])

        # In Inhaltsverzeichnis mit korrekten Seitenbereichen konvertieren
        inhaltsverzeichnis = []
        for i, eintrag in enumerate(unique_eintraege):
            typ = self._erkenne_dokumenttyp_aus_titel(eintrag['titel'])

            iv_eintrag = {
                'position': i,
                'titel': eintrag['titel'],
                'typ': typ,
                'seite_von': eintrag['seite_von'],
                'seite_bis': anzahl_seiten  # Default: bis zum Ende
            }

            # Wenn explizite Seite-bis angegeben, diese verwenden
            if 'seite_bis_explizit' in eintrag:
                iv_eintrag['seite_bis'] = eintrag['seite_bis_explizit']
            # Sonst: Seite bis = nächste Seite - 1
            elif i + 1 < len(unique_eintraege):
                iv_eintrag['seite_bis'] = unique_eintraege[i + 1]['seite_von'] - 1

            # Sicherstellen dass seite_bis >= seite_von
            if iv_eintrag['seite_bis'] < iv_eintrag['seite_von']:
                iv_eintrag['seite_bis'] = iv_eintrag['seite_von']

            inhaltsverzeichnis.append(iv_eintrag)

        return inhaltsverzeichnis

    def _erweiterte_toc_suche(self, text: str, anzahl_seiten: int) -> List[Dict]:
        """Erweiterte Suche nach Inhaltsverzeichnis-Einträgen"""
        eintraege = []

        # Suche nach Mustern im gesamten Text
        patterns = [
            # "1. Titel 5" oder "1) Titel 5"
            (r'(\d+)[\.\)]\s*([A-Za-zäöüÄÖÜß][^\d\n]{2,50}?)\s+(\d+)(?:\s|$)', True),
            # "Titel ... 5"
            (r'([A-Za-zäöüÄÖÜß][^\n\.…]{2,40}?)[\.…]{2,}\s*(\d+)', False),
        ]

        for pattern, hat_position in patterns:
            for match in re.finditer(pattern, text, re.MULTILINE):
                try:
                    if hat_position:
                        position = int(match.group(1))
                        titel = match.group(2).strip()
                        seite = int(match.group(3))
                    else:
                        position = len(eintraege)
                        titel = match.group(1).strip()
                        seite = int(match.group(2))

                    # Validierung
                    if 1 <= seite <= anzahl_seiten and 2 <= len(titel) <= 100:
                        # Keine reinen Zahlen oder kurze Wörter
                        if not titel.isdigit() and not re.match(r'^\d', titel):
                            eintraege.append({
                                'position': position,
                                'titel': titel,
                                'seite_von': seite
                            })
                except:
                    pass

        return eintraege

    def _analysiere_seiten_fuer_dokumente(
        self,
        seiten_texte: List[Dict],
        anzahl_seiten: int
    ) -> List[Dict]:
        """Analysiert jede Seite um Dokumentgrenzen zu erkennen"""
        if not seiten_texte or anzahl_seiten == 0:
            return []

        # Wenn nur eine Seite, ein Dokument
        if anzahl_seiten == 1:
            return [{
                'position': 0,
                'titel': 'Dokument 1',
                'typ': 'SONSTIGES',
                'seite_von': 1,
                'seite_bis': 1
            }]

        inhaltsverzeichnis = []
        aktuelles_dokument = None

        # Schlüsselwörter die einen neuen Dokumentanfang signalisieren
        dokument_start_keywords = [
            r'^gutachten',
            r'^rechnung',
            r'^kostenvoranschlag',
            r'^vollmacht',
            r'^kfz.gutachten',
            r'^schadensgutachten',
            r'^kürzungsschreiben',
            r'^anspruchsschreiben',
            r'sehr geehrte',
            r'^betreff:',
            r'^unser zeichen',
            r'^ihr zeichen',
            r'^anlage\s*\d',
        ]

        for seiten_info in seiten_texte:
            seite = seiten_info['seite']
            text = seiten_info['text'].lower()[:500]  # Nur Anfang prüfen

            # Prüfen ob neue Dokumentseite
            ist_neues_dokument = False
            erkannter_titel = None

            for pattern in dokument_start_keywords:
                if re.search(pattern, text, re.IGNORECASE | re.MULTILINE):
                    ist_neues_dokument = True
                    # Titel aus erstem Match extrahieren
                    match = re.search(pattern + r'[^\n]*', text, re.IGNORECASE)
                    if match:
                        erkannter_titel = match.group(0).strip()[:50]
                    break

            if ist_neues_dokument or seite == 1:
                # Vorheriges Dokument abschließen
                if aktuelles_dokument:
                    aktuelles_dokument['seite_bis'] = seite - 1
                    inhaltsverzeichnis.append(aktuelles_dokument)

                # Neues Dokument starten
                typ = self._erkenne_dokumenttyp_aus_titel(erkannter_titel or "")
                aktuelles_dokument = {
                    'position': len(inhaltsverzeichnis),
                    'titel': erkannter_titel or f'Dokument {len(inhaltsverzeichnis) + 1}',
                    'typ': typ,
                    'seite_von': seite,
                    'seite_bis': anzahl_seiten
                }

        # Letztes Dokument hinzufügen
        if aktuelles_dokument:
            aktuelles_dokument['seite_bis'] = anzahl_seiten
            inhaltsverzeichnis.append(aktuelles_dokument)

        # Fallback: Wenn keine Dokumente erkannt, gesamtes PDF als ein Dokument
        if not inhaltsverzeichnis:
            inhaltsverzeichnis = [{
                'position': 0,
                'titel': 'Gesamtdokument',
                'typ': 'AKTE',
                'seite_von': 1,
                'seite_bis': anzahl_seiten
            }]

        return inhaltsverzeichnis

    def _extrahiere_dokumente(
        self,
        akten_import: AktenImport,
        pdf_inhalt: bytes,
        pdf_analyse: Dict
    ) -> List[AktenDokument]:
        """Extrahiert einzelne Dokumente aus dem PDF"""
        dokumente = []
        inhaltsverzeichnis = pdf_analyse.get('inhaltsverzeichnis', [])

        if not inhaltsverzeichnis:
            # Fallback: Gesamtes PDF als ein Dokument
            inhaltsverzeichnis = [{
                'position': 0,
                'titel': 'Gesamtakte',
                'typ': 'AKTE',
                'seite_von': 1,
                'seite_bis': pdf_analyse.get('anzahl_seiten', 1)
            }]

        gesamt_seiten = pdf_analyse.get('anzahl_seiten', 1)

        for i, eintrag in enumerate(inhaltsverzeichnis):
            # Fortschritts-Prozent berechnen
            seiten_anteil = (eintrag.get('seite_bis', 1) - eintrag.get('seite_von', 1) + 1) / gesamt_seiten
            fortschritt = round(seiten_anteil * 100, 1)

            akten_dokument = AktenDokument(
                akten_import_id=akten_import.id,
                projekt_id=akten_import.projekt_id,
                position_im_inhaltsverzeichnis=eintrag.get('position', i),
                titel=eintrag.get('titel', f'Dokument {i + 1}'),
                dokumenttyp=eintrag.get('typ', 'SONSTIGES'),
                seite_von=eintrag.get('seite_von', 1),
                seite_bis=eintrag.get('seite_bis', 1),
                ist_meilenstein=eintrag.get('typ') in ['GUTACHTEN', 'URTEIL', 'KLAGESCHRIFT'],
                fortschritt_prozent=fortschritt
            )

            self.db.add(akten_dokument)
            dokumente.append(akten_dokument)

            # Einzelnes PDF erstellen und als Dokument speichern
            try:
                einzel_pdf = self._extrahiere_seiten(
                    pdf_inhalt,
                    eintrag.get('seite_von', 1),
                    eintrag.get('seite_bis', 1)
                )

                if einzel_pdf:
                    from src.models import Dokument, DokumentTyp
                    from src.services.dokumente import DokumentenService

                    # Dokument erstellen
                    dok = Dokument(
                        projekt_id=akten_import.projekt_id,
                        original_dateiname=f"{eintrag.get('titel', 'Dokument')}_{i + 1}.pdf",
                        mime_type="application/pdf",
                        dateipfad=f"imports/{akten_import.id}/{i + 1}.pdf",
                        dateigroesse=len(einzel_pdf),
                        dokument_typ=DokumentTyp.SONSTIG,
                        hochgeladen_von_user_id=akten_import.importiert_von_user_id,
                        beschreibung=f"Importiert aus: {akten_import.original_dateiname}"
                    )
                    self.db.add(dok)
                    self.db.flush()

                    akten_dokument.dokument_id = dok.id

            except Exception as e:
                # Fehler beim Extrahieren einzelner Seiten ignorieren
                pass

        self.db.flush()
        return dokumente

    def _extrahiere_seiten(self, pdf_inhalt: bytes, von: int, bis: int) -> Optional[bytes]:
        """Extrahiert Seiten aus einem PDF"""
        try:
            import io
            import PyPDF2

            pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_inhalt))
            pdf_writer = PyPDF2.PdfWriter()

            # Seiten hinzufügen (0-basiert)
            for seite in range(von - 1, min(bis, len(pdf_reader.pages))):
                pdf_writer.add_page(pdf_reader.pages[seite])

            output = io.BytesIO()
            pdf_writer.write(output)
            return output.getvalue()

        except ImportError:
            return None
        except Exception:
            return None

    def _finde_aktenvorblatt(self, seiten_texte: List[Dict]) -> str:
        """Findet und extrahiert das Aktenvorblatt (typischerweise Seite 1-2)"""
        aktenvorblatt_keywords = [
            r'aktenvorblatt',
            r'aktendeckblatt',
            r'deckblatt',
            r'stammdaten',
            r'fallübersicht',
            r'aktenzeichen',
            r'geschädigter',
            r'unfallgegner',
            r'mandant',
        ]

        aktenvorblatt_text = ""

        # Prüfe erste 3 Seiten
        for seiten_info in seiten_texte[:3]:
            text_lower = seiten_info['text'].lower()

            # Zähle wie viele Keywords auf der Seite vorkommen
            keyword_count = sum(1 for kw in aktenvorblatt_keywords if re.search(kw, text_lower))

            # Wenn mindestens 2 Keywords gefunden, ist es wahrscheinlich das Aktenvorblatt
            if keyword_count >= 2:
                aktenvorblatt_text += seiten_info['text'] + "\n"

        # Fallback: Wenn kein eindeutiges Aktenvorblatt, verwende Seite 1
        if not aktenvorblatt_text and seiten_texte:
            aktenvorblatt_text = seiten_texte[0]['text']

        return aktenvorblatt_text

    def _extrahiere_beteiligte(
        self,
        akten_import: AktenImport,
        text_inhalt: str,
        seiten_texte: List[Dict] = None
    ) -> List[AktenBeteiligter]:
        """Extrahiert Beteiligte aus dem Aktenvorblatt"""
        beteiligte = []

        # Aktenvorblatt-Text ermitteln
        if seiten_texte:
            aktenvorblatt_text = self._finde_aktenvorblatt(seiten_texte)
        else:
            # Fallback: Ersten Teil des Textes verwenden
            aktenvorblatt_text = text_inhalt[:3000] if text_inhalt else ""

        gefundene_namen = set()  # Um Duplikate zu vermeiden

        for rolle, patterns in self.BETEILIGTER_PATTERNS.items():
            for pattern in patterns:
                matches = re.finditer(pattern, aktenvorblatt_text, re.IGNORECASE | re.MULTILINE)
                for match in matches:
                    name = match.group(1).strip()

                    # Bereinigung
                    name = self._bereinige_name(name)

                    # Validierung
                    if not name or len(name) < 2 or name.lower() in gefundene_namen:
                        continue

                    # Prüfen ob es ein gültiger Name ist (keine Seitenzahlen, etc.)
                    if re.match(r'^[\d\s\-\.]+$', name):
                        continue

                    gefundene_namen.add(name.lower())

                    # Namen und Adresse aufteilen
                    name_info = self._parse_name_adresse(name)

                    beteiligter = AktenBeteiligter(
                        akten_import_id=akten_import.id,
                        projekt_id=akten_import.projekt_id,
                        rolle=rolle,
                        vorname=name_info.get('vorname', ''),
                        name=name_info.get('nachname', name),
                        adresse=name_info.get('adresse'),
                        extrahiert_aus_pdf=True
                    )

                    self.db.add(beteiligter)
                    beteiligte.append(beteiligter)
                    break  # Nur ersten Treffer pro Pattern

        # Zusätzlich: Tabellenbasierte Extraktion versuchen
        tabellen_beteiligte = self._extrahiere_beteiligte_aus_tabelle(aktenvorblatt_text, akten_import, gefundene_namen)
        beteiligte.extend(tabellen_beteiligte)

        self.db.flush()
        return beteiligte

    def _bereinige_name(self, name: str) -> str:
        """Bereinigt einen extrahierten Namen"""
        # Entferne führende/nachfolgende Leerzeichen und Sonderzeichen
        name = name.strip(' \t\n\r:;,')

        # Entferne häufige Störungen
        name = re.sub(r'\s+', ' ', name)  # Mehrfache Leerzeichen
        name = re.sub(r'^(Herr|Frau|Hr\.|Fr\.)\s+', '', name, flags=re.IGNORECASE)

        # Kürze bei zu langen Einträgen (wahrscheinlich falsch erfasst)
        if len(name) > 100:
            # Versuche beim ersten Zeilenumbruch oder Komma abzuschneiden
            for sep in ['\n', ',', ';']:
                if sep in name:
                    name = name.split(sep)[0].strip()
                    break

        return name[:100]  # Maximale Länge

    def _parse_name_adresse(self, text: str) -> Dict[str, str]:
        """Parst einen Text und trennt Name und Adresse"""
        result = {'vorname': '', 'nachname': '', 'adresse': None}

        # Versuche Adresse zu erkennen (PLZ-Muster)
        adress_match = re.search(r'(\d{5}\s+[A-Za-zäöüÄÖÜß\s]+)', text)
        if adress_match:
            result['adresse'] = adress_match.group(1).strip()
            text = text[:adress_match.start()].strip()

        # Versuche Straße zu erkennen
        strasse_match = re.search(r'([A-Za-zäöüÄÖÜß]+(?:straße|str\.|weg|platz|allee|ring)\s*\d*[a-zA-Z]?)', text, re.IGNORECASE)
        if strasse_match:
            strasse = strasse_match.group(1).strip()
            if result['adresse']:
                result['adresse'] = strasse + ', ' + result['adresse']
            else:
                result['adresse'] = strasse
            text = text[:strasse_match.start()].strip()

        # Namen aufteilen
        name_teile = text.strip().split()
        if len(name_teile) >= 2:
            result['vorname'] = name_teile[0]
            result['nachname'] = ' '.join(name_teile[1:])
        elif len(name_teile) == 1:
            result['nachname'] = name_teile[0]

        return result

    def _extrahiere_beteiligte_aus_tabelle(
        self,
        text: str,
        akten_import: AktenImport,
        bereits_gefunden: set
    ) -> List[AktenBeteiligter]:
        """Versucht Beteiligte aus tabellenartigen Strukturen zu extrahieren"""
        beteiligte = []

        # Typische Tabellen-Muster in Aktenvorblättern:
        # "Geschädigter:     Max Mustermann"
        # "Geschädigter      Max Mustermann"
        # "| Geschädigter | Max Mustermann |"

        tabellen_patterns = [
            # Format: "Rolle:    Name" oder "Rolle     Name"
            (r'(Geschädigter|Mandant|Auftraggeber)[\s:]+([A-Za-zäöüÄÖÜß][A-Za-zäöüÄÖÜß\s\-\.]+?)(?:\n|,|\d{5}|$)', BeteiligtenRolle.GESCHAEDIGTER),
            (r'(Unfallgegner|Schädiger|Verursacher)[\s:]+([A-Za-zäöüÄÖÜß][A-Za-zäöüÄÖÜß\s\-\.]+?)(?:\n|,|\d{5}|$)', BeteiligtenRolle.UNFALLVERURSACHER),
            (r'(Haftpflichtvers(?:icherung)?|Gegn\.?\s*Vers(?:icherung)?)[\s:]+([A-Za-zäöüÄÖÜß][A-Za-zäöüÄÖÜß\s\-\.]+?)(?:\n|,|\d{5}|$)', BeteiligtenRolle.VERSICHERUNG_VERURSACHER),
            (r'(Gutachter|Sachverständiger)[\s:]+([A-Za-zäöüÄÖÜß][A-Za-zäöüÄÖÜß\s\-\.]+?)(?:\n|,|\d{5}|$)', BeteiligtenRolle.GUTACHTER),
            (r'(Werkstatt|Autohaus|Reparaturbetrieb)[\s:]+([A-Za-zäöüÄÖÜß][A-Za-zäöüÄÖÜß\s\-\.]+?)(?:\n|,|\d{5}|$)', BeteiligtenRolle.WERKSTATT),
        ]

        for pattern, rolle in tabellen_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                name = match.group(2).strip()
                name = self._bereinige_name(name)

                if name and len(name) >= 2 and name.lower() not in bereits_gefunden:
                    bereits_gefunden.add(name.lower())

                    name_info = self._parse_name_adresse(name)

                    beteiligter = AktenBeteiligter(
                        akten_import_id=akten_import.id,
                        projekt_id=akten_import.projekt_id,
                        rolle=rolle,
                        vorname=name_info.get('vorname', ''),
                        name=name_info.get('nachname', name),
                        adresse=name_info.get('adresse'),
                        extrahiert_aus_pdf=True
                    )

                    self.db.add(beteiligter)
                    beteiligte.append(beteiligter)

        return beteiligte

    def erstelle_einladung(
        self,
        beteiligter_id: int,
        email: str,
        erstellt_von_user_id: int,
        gueltig_tage: int = 7
    ) -> Einladung:
        """Erstellt eine Einladung für einen Beteiligten"""
        beteiligter = self.db.query(AktenBeteiligter).get(beteiligter_id)

        if not beteiligter:
            raise ValueError("Beteiligter nicht gefunden")

        # Einmalpasswort generieren (8 Zeichen)
        einmalpasswort = secrets.token_urlsafe(6)[:8].upper()

        # Einladungscode generieren
        einladungscode = secrets.token_urlsafe(32)

        einladung = Einladung(
            projekt_id=beteiligter.projekt_id,
            beteiligter_id=beteiligter_id,
            email=email,
            einladungscode=einladungscode,
            einmalpasswort=hashlib.sha256(einmalpasswort.encode()).hexdigest(),
            einmalpasswort_klartext=einmalpasswort,
            status=EinladungsStatus.AUSSTEHEND,
            gueltig_bis=datetime.now() + timedelta(days=gueltig_tage),
            erstellt_von_user_id=erstellt_von_user_id
        )

        # E-Mail des Beteiligten aktualisieren
        beteiligter.email = email

        self.db.add(einladung)
        self.db.flush()

        return einladung

    def versende_einladung(self, einladung_id: int) -> bool:
        """Markiert Einladung als versendet (E-Mail-Versand extern)"""
        einladung = self.db.query(Einladung).get(einladung_id)

        if not einladung:
            return False

        einladung.status = EinladungsStatus.VERSENDET
        einladung.versendet_am = datetime.now()
        # Klartext-Passwort nach Versand löschen
        # einladung.einmalpasswort_klartext = None

        self.db.flush()
        return True

    def einladung_annehmen(
        self,
        einladungscode: str,
        einmalpasswort: str,
        neues_passwort: str
    ) -> Optional[int]:
        """Nimmt eine Einladung an und erstellt User"""
        einladung = self.db.query(Einladung).filter(
            Einladung.einladungscode == einladungscode
        ).first()

        if not einladung:
            return None

        # Prüfen ob gültig
        if einladung.status != EinladungsStatus.VERSENDET:
            return None

        if einladung.gueltig_bis < datetime.now():
            einladung.status = EinladungsStatus.ABGELAUFEN
            self.db.flush()
            return None

        # Passwort prüfen
        pw_hash = hashlib.sha256(einmalpasswort.encode()).hexdigest()
        if pw_hash != einladung.einmalpasswort:
            return None

        # User erstellen
        from src.models import User, Rollen

        beteiligter = einladung.beteiligter

        # Rolle basierend auf Beteiligtenrolle
        user_rolle = {
            BeteiligtenRolle.GESCHAEDIGTER: Rollen.UNFALLOPFER,
            BeteiligtenRolle.VERSICHERUNG_GESCHAEDIGTER: Rollen.VERSICHERUNG_EIGEN,
            BeteiligtenRolle.VERSICHERUNG_VERURSACHER: Rollen.VERSICHERUNG_GEGNER,
            BeteiligtenRolle.GUTACHTER: Rollen.GUTACHTER,
            BeteiligtenRolle.WERKSTATT: Rollen.WERKSTATT,
        }.get(beteiligter.rolle, Rollen.UNFALLOPFER)

        user = User(
            email=einladung.email,
            name=f"{beteiligter.vorname} {beteiligter.name}".strip(),
            rolle=user_rolle,
            ist_aktiv=True,
            muss_passwort_aendern=False
        )
        user.passwort_setzen(neues_passwort)

        self.db.add(user)
        self.db.flush()

        # Beteiligter mit User verknüpfen
        beteiligter.user_id = user.id

        # Einladung als angenommen markieren
        einladung.status = EinladungsStatus.ANGENOMMEN
        einladung.angenommen_am = datetime.now()
        einladung.einmalpasswort_klartext = None

        self.db.flush()

        return user.id

    def dokument_freigeben(
        self,
        akten_dokument_id: int,
        beteiligter_ids: List[int],
        freigegeben_von_user_id: int
    ) -> List[DokumentFreigabe]:
        """Gibt ein Dokument für mehrere Beteiligte frei"""
        freigaben = []

        for beteiligter_id in beteiligter_ids:
            # Prüfen ob bereits freigegeben
            existiert = self.db.query(DokumentFreigabe).filter(
                DokumentFreigabe.akten_dokument_id == akten_dokument_id,
                DokumentFreigabe.beteiligter_id == beteiligter_id
            ).first()

            if not existiert:
                freigabe = DokumentFreigabe(
                    akten_dokument_id=akten_dokument_id,
                    beteiligter_id=beteiligter_id,
                    freigegeben_von_user_id=freigegeben_von_user_id
                )
                self.db.add(freigabe)
                freigaben.append(freigabe)

        self.db.flush()
        return freigaben

    def hole_freigegebene_dokumente(self, user_id: int) -> List[Dict]:
        """Holt alle für einen User freigegebenen Dokumente"""
        # Beteiligten für User finden
        beteiligter = self.db.query(AktenBeteiligter).filter(
            AktenBeteiligter.user_id == user_id
        ).first()

        if not beteiligter:
            return []

        # Freigaben holen
        freigaben = self.db.query(DokumentFreigabe).filter(
            DokumentFreigabe.beteiligter_id == beteiligter.id
        ).all()

        result = []
        for freigabe in freigaben:
            dok = freigabe.akten_dokument
            result.append({
                'freigabe_id': freigabe.id,
                'dokument_id': dok.dokument_id,
                'titel': dok.titel,
                'dokumenttyp': dok.dokumenttyp,
                'freigegeben_am': freigabe.freigegeben_am,
                'gelesen': freigabe.gelesen_am is not None
            })

        return result

    def markiere_als_gelesen(self, freigabe_id: int):
        """Markiert eine Freigabe als gelesen"""
        freigabe = self.db.query(DokumentFreigabe).get(freigabe_id)
        if freigabe and not freigabe.gelesen_am:
            freigabe.gelesen_am = datetime.now()
            self.db.flush()

    def berechne_aktenfortschritt(self, projekt_id: int) -> Dict[str, Any]:
        """Berechnet den Fortschritt einer Akte"""
        dokumente = self.db.query(AktenDokument).filter(
            AktenDokument.projekt_id == projekt_id
        ).all()

        if not dokumente:
            return {'fortschritt': 0, 'meilensteine': []}

        gesamt_fortschritt = 0
        meilensteine = []

        for dok in dokumente:
            # Prüfen ob Dokument bearbeitet wurde
            if dok.dokument_id:
                from src.models import Dokument
                original_dok = self.db.query(Dokument).get(dok.dokument_id)
                if original_dok and original_dok.freigabe_erteilt:
                    gesamt_fortschritt += dok.fortschritt_prozent

            if dok.ist_meilenstein:
                meilensteine.append({
                    'titel': dok.titel,
                    'position': dok.position_im_inhaltsverzeichnis,
                    'abgeschlossen': dok.dokument_id is not None
                })

        return {
            'fortschritt': min(100, gesamt_fortschritt),
            'meilensteine': meilensteine,
            'anzahl_dokumente': len(dokumente)
        }

    def erstelle_masseneinladung(
        self,
        beteiligter_ids: List[int],
        erstellt_von_user_id: int
    ) -> List[Einladung]:
        """Erstellt Einladungen für mehrere Beteiligte"""
        einladungen = []

        for beteiligter_id in beteiligter_ids:
            beteiligter = self.db.query(AktenBeteiligter).get(beteiligter_id)

            if beteiligter and beteiligter.email and not beteiligter.user_id:
                try:
                    einladung = self.erstelle_einladung(
                        beteiligter_id=beteiligter_id,
                        email=beteiligter.email,
                        erstellt_von_user_id=erstellt_von_user_id
                    )
                    einladungen.append(einladung)
                except:
                    pass

        return einladungen
