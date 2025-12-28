# Schadenmanager - Technische Dokumentation

## Version 1.0 | Stand: Dezember 2025

---

## 1. Systemübersicht

Der **Schadenmanager** ist eine webbasierte Anwendung zur Verwaltung von Verkehrsunfallschäden. Die Anwendung ermöglicht die Zusammenarbeit zwischen verschiedenen Parteien (Unfallopfer, Anwälte, Werkstätten, Gutachter, Versicherungen) und digitalisiert den gesamten Schadenabwicklungsprozess.

### 1.1 Technologie-Stack

| Komponente | Technologie |
|------------|-------------|
| Frontend | Streamlit (Python) |
| Backend | Python 3.10+ |
| Datenbank | SQLite / PostgreSQL (SQLAlchemy ORM) |
| OCR | Tesseract OCR + PIL |
| Geocoding | OpenStreetMap Nominatim API |
| Authentifizierung | Session-basiert |

### 1.2 Projektstruktur

```
Schadenmanager/
├── src/
│   ├── config/           # Konfiguration & Datenbankverbindung
│   ├── models/           # SQLAlchemy Datenmodelle
│   ├── services/         # Business-Logik & externe Services
│   └── ui/
│       ├── pages/        # Streamlit-Seiten
│       └── components/   # Wiederverwendbare UI-Komponenten
├── uploads/              # Hochgeladene Dateien
├── docs/                 # Dokumentation
└── app.py               # Haupteinstiegspunkt
```

---

## 2. Datenbankmodelle

### 2.1 Kernmodelle

#### UnfallProjekt
Zentrales Projekt, das alle Parteien und Daten eines Unfalls verbindet.

```
unfallprojekt
├── id (PK)
├── projektnummer (unique)
├── aktenzeichen
├── datum_unfall, uhrzeit_unfall, ort_unfall
├── beschreibung_unfall
├── schuld_eigen_prozent
├── status (OFFEN, IN_BEARBEITUNG, ABGESCHLOSSEN, STORNIERT)
├── unfallopfer_user_id (FK → user)
├── anwalt_user_id (FK → user)
├── werkstatt_user_id (FK → user)
├── gutachter_user_id (FK → user)
├── kfz_eigen_id (FK → fahrzeug)
├── kfz_gegner_id (FK → fahrzeug)
└── erstellt_am, aktualisiert_am
```

#### UnfallaufnahmeBeteiligter (NEU)
Speichert Beteiligte, die über die mobile Unfallaufnahme erfasst wurden.

```
unfallaufnahme_beteiligter
├── id (PK)
├── unfallprojekt_id (FK → unfallprojekt)
├── rolle (UNFALLGEGNER, ZEUGE, BEIFAHRER, HALTER, etc.)
├── vorname, nachname
├── geburtsdatum
├── telefon, email
├── strasse, hausnummer, plz, ort, land
├── adresse_komplett
├── kennzeichen
├── versicherung, versicherungsnummer
├── ocr_erfasst (Boolean)
├── ocr_konfidenz (Float 0.0-1.0)
├── ocr_rohtext
├── ausweisnummer
└── erstellt_am, aktualisiert_am
```

#### Dokument
Hochgeladene Dokumente mit OCR-Verarbeitung.

```
dokument
├── id (PK)
├── unfallprojekt_id (FK)
├── dokument_typ (PERSONALAUSWEIS, FAHRZEUGSCHEIN, GUTACHTEN, etc.)
├── original_dateiname, dateipfad
├── ocr_text
├── ocr_verarbeitet (Boolean)
├── ki_strukturierte_daten (JSON)
├── sichtbarkeit
├── freigabe_erforderlich, freigabe_erteilt
└── erstellt_am
```

#### User
Benutzerkonten mit Rollenzuweisung.

```
user
├── id (PK)
├── email (unique)
├── passwort_hash
├── rolle (ADMIN, ANWALT, UNFALLOPFER, WERKSTATT, GUTACHTER, etc.)
├── organisation_id (FK)
├── vorname, nachname
├── telefon
└── aktiv
```

### 2.2 Weitere Modelle

| Modell | Beschreibung |
|--------|-------------|
| `Fahrzeug` | Fahrzeugdaten (Kennzeichen, Hersteller, Typ) |
| `Organisation` | Kanzleien, Werkstätten, Versicherungen |
| `TimelineMeilenstein` | Prozessfortschritt-Tracking |
| `KostenPosition` | Schadenspositionen |
| `Korrespondenz` | Schriftverkehr |
| `AktenBeteiligter` | Beteiligte aus PDF-Aktenimport |
| `Versicherung` | Versicherungsstammdaten |

---

## 3. Hauptworkflows

### 3.1 Mobile Unfallaufnahme

Die mobile Unfallaufnahme ermöglicht es Unfallopfern, direkt am Unfallort alle relevanten Daten zu erfassen.

#### Ablaufdiagramm

```
┌─────────────────────────────────────────────────────────────┐
│                    UNFALLAUFNAHME WORKFLOW                   │
└─────────────────────────────────────────────────────────────┘

SCHRITT 1: Wann & Wo
├─ Unfalldatum und -uhrzeit erfassen
├─ GPS-Standort ermitteln (automatisch)
├─ GPS → Adresse konvertieren (Reverse Geocoding)
└─ Wetterbedingungen auswählen

         ↓

SCHRITT 2: Bilder vom Unfall
├─ Fotos der Unfallstelle aufnehmen
├─ Fahrzeugschäden dokumentieren
└─ Übersichtsfotos erstellen

         ↓

SCHRITT 3: Beteiligte erfassen
├─ Personalausweis fotografieren
├─ OCR-Texterkennung durchführen
│   └─ Extrahiert: Name, Adresse, Geburtsdatum
├─ Daten in Formularfelder übertragen
├─ Manuelle Korrektur/Ergänzung möglich
└─ Weitere Beteiligte hinzufügen

         ↓

SCHRITT 4: Kennzeichen
├─ Kennzeichen fotografieren
└─ Automatische Texterkennung

         ↓

SCHRITT 5: Abschluss
├─ Zusammenfassung anzeigen
├─ Bestätigung durch Benutzer
└─ Speicherung in Datenbank
    ├─ UnfallProjekt erstellen
    ├─ Beteiligte als UnfallaufnahmeBeteiligter speichern
    └─ Fotos als Dokumente speichern
```

#### OCR-Datenfluss (Personalausweis)

```
Foto-Upload
    ↓
PIL Bildvorverarbeitung
├─ Graustufen-Konvertierung
└─ Kontrast-Erhöhung (+50%)
    ↓
Tesseract OCR (lang='deu')
├─ Originalfoto → Text
└─ Verbessertes Foto → Text
    ↓
Textkombination
    ↓
Regex-Parsing
├─ NACHNAME → r'(?:NACHNAME|FAMILIENNAME)[:\s]+([A-ZÄÖÜa-zäöüß\-]+)'
├─ VORNAME → r'(?:VORNAME|VORNAMEN)[:\s]+([A-ZÄÖÜa-zäöüß\-]+)'
├─ GEBURTSDATUM → r'\d{2}[.\-/]\d{2}[.\-/]\d{4}'
├─ STRASSE → r'([A-ZÄÖÜa-zäöüß\.\-]+(?:str(?:aße|\.)?|weg|allee|platz))\s*(\d+\s*[a-zA-Z]?)'
├─ PLZ/ORT → r'(\d{5})\s+([A-ZÄÖÜa-zäöüß\s\-]+)'
└─ AUSWEISNUMMER → r'[A-Z0-9]{9,10}'
    ↓
Session State
├─ st.session_state['neuer_vorname']
├─ st.session_state['neuer_name']
├─ st.session_state['neue_strasse']
├─ st.session_state['neue_hausnummer']
├─ st.session_state['neue_plz']
└─ st.session_state['neue_ort']
    ↓
Formularfelder (vorausgefüllt)
    ↓
Benutzer-Korrektur (optional)
    ↓
"Beteiligten hinzufügen"
    ↓
st.session_state.unfallaufnahme['beteiligte']
├─ ocr_erfasst: True/False
└─ Alle Personendaten
    ↓
"Unfallaufnahme absenden"
    ↓
_speichere_unfallaufnahme()
├─ UnfallProjekt erstellen
├─ UnfallaufnahmeBeteiligter für jeden Beteiligten
└─ Dokumente für alle Fotos
    ↓
Datenbank (persistiert)
```

### 3.2 Reverse Geocoding (GPS → Adresse)

```python
# Automatische Adressermittlung bei GPS-Eingabe
def _reverse_geocode(lat: float, lng: float) -> dict:
    """
    Konvertiert GPS-Koordinaten in Postadresse.
    Verwendet OpenStreetMap Nominatim API.

    Returns:
        {
            'strasse': 'Musterstraße',
            'hausnummer': '42',
            'plz': '12345',
            'ort': 'Berlin',
            'display_name': 'Musterstraße 42, 12345 Berlin, Deutschland'
        }
    """
```

**Ablauf:**
1. Benutzer gibt GPS-Koordinaten ein (manuell oder per Geolocation API)
2. System erkennt neue Koordinaten
3. Automatischer API-Aufruf an Nominatim
4. Adressfelder werden ausgefüllt
5. Benutzer kann korrigieren

### 3.3 Zentralruf-Integration (nur Anwälte)

Die Zentralruf-Integration ermöglicht Anwälten, die gegnerische Versicherung über den Zentralruf der Autoversicherer zu ermitteln.

```
┌─────────────────────────────────────────────────────────────┐
│              ZENTRALRUF WORKFLOW (Anwälte)                  │
└─────────────────────────────────────────────────────────────┘

1. Anwalt öffnet Tab "🔍 Zentralruf" in Versicherungsverwaltung
2. System lädt Projektdaten automatisch:
   ├─ Kennzeichen des Gegners
   ├─ Unfalldatum
   └─ Unfallort
3. Anwalt kopiert Daten
4. Klick auf "🌐 Zentralruf.de öffnen"
5. Manuelles Einfügen auf zentralruf.de
6. Ergebnis (Versicherung, Schadennummer) zurück eintragen
7. Speichern im Projekt
```

---

## 4. Rollenbasierte Zugriffskontrolle

### 4.1 Verfügbare Rollen

| Rolle | Kürzel | Beschreibung |
|-------|--------|-------------|
| Administrator | ADMIN | Vollzugriff |
| Anwalt | ANWALT | Fallführung, Zentralruf |
| Unfallopfer | UNFALLOPFER | Eigene Daten, Unfallaufnahme |
| Werkstatt | WERKSTATT | Reparaturdaten |
| Gutachter | GUTACHTER | Gutachten erstellen |
| Versicherung | VERSICHERUNG | Schadensbearbeitung |
| Ersatzwagenanbieter | ERSATZWAGEN | Mietfahrzeuge |

### 4.2 Funktionszuordnung

```
┌────────────────────────────────────────────────────────────────────────────┐
│                        FUNKTIONEN NACH ROLLEN                               │
├─────────────────────────────┬──────────────────────────────────────────────┤
│ Funktion                    │ ADMIN  ANWALT  OPFER  WERKS  GUTAC  VERS    │
├─────────────────────────────┼──────────────────────────────────────────────┤
│ Dashboard                   │   ✓      ✓       ✓      ✓      ✓      ✓     │
│ Unfallaufnahme vor Ort      │   ✓      -       ✓      -      -      -     │
│ Projekte verwalten          │   ✓      ✓       -      -      -      -     │
│ Zentralruf                  │   ✓      ✓       -      -      -      -     │
│ Dokumente hochladen         │   ✓      ✓       ✓      ✓      ✓      -     │
│ Gutachten erstellen         │   ✓      -       -      -      ✓      -     │
│ Kostenrechnung              │   ✓      ✓       -      ✓      -      -     │
│ Benutzerverwaltung          │   ✓      -       -      -      -      -     │
│ Systemeinstellungen         │   ✓      -       -      -      -      -     │
└─────────────────────────────┴──────────────────────────────────────────────┘
```

---

## 5. API-Schnittstellen

### 5.1 Externe APIs

| API | Zweck | Endpunkt |
|-----|-------|----------|
| OpenStreetMap Nominatim | Reverse Geocoding | `nominatim.openstreetmap.org/reverse` |
| Zentralruf | Versicherungsermittlung | `www.zentralruf.de` (manuell) |

### 5.2 Interne Services

```python
# OCR Service
from src.services.ocr import get_ocr_service, get_ki_extraktor

ocr_service = get_ocr_service()
result = ocr_service.verarbeite_bild(image_file)

# Authentifizierung
from src.services.auth import get_current_user_id, get_current_user_role

user_id = get_current_user_id()
rolle = get_current_user_role()

# Datenbank
from src.config.database import get_session

with get_session() as db:
    projekt = db.query(UnfallProjekt).filter_by(id=projekt_id).first()
```

---

## 6. Dateispeicherung

### 6.1 Upload-Verzeichnisstruktur

```
uploads/
├── dokumente/
│   └── {projekt_id}/
│       ├── personalausweis_abc123.jpg
│       ├── gutachten_def456.pdf
│       └── ...
├── unfallaufnahme/
│   └── {projekt_id}/
│       ├── unfallstelle_ghi789.jpg
│       ├── kennzeichen_1_jkl012.jpg
│       └── ...
└── temp/
    └── {session_id}/
        └── ...
```

### 6.2 Unterstützte Dateiformate

| Kategorie | Formate |
|-----------|---------|
| Bilder | JPG, JPEG, PNG, GIF, BMP, TIFF |
| Dokumente | PDF |
| OCR-fähig | JPG, PNG, PDF (mit Tesseract) |

---

## 7. Session Management

### 7.1 Streamlit Session State

```python
# Unfallaufnahme Session State Struktur
st.session_state.unfallaufnahme = {
    'schritt': 1,                    # Aktueller Schritt (1-5)
    'datum': date.today(),           # Unfalldatum
    'uhrzeit': datetime.now().time(), # Unfallzeit
    'ort': '',                       # Freitext-Ort
    'ort_details': {                 # Strukturierte Adresse
        'strasse': '',
        'hausnummer': '',
        'plz': '',
        'ort': '',
        'land': 'Deutschland'
    },
    'gps_koordinaten': '',           # GPS-String
    'wetter': None,                  # Wetterbedingung
    'fotos': {},                     # Hochgeladene Fotos
    'beteiligte': [],                # Liste der Beteiligten
    'kennzeichen_fotos': [],         # Kennzeichenfotos
    'notizen': '',                   # Zusätzliche Notizen
    'ocr_ergebnis': {},              # Aktuelle OCR-Ergebnisse
    'geplante_beteiligte': [],       # Geplante Beteiligtenrollen
    'abgesendet': False              # Erfolgreich abgesendet?
}
```

---

## 8. Fehlerbehandlung

### 8.1 OCR-Fehler

| Fehler | Ursache | Lösung |
|--------|---------|--------|
| Tesseract nicht gefunden | Nicht installiert | `apt-get install tesseract-ocr tesseract-ocr-deu` |
| Leerer OCR-Text | Schlechte Bildqualität | Bessere Beleuchtung, schärferes Foto |
| Falsche Zeichen | OCR-Ungenauigkeit | Manuelle Korrektur im Formular |

### 8.2 Datenbank-Fehler

```python
try:
    with get_session() as db:
        # Datenbankoperationen
        db.commit()
except Exception as e:
    # Automatischer Rollback durch Context Manager
    st.error(f"Datenbankfehler: {e}")
```

---

## 9. Sicherheit

### 9.1 Authentifizierung

- Session-basierte Authentifizierung
- Passwort-Hashing (bcrypt)
- Rollenbasierte Zugriffskontrolle

### 9.2 Datenschutz (DSGVO)

- Protokollierung aller Datenzugriffe (`DSGVOProtokoll`)
- Löschfunktion für personenbezogene Daten
- Einwilligungsmanagement

### 9.3 Dateisicherheit

- Validierung von Dateitypen
- Größenbeschränkung für Uploads
- Sichere Dateipfade (keine Path Traversal)

---

## 10. Deployment

### 10.1 Voraussetzungen

```bash
# System-Pakete
apt-get install tesseract-ocr tesseract-ocr-deu

# Python-Abhängigkeiten
pip install -r requirements.txt
```

### 10.2 Konfiguration

```python
# src/config/settings.py
DATABASE_URL = "sqlite:///schadenmanager.db"  # oder PostgreSQL
DEBUG = False
SECRET_KEY = "..."
```

### 10.3 Start

```bash
streamlit run app.py --server.port 8501
```

---

## 11. Wartung & Monitoring

### 11.1 Logs

- Fehler werden in stdout/stderr ausgegeben
- Audit-Log in Datenbank (`AuditLog` Tabelle)

### 11.2 Datenbank-Backup

```bash
# SQLite
cp schadenmanager.db backup_$(date +%Y%m%d).db

# PostgreSQL
pg_dump schadenmanager > backup_$(date +%Y%m%d).sql
```

---

## 12. Bekannte Einschränkungen

1. **OCR-Genauigkeit**: Abhängig von Bildqualität (70-95% Genauigkeit)
2. **Zentralruf**: Keine API-Integration, manuelles Kopieren erforderlich
3. **Offline-Modus**: Nicht unterstützt (benötigt Internetverbindung)
4. **Browser-Unterstützung**: Moderne Browser (Chrome, Firefox, Safari, Edge)

---

## 13. Changelog

### Version 1.0 (Dezember 2025)

- **NEU**: `UnfallaufnahmeBeteiligter` Model für persistente Speicherung
- **FIX**: OCR-Daten werden jetzt korrekt in Datenbank gespeichert
- **FIX**: `_speichere_unfallaufnahme()` vollständig implementiert
- **NEU**: Automatische GPS → Adresse Konvertierung
- **NEU**: Zentralruf-Integration für Anwälte
- **GEÄNDERT**: Button "Bilder" → "Bilder vom Unfall"

---

## Anhang A: Datenbankschema (ER-Diagramm)

```
┌─────────────────┐     ┌─────────────────────────────┐     ┌─────────────┐
│   Organisation  │     │       UnfallProjekt          │     │    User     │
├─────────────────┤     ├─────────────────────────────┤     ├─────────────┤
│ id              │◄────┤ anlegende_organisation_id   │     │ id          │
│ name            │     │ id                          │────►│ email       │
│ typ             │     │ projektnummer               │     │ rolle       │
└─────────────────┘     │ datum_unfall                │     │ passwort    │
                        │ ort_unfall                  │     └─────────────┘
                        │ status                      │            │
                        │ unfallopfer_user_id ────────┼────────────┘
                        │ anwalt_user_id              │
                        └─────────────────────────────┘
                                    │
                   ┌────────────────┼────────────────┐
                   │                │                │
                   ▼                ▼                ▼
        ┌──────────────────┐  ┌───────────┐  ┌────────────────────────────┐
        │     Dokument     │  │ Fahrzeug  │  │ UnfallaufnahmeBeteiligter  │
        ├──────────────────┤  ├───────────┤  ├────────────────────────────┤
        │ id               │  │ id        │  │ id                         │
        │ unfallprojekt_id │  │ kennz.    │  │ unfallprojekt_id           │
        │ dokument_typ     │  │ marke     │  │ rolle                      │
        │ ocr_text         │  │ modell    │  │ vorname, nachname          │
        │ dateipfad        │  └───────────┘  │ strasse, plz, ort          │
        └──────────────────┘                 │ ocr_erfasst                │
                                             └────────────────────────────┘
```

---

*Dokumentation erstellt: 28.12.2025*
*Autor: Claude Code Assistant*
