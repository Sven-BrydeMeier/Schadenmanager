"""
Storage-Modul für Schadenmanager

Bietet eine einheitliche Abstraktionsschicht für verschiedene Storage-Backends.
"""

from typing import Union

from src.storage.base import StorageBackend
from src.storage.local_backend import LocalFSBackend

# Lazy import für Supabase (nur wenn benötigt)
_supabase_backend = None


def get_storage_backend(backend_type: str = None) -> Union[LocalFSBackend, 'SupabaseStorageBackend']:
    """
    Factory-Funktion für Storage-Backends.

    Gibt das konfigurierte Storage-Backend zurück.

    Args:
        backend_type: "local" oder "supabase" (default: aus STORAGE_BACKEND ENV)

    Returns:
        Storage-Backend Instanz

    Raises:
        ValueError: Bei unbekanntem Backend-Typ
    """
    from src.config.settings import get_settings

    settings = get_settings()

    # Backend-Typ aus Parameter oder Settings
    if backend_type is None:
        backend_type = getattr(settings, 'storage_backend', 'local')

    backend_type = backend_type.lower()

    if backend_type == 'local':
        return LocalFSBackend()

    elif backend_type == 'supabase':
        from src.storage.supabase_backend import SupabaseStorageBackend
        return SupabaseStorageBackend()

    else:
        raise ValueError(
            f"Unbekannter Storage-Backend-Typ: {backend_type}. "
            f"Erlaubt: 'local', 'supabase'"
        )


def generate_storage_key(
    projekt_id: int,
    kategorie: str,
    dateiname: str,
    subfolder: str = None
) -> str:
    """
    Generiert einen Storage-Key nach dem empfohlenen Schema.

    Args:
        projekt_id: ID des Projekts
        kategorie: Kategorie (z.B. "dokumente", "korrespondenz", "schadensbilder")
        dateiname: Ursprünglicher Dateiname
        subfolder: Optionaler Unterordner

    Returns:
        Storage-Key (z.B. "dokumente/123/scans/datei.pdf")
    """
    import os
    from datetime import datetime

    # Dateiname bereinigen
    safe_filename = "".join(
        c for c in dateiname
        if c.isalnum() or c in "._-"
    )

    # Timestamp für Eindeutigkeit
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Key zusammensetzen
    parts = [kategorie, str(projekt_id)]

    if subfolder:
        parts.append(subfolder)

    # Dateiname mit Timestamp
    name, ext = os.path.splitext(safe_filename)
    parts.append(f"{name}_{timestamp}{ext}")

    return "/".join(parts)


__all__ = [
    'StorageBackend',
    'LocalFSBackend',
    'get_storage_backend',
    'generate_storage_key'
]
