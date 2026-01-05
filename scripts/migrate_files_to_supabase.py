#!/usr/bin/env python3
"""
Migrations-Skript: Lokale Dateien zu Supabase Storage migrieren

Dieses Skript migriert alle Dokumente vom lokalen Dateisystem
zu Supabase Storage. Es kann inkrementell ausgeführt werden
und überspringt bereits migrierte Dateien.

Verwendung:
    python scripts/migrate_files_to_supabase.py [--dry-run] [--batch-size=100]

Optionen:
    --dry-run       Zeigt nur was migriert würde, ohne tatsächliche Änderungen
    --batch-size=N  Anzahl Dateien pro Batch (Standard: 100)
    --delete-local  Löscht lokale Dateien nach erfolgreicher Migration
    --verbose       Ausführliche Ausgabe
"""

import os
import sys
import argparse
import mimetypes
from datetime import datetime
from typing import Optional, Tuple

# Projekt-Root zum Python-Pfad hinzufügen
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.config.settings import get_settings
from src.models import Dokument
from src.storage import get_storage_backend, generate_storage_key


class MigrationStats:
    """Statistiken für die Migration"""

    def __init__(self):
        self.total = 0
        self.migrated = 0
        self.skipped_already_migrated = 0
        self.skipped_file_not_found = 0
        self.errors = 0
        self.bytes_uploaded = 0

    def print_summary(self):
        print("\n" + "=" * 50)
        print("MIGRATIONS-ZUSAMMENFASSUNG")
        print("=" * 50)
        print(f"Gesamt Dokumente:           {self.total}")
        print(f"Erfolgreich migriert:       {self.migrated}")
        print(f"Bereits migriert:           {self.skipped_already_migrated}")
        print(f"Datei nicht gefunden:       {self.skipped_file_not_found}")
        print(f"Fehler:                     {self.errors}")
        print(f"Hochgeladen:                {self._format_bytes(self.bytes_uploaded)}")
        print("=" * 50)

    def _format_bytes(self, bytes_val: int) -> str:
        """Formatiert Bytes in lesbare Größe"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_val < 1024:
                return f"{bytes_val:.2f} {unit}"
            bytes_val /= 1024
        return f"{bytes_val:.2f} TB"


def get_mime_type(filepath: str) -> str:
    """Ermittelt den MIME-Type einer Datei"""
    mime_type, _ = mimetypes.guess_type(filepath)
    return mime_type or 'application/octet-stream'


def migrate_document(
    dokument: Dokument,
    local_backend,
    supabase_backend,
    db_session,
    dry_run: bool = False,
    delete_local: bool = False,
    verbose: bool = False
) -> Tuple[bool, str]:
    """
    Migriert ein einzelnes Dokument zu Supabase.

    Returns:
        Tuple aus (erfolg, nachricht)
    """
    # Prüfen ob bereits migriert
    if dokument.storage_provider == 'supabase':
        return False, "bereits_migriert"

    # Lokalen Pfad ermitteln
    local_path = dokument.dateipfad
    if not local_path:
        return False, "kein_pfad"

    # Prüfen ob Datei existiert
    if not os.path.exists(local_path):
        return False, "datei_nicht_gefunden"

    if verbose:
        print(f"  Lese: {local_path}")

    # Datei lesen
    try:
        with open(local_path, 'rb') as f:
            file_data = f.read()
    except Exception as e:
        return False, f"lesefehler: {str(e)}"

    # Storage-Key generieren
    kategorie = "dokumente"
    if dokument.dokument_typ:
        kategorie = dokument.dokument_typ.value.lower()

    storage_key = generate_storage_key(
        projekt_id=dokument.unfallprojekt_id,
        kategorie=kategorie,
        dateiname=dokument.original_dateiname or os.path.basename(local_path)
    )

    if verbose:
        print(f"  Storage-Key: {storage_key}")

    if dry_run:
        return True, f"würde_migrieren: {storage_key}"

    # Zu Supabase hochladen
    try:
        content_type = dokument.mime_typ or get_mime_type(local_path)
        supabase_backend.put_bytes(storage_key, file_data, content_type)
    except Exception as e:
        return False, f"upload_fehler: {str(e)}"

    # Dokument-Record aktualisieren
    try:
        dokument.storage_provider = 'supabase'
        dokument.storage_key = storage_key
        db_session.commit()
    except Exception as e:
        # Rollback und Datei aus Supabase löschen
        db_session.rollback()
        try:
            supabase_backend.delete(storage_key)
        except:
            pass
        return False, f"db_fehler: {str(e)}"

    # Optionales Löschen der lokalen Datei
    if delete_local:
        try:
            os.remove(local_path)
            if verbose:
                print(f"  Lokale Datei gelöscht: {local_path}")
        except Exception as e:
            print(f"  WARNUNG: Konnte lokale Datei nicht löschen: {e}")

    return True, f"migriert: {storage_key}"


def run_migration(
    dry_run: bool = False,
    batch_size: int = 100,
    delete_local: bool = False,
    verbose: bool = False
):
    """Führt die komplette Migration durch"""

    print("=" * 50)
    print("DATEI-MIGRATION: Local -> Supabase Storage")
    print("=" * 50)
    print(f"Modus:        {'DRY-RUN (keine Änderungen)' if dry_run else 'LIVE'}")
    print(f"Batch-Größe:  {batch_size}")
    print(f"Lokal löschen: {'Ja' if delete_local else 'Nein'}")
    print("=" * 50)
    print()

    # Settings und Backends initialisieren
    settings = get_settings()

    # Prüfen ob Supabase konfiguriert ist
    if not settings.supabase_url or not settings.supabase_service_role_key:
        print("FEHLER: Supabase ist nicht konfiguriert!")
        print("Bitte setzen Sie SUPABASE_URL und SUPABASE_SERVICE_ROLE_KEY in .env")
        sys.exit(1)

    # Datenbank-Session erstellen
    engine = create_engine(settings.database_url)
    Session = sessionmaker(bind=engine)
    db = Session()

    # Storage-Backends
    local_backend = get_storage_backend('local')
    supabase_backend = get_storage_backend('supabase')

    # Statistiken
    stats = MigrationStats()

    try:
        # Alle Dokumente mit lokalem Storage laden
        query = db.query(Dokument).filter(
            Dokument.storage_provider.in_(['local', None]),
            Dokument.dateipfad.isnot(None)
        )

        stats.total = query.count()
        print(f"Gefundene Dokumente zur Migration: {stats.total}")
        print()

        if stats.total == 0:
            print("Keine Dokumente zur Migration gefunden.")
            return

        # In Batches verarbeiten
        offset = 0
        batch_num = 1

        while offset < stats.total:
            dokumente = query.offset(offset).limit(batch_size).all()

            if not dokumente:
                break

            print(f"Batch {batch_num}: Verarbeite {len(dokumente)} Dokumente...")

            for dok in dokumente:
                if verbose:
                    print(f"\nDokument ID {dok.id}: {dok.original_dateiname}")

                success, message = migrate_document(
                    dokument=dok,
                    local_backend=local_backend,
                    supabase_backend=supabase_backend,
                    db_session=db,
                    dry_run=dry_run,
                    delete_local=delete_local,
                    verbose=verbose
                )

                if success:
                    stats.migrated += 1
                    if dok.dateigroesse:
                        stats.bytes_uploaded += dok.dateigroesse
                elif message == "bereits_migriert":
                    stats.skipped_already_migrated += 1
                elif message == "datei_nicht_gefunden" or message == "kein_pfad":
                    stats.skipped_file_not_found += 1
                    if verbose:
                        print(f"  ÜBERSPRUNGEN: {message}")
                else:
                    stats.errors += 1
                    print(f"  FEHLER bei Dokument {dok.id}: {message}")

            offset += batch_size
            batch_num += 1

            # Fortschritt anzeigen
            progress = min(offset, stats.total)
            pct = (progress / stats.total) * 100
            print(f"  Fortschritt: {progress}/{stats.total} ({pct:.1f}%)")

    finally:
        db.close()

    # Zusammenfassung
    stats.print_summary()

    if dry_run:
        print("\nDies war ein DRY-RUN. Keine Änderungen wurden vorgenommen.")
        print("Führen Sie das Skript ohne --dry-run aus, um die Migration durchzuführen.")


def main():
    parser = argparse.ArgumentParser(
        description='Migriert lokale Dateien zu Supabase Storage'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Zeigt nur was migriert würde, ohne Änderungen'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=100,
        help='Anzahl Dateien pro Batch (Standard: 100)'
    )
    parser.add_argument(
        '--delete-local',
        action='store_true',
        help='Löscht lokale Dateien nach erfolgreicher Migration'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Ausführliche Ausgabe'
    )

    args = parser.parse_args()

    run_migration(
        dry_run=args.dry_run,
        batch_size=args.batch_size,
        delete_local=args.delete_local,
        verbose=args.verbose
    )


if __name__ == '__main__':
    main()
