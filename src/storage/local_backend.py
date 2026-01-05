"""
Local Filesystem Storage Backend

Für Development und Backward-Compatibility mit bestehenden lokalen Dateien.
"""

import os
import shutil
from pathlib import Path
from typing import List, Optional
from urllib.parse import quote

from src.config.settings import get_settings


class LocalFSBackend:
    """
    Storage-Backend für lokales Dateisystem.

    Speichert Dateien im konfigurierten Upload-Verzeichnis.
    """

    def __init__(self, base_path: Optional[str] = None):
        """
        Initialisiert das Backend.

        Args:
            base_path: Basis-Verzeichnis für Dateien (default: aus Settings)
        """
        settings = get_settings()
        self.base_path = Path(base_path or settings.upload_folder)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _resolve_path(self, key: str) -> Path:
        """Löst einen Key zu einem absoluten Pfad auf"""
        # Sicherheitscheck: Verhindere Path Traversal
        clean_key = key.lstrip("/").replace("..", "")
        return self.base_path / clean_key

    def put_bytes(self, key: str, data: bytes, content_type: str) -> str:
        """
        Speichert Bytes unter dem angegebenen Key.

        Args:
            key: Pfad/Key im Storage
            data: Die zu speichernden Bytes
            content_type: MIME-Type (wird für lokale Dateien ignoriert)

        Returns:
            Der finale Storage-Key
        """
        file_path = self._resolve_path(key)

        # Verzeichnis erstellen falls nötig
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Datei schreiben
        with open(file_path, 'wb') as f:
            f.write(data)

        return key

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
        file_path = self._resolve_path(key)

        if not file_path.exists():
            raise FileNotFoundError(f"Datei nicht gefunden: {key}")

        with open(file_path, 'rb') as f:
            return f.read()

    def get_signed_url(self, key: str, expires_in: int = 3600) -> str:
        """
        Generiert eine URL für lokalen Zugriff.

        Für lokale Dateien wird ein file://-Pfad zurückgegeben.
        In Streamlit-Kontext ist dies meist nicht direkt nutzbar.

        Args:
            key: Pfad/Key im Storage
            expires_in: Ignoriert für lokale Dateien

        Returns:
            file://-URL zum lokalen Pfad
        """
        file_path = self._resolve_path(key)
        return f"file://{file_path.absolute()}"

    def get_local_path(self, key: str) -> Path:
        """
        Gibt den lokalen Pfad für einen Key zurück.

        Diese Methode ist spezifisch für LocalFSBackend.

        Args:
            key: Pfad/Key im Storage

        Returns:
            Absoluter Pfad zur Datei
        """
        return self._resolve_path(key)

    def delete(self, key: str) -> bool:
        """
        Löscht eine Datei.

        Args:
            key: Pfad/Key im Storage

        Returns:
            True wenn erfolgreich, False sonst
        """
        file_path = self._resolve_path(key)

        try:
            if file_path.exists():
                file_path.unlink()
                return True
            return False
        except Exception:
            return False

    def move(self, old_key: str, new_key: str) -> bool:
        """
        Verschiebt eine Datei.

        Args:
            old_key: Alter Pfad/Key
            new_key: Neuer Pfad/Key

        Returns:
            True wenn erfolgreich, False sonst
        """
        old_path = self._resolve_path(old_key)
        new_path = self._resolve_path(new_key)

        try:
            # Zielverzeichnis erstellen
            new_path.parent.mkdir(parents=True, exist_ok=True)

            # Datei verschieben
            shutil.move(str(old_path), str(new_path))
            return True
        except Exception:
            return False

    def exists(self, key: str) -> bool:
        """
        Prüft ob eine Datei existiert.

        Args:
            key: Pfad/Key im Storage

        Returns:
            True wenn existiert, False sonst
        """
        file_path = self._resolve_path(key)
        return file_path.exists()

    def list_keys(self, prefix: str) -> List[str]:
        """
        Listet alle Keys mit dem angegebenen Prefix.

        Args:
            prefix: Prefix für die Suche

        Returns:
            Liste von Keys
        """
        prefix_path = self._resolve_path(prefix)
        keys = []

        if prefix_path.is_dir():
            for file_path in prefix_path.rglob("*"):
                if file_path.is_file():
                    # Relativen Key berechnen
                    rel_path = file_path.relative_to(self.base_path)
                    keys.append(str(rel_path))

        return keys

    def get_size(self, key: str) -> int:
        """
        Gibt die Dateigröße in Bytes zurück.

        Args:
            key: Pfad/Key im Storage

        Returns:
            Dateigröße in Bytes

        Raises:
            FileNotFoundError: Wenn der Key nicht existiert
        """
        file_path = self._resolve_path(key)

        if not file_path.exists():
            raise FileNotFoundError(f"Datei nicht gefunden: {key}")

        return file_path.stat().st_size
