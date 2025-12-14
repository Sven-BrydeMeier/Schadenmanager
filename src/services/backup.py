"""
Backup/Export Service
Vollständiges Backup und Export aller Projektdaten
"""
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from enum import Enum
import json
import zipfile
import io
import base64
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from src.models.base import Base


class BackupTyp(str, Enum):
    """Typ des Backups"""
    VOLLSTAENDIG = "VOLLSTAENDIG"
    PROJEKT = "PROJEKT"
    DATENBANK = "DATENBANK"
    DOKUMENTE = "DOKUMENTE"
    KONFIGURATION = "KONFIGURATION"


class BackupStatus(str, Enum):
    """Status eines Backups"""
    GESTARTET = "GESTARTET"
    LAEUFT = "LAEUFT"
    ABGESCHLOSSEN = "ABGESCHLOSSEN"
    FEHLER = "FEHLER"


class ExportFormat(str, Enum):
    """Export-Formate"""
    ZIP = "ZIP"
    JSON = "JSON"
    CSV = "CSV"
    XML = "XML"


class Backup(Base):
    """Model für Backups"""
    __tablename__ = "backup"

    id = Column(Integer, primary_key=True)

    # Backup-Daten
    bezeichnung = Column(String(200), nullable=False)
    backup_typ = Column(SQLEnum(BackupTyp), default=BackupTyp.VOLLSTAENDIG)
    status = Column(SQLEnum(BackupStatus), default=BackupStatus.GESTARTET)
    format = Column(SQLEnum(ExportFormat), default=ExportFormat.ZIP)

    # Umfang
    projekt_id = Column(Integer, ForeignKey("unfallprojekt.id"))  # Für Projekt-Backup
    _enthaltene_tabellen = Column("enthaltene_tabellen", Text)

    # Ergebnis
    dateiname = Column(String(200))
    dateigroesse_bytes = Column(Integer)
    dateipfad = Column(String(500))

    # Statistik
    anzahl_projekte = Column(Integer, default=0)
    anzahl_dokumente = Column(Integer, default=0)
    anzahl_datensaetze = Column(Integer, default=0)

    # Fehler
    fehler_nachricht = Column(Text)

    # Metadaten
    gestartet_am = Column(DateTime, default=datetime.now)
    abgeschlossen_am = Column(DateTime)
    erstellt_von_user_id = Column(Integer, ForeignKey("user.id"))

    @property
    def enthaltene_tabellen(self) -> List[str]:
        if self._enthaltene_tabellen:
            return json.loads(self._enthaltene_tabellen)
        return []

    @enthaltene_tabellen.setter
    def enthaltene_tabellen(self, value: List[str]):
        self._enthaltene_tabellen = json.dumps(value)

    @property
    def dauer_sekunden(self) -> Optional[float]:
        if self.gestartet_am and self.abgeschlossen_am:
            return (self.abgeschlossen_am - self.gestartet_am).total_seconds()
        return None


class BackupService:
    """Service für Backup und Export"""

    # Tabellen für vollständiges Backup
    ALLE_TABELLEN = [
        'unfallprojekt', 'beteiligte', 'dokument', 'kosten',
        'forderung', 'zahlung', 'timeline_eintrag', 'notiz',
        'termin', 'frist', 'nachricht', 'user'
    ]

    def __init__(self, db_session):
        self.db = db_session

    def backup_erstellen(
        self,
        bezeichnung: str,
        backup_typ: BackupTyp = BackupTyp.VOLLSTAENDIG,
        projekt_id: Optional[int] = None,
        format: ExportFormat = ExportFormat.ZIP,
        erstellt_von_user_id: Optional[int] = None
    ) -> Backup:
        """Startet ein neues Backup"""
        backup = Backup(
            bezeichnung=bezeichnung,
            backup_typ=backup_typ,
            format=format,
            projekt_id=projekt_id,
            erstellt_von_user_id=erstellt_von_user_id
        )

        self.db.add(backup)
        self.db.flush()

        try:
            # Backup durchführen
            backup.status = BackupStatus.LAEUFT

            if backup_typ == BackupTyp.VOLLSTAENDIG:
                self._vollstaendiges_backup(backup)
            elif backup_typ == BackupTyp.PROJEKT:
                self._projekt_backup(backup, projekt_id)
            elif backup_typ == BackupTyp.DATENBANK:
                self._datenbank_backup(backup)

            backup.status = BackupStatus.ABGESCHLOSSEN
            backup.abgeschlossen_am = datetime.now()

        except Exception as e:
            backup.status = BackupStatus.FEHLER
            backup.fehler_nachricht = str(e)
            backup.abgeschlossen_am = datetime.now()

        self.db.flush()
        return backup

    def _vollstaendiges_backup(self, backup: Backup):
        """Erstellt ein vollständiges Backup"""
        from src.models import UnfallProjekt

        daten = {
            'meta': {
                'typ': 'vollstaendig',
                'erstellt_am': datetime.now().isoformat(),
                'version': '1.0'
            },
            'projekte': [],
            'statistik': {
                'projekte': 0,
                'dokumente': 0,
                'datensaetze': 0
            }
        }

        # Alle Projekte exportieren
        projekte = self.db.query(UnfallProjekt).all()
        for projekt in projekte:
            projekt_daten = self._exportiere_projekt(projekt)
            daten['projekte'].append(projekt_daten)
            daten['statistik']['projekte'] += 1
            daten['statistik']['dokumente'] += len(projekt_daten.get('dokumente', []))

        backup.anzahl_projekte = daten['statistik']['projekte']
        backup.anzahl_dokumente = daten['statistik']['dokumente']
        backup.enthaltene_tabellen = self.ALLE_TABELLEN

        # Datei erstellen
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup.dateiname = f"backup_vollstaendig_{timestamp}.json"

    def _projekt_backup(self, backup: Backup, projekt_id: int):
        """Erstellt ein Projekt-Backup"""
        from src.models import UnfallProjekt

        projekt = self.db.query(UnfallProjekt).get(projekt_id)
        if not projekt:
            raise ValueError("Projekt nicht gefunden")

        daten = {
            'meta': {
                'typ': 'projekt',
                'projekt_id': projekt_id,
                'erstellt_am': datetime.now().isoformat(),
                'version': '1.0'
            },
            'projekt': self._exportiere_projekt(projekt)
        }

        backup.anzahl_projekte = 1
        backup.anzahl_dokumente = len(daten['projekt'].get('dokumente', []))

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup.dateiname = f"backup_projekt_{projekt.projektnummer}_{timestamp}.json"

    def _datenbank_backup(self, backup: Backup):
        """Erstellt ein reines Datenbank-Backup"""
        # Vereinfachte Version - in Produktion: pg_dump oder ähnliches
        backup.dateiname = f"backup_db_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
        backup.enthaltene_tabellen = self.ALLE_TABELLEN

    def _exportiere_projekt(self, projekt) -> Dict[str, Any]:
        """Exportiert ein einzelnes Projekt"""
        daten = {
            'id': projekt.id,
            'projektnummer': projekt.projektnummer,
            'aktenzeichen': projekt.aktenzeichen,
            'status': projekt.status.value if projekt.status else None,
            'erstellt_am': projekt.erstellt_am.isoformat() if projekt.erstellt_am else None,
            'unfalldatum': projekt.unfalldatum.isoformat() if projekt.unfalldatum else None,
            'unfallort': projekt.unfallort,
            'kennzeichen_mandant': projekt.kennzeichen_mandant,
            'kennzeichen_gegner': projekt.kennzeichen_gegner,
            'beteiligte': [],
            'kosten': [],
            'dokumente': [],
            'timeline': [],
            'fristen': []
        }

        # Beteiligte
        if hasattr(projekt, 'beteiligte'):
            for b in projekt.beteiligte:
                daten['beteiligte'].append({
                    'rolle': b.rolle.value if b.rolle else None,
                    'vorname': b.vorname,
                    'nachname': b.nachname,
                    'firma': b.firma,
                    'email': b.email,
                    'telefon': b.telefon
                })

        # Kosten
        if hasattr(projekt, 'kosten'):
            for k in projekt.kosten:
                daten['kosten'].append({
                    'kategorie': k.kategorie.value if k.kategorie else None,
                    'bezeichnung': k.bezeichnung,
                    'betrag': float(k.betrag) if k.betrag else 0,
                    'datum': k.datum.isoformat() if k.datum else None
                })

        # Dokumente (ohne Binärdaten)
        if hasattr(projekt, 'dokumente'):
            for d in projekt.dokumente:
                daten['dokumente'].append({
                    'dateiname': d.dateiname,
                    'kategorie': d.kategorie.value if d.kategorie else None,
                    'groesse': d.groesse,
                    'erstellt_am': d.erstellt_am.isoformat() if d.erstellt_am else None
                })

        # Timeline
        if hasattr(projekt, 'timeline_eintraege'):
            for t in projekt.timeline_eintraege:
                daten['timeline'].append({
                    'typ': t.typ.value if t.typ else None,
                    'titel': t.titel,
                    'beschreibung': t.beschreibung,
                    'datum': t.datum.isoformat() if t.datum else None
                })

        # Fristen
        if hasattr(projekt, 'fristen'):
            for f in projekt.fristen:
                daten['fristen'].append({
                    'bezeichnung': f.bezeichnung,
                    'frist_typ': f.frist_typ.value if f.frist_typ else None,
                    'frist_datum': f.frist_datum.isoformat() if f.frist_datum else None,
                    'erledigt': f.erledigt
                })

        return daten

    def backup_als_json(self, backup_id: int) -> Optional[str]:
        """Gibt Backup-Daten als JSON zurück"""
        backup = self.db.query(Backup).get(backup_id)

        if not backup:
            return None

        # Backup-Daten rekonstruieren
        if backup.backup_typ == BackupTyp.PROJEKT and backup.projekt_id:
            from src.models import UnfallProjekt
            projekt = self.db.query(UnfallProjekt).get(backup.projekt_id)
            if projekt:
                return json.dumps(self._exportiere_projekt(projekt), indent=2, default=str)

        return json.dumps({'backup_id': backup_id, 'status': backup.status.value}, indent=2)

    def backup_als_zip(self, backup_id: int) -> Optional[bytes]:
        """Erstellt ein ZIP-Archiv des Backups"""
        backup = self.db.query(Backup).get(backup_id)

        if not backup:
            return None

        # ZIP erstellen
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Manifest
            manifest = {
                'backup_id': backup.id,
                'bezeichnung': backup.bezeichnung,
                'typ': backup.backup_typ.value,
                'erstellt_am': backup.gestartet_am.isoformat() if backup.gestartet_am else None,
                'anzahl_projekte': backup.anzahl_projekte,
                'anzahl_dokumente': backup.anzahl_dokumente
            }
            zip_file.writestr('manifest.json', json.dumps(manifest, indent=2))

            # Daten
            json_daten = self.backup_als_json(backup_id)
            if json_daten:
                zip_file.writestr('daten.json', json_daten)

        zip_buffer.seek(0)
        return zip_buffer.read()

    def alle_backups(self, limit: int = 50) -> List[Backup]:
        """Holt alle Backups"""
        return self.db.query(Backup).order_by(
            Backup.gestartet_am.desc()
        ).limit(limit).all()

    def backup_loeschen(self, backup_id: int) -> bool:
        """Löscht ein Backup"""
        backup = self.db.query(Backup).get(backup_id)
        if backup:
            self.db.delete(backup)
            self.db.flush()
            return True
        return False

    def importiere_backup(self, json_daten: str) -> Dict[str, Any]:
        """Importiert Daten aus einem Backup"""
        try:
            daten = json.loads(json_daten)

            ergebnis = {
                'erfolgreich': True,
                'importierte_projekte': 0,
                'fehler': []
            }

            # Projekte importieren
            for projekt_daten in daten.get('projekte', []):
                try:
                    self._importiere_projekt(projekt_daten)
                    ergebnis['importierte_projekte'] += 1
                except Exception as e:
                    ergebnis['fehler'].append(str(e))

            return ergebnis

        except Exception as e:
            return {
                'erfolgreich': False,
                'fehler': [str(e)]
            }

    def _importiere_projekt(self, daten: Dict) -> int:
        """Importiert ein einzelnes Projekt"""
        from src.models import UnfallProjekt

        # Neues Projekt erstellen
        projekt = UnfallProjekt(
            aktenzeichen=daten.get('aktenzeichen'),
            unfallort=daten.get('unfallort'),
            kennzeichen_mandant=daten.get('kennzeichen_mandant'),
            kennzeichen_gegner=daten.get('kennzeichen_gegner')
        )

        if daten.get('unfalldatum'):
            projekt.unfalldatum = date.fromisoformat(daten['unfalldatum'])

        self.db.add(projekt)
        self.db.flush()

        return projekt.id

    def automatisches_backup_konfigurieren(
        self,
        aktiviert: bool = True,
        intervall_tage: int = 7,
        aufbewahrung_tage: int = 90
    ) -> Dict[str, Any]:
        """Konfiguriert automatische Backups"""
        # Konfiguration speichern (würde in Einstellungen-Tabelle gespeichert)
        return {
            'aktiviert': aktiviert,
            'intervall_tage': intervall_tage,
            'aufbewahrung_tage': aufbewahrung_tage,
            'naechstes_backup': (datetime.now().date() +
                                 __import__('datetime').timedelta(days=intervall_tage)).isoformat()
        }

    def speicherplatz_statistik(self) -> Dict[str, Any]:
        """Berechnet Speicherplatz-Statistik"""
        backups = self.db.query(Backup).all()

        gesamt_bytes = sum(b.dateigroesse_bytes or 0 for b in backups)

        return {
            'anzahl_backups': len(backups),
            'gesamt_bytes': gesamt_bytes,
            'gesamt_mb': round(gesamt_bytes / (1024 * 1024), 2),
            'aeltestes_backup': min(
                [b.gestartet_am for b in backups if b.gestartet_am],
                default=None
            ),
            'neuestes_backup': max(
                [b.gestartet_am for b in backups if b.gestartet_am],
                default=None
            )
        }
