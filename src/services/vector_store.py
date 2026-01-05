"""
VectorStoreService - Verwaltet Vektor-Embeddings für semantische Dokumentensuche

Verwendet ChromaDB als Vektordatenbank und OpenAI/Anthropic Embeddings
für die semantische Suche in Dokumenten.
"""

import os
import json
import hashlib
from typing import List, Dict, Optional, Any
from datetime import datetime

from src.config.settings import get_settings

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


class VectorStoreService:
    """
    Service für Vektor-Embeddings und semantische Dokumentensuche.

    Verwendet ChromaDB als persistente Vektordatenbank und OpenAI
    Embeddings für die Vektorisierung von Dokumenttexten.
    """

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

            # Stelle sicher, dass das Verzeichnis existiert
            os.makedirs(self.settings.vector_store_path, exist_ok=True)

            self._client = chromadb.PersistentClient(
                path=self.settings.vector_store_path
            )
        return self._client

    @property
    def collection(self):
        """Lazy initialization der ChromaDB Collection"""
        if self._collection is None:
            self._collection = self.client.get_or_create_collection(
                name="dokumente",
                metadata={"description": "Schadenmanager Dokumente"}
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
        """
        Erstellt einen Embedding-Vektor für den gegebenen Text.

        Args:
            text: Der zu vektorisierende Text

        Returns:
            Liste von Floats (Embedding-Vektor)
        """
        # Text auf maximale Länge begrenzen (ca. 8000 Tokens)
        max_chars = 30000
        if len(text) > max_chars:
            text = text[:max_chars]

        response = self.openai_client.embeddings.create(
            model=self.settings.embedding_model,
            input=text
        )
        return response.data[0].embedding

    def _chunk_text(self, text: str) -> List[str]:
        """
        Teilt einen langen Text in überlappende Chunks.

        Args:
            text: Der zu teilende Text

        Returns:
            Liste von Text-Chunks
        """
        chunk_size = self.settings.embedding_chunk_size
        overlap = self.settings.embedding_chunk_overlap

        if len(text) <= chunk_size:
            return [text]

        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size

            # Versuche, am Satzende zu trennen
            if end < len(text):
                # Suche nach Satzende im letzten Viertel des Chunks
                search_start = end - chunk_size // 4
                last_period = text.rfind('.', search_start, end)
                last_newline = text.rfind('\n', search_start, end)

                break_point = max(last_period, last_newline)
                if break_point > search_start:
                    end = break_point + 1

            chunks.append(text[start:end].strip())
            start = end - overlap

        return [c for c in chunks if c]  # Leere Chunks entfernen

    def _generate_chunk_id(self, dokument_id: int, chunk_index: int) -> str:
        """Generiert eine eindeutige ID für einen Chunk"""
        return f"dok_{dokument_id}_chunk_{chunk_index}"

    def indexiere_dokument(
        self,
        dokument_id: int,
        text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Fügt ein Dokument zum Vector Store hinzu.

        Der Text wird in Chunks aufgeteilt und jeder Chunk wird
        separat vektorisiert und gespeichert.

        Args:
            dokument_id: ID des Dokuments in der Datenbank
            text: Der Dokumenttext (z.B. aus OCR)
            metadata: Zusätzliche Metadaten (projekt_id, dokument_typ, etc.)

        Returns:
            Anzahl der erstellten Chunks
        """
        if not text or not text.strip():
            return 0

        # Alte Chunks für dieses Dokument löschen
        self.loesche_dokument(dokument_id)

        # Text in Chunks aufteilen
        chunks = self._chunk_text(text)

        if not chunks:
            return 0

        # Basis-Metadaten
        base_metadata = {
            "dokument_id": dokument_id,
            "indexiert_am": datetime.utcnow().isoformat(),
        }

        if metadata:
            base_metadata.update(metadata)

        # Embeddings erstellen und speichern
        ids = []
        embeddings = []
        metadatas = []
        documents = []

        for i, chunk in enumerate(chunks):
            chunk_id = self._generate_chunk_id(dokument_id, i)
            embedding = self._create_embedding(chunk)

            chunk_metadata = base_metadata.copy()
            chunk_metadata["chunk_index"] = i
            chunk_metadata["total_chunks"] = len(chunks)

            ids.append(chunk_id)
            embeddings.append(embedding)
            metadatas.append(chunk_metadata)
            documents.append(chunk)

        # Batch-Insert in ChromaDB
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=documents
        )

        return len(chunks)

    def suche_aehnliche(
        self,
        query: str,
        projekt_id: Optional[int] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Findet semantisch ähnliche Dokumente/Chunks.

        Args:
            query: Die Suchanfrage
            projekt_id: Optional - Beschränkt Suche auf ein Projekt
            limit: Maximale Anzahl Ergebnisse

        Returns:
            Liste von Dictionaries mit:
            - dokument_id: int
            - chunk_text: str
            - score: float (Ähnlichkeit)
            - metadata: dict
        """
        # Embedding für Query erstellen
        query_embedding = self._create_embedding(query)

        # Filter für Projekt
        where_filter = None
        if projekt_id is not None:
            where_filter = {"unfallprojekt_id": projekt_id}

        # Suche in ChromaDB
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=limit,
            where=where_filter,
            include=["documents", "metadatas", "distances"]
        )

        # Ergebnisse formatieren
        formatted_results = []

        if results and results['ids'] and results['ids'][0]:
            for i, chunk_id in enumerate(results['ids'][0]):
                formatted_results.append({
                    "dokument_id": results['metadatas'][0][i].get('dokument_id'),
                    "chunk_text": results['documents'][0][i],
                    "score": 1 - results['distances'][0][i],  # Distanz zu Ähnlichkeit
                    "metadata": results['metadatas'][0][i]
                })

        return formatted_results

    def loesche_dokument(self, dokument_id: int) -> int:
        """
        Entfernt alle Chunks eines Dokuments aus dem Index.

        Args:
            dokument_id: ID des zu löschenden Dokuments

        Returns:
            Anzahl der gelöschten Chunks
        """
        # Finde alle Chunks für dieses Dokument
        try:
            results = self.collection.get(
                where={"dokument_id": dokument_id},
                include=["metadatas"]
            )

            if results and results['ids']:
                self.collection.delete(ids=results['ids'])
                return len(results['ids'])
        except Exception:
            pass

        return 0

    def reindexiere_projekt(
        self,
        projekt_id: int,
        dokumente: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """
        Reindexiert alle Dokumente eines Projekts.

        Args:
            projekt_id: ID des Projekts
            dokumente: Liste von Dokumenten mit 'id' und 'text'

        Returns:
            Dictionary mit Statistiken:
            - dokumente_verarbeitet: int
            - chunks_erstellt: int
        """
        stats = {
            "dokumente_verarbeitet": 0,
            "chunks_erstellt": 0
        }

        for dok in dokumente:
            if dok.get('text'):
                chunks = self.indexiere_dokument(
                    dokument_id=dok['id'],
                    text=dok['text'],
                    metadata={
                        "unfallprojekt_id": projekt_id,
                        "dokument_typ": dok.get('dokument_typ'),
                        "dateiname": dok.get('dateiname')
                    }
                )
                stats["dokumente_verarbeitet"] += 1
                stats["chunks_erstellt"] += chunks

        return stats

    def get_statistiken(self) -> Dict[str, Any]:
        """
        Gibt Statistiken über den Vector Store zurück.

        Returns:
            Dictionary mit:
            - total_chunks: int
            - collection_name: str
        """
        return {
            "total_chunks": self.collection.count(),
            "collection_name": self.collection.name,
            "vector_store_path": self.settings.vector_store_path
        }
