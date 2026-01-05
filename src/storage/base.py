"""
Storage-Abstraktionsschicht für Schadenmanager

Ermöglicht den Wechsel zwischen verschiedenen Storage-Backends:
- LocalFSBackend: Lokales Dateisystem (Development, Backward-Compatibility)
- SupabaseStorageBackend: Supabase Storage (Production)
"""

from typing import Protocol, Optional, runtime_checkable
from abc import ABC, abstractmethod


@runtime_checkable
class StorageBackend(Protocol):
    """
    Protocol für Storage-Backends.

    Alle Implementierungen müssen diese Methoden bereitstellen.
    """

    def put_bytes(self, key: str, data: bytes, content_type: str) -> str:
        """
        Speichert Bytes unter dem angegebenen Key.

        Args:
            key: Pfad/Key im Storage (z.B. "dokumente/123/datei.pdf")
            data: Die zu speichernden Bytes
            content_type: MIME-Type (z.B. "application/pdf")

        Returns:
            Der finale Storage-Key
        """
        ...

    def get_bytes(self, key: str) -> bytes:
        """
        Lädt Bytes vom angegebenen Key.

        Args:
            key: Pfad/Key im Storage

        Returns:
            Die geladenen Bytes

        Raises:
            FileNotFoundError: Wenn der Key nicht existiert
        """
        ...

    def get_signed_url(self, key: str, expires_in: int = 3600) -> str:
        """
        Generiert eine signierte URL für temporären Zugriff.

        Args:
            key: Pfad/Key im Storage
            expires_in: Gültigkeitsdauer in Sekunden (default: 1 Stunde)

        Returns:
            Signierte URL
        """
        ...

    def delete(self, key: str) -> bool:
        """
        Löscht eine Datei.

        Args:
            key: Pfad/Key im Storage

        Returns:
            True wenn erfolgreich, False sonst
        """
        ...

    def move(self, old_key: str, new_key: str) -> bool:
        """
        Verschiebt eine Datei.

        Args:
            old_key: Alter Pfad/Key
            new_key: Neuer Pfad/Key

        Returns:
            True wenn erfolgreich, False sonst
        """
        ...

    def exists(self, key: str) -> bool:
        """
        Prüft ob eine Datei existiert.

        Args:
            key: Pfad/Key im Storage

        Returns:
            True wenn existiert, False sonst
        """
        ...

    def list_keys(self, prefix: str) -> list:
        """
        Listet alle Keys mit dem angegebenen Prefix.

        Args:
            prefix: Prefix für die Suche (z.B. "dokumente/123/")

        Returns:
            Liste von Keys
        """
        ...
