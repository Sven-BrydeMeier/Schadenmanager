# Schadenmanager - Verkehrsunfall-Abwicklungs-App

## Projektübersicht

Der Schadenmanager ist eine professionelle, moderne, card-basierte Web-App zur Abwicklung von Verkehrsunfällen. Die App koordiniert nach einem Verkehrsunfall die Kommunikation und den Datenaustausch zwischen allen beteiligten Parteien.

## Tech-Stack

- **Frontend/Backend**: Streamlit
- **Sprache**: Python
- **Datenbank**: SQLAlchemy ORM (PostgreSQL/SQLite)
- **Authentifizierung**: Passwort + 2FA (TOTP/SMS via Twilio)
- **OCR**: Tesseract
- **KI-Integration**: OpenAI/Anthropic API

## Projektstruktur

```
Schadenmanager/
├── app.py                      # Hauptanwendung
├── requirements.txt            # Python-Abhängigkeiten
├── .env.example               # Umgebungsvariablen-Vorlage
├── config/
│   └── meilensteine.json      # Meilenstein-Konfiguration
└── src/
    ├── config/
    │   ├── settings.py        # Anwendungskonfiguration
    │   └── database.py        # Datenbank-Setup
    ├── models/
    │   ├── enums.py           # Enums (Rollen, Status, etc.)
    │   ├── organisation.py    # Organisation-Modell
    │   ├── user.py            # Benutzer-Modell
    │   ├── fahrzeug.py        # Fahrzeug-Modell
    │   ├── unfallprojekt.py   # UnfallProjekt-Modell
    │   ├── dokument.py        # Dokument-Modell
    │   ├── timeline.py        # Timeline-Meilensteine
    │   ├── kosten.py          # Kostenpositionen
    │   ├── ersatzwagen.py     # Ersatzwagen-Anbieter/Angebote
    │   ├── gebuehren.py       # RA-Gebührenberechnung
    │   └── korrespondenz.py   # Korrespondenz
    ├── services/
    │   ├── auth.py            # Authentifizierung + 2FA
    │   ├── meilenstein_engine.py  # Meilenstein-Regel-Engine
    │   ├── ocr.py             # OCR + KI-Datenextraktion
    │   └── ki_textgenerator.py    # KI-Textgenerierung
    └── ui/
        ├── styles.py          # CSS-Styles
        ├── components.py      # UI-Komponenten
        └── pages/
            ├── login.py       # Login/Registrierung
            ├── dashboard.py   # Rollen-Dashboards
            ├── projekte.py    # Projekt-Verwaltung
            ├── dokumente.py   # Dokumenten-Upload
            ├── kosten.py      # Kostenpositionen
            ├── ersatzwagen.py # Ersatzwagen-Modul
            ├── gebuehren.py   # RA-Gebühren
            └── korrespondenz.py # Korrespondenz + KI
```

## Rollen

- **WERKSTATT**: Reparaturen, Ersatzwagen
- **GUTACHTER**: Gutachten erstellen/hochladen
- **VERSICHERUNG_EIGEN**: Eigene Versicherung des Unfallopfers
- **VERSICHERUNG_GEGNER**: Gegnerische Haftpflichtversicherung
- **ANWALT**: Rechtliche Vertretung, Korrespondenz, Gebühren
- **UNFALLOPFER**: Mandant, sieht vereinfachte Übersicht
- **ADMIN**: Voller Zugriff, Verwaltung

## Hauptfunktionen

1. **Projektanlage & Onboarding** - Projekt anlegen, Einladungslinks für Beteiligte
2. **OCR & KI-Datenerfassung** - Automatische Extraktion aus Dokumenten
3. **Ersatzwagen-Modul** - Auswahl und Verwaltung von Mietwagen
4. **Kostenpositionen & Ampelsystem** - ROT/ORANGE/GRÜN Status
5. **Kürzungen & Stellungnahmen** - Reaktion auf Versicherungs-Kürzungen
6. **RA-Gebührenberechnung** - RVG-konforme Berechnung
7. **KI-Textgenerierung** - Anspruchsschreiben, Erwiderungen
8. **Timeline & Meilensteine** - Konfigurierbare Regel-Engine

## Starten der Anwendung

```bash
# Virtuelle Umgebung erstellen
python -m venv venv
source venv/bin/activate  # Linux/Mac
# oder: venv\Scripts\activate  # Windows

# Abhängigkeiten installieren
pip install -r requirements.txt

# .env-Datei erstellen
cp .env.example .env
# .env mit Ihren Werten bearbeiten

# Anwendung starten
streamlit run app.py
```

## Entwicklung

- Die Meilenstein-Regeln sind in `config/meilensteine.json` konfigurierbar
- UI-Styles können in `src/ui/styles.py` angepasst werden
- Neue Dokumenttypen in `src/models/enums.py` hinzufügen
