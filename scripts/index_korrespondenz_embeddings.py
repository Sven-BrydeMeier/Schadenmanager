#!/usr/bin/env python3
"""
Skript: Korrespondenz-Embeddings initial erstellen

Indexiert alle versendeten Korrespondenzen für die
Stil-Referenz-Funktion bei KI-Schreibvorschlägen.

Verwendung:
    python scripts/index_korrespondenz_embeddings.py [--reindex-all] [--verbose]

Optionen:
    --reindex-all  Reindexiert auch bereits indizierte Korrespondenzen
    --verbose      Ausführliche Ausgabe
"""

import os
import sys
import argparse
from datetime import datetime

# Projekt-Root zum Python-Pfad hinzufügen
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.config.settings import get_settings
from src.models import Korrespondenz
from src.services.korrespondenz_embeddings import get_korrespondenz_embedding_service


def run_indexing(reindex_all: bool = False, verbose: bool = False):
    """Führt die Indexierung durch"""

    print("=" * 50)
    print("KORRESPONDENZ-EMBEDDINGS INDEXIERUNG")
    print("=" * 50)
    print(f"Modus: {'Alle reindexieren' if reindex_all else 'Nur neue indexieren'}")
    print("=" * 50)
    print()

    # Settings laden
    settings = get_settings()

    # Prüfen ob OpenAI konfiguriert ist
    if not settings.openai_api_key:
        print("FEHLER: OpenAI API Key nicht konfiguriert!")
        print("Bitte setzen Sie OPENAI_API_KEY in .env für Embeddings.")
        sys.exit(1)

    # Datenbank-Session erstellen
    engine = create_engine(settings.database_url)
    Session = sessionmaker(bind=engine)
    db = Session()

    # Embedding-Service
    embedding_service = get_korrespondenz_embedding_service()

    # Statistiken
    stats = {
        "gefunden": 0,
        "indexiert": 0,
        "uebersprungen": 0,
        "fehler": 0
    }

    try:
        # Korrespondenzen laden
        query = db.query(Korrespondenz).filter(
            Korrespondenz.status == "VERSENDET"
        )

        if not reindex_all:
            query = query.filter(Korrespondenz.embedding_erstellt == False)

        korrespondenzen = query.all()
        stats["gefunden"] = len(korrespondenzen)

        print(f"Gefundene Korrespondenzen: {stats['gefunden']}")
        print()

        if stats["gefunden"] == 0:
            print("Keine Korrespondenzen zur Indexierung gefunden.")
            return

        # Indexieren
        for i, korr in enumerate(korrespondenzen, 1):
            if verbose:
                print(f"[{i}/{stats['gefunden']}] Korrespondenz ID {korr.id}: {korr.betreff or '(Kein Betreff)'}")

            try:
                text = korr.text_final or korr.text_entwurf
                if not text or not text.strip():
                    stats["uebersprungen"] += 1
                    if verbose:
                        print("  -> Übersprungen (kein Text)")
                    continue

                # Reindexieren falls gewünscht
                if reindex_all and korr.embedding_erstellt:
                    embedding_service.loesche_korrespondenz(korr.id)

                chunks = embedding_service.indexiere_korrespondenz(korr, db)

                if chunks > 0:
                    stats["indexiert"] += 1
                    if verbose:
                        print(f"  -> Indexiert ({chunks} Chunk(s))")
                else:
                    stats["uebersprungen"] += 1
                    if verbose:
                        print("  -> Übersprungen")

            except Exception as e:
                stats["fehler"] += 1
                print(f"  -> FEHLER: {str(e)}")

            # Fortschritt alle 10 Dokumente
            if i % 10 == 0 and not verbose:
                pct = (i / stats["gefunden"]) * 100
                print(f"Fortschritt: {i}/{stats['gefunden']} ({pct:.1f}%)")

    finally:
        db.close()

    # Zusammenfassung
    print()
    print("=" * 50)
    print("ZUSAMMENFASSUNG")
    print("=" * 50)
    print(f"Gefunden:     {stats['gefunden']}")
    print(f"Indexiert:    {stats['indexiert']}")
    print(f"Übersprungen: {stats['uebersprungen']}")
    print(f"Fehler:       {stats['fehler']}")
    print("=" * 50)

    # Statistiken vom Service
    try:
        service_stats = embedding_service.get_statistiken()
        print()
        print("Embedding-Store Statistiken:")
        print(f"  Total Embeddings: {service_stats['total_embeddings']}")
        print(f"  Collection: {service_stats['collection_name']}")
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(
        description='Indexiert Korrespondenz-Embeddings für Stil-Referenzen'
    )
    parser.add_argument(
        '--reindex-all',
        action='store_true',
        help='Reindexiert auch bereits indizierte Korrespondenzen'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Ausführliche Ausgabe'
    )

    args = parser.parse_args()

    run_indexing(
        reindex_all=args.reindex_all,
        verbose=args.verbose
    )


if __name__ == '__main__':
    main()
