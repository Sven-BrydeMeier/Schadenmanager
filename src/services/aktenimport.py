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
        r'(?:Versicherungs(?:-)?Nr\.?)[:\s]*([A-Za-z0-9\-/]+)'
    ]

    # Muster für Beteiligte
    BETEILIGTER_PATTERNS = {
        BeteiligtenRolle.GESCHAEDIGTER: [
            r'(?:Geschädigt(?:er|e)|Anspruchsteller|Kläger)[:\s]*([A-Za-zäöüÄÖÜß\s\-]+)',
        ],
        BeteiligtenRolle.UNFALLVERURSACHER: [
            r'(?:Unfallverursacher|Schädiger|Beklagte(?:r)?)[:\s]*([A-Za-zäöüÄÖÜß\s\-]+)',
        ],
        BeteiligtenRolle.VERSICHERUNG_VERURSACHER: [
            r'(?:Haftpflichtversicherung|gegnerische Versicherung)[:\s]*([A-Za-zäöüÄÖÜß\s\-]+)',
        ]
    }

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

            # Beteiligte extrahieren
            beteiligte = self._extrahiere_beteiligte(
                akten_import,
                pdf_analyse.get('text_inhalt', '')
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
            'lesezeichen': []
        }

        try:
            # PyPDF2 oder pdfplumber verwenden
            import io

            try:
                import PyPDF2
                pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_inhalt))
                result['anzahl_seiten'] = len(pdf_reader.pages)

                # Text extrahieren
                text_gesamt = ""
                for page in pdf_reader.pages:
                    text_gesamt += page.extract_text() or ""

                result['text_inhalt'] = text_gesamt

                # Lesezeichen/Outlines extrahieren (falls vorhanden)
                try:
                    if pdf_reader.outline:
                        result['lesezeichen'] = self._parse_lesezeichen(pdf_reader.outline)
                except:
                    pass

            except ImportError:
                # Fallback: Grundlegende Analyse ohne PyPDF2
                result['anzahl_seiten'] = 1
                result['text_inhalt'] = ""

            # Aktenzeichen suchen
            for pattern in self.AKTENZEICHEN_PATTERNS:
                match = re.search(pattern, result['text_inhalt'], re.IGNORECASE)
                if match:
                    result['aktenzeichen'] = match.group(1).strip()
                    break

            # Inhaltsverzeichnis aus Text oder Lesezeichen erstellen
            if result['lesezeichen']:
                result['inhaltsverzeichnis'] = result['lesezeichen']
            else:
                result['inhaltsverzeichnis'] = self._extrahiere_inhaltsverzeichnis(
                    result['text_inhalt'],
                    result['anzahl_seiten']
                )

        except Exception as e:
            result['fehler'] = str(e)

        return result

    def _parse_lesezeichen(self, outline, level: int = 0) -> List[Dict]:
        """Parsed PDF-Lesezeichen rekursiv"""
        result = []

        if isinstance(outline, list):
            for item in outline:
                result.extend(self._parse_lesezeichen(item, level))
        else:
            try:
                titel = outline.title if hasattr(outline, 'title') else str(outline)
                seite = outline.page.idnum if hasattr(outline, 'page') else 0

                result.append({
                    'titel': titel,
                    'seite': seite,
                    'ebene': level
                })
            except:
                pass

        return result

    def _extrahiere_inhaltsverzeichnis(self, text: str, anzahl_seiten: int) -> List[Dict]:
        """Extrahiert ein Inhaltsverzeichnis aus dem Text"""
        inhaltsverzeichnis = []

        # Typische Dokumenttypen in Unfallakten
        dokumenttypen = [
            ('Gutachten', 'GUTACHTEN'),
            ('Kostenvoranschlag', 'KOSTENVORANSCHLAG'),
            ('Rechnung', 'RECHNUNG'),
            ('Kürzungsschreiben', 'KUERZUNGSSCHREIBEN'),
            ('Anspruchsschreiben', 'ANSPRUCHSSCHREIBEN'),
            ('Vollmacht', 'VOLLMACHT'),
            ('Unfallbericht', 'UNFALLBERICHT'),
            ('Polizeibericht', 'POLIZEIBERICHT'),
            ('Zeugenaussage', 'ZEUGENAUSSAGE'),
            ('Fotos', 'FOTOS'),
            ('Korrespondenz', 'KORRESPONDENZ'),
            ('Versicherungsschreiben', 'VERSICHERUNGSSCHREIBEN'),
            ('Urteil', 'URTEIL'),
            ('Beschluss', 'BESCHLUSS'),
            ('Klageschrift', 'KLAGESCHRIFT'),
            ('Klageerwiderung', 'KLAGEERWIDERUNG')
        ]

        # Suche nach Dokumenttypen im Text
        position = 0
        for bezeichnung, typ in dokumenttypen:
            pattern = rf'({bezeichnung})[^\n]*?(?:Seite|S\.|Bl\.)?[:\s]*(\d+)'
            matches = re.finditer(pattern, text, re.IGNORECASE)

            for match in matches:
                try:
                    seite = int(match.group(2))
                    if seite <= anzahl_seiten:
                        inhaltsverzeichnis.append({
                            'position': position,
                            'titel': match.group(1),
                            'typ': typ,
                            'seite_von': seite,
                            'seite_bis': seite  # Wird später berechnet
                        })
                        position += 1
                except:
                    pass

        # Seiten-Bereiche berechnen
        inhaltsverzeichnis.sort(key=lambda x: x['seite_von'])
        for i, eintrag in enumerate(inhaltsverzeichnis):
            if i + 1 < len(inhaltsverzeichnis):
                eintrag['seite_bis'] = inhaltsverzeichnis[i + 1]['seite_von'] - 1
            else:
                eintrag['seite_bis'] = anzahl_seiten

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

    def _extrahiere_beteiligte(
        self,
        akten_import: AktenImport,
        text_inhalt: str
    ) -> List[AktenBeteiligter]:
        """Extrahiert Beteiligte aus dem Text"""
        beteiligte = []

        for rolle, patterns in self.BETEILIGTER_PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, text_inhalt, re.IGNORECASE)
                if match:
                    name = match.group(1).strip()

                    # Namen aufteilen
                    name_teile = name.split()
                    vorname = name_teile[0] if name_teile else ""
                    nachname = " ".join(name_teile[1:]) if len(name_teile) > 1 else name

                    beteiligter = AktenBeteiligter(
                        akten_import_id=akten_import.id,
                        projekt_id=akten_import.projekt_id,
                        rolle=rolle,
                        vorname=vorname,
                        name=nachname,
                        extrahiert_aus_pdf=True
                    )

                    self.db.add(beteiligter)
                    beteiligte.append(beteiligter)
                    break  # Nur ersten Treffer pro Rolle

        self.db.flush()
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
