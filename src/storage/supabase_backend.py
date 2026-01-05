"""
Supabase Storage Backend

Für Production-Umgebungen mit Supabase Storage.
"""

from typing import List, Optional
import mimetypes

from src.config.settings import get_settings


class SupabaseStorageBackend:
    """
    Storage-Backend für Supabase Storage.

    Speichert Dateien in einem Supabase Storage Bucket.
    """

    def __init__(
        self,
        url: Optional[str] = None,
        key: Optional[str] = None,
        bucket: Optional[str] = None
    ):
        """
        Initialisiert das Backend.

        Args:
            url: Supabase URL (default: aus Settings/ENV)
            key: Supabase Service Role Key (default: aus Settings/ENV)
            bucket: Bucket-Name (default: aus Settings/ENV)
        """
        settings = get_settings()

        self.url = url or getattr(settings, 'supabase_url', None)
        self.key = key or getattr(settings, 'supabase_service_role_key', None)
        self.bucket = bucket or getattr(settings, 'supabase_bucket', 'schadenmanager')

        if not self.url or not self.key:
            raise ValueError(
                "Supabase-Konfiguration fehlt. "
                "Bitte SUPABASE_URL und SUPABASE_SERVICE_ROLE_KEY setzen."
            )

        self._client = None

    @property
    def client(self):
        """Lazy initialization des Supabase Clients"""
        if self._client is None:
            try:
                from supabase import create_client
                self._client = create_client(self.url, self.key)
            except ImportError:
                raise ImportError(
                    "supabase-py ist nicht installiert. "
                    "Bitte installieren mit: pip install supabase"
                )
        return self._client

    @property
    def storage(self):
        """Zugriff auf den Storage-Bucket"""
        return self.client.storage.from_(self.bucket)

    def put_bytes(self, key: str, data: bytes, content_type: str) -> str:
        """
        Speichert Bytes unter dem angegebenen Key.

        Args:
            key: Pfad/Key im Storage
            data: Die zu speichernden Bytes
            content_type: MIME-Type

        Returns:
            Der finale Storage-Key
        """
        # Führenden Slash entfernen
        clean_key = key.lstrip("/")

        # Upload mit upsert (überschreibt falls vorhanden)
        self.storage.upload(
            path=clean_key,
            file=data,
            file_options={
                "content-type": content_type,
                "upsert": "true"
            }
        )

        return clean_key

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
        clean_key = key.lstrip("/")

        try:
            response = self.storage.download(clean_key)
            return response
        except Exception as e:
            if "not found" in str(e).lower() or "404" in str(e):
                raise FileNotFoundError(f"Datei nicht gefunden: {key}")
            raise

    def get_signed_url(self, key: str, expires_in: int = 3600) -> str:
        """
        Generiert eine signierte URL für temporären Zugriff.

        Args:
            key: Pfad/Key im Storage
            expires_in: Gültigkeitsdauer in Sekunden (default: 1 Stunde)

        Returns:
            Signierte URL
        """
        clean_key = key.lstrip("/")

        response = self.storage.create_signed_url(
            path=clean_key,
            expires_in=expires_in
        )

        # Supabase gibt je nach Version unterschiedliche Schlüssel zurück
        return response.get('signedURL') or response.get('signed_url') or response.get('signedUrl', '')

    def get_public_url(self, key: str) -> str:
        """
        Generiert eine öffentliche URL (falls Bucket public ist).

        Args:
            key: Pfad/Key im Storage

        Returns:
            Öffentliche URL
        """
        clean_key = key.lstrip("/")
        response = self.storage.get_public_url(clean_key)
        return response.get('publicURL') or response.get('public_url') or response.get('publicUrl', '')

    def delete(self, key: str) -> bool:
        """
        Löscht eine Datei.

        Args:
            key: Pfad/Key im Storage

        Returns:
            True wenn erfolgreich, False sonst
        """
        clean_key = key.lstrip("/")

        try:
            self.storage.remove([clean_key])
            return True
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
        old_clean = old_key.lstrip("/")
        new_clean = new_key.lstrip("/")

        try:
            self.storage.move(old_clean, new_clean)
            return True
        except Exception:
            # Fallback: Kopieren + Löschen
            try:
                data = self.get_bytes(old_key)
                content_type = mimetypes.guess_type(new_key)[0] or 'application/octet-stream'
                self.put_bytes(new_key, data, content_type)
                self.delete(old_key)
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
        try:
            # Versuche Metadaten abzurufen
            self.get_bytes(key)
            return True
        except FileNotFoundError:
            return False
        except Exception:
            return False

    def list_keys(self, prefix: str) -> List[str]:
        """
        Listet alle Keys mit dem angegebenen Prefix.

        Args:
            prefix: Prefix für die Suche

        Returns:
            Liste von Keys
        """
        clean_prefix = prefix.lstrip("/")

        try:
            response = self.storage.list(clean_prefix)
            keys = []

            for item in response:
                if item.get('name'):
                    full_key = f"{clean_prefix}/{item['name']}".lstrip("/")
                    keys.append(full_key)

            return keys
        except Exception:
            return []

    def get_metadata(self, key: str) -> dict:
        """
        Gibt Metadaten einer Datei zurück.

        Args:
            key: Pfad/Key im Storage

        Returns:
            Dict mit Metadaten (size, content_type, etc.)
        """
        clean_key = key.lstrip("/")

        try:
            # Supabase API für Metadaten
            response = self.storage.list(clean_key.rsplit('/', 1)[0] if '/' in clean_key else '')

            for item in response:
                if item.get('name') == clean_key.split('/')[-1]:
                    return {
                        'size': item.get('metadata', {}).get('size', 0),
                        'content_type': item.get('metadata', {}).get('mimetype', 'application/octet-stream'),
                        'created_at': item.get('created_at'),
                        'updated_at': item.get('updated_at')
                    }

            return {}
        except Exception:
            return {}
