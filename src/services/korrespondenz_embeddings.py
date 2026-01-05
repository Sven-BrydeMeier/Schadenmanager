"""
KorrespondenzEmbeddingService - Verwaltet Embeddings für Korrespondenz-Texte

Ermöglicht das Finden ähnlicher Korrespondenz für Stil-Referenzen
bei der KI-gestützten Schreibgenerierung.
"""

import json
from typing import List, Dict, Optional, Any
from datetime import datetime

from sqlalchemy.orm import Session

from src.config.settings import get_settings
from src.models import Korrespondenz, KorrespondenzRichtung

# Lazy imports für optionale Abhängigkeiten
_chromadb = None
_openai = None


def _get_chromadb():
    """Lazy import für ChromaDB"""
    global _chromadb
    if _chromadb is None:
        try:
            import chromadb
            _chromadb = chromadb
        except ImportError:
            raise ImportError(
                "ChromaDB ist nicht installiert. "
                "Bitte installieren mit: pip install chromadb"
            )
    return _chromadb


def _get_openai():
    """Lazy import für OpenAI"""
    global _openai
    if _openai is None:
        try:
            import openai
            _openai = openai
        except ImportError:
            raise ImportError(
                "OpenAI ist nicht installiert. "
                "Bitte installieren mit: pip install openai"
            )
    return _openai


class KorrespondenzEmbeddingService:
    """
    Service für Korrespondenz-Embeddings zur Stil-Referenz.

    Speichert versendete Korrespondenz als Embeddings, um bei neuen
    Schreiben ähnliche vergangene Texte als Stil-Referenz zu finden.
    """

    COLLECTION_NAME = "korrespondenz"

    def __init__(self):
        self.settings = get_settings()
        self._client = None
        self._collection = None
        self._openai_client = None

    @property
    def client(self):
        """Lazy initialization des ChromaDB Clients"""
        if self._client is None:
            chromadb = _get_chromadb()
            import os
            os.makedirs(self.settings.vector_store_path, exist_ok=True)
            self._client = chromadb.PersistentClient(
                path=self.settings.vector_store_path
            )
        return self._client

    @property
    def collection(self):
        """Lazy initialization der Korrespondenz-Collection"""
        if self._collection is None:
            self._collection = self.client.get_or_create_collection(
                name=self.COLLECTION_NAME,
                metadata={"description": "Korrespondenz für Stil-Referenz"}
            )
        return self._collection

    @property
    def openai_client(self):
        """Lazy initialization des OpenAI Clients"""
        if self._openai_client is None:
            openai = _get_openai()
            api_key = self.settings.openai_api_key
            if not api_key:
                raise ValueError(
                    "OpenAI API Key nicht konfiguriert. "
                    "Bitte OPENAI_API_KEY in .env setzen."
                )
            self._openai_client = openai.OpenAI(api_key=api_key)
        return self._openai_client

    def _create_embedding(self, text: str) -> List[float]:
        """Erstellt einen Embedding-Vektor für den gegebenen Text."""
        max_chars = 30000
        if len(text) > max_chars:
            text = text[:max_chars]

        response = self.openai_client.embeddings.create(
            model=self.settings.embedding_model,
            input=text
        )
        return response.data[0].embedding

    def _generate_chunk_id(self, korrespondenz_id: int, chunk_index: int = 0) -> str:
        """Generiert eine eindeutige ID für einen Korrespondenz-Chunk"""
        return f"korr_{korrespondenz_id}_chunk_{chunk_index}"

    def indexiere_korrespondenz(
        self,
        korrespondenz: Korrespondenz,
        db: Session
    ) -> int:
        """
        Indexiert eine Korrespondenz für Stil-Referenz.

        Nur versendete Korrespondenzen mit finalem Text werden indexiert.

        Args:
            korrespondenz: Die zu indexierende Korrespondenz
            db: Datenbank-Session

        Returns:
            Anzahl der erstellten Chunks (0 oder 1)
        """
        # Nur versendete Korrespondenz mit Text indexieren
        text = korrespondenz.text_final or korrespondenz.text_entwurf
        if not text or not text.strip():
            return 0

        if korrespondenz.status != "VERSENDET":
            return 0

        # Alte Embeddings löschen
        self.loesche_korrespondenz(korrespondenz.id)

        # Embedding erstellen
        chunk_id = self._generate_chunk_id(korrespondenz.id)
        embedding = self._create_embedding(text)

        # Metadaten zusammenstellen
        metadata = {
            "korrespondenz_id": korrespondenz.id,
            "unfallprojekt_id": korrespondenz.unfallprojekt_id,
            "richtung": korrespondenz.richtung.value if korrespondenz.richtung else None,
            "betreff": korrespondenz.betreff or "",
            "ki_generiert": korrespondenz.ki_generiert,
            "erstellt_am": korrespondenz.erstellt_am.isoformat() if korrespondenz.erstellt_am else None,
            "versendet_am": korrespondenz.versendet_am.isoformat() if korrespondenz.versendet_am else None,
            "indexiert_am": datetime.utcnow().isoformat()
        }

        # In ChromaDB speichern
        self.collection.add(
            ids=[chunk_id],
            embeddings=[embedding],
            metadatas=[metadata],
            documents=[text]
        )

        # Korrespondenz-Model aktualisieren
        korrespondenz.embedding_erstellt = True
        korrespondenz.embedding_erstellt_am = datetime.utcnow()
        korrespondenz.embedding_chunk_ids = json.dumps([chunk_id])
        db.commit()

        return 1

    def suche_aehnliche_korrespondenz(
        self,
        query: str,
        richtung: Optional[KorrespondenzRichtung] = None,
        limit: int = 3,
        exclude_projekt_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Findet semantisch ähnliche Korrespondenz für Stil-Referenz.

        Args:
            query: Suchtext (z.B. Betreff oder Thema des neuen Schreibens)
            richtung: Optional - Filtert nach Korrespondenz-Richtung
            limit: Maximale Anzahl Ergebnisse
            exclude_projekt_id: Optional - Schließt Korrespondenz aus diesem Projekt aus

        Returns:
            Liste von Dictionaries mit:
            - korrespondenz_id: int
            - text: str
            - score: float
            - metadata: dict
        """
        query_embedding = self._create_embedding(query)

        # Filter zusammenstellen
        where_filter = None
        if richtung:
            where_filter = {"richtung": richtung.value}

        # Suche in ChromaDB
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=limit * 2,  # Mehr holen für Filtering
            where=where_filter,
            include=["documents", "metadatas", "distances"]
        )

        # Ergebnisse formatieren und filtern
        formatted_results = []

        if results and results['ids'] and results['ids'][0]:
            for i, chunk_id in enumerate(results['ids'][0]):
                metadata = results['metadatas'][0][i]

                # Projekt ausschließen wenn gewünscht
                if exclude_projekt_id and metadata.get('unfallprojekt_id') == exclude_projekt_id:
                    continue

                formatted_results.append({
                    "korrespondenz_id": metadata.get('korrespondenz_id'),
                    "text": results['documents'][0][i],
                    "score": 1 - results['distances'][0][i],
                    "metadata": metadata
                })

                if len(formatted_results) >= limit:
                    break

        return formatted_results

    def finde_stil_referenzen(
        self,
        schreiben_typ: str,
        empfaenger_typ: str,
        kontext: str,
        limit: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Findet passende Stil-Referenzen für ein neues Schreiben.

        Sucht nach ähnlichen vergangenen Schreiben basierend auf
        Schreiben-Typ, Empfänger und Kontext.

        Args:
            schreiben_typ: Art des Schreibens (z.B. "ANSPRUCHSSCHREIBEN")
            empfaenger_typ: Art des Empfängers (z.B. "VERSICHERUNG_GEGNER")
            kontext: Zusätzlicher Kontext für die Suche
            limit: Maximale Anzahl Referenzen

        Returns:
            Liste ähnlicher Korrespondenzen mit Text und Score
        """
        # Mapping von Empfänger-Typ zu Korrespondenz-Richtung
        richtung_mapping = {
            "VERSICHERUNG_GEGNER": KorrespondenzRichtung.RA_AN_VERSICHERUNG,
            "VERSICHERUNG_EIGEN": KorrespondenzRichtung.RA_AN_VERSICHERUNG,
            "MANDANT": KorrespondenzRichtung.RA_AN_MANDANT,
        }

        richtung = richtung_mapping.get(empfaenger_typ)

        # Suchquery aus Typ und Kontext zusammensetzen
        query = f"{schreiben_typ} {empfaenger_typ} {kontext}"

        return self.suche_aehnliche_korrespondenz(
            query=query,
            richtung=richtung,
            limit=limit
        )

    def loesche_korrespondenz(self, korrespondenz_id: int) -> int:
        """
        Entfernt Embeddings einer Korrespondenz.

        Args:
            korrespondenz_id: ID der Korrespondenz

        Returns:
            Anzahl der gelöschten Chunks
        """
        try:
            results = self.collection.get(
                where={"korrespondenz_id": korrespondenz_id},
                include=["metadatas"]
            )

            if results and results['ids']:
                self.collection.delete(ids=results['ids'])
                return len(results['ids'])
        except Exception:
            pass

        return 0

    def indexiere_alle_korrespondenzen(self, db: Session) -> Dict[str, int]:
        """
        Indexiert alle versendeten Korrespondenzen ohne Embedding.

        Nützlich für initiale Indizierung oder Reindexierung.

        Args:
            db: Datenbank-Session

        Returns:
            Statistiken über die Indizierung
        """
        stats = {
            "gefunden": 0,
            "indexiert": 0,
            "uebersprungen": 0,
            "fehler": 0
        }

        # Alle versendeten Korrespondenzen ohne Embedding finden
        korrespondenzen = db.query(Korrespondenz).filter(
            Korrespondenz.status == "VERSENDET",
            Korrespondenz.embedding_erstellt == False
        ).all()

        stats["gefunden"] = len(korrespondenzen)

        for korr in korrespondenzen:
            try:
                chunks = self.indexiere_korrespondenz(korr, db)
                if chunks > 0:
                    stats["indexiert"] += 1
                else:
                    stats["uebersprungen"] += 1
            except Exception as e:
                stats["fehler"] += 1

        return stats

    def get_statistiken(self) -> Dict[str, Any]:
        """Gibt Statistiken über die Korrespondenz-Embeddings zurück."""
        return {
            "total_embeddings": self.collection.count(),
            "collection_name": self.COLLECTION_NAME,
            "vector_store_path": self.settings.vector_store_path
        }


# Singleton-Instanz
_service = None


def get_korrespondenz_embedding_service() -> KorrespondenzEmbeddingService:
    """Gibt die Singleton-Instanz des KorrespondenzEmbeddingService zurück"""
    global _service
    if _service is None:
        _service = KorrespondenzEmbeddingService()
    return _service
