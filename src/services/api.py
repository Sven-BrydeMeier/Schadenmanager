"""
REST-API Service
API-Endpoints für externe Systeme und Integrationen
"""
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from enum import Enum
import json
import hashlib
import secrets
from functools import wraps
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from src.models.base import Base


class APIKeyStatus(str, Enum):
    """Status eines API-Keys"""
    AKTIV = "AKTIV"
    INAKTIV = "INAKTIV"
    GESPERRT = "GESPERRT"
    ABGELAUFEN = "ABGELAUFEN"


class APIBerechtigung(str, Enum):
    """API-Berechtigungen"""
    LESEN = "LESEN"
    SCHREIBEN = "SCHREIBEN"
    LOESCHEN = "LOESCHEN"
    ADMIN = "ADMIN"


class APIKey(Base):
    """Model für API-Keys"""
    __tablename__ = "api_key"

    id = Column(Integer, primary_key=True)

    # Key
    bezeichnung = Column(String(100), nullable=False)
    api_key = Column(String(64), unique=True, nullable=False)
    api_secret_hash = Column(String(128))  # Gehashtes Secret

    # Berechtigungen
    _berechtigungen = Column("berechtigungen", Text)

    # Einschränkungen
    erlaubte_endpoints = Column(Text)  # JSON-Array oder * für alle
    rate_limit_pro_minute = Column(Integer, default=60)
    rate_limit_pro_tag = Column(Integer, default=10000)

    # Status
    status = Column(String(20), default=APIKeyStatus.AKTIV.value)
    gueltig_bis = Column(DateTime)

    # Nutzung
    letzter_zugriff = Column(DateTime)
    zugriffe_gesamt = Column(Integer, default=0)
    zugriffe_heute = Column(Integer, default=0)
    zugriffe_heute_datum = Column(DateTime)

    # Besitzer
    user_id = Column(Integer, ForeignKey("user.id"))
    erstellt_von_user_id = Column(Integer, ForeignKey("user.id"))

    # Metadaten
    erstellt_am = Column(DateTime, default=datetime.now)

    @property
    def berechtigungen(self) -> List[str]:
        if self._berechtigungen:
            return json.loads(self._berechtigungen)
        return []

    @berechtigungen.setter
    def berechtigungen(self, value: List[str]):
        self._berechtigungen = json.dumps(value)

    @property
    def ist_aktiv(self) -> bool:
        if self.status != APIKeyStatus.AKTIV.value:
            return False
        if self.gueltig_bis and self.gueltig_bis < datetime.now():
            return False
        return True


class APILog(Base):
    """Model für API-Zugriffsprotokolle"""
    __tablename__ = "api_log"

    id = Column(Integer, primary_key=True)

    # Request
    api_key_id = Column(Integer, ForeignKey("api_key.id"))
    endpoint = Column(String(200))
    methode = Column(String(10))  # GET, POST, PUT, DELETE
    request_body = Column(Text)

    # Response
    status_code = Column(Integer)
    response_body = Column(Text)
    fehler_nachricht = Column(Text)

    # Meta
    ip_adresse = Column(String(50))
    user_agent = Column(String(500))
    dauer_ms = Column(Integer)

    # Zeitstempel
    zeitstempel = Column(DateTime, default=datetime.now)


class APIService:
    """Service für API-Verwaltung"""

    def __init__(self, db_session):
        self.db = db_session

    def api_key_erstellen(
        self,
        bezeichnung: str,
        berechtigungen: List[APIBerechtigung],
        user_id: Optional[int] = None,
        gueltig_bis: Optional[datetime] = None,
        rate_limit_pro_minute: int = 60,
        erstellt_von_user_id: Optional[int] = None
    ) -> Dict[str, str]:
        """Erstellt einen neuen API-Key"""
        # Generiere Key und Secret
        api_key = f"sm_{secrets.token_hex(16)}"
        api_secret = secrets.token_hex(32)
        api_secret_hash = hashlib.sha256(api_secret.encode()).hexdigest()

        key = APIKey(
            bezeichnung=bezeichnung,
            api_key=api_key,
            api_secret_hash=api_secret_hash,
            user_id=user_id,
            gueltig_bis=gueltig_bis,
            rate_limit_pro_minute=rate_limit_pro_minute,
            erstellt_von_user_id=erstellt_von_user_id
        )
        key.berechtigungen = [b.value for b in berechtigungen]

        self.db.add(key)
        self.db.flush()

        # Secret nur einmal zurückgeben!
        return {
            'api_key': api_key,
            'api_secret': api_secret,
            'bezeichnung': bezeichnung,
            'hinweis': 'Das API-Secret wird nur einmal angezeigt. Bitte sicher aufbewahren!'
        }

    def api_key_validieren(self, api_key: str, api_secret: str) -> Optional[APIKey]:
        """Validiert einen API-Key"""
        key = self.db.query(APIKey).filter(APIKey.api_key == api_key).first()

        if not key:
            return None

        if not key.ist_aktiv:
            return None

        # Secret prüfen
        secret_hash = hashlib.sha256(api_secret.encode()).hexdigest()
        if secret_hash != key.api_secret_hash:
            return None

        # Zugriff protokollieren
        key.letzter_zugriff = datetime.now()
        key.zugriffe_gesamt += 1

        # Tägliche Zugriffe
        heute = date.today()
        if key.zugriffe_heute_datum and key.zugriffe_heute_datum.date() == heute:
            key.zugriffe_heute += 1
        else:
            key.zugriffe_heute = 1
            key.zugriffe_heute_datum = datetime.now()

        self.db.flush()

        return key

    def hat_berechtigung(self, key: APIKey, berechtigung: APIBerechtigung) -> bool:
        """Prüft ob ein Key eine bestimmte Berechtigung hat"""
        if APIBerechtigung.ADMIN.value in key.berechtigungen:
            return True
        return berechtigung.value in key.berechtigungen

    def rate_limit_pruefen(self, key: APIKey) -> Dict[str, Any]:
        """Prüft das Rate-Limit"""
        heute = date.today()

        # Tägliches Limit
        if key.zugriffe_heute_datum and key.zugriffe_heute_datum.date() == heute:
            if key.zugriffe_heute >= key.rate_limit_pro_tag:
                return {
                    'erlaubt': False,
                    'grund': 'Tägliches Limit erreicht',
                    'limit': key.rate_limit_pro_tag,
                    'aktuell': key.zugriffe_heute
                }

        return {
            'erlaubt': True,
            'verbleibend_heute': key.rate_limit_pro_tag - (key.zugriffe_heute or 0)
        }

    def api_key_deaktivieren(self, key_id: int) -> bool:
        """Deaktiviert einen API-Key"""
        key = self.db.query(APIKey).get(key_id)
        if key:
            key.status = APIKeyStatus.INAKTIV.value
            self.db.flush()
            return True
        return False

    def api_zugriff_protokollieren(
        self,
        api_key_id: int,
        endpoint: str,
        methode: str,
        status_code: int,
        request_body: Optional[str] = None,
        response_body: Optional[str] = None,
        fehler: Optional[str] = None,
        ip_adresse: Optional[str] = None,
        dauer_ms: Optional[int] = None
    ) -> APILog:
        """Protokolliert einen API-Zugriff"""
        log = APILog(
            api_key_id=api_key_id,
            endpoint=endpoint,
            methode=methode,
            status_code=status_code,
            request_body=request_body[:5000] if request_body else None,
            response_body=response_body[:5000] if response_body else None,
            fehler_nachricht=fehler,
            ip_adresse=ip_adresse,
            dauer_ms=dauer_ms
        )

        self.db.add(log)
        self.db.flush()

        return log

    def alle_api_keys(self, user_id: Optional[int] = None) -> List[APIKey]:
        """Holt alle API-Keys"""
        query = self.db.query(APIKey)

        if user_id:
            query = query.filter(APIKey.user_id == user_id)

        return query.order_by(APIKey.erstellt_am.desc()).all()

    def api_logs(
        self,
        api_key_id: Optional[int] = None,
        limit: int = 100
    ) -> List[APILog]:
        """Holt API-Logs"""
        query = self.db.query(APILog)

        if api_key_id:
            query = query.filter(APILog.api_key_id == api_key_id)

        return query.order_by(APILog.zeitstempel.desc()).limit(limit).all()

    def api_statistik(self, api_key_id: Optional[int] = None) -> Dict[str, Any]:
        """Erstellt API-Statistik"""
        query = self.db.query(APILog)

        if api_key_id:
            query = query.filter(APILog.api_key_id == api_key_id)

        logs = query.all()

        return {
            'gesamt_aufrufe': len(logs),
            'erfolgreiche_aufrufe': len([l for l in logs if 200 <= (l.status_code or 0) < 300]),
            'fehlerhafte_aufrufe': len([l for l in logs if (l.status_code or 0) >= 400]),
            'durchschnittliche_dauer_ms': sum(l.dauer_ms or 0 for l in logs) / len(logs) if logs else 0,
            'nach_endpoint': self._zaehle_nach_endpoint(logs),
            'nach_methode': self._zaehle_nach_methode(logs)
        }

    def _zaehle_nach_endpoint(self, logs: List[APILog]) -> Dict[str, int]:
        """Zählt Aufrufe nach Endpoint"""
        zaehler = {}
        for log in logs:
            ep = log.endpoint or 'unbekannt'
            zaehler[ep] = zaehler.get(ep, 0) + 1
        return dict(sorted(zaehler.items(), key=lambda x: x[1], reverse=True)[:10])

    def _zaehle_nach_methode(self, logs: List[APILog]) -> Dict[str, int]:
        """Zählt Aufrufe nach HTTP-Methode"""
        zaehler = {}
        for log in logs:
            m = log.methode or 'unbekannt'
            zaehler[m] = zaehler.get(m, 0) + 1
        return zaehler


# API-Endpoint-Definitionen für Dokumentation
API_ENDPOINTS = {
    'projekte': {
        'GET /api/v1/projekte': 'Liste aller Projekte',
        'GET /api/v1/projekte/{id}': 'Einzelnes Projekt',
        'POST /api/v1/projekte': 'Neues Projekt erstellen',
        'PUT /api/v1/projekte/{id}': 'Projekt aktualisieren',
        'DELETE /api/v1/projekte/{id}': 'Projekt löschen'
    },
    'dokumente': {
        'GET /api/v1/projekte/{id}/dokumente': 'Dokumente eines Projekts',
        'POST /api/v1/projekte/{id}/dokumente': 'Dokument hochladen',
        'GET /api/v1/dokumente/{id}': 'Dokument herunterladen',
        'DELETE /api/v1/dokumente/{id}': 'Dokument löschen'
    },
    'kosten': {
        'GET /api/v1/projekte/{id}/kosten': 'Kosten eines Projekts',
        'POST /api/v1/projekte/{id}/kosten': 'Kosten hinzufügen',
        'PUT /api/v1/kosten/{id}': 'Kosten aktualisieren',
        'DELETE /api/v1/kosten/{id}': 'Kosten löschen'
    },
    'beteiligte': {
        'GET /api/v1/projekte/{id}/beteiligte': 'Beteiligte eines Projekts',
        'POST /api/v1/projekte/{id}/beteiligte': 'Beteiligten hinzufügen',
        'PUT /api/v1/beteiligte/{id}': 'Beteiligten aktualisieren'
    },
    'fristen': {
        'GET /api/v1/projekte/{id}/fristen': 'Fristen eines Projekts',
        'GET /api/v1/fristen/kritisch': 'Alle kritischen Fristen',
        'POST /api/v1/projekte/{id}/fristen': 'Frist erstellen'
    },
    'statistik': {
        'GET /api/v1/statistik/dashboard': 'Dashboard-Statistiken',
        'GET /api/v1/statistik/kosten': 'Kostenstatistik',
        'GET /api/v1/statistik/projekte': 'Projektstatistik'
    }
}


def generiere_api_dokumentation() -> str:
    """Generiert die API-Dokumentation als Markdown"""
    doc = """# Schadenmanager REST-API

## Authentifizierung

Alle API-Anfragen müssen die folgenden Header enthalten:

```
X-API-Key: <ihr_api_key>
X-API-Secret: <ihr_api_secret>
```

## Rate Limiting

- Standard: 60 Anfragen pro Minute
- Maximum: 10.000 Anfragen pro Tag

## Endpunkte

"""
    for kategorie, endpoints in API_ENDPOINTS.items():
        doc += f"### {kategorie.title()}\n\n"
        for endpoint, beschreibung in endpoints.items():
            doc += f"- `{endpoint}` - {beschreibung}\n"
        doc += "\n"

    doc += """
## Antwortformat

Alle Antworten sind im JSON-Format:

```json
{
    "success": true,
    "data": { ... },
    "meta": {
        "timestamp": "2024-01-15T10:30:00",
        "request_id": "abc123"
    }
}
```

## Fehlerbehandlung

Bei Fehlern:

```json
{
    "success": false,
    "error": {
        "code": "NOT_FOUND",
        "message": "Projekt nicht gefunden"
    }
}
```

## Status-Codes

- `200` - Erfolg
- `201` - Erstellt
- `400` - Ungültige Anfrage
- `401` - Nicht authentifiziert
- `403` - Keine Berechtigung
- `404` - Nicht gefunden
- `429` - Rate Limit erreicht
- `500` - Server-Fehler
"""
    return doc
