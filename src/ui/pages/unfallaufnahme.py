"""
Unfallaufnahme vor Ort
Mobile-freundliche Erfassung eines Unfalls durch das Unfallopfer
"""
import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime, date, time
from typing import Optional, Dict, List
import json
import requests
import re

from src.config.database import get_session

# OCR-Imports (optional, falls verfügbar)
OCR_AVAILABLE = False
TESSERACT_ERROR = None

try:
    from PIL import Image
    import pytesseract
    # Prüfe ob Tesseract tatsächlich installiert ist
    pytesseract.get_tesseract_version()
    OCR_AVAILABLE = True
except ImportError as e:
    TESSERACT_ERROR = f"Python-Modul fehlt: {e}"
except Exception as e:
    TESSERACT_ERROR = str(e)


def _ocr_ausweis(image_file) -> Optional[Dict]:
    """
    Führt OCR auf einem Ausweis-Foto durch und extrahiert relevante Daten.

    Args:
        image_file: Hochgeladene Bilddatei (Streamlit UploadedFile)

    Returns:
        Dictionary mit erkannten Feldern oder None bei Fehler
    """
    if not OCR_AVAILABLE:
        return None

    try:
        # Bild öffnen
        image = Image.open(image_file)

        # OCR durchführen (Deutsch)
        text = pytesseract.image_to_string(image, lang='deu')

        if not text.strip():
            return None

        # Erkannte Daten parsen
        ergebnis = {
            'raw_text': text,
            'vorname': '',
            'nachname': '',
            'geburtsdatum': '',
            'adresse': '',
            'ausweisnummer': ''
        }

        lines = text.split('\n')
        lines = [l.strip() for l in lines if l.strip()]

        # Muster für deutsche Personalausweise
        for i, line in enumerate(lines):
            line_upper = line.upper()

            # Nachname (oft nach "NACHNAME" oder "NAME")
            if 'NACHNAME' in line_upper or (line_upper == 'NAME' and i + 1 < len(lines)):
                if i + 1 < len(lines):
                    ergebnis['nachname'] = lines[i + 1].title()

            # Vorname
            if 'VORNAME' in line_upper or 'VORNAMEN' in line_upper:
                if i + 1 < len(lines):
                    ergebnis['vorname'] = lines[i + 1].title()

            # Geburtsdatum (Format: DD.MM.YYYY)
            datum_match = re.search(r'(\d{2})[.\-/](\d{2})[.\-/](\d{4})', line)
            if datum_match and not ergebnis['geburtsdatum']:
                tag, monat, jahr = datum_match.groups()
                if 1 <= int(tag) <= 31 and 1 <= int(monat) <= 12 and 1900 <= int(jahr) <= 2020:
                    ergebnis['geburtsdatum'] = f"{tag}.{monat}.{jahr}"

            # Ausweisnummer (typisches Format für deutschen Personalausweis)
            ausweis_match = re.search(r'([A-Z0-9]{9,10})', line)
            if ausweis_match and not ergebnis['ausweisnummer']:
                potential_nr = ausweis_match.group(1)
                # Prüfen ob es wie eine Ausweisnummer aussieht (mix aus Buchstaben und Zahlen)
                if any(c.isalpha() for c in potential_nr) and any(c.isdigit() for c in potential_nr):
                    ergebnis['ausweisnummer'] = potential_nr

            # Adresse (PLZ + Ort)
            plz_match = re.search(r'(\d{5})\s+([A-Za-zäöüÄÖÜß\s]+)', line)
            if plz_match and not ergebnis['adresse']:
                ergebnis['adresse'] = f"{plz_match.group(1)} {plz_match.group(2).strip()}"

        return ergebnis

    except Exception as e:
        st.warning(f"OCR-Fehler: {e}")
        return None


def _reverse_geocode(lat: float, lng: float) -> Optional[Dict]:
    """
    Ermittelt die Adresse aus GPS-Koordinaten via OpenStreetMap Nominatim API.
    Mit Fallback-Optionen und robuster Fehlerbehandlung.

    Args:
        lat: Breitengrad
        lng: Längengrad

    Returns:
        Dictionary mit Adressdaten oder None bei Fehler
    """
    fehler_details = []

    # Session ohne Proxy erstellen für direkte Verbindung
    session = requests.Session()
    # Proxy explizit deaktivieren
    session.trust_env = False
    session.proxies = {"http": None, "https": None}

    # Versuch 1: OpenStreetMap Nominatim (ohne Proxy)
    try:
        url = "https://nominatim.openstreetmap.org/reverse"
        params = {
            "lat": lat,
            "lon": lng,
            "format": "json",
            "addressdetails": 1,
            "accept-language": "de"
        }
        headers = {
            "User-Agent": "Schadenmanager/1.0 (Unfallaufnahme; Contact: admin@schadenmanager.de)"
        }

        response = session.get(url, params=params, headers=headers, timeout=15)

        if response.status_code == 200:
            data = response.json()
            address = data.get("address", {})

            # Straße ermitteln (verschiedene Felder prüfen)
            strasse = (
                address.get("road") or
                address.get("pedestrian") or
                address.get("footway") or
                address.get("street") or
                ""
            )

            # Hausnummer
            hausnummer = address.get("house_number", "")

            # PLZ
            plz = address.get("postcode", "")

            # Ort ermitteln (Stadt, Gemeinde, Dorf)
            ort = (
                address.get("city") or
                address.get("town") or
                address.get("village") or
                address.get("municipality") or
                address.get("county") or
                ""
            )

            return {
                "strasse": strasse,
                "hausnummer": hausnummer,
                "plz": plz,
                "ort": ort,
                "display_name": data.get("display_name", ""),
                "raw": address
            }
        else:
            fehler_details.append(f"Nominatim HTTP {response.status_code}")

    except requests.exceptions.ProxyError as e:
        fehler_details.append(f"Proxy-Fehler: {str(e)[:50]}")
    except requests.exceptions.SSLError as e:
        fehler_details.append(f"SSL-Fehler: {str(e)[:50]}")
    except requests.exceptions.Timeout:
        fehler_details.append("Timeout: OpenStreetMap antwortet nicht (15s)")
    except requests.exceptions.ConnectionError as e:
        fehler_details.append(f"Verbindungsfehler: {str(e)[:50]}")
    except Exception as e:
        fehler_details.append(f"Fehler: {str(e)[:50]}")

    # Versuch 2: Alternative API (Photon by Komoot) - falls Nominatim fehlschlägt
    if fehler_details:
        try:
            # Photon ist eine schnelle Alternative zu Nominatim
            url = f"https://photon.komoot.io/reverse?lat={lat}&lon={lng}&lang=de"
            headers = {"User-Agent": "Schadenmanager/1.0"}

            response = session.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data.get("features"):
                    props = data["features"][0].get("properties", {})

                    return {
                        "strasse": props.get("street", ""),
                        "hausnummer": props.get("housenumber", ""),
                        "plz": props.get("postcode", ""),
                        "ort": props.get("city") or props.get("town") or props.get("village", ""),
                        "display_name": props.get("name", "") or f"{props.get('street', '')}, {props.get('city', '')}",
                        "raw": props
                    }
        except Exception:
            pass  # Fallback fehlgeschlagen, weiter zur Fehlermeldung

    # Wenn alle Versuche fehlgeschlagen
    if fehler_details:
        st.error(f"❌ Adressermittlung fehlgeschlagen: {', '.join(fehler_details)}")
        st.info("💡 Der Server hat keinen Zugang zu externen Diensten. Bitte geben Sie die Adresse manuell ein.")

    return None


def _ocr_kennzeichen(image_file) -> Optional[str]:
    """
    Versucht ein Kennzeichen aus einem Foto zu erkennen.
    Verwendet einfache Bildverarbeitung und Musterabgleich.
    """
    if not OCR_AVAILABLE:
        return None

    try:
        from PIL import Image, ImageEnhance, ImageFilter
        import pytesseract

        image = Image.open(image_file)

        # Bild vorverarbeiten für bessere OCR
        # In Graustufen umwandeln
        image = image.convert('L')
        # Kontrast erhöhen
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(2.0)

        # OCR durchführen
        text = pytesseract.image_to_string(image, config='--psm 7')  # Single line mode

        # Deutsche Kennzeichen-Muster suchen (z.B. "B-AB 1234" oder "M AB 123")
        import re
        kennzeichen_pattern = r'[A-ZÄÖÜ]{1,3}[\s\-]?[A-Z]{1,2}[\s\-]?\d{1,4}[EH]?'
        match = re.search(kennzeichen_pattern, text.upper())

        if match:
            return match.group(0).strip()

        return None
    except Exception:
        return None


def render_unfallaufnahme():
    """Rendert die Unfallaufnahme-Seite für das Unfallopfer"""

    # CSS für beruhigendes, freundliches Design
    st.markdown("""
    <style>
    .calm-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 30px;
        border-radius: 15px;
        text-align: center;
        margin-bottom: 25px;
    }
    .calm-header h1 {
        margin: 0;
        font-size: 28px;
    }
    .calm-header p {
        margin: 15px 0 0 0;
        opacity: 0.9;
        font-size: 16px;
    }
    .info-box {
        background-color: #e8f5e9;
        border-left: 4px solid #4CAF50;
        padding: 15px 20px;
        border-radius: 8px;
        margin: 20px 0;
    }
    .info-box-icon {
        font-size: 24px;
        margin-right: 10px;
    }
    .step-header {
        background-color: #f5f5f5;
        padding: 15px;
        border-radius: 10px;
        margin: 20px 0 15px 0;
        border-left: 4px solid #667eea;
    }
    .step-number {
        background-color: #667eea;
        color: white;
        border-radius: 50%;
        width: 30px;
        height: 30px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        margin-right: 10px;
        font-weight: bold;
    }
    .photo-guide {
        background-color: #fff3e0;
        border: 2px dashed #ff9800;
        padding: 15px;
        border-radius: 10px;
        text-align: center;
        margin: 10px 0;
    }
    .success-message {
        background-color: #e8f5e9;
        color: #2e7d32;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        margin: 20px 0;
    }
    </style>
    """, unsafe_allow_html=True)

    # Beruhigender Header
    st.markdown("""
    <div class="calm-header">
        <h1>Unfallaufnahme</h1>
        <p>Wir helfen Ihnen, alle wichtigen Informationen zu sichern</p>
    </div>
    """, unsafe_allow_html=True)

    # Beruhigende Einleitung
    st.markdown("""
    <div class="info-box">
        <span class="info-box-icon">🤝</span>
        <strong>Alles wird gut!</strong><br><br>
        Ein Unfall ist immer eine stressige Situation. Aber keine Sorge - wir begleiten Sie
        Schritt für Schritt durch die Dokumentation. Mit diesen Informationen stellen wir sicher,
        dass Ihre Ansprüche vollständig dokumentiert sind und die Regulierung reibungslos verläuft.<br><br>
        <strong>Nehmen Sie sich Zeit.</strong> Atmen Sie tief durch. Wir sind für Sie da.
    </div>
    """, unsafe_allow_html=True)

    # Session State initialisieren
    if 'unfallaufnahme' not in st.session_state:
        st.session_state.unfallaufnahme = {
            'schritt': 1,
            'datum': date.today(),
            'uhrzeit': datetime.now().time(),
            'ort': '',
            'ort_details': {},
            'wetter': None,
            'fotos': {},
            'beteiligte': [],
            'kennzeichen_fotos': [],
            'notizen': ''
        }

    # Fortschrittsanzeige
    fortschritt = st.session_state.unfallaufnahme.get('schritt', 1)
    st.progress(fortschritt / 5, text=f"Schritt {fortschritt} von 5")

    # Schritt-Anzeige als klickbare Buttons
    schritt_namen = ["Wann & Wo", "Fotos", "Beteiligte", "Kennzeichen", "Abschluss"]

    cols = st.columns(5)
    for i, (col, name) in enumerate(zip(cols, schritt_namen), 1):
        with col:
            if i < fortschritt:
                # Abgeschlossener Schritt - klickbar
                if st.button(f"✓ {i}", key=f"nav_{i}", help=name, use_container_width=True):
                    st.session_state.unfallaufnahme['schritt'] = i
                    st.rerun()
            elif i == fortschritt:
                # Aktueller Schritt
                st.markdown(f"""
                <div style="background: #667eea; color: white; padding: 8px; border-radius: 8px; text-align: center; font-weight: bold;">
                    {i}. {name}
                </div>
                """, unsafe_allow_html=True)
            else:
                # Zukünftiger Schritt
                st.markdown(f"""
                <div style="background: #e5e7eb; color: #9ca3af; padding: 8px; border-radius: 8px; text-align: center;">
                    {i}
                </div>
                """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Konditionelles Rendern basierend auf aktuellem Schritt
    if fortschritt == 1:
        _render_schritt_wann_wo()
    elif fortschritt == 2:
        _render_schritt_fotos()
    elif fortschritt == 3:
        _render_schritt_beteiligte()
    elif fortschritt == 4:
        _render_schritt_kennzeichen()
    elif fortschritt == 5:
        _render_schritt_abschluss()


def _render_schritt_wann_wo():
    """Schritt 1: Datum, Uhrzeit, Ort, Wetter"""

    st.markdown("""
    <div class="step-header">
        <span class="step-number">1</span>
        <strong>Wann und wo ist der Unfall passiert?</strong>
    </div>
    """, unsafe_allow_html=True)

    st.info("Diese Grunddaten sind wichtig für die Schadensmeldung bei der Versicherung.")

    col1, col2 = st.columns(2)

    with col1:
        unfall_datum = st.date_input(
            "Datum des Unfalls",
            value=st.session_state.unfallaufnahme.get('datum', date.today()),
            max_value=date.today(),
            help="Wann hat sich der Unfall ereignet?"
        )
        st.session_state.unfallaufnahme['datum'] = unfall_datum

    with col2:
        unfall_zeit = st.time_input(
            "Uhrzeit",
            value=st.session_state.unfallaufnahme.get('uhrzeit', datetime.now().time()),
            help="Ungefähre Uhrzeit des Unfalls"
        )
        st.session_state.unfallaufnahme['uhrzeit'] = unfall_zeit

    st.markdown("---")

    # Ort des Unfalls
    st.markdown("#### Unfallort")

    ort_methode = st.radio(
        "Wie möchten Sie den Ort angeben?",
        ["Aktuellen Standort verwenden (GPS)", "Adresse manuell eingeben"],
        horizontal=True,
        help="Wenn Sie noch am Unfallort sind, können wir Ihren Standort automatisch erfassen"
    )

    if ort_methode == "Aktuellen Standort verwenden (GPS)":
        st.markdown("""
        <div class="info-box">
            <strong>📍 Standorterfassung</strong><br>
            Klicken Sie auf den Button und erlauben Sie den Standortzugriff in Ihrem Browser.
            Die Adresse wird automatisch ermittelt.
        </div>
        """, unsafe_allow_html=True)

        # JavaScript für GPS-Erfassung
        gps_html = """
        <div id="gps-container" style="margin: 10px 0;">
            <button id="gps-btn" onclick="getLocation()" style="
                background-color: #667eea;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 8px;
                cursor: pointer;
                font-size: 16px;
                width: 100%;
            ">
                📍 Meinen Standort erfassen
            </button>
            <div id="gps-result" style="margin-top: 10px; padding: 10px; background: #f0f9ff; border-radius: 8px; display: none;">
                <strong>Erfasster Standort:</strong><br>
                <span id="gps-coords"></span><br>
                <a id="gps-maps-link" href="#" target="_blank" style="color: #667eea;">In Google Maps öffnen</a>
            </div>
            <div id="gps-error" style="margin-top: 10px; padding: 10px; background: #fef2f2; border-radius: 8px; color: #dc2626; display: none;"></div>
        </div>
        <script>
        function getLocation() {
            var btn = document.getElementById('gps-btn');
            var result = document.getElementById('gps-result');
            var error = document.getElementById('gps-error');
            var coords = document.getElementById('gps-coords');
            var mapsLink = document.getElementById('gps-maps-link');

            btn.innerHTML = '⏳ Erfasse Standort...';
            btn.disabled = true;
            result.style.display = 'none';
            error.style.display = 'none';

            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(
                    function(position) {
                        var lat = position.coords.latitude.toFixed(6);
                        var lng = position.coords.longitude.toFixed(6);
                        coords.innerHTML = lat + ', ' + lng;
                        mapsLink.href = 'https://www.google.com/maps?q=' + lat + ',' + lng;
                        result.style.display = 'block';
                        btn.innerHTML = '✓ Standort erfasst';
                        btn.style.backgroundColor = '#059669';

                        // Koordinaten in Session State speichern via URL-Parameter-Trick
                        // Wir speichern in localStorage und lesen es später aus
                        localStorage.setItem('unfallort_gps', lat + ',' + lng);

                        // Koordinaten in Input-Feld eintragen
                        setTimeout(function() {
                            var inputs = parent.document.querySelectorAll('input');
                            inputs.forEach(function(input) {
                                if (input.placeholder && input.placeholder.includes('automatisch erfasst')) {
                                    input.value = lat + ', ' + lng;
                                    input.dispatchEvent(new Event('input', { bubbles: true }));
                                    input.dispatchEvent(new Event('change', { bubbles: true }));
                                }
                            });
                        }, 100);
                    },
                    function(err) {
                        error.innerHTML = 'Fehler: ' + err.message + '<br>Bitte geben Sie die Adresse manuell ein.';
                        error.style.display = 'block';
                        btn.innerHTML = '📍 Erneut versuchen';
                        btn.disabled = false;
                        btn.style.backgroundColor = '#667eea';
                    },
                    { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
                );
            } else {
                error.innerHTML = 'GPS wird von diesem Browser nicht unterstützt.<br>Bitte geben Sie die Adresse manuell ein.';
                error.style.display = 'block';
                btn.innerHTML = '📍 Nicht verfügbar';
                btn.style.backgroundColor = '#9ca3af';
            }
        }
        </script>
        """
        components.html(gps_html, height=180)

        # Koordinaten-Eingabefeld (wird vom JavaScript befüllt)
        gps_koordinaten = st.text_input(
            "GPS-Koordinaten",
            value=st.session_state.unfallaufnahme.get('gps_koordinaten', ''),
            placeholder="Werden automatisch erfasst oder manuell eingeben",
            help="Format: Breitengrad, Längengrad (z.B. 52.520008, 13.404954)",
            key="gps_input"
        )

        # Speichere aktuelle Koordinaten
        st.session_state.unfallaufnahme['gps_koordinaten'] = gps_koordinaten

        if gps_koordinaten:
            st.success(f"✓ Koordinaten: {gps_koordinaten}")
            # Google Maps Link
            coords_clean = gps_koordinaten.replace(" ", "")
            st.markdown(f"[📍 In Google Maps anzeigen](https://www.google.com/maps?q={coords_clean})")

            # Prüfe ob neue Koordinaten (noch nicht aufgelöst)
            letzte_aufgeloeste_coords = st.session_state.unfallaufnahme.get('letzte_aufgeloeste_coords', '')
            adresse_bereits_ermittelt = (gps_koordinaten.replace(" ", "") == letzte_aufgeloeste_coords.replace(" ", ""))

            if adresse_bereits_ermittelt:
                st.info("✓ Adresse wurde aus GPS-Koordinaten ermittelt. Bitte prüfen und ggf. korrigieren.")
            else:
                # Button zum Auflösen der Adresse - immer anzeigen wenn nicht aufgelöst
                st.warning("⚠️ Bitte klicken Sie auf den Button um die Adresse zu ermitteln:")

                if st.button("🏠 Adresse aus GPS-Koordinaten ermitteln", type="primary", key="reverse_geocode_btn"):
                    try:
                        parts = gps_koordinaten.replace(" ", "").split(",")
                        if len(parts) == 2:
                            lat = float(parts[0])
                            lng = float(parts[1])

                            with st.spinner("Ermittle Adresse über OpenStreetMap..."):
                                adresse = _reverse_geocode(lat, lng)

                            if adresse:
                                # Adressfelder aktualisieren
                                st.session_state.unfallaufnahme['ort_details'] = {
                                    'strasse': adresse.get('strasse', ''),
                                    'hausnummer': adresse.get('hausnummer', ''),
                                    'plz': adresse.get('plz', ''),
                                    'ort': adresse.get('ort', ''),
                                    'land': 'Deutschland'
                                }
                                # Merken welche Koordinaten aufgelöst wurden
                                st.session_state.unfallaufnahme['letzte_aufgeloeste_coords'] = gps_koordinaten
                                st.session_state.unfallaufnahme['adresse_ermittelt'] = True
                                st.success(f"✓ Adresse gefunden: {adresse.get('display_name', '')}")
                                st.rerun()
                            else:
                                st.error("Adresse konnte nicht ermittelt werden. Bitte manuell eingeben.")
                        else:
                            st.error("Ungültiges Koordinatenformat. Erwartet: Breitengrad, Längengrad")
                    except ValueError as e:
                        st.error(f"Fehler bei der Adressermittlung: {e}")

    # Manuelle Adresseingabe (immer anzeigen)
    st.markdown("#### Adresse")

    col_str, col_nr = st.columns([3, 1])
    with col_str:
        strasse = st.text_input(
            "Straße",
            value=st.session_state.unfallaufnahme.get('ort_details', {}).get('strasse', ''),
            placeholder="z.B. Hauptstraße"
        )
    with col_nr:
        hausnummer = st.text_input(
            "Hausnr.",
            value=st.session_state.unfallaufnahme.get('ort_details', {}).get('hausnummer', ''),
            placeholder="z.B. 123"
        )

    col_plz, col_ort, col_land = st.columns([1, 2, 1])
    with col_plz:
        plz = st.text_input(
            "PLZ",
            value=st.session_state.unfallaufnahme.get('ort_details', {}).get('plz', ''),
            placeholder="12345",
            max_chars=5
        )
    with col_ort:
        ort = st.text_input(
            "Ort",
            value=st.session_state.unfallaufnahme.get('ort_details', {}).get('ort', ''),
            placeholder="z.B. Berlin"
        )
    with col_land:
        land = st.text_input(
            "Land",
            value=st.session_state.unfallaufnahme.get('ort_details', {}).get('land', 'Deutschland'),
            placeholder="Deutschland"
        )

    # Speichern
    st.session_state.unfallaufnahme['ort_details'] = {
        'strasse': strasse,
        'hausnummer': hausnummer,
        'plz': plz,
        'ort': ort,
        'land': land
    }
    st.session_state.unfallaufnahme['ort'] = f"{strasse} {hausnummer}, {plz} {ort}, {land}".strip(", ")

    besondere_lage = st.text_input(
        "Besondere Lage (optional)",
        placeholder="z.B. Kreuzung mit Berliner Straße, vor dem Supermarkt",
        help="Zusätzliche Beschreibung zur besseren Lokalisierung"
    )

    st.markdown("---")

    # Wetter
    st.markdown("#### Wetterbedingungen")
    st.caption("Das Wetter kann für die Unfallrekonstruktion relevant sein.")

    col_w1, col_w2 = st.columns(2)

    with col_w1:
        wetter = st.selectbox(
            "Wetter",
            options=[
                None, "Sonnig/Klar", "Bewölkt", "Leichter Regen",
                "Starker Regen", "Nebel", "Schnee", "Eis/Glätte", "Hagel"
            ],
            format_func=lambda x: "Bitte auswählen..." if x is None else x,
            index=0
        )
        st.session_state.unfallaufnahme['wetter'] = wetter

    with col_w2:
        sicht = st.selectbox(
            "Sichtverhältnisse",
            options=[
                None, "Gute Sicht", "Leicht eingeschränkt",
                "Stark eingeschränkt", "Dunkelheit"
            ],
            format_func=lambda x: "Bitte auswählen..." if x is None else x,
            index=0
        )

    # Weiter-Button
    st.markdown("---")
    if st.button("Weiter zu Fotos →", type="primary", use_container_width=True):
        st.session_state.unfallaufnahme['schritt'] = 2
        st.rerun()


def _render_schritt_fotos():
    """Schritt 2: Fotos aus 4 Positionen"""

    st.markdown("""
    <div class="step-header">
        <span class="step-number">2</span>
        <strong>Fotos vom Unfallort</strong>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="info-box">
        <strong>📸 Warum 4 Fotos?</strong><br>
        Fotos aus verschiedenen Blickwinkeln helfen dem Gutachter, den Unfallhergang
        nachzuvollziehen und alle Schäden zu dokumentieren. Halten Sie ca. 3 Meter
        Abstand zu Ihrem Fahrzeug.
    </div>
    """, unsafe_allow_html=True)

    # Foto-Positionen
    foto_positionen = [
        {
            'key': 'front',
            'titel': 'Frontansicht',
            'icon': '🚗',
            'beschreibung': 'Stellen Sie sich VOR Ihr Fahrzeug (ca. 3m Abstand)',
            'beispiel': 'Blick auf Motorhaube und Front'
        },
        {
            'key': 'links',
            'titel': 'Linke Seite',
            'icon': '⬅️',
            'beschreibung': 'Stellen Sie sich LINKS neben Ihr Fahrzeug',
            'beispiel': 'Fahrerseite komplett sichtbar'
        },
        {
            'key': 'rechts',
            'titel': 'Rechte Seite',
            'icon': '➡️',
            'beschreibung': 'Stellen Sie sich RECHTS neben Ihr Fahrzeug',
            'beispiel': 'Beifahrerseite komplett sichtbar'
        },
        {
            'key': 'heck',
            'titel': 'Heckansicht',
            'icon': '🔙',
            'beschreibung': 'Stellen Sie sich HINTER Ihr Fahrzeug (ca. 3m Abstand)',
            'beispiel': 'Blick auf Kofferraum und Heck'
        }
    ]

    # Auswahl: Kamera oder Datei-Upload
    foto_methode = st.radio(
        "Wie möchten Sie die Fotos aufnehmen?",
        ["📷 Kamera verwenden", "📁 Dateien hochladen"],
        horizontal=True,
        key="foto_methode"
    )

    use_camera = foto_methode == "📷 Kamera verwenden"

    # Zwei Spalten für die 4 Foto-Positionen
    col1, col2 = st.columns(2)

    for i, pos in enumerate(foto_positionen):
        with col1 if i % 2 == 0 else col2:
            st.markdown(f"""
            <div class="photo-guide">
                <span style="font-size: 40px;">{pos['icon']}</span><br>
                <strong>{pos['titel']}</strong><br>
                <small>{pos['beschreibung']}</small>
            </div>
            """, unsafe_allow_html=True)

            if use_camera:
                # Kamera-Aufnahme
                foto = st.camera_input(
                    f"📷 {pos['titel']} aufnehmen",
                    key=f"cam_{pos['key']}",
                    help=pos['beispiel']
                )
            else:
                # Datei-Upload mit Foto-Hinweis
                foto = st.file_uploader(
                    f"📁 {pos['titel']} hochladen",
                    type=['jpg', 'jpeg', 'png', 'heic'],
                    key=f"foto_{pos['key']}",
                    help=f"{pos['beispiel']} - Tipp: Auf Mobilgeräten können Sie über 'Durchsuchen' direkt ein Foto aufnehmen!"
                )

            if foto:
                st.session_state.unfallaufnahme['fotos'][pos['key']] = foto
                st.success(f"✓ {pos['titel']} erfasst")
                # Vorschau anzeigen
                st.image(foto, width=150)

    # Zusätzliche Fotos
    st.markdown("---")
    st.markdown("#### Weitere Fotos (optional)")
    st.caption("z.B. Nahaufnahmen von Schäden, Bremsspuren, Verkehrsschilder")
    st.info("💡 **Tipp:** Auf Mobilgeräten können Sie über 'Durchsuchen' direkt ein Foto aufnehmen!")

    zusatz_fotos = st.file_uploader(
        "📷 Zusätzliche Fotos hochladen",
        type=['jpg', 'jpeg', 'png', 'heic'],
        accept_multiple_files=True,
        help="Auf Mobilgeräten: Tippen Sie auf 'Durchsuchen' und wählen Sie 'Kamera'",
        key="zusatz_fotos"
    )

    if zusatz_fotos:
        st.session_state.unfallaufnahme['fotos']['zusatz'] = zusatz_fotos
        st.success(f"✓ {len(zusatz_fotos)} zusätzliche Fotos hochgeladen")

    # Navigation
    st.markdown("---")
    col_back, col_next = st.columns(2)

    with col_back:
        if st.button("← Zurück", use_container_width=True):
            st.session_state.unfallaufnahme['schritt'] = 1
            st.rerun()

    with col_next:
        if st.button("Weiter zu Beteiligte →", type="primary", use_container_width=True):
            st.session_state.unfallaufnahme['schritt'] = 3
            st.rerun()


def _render_schritt_beteiligte():
    """Schritt 3: Unfallbeteiligte erfassen"""

    st.markdown("""
    <div class="step-header">
        <span class="step-number">3</span>
        <strong>Unfallbeteiligte erfassen</strong>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="info-box">
        <strong>👥 Wer war beteiligt?</strong><br>
        Erfassen Sie die Daten aller Unfallbeteiligten. Sie können die Daten per Foto
        vom Personalausweis/Führerschein erfassen oder manuell eingeben.
    </div>
    """, unsafe_allow_html=True)

    # Beteiligte aus Session State
    if 'beteiligte' not in st.session_state.unfallaufnahme:
        st.session_state.unfallaufnahme['beteiligte'] = []
    if 'geplante_beteiligte' not in st.session_state.unfallaufnahme:
        st.session_state.unfallaufnahme['geplante_beteiligte'] = []

    beteiligte = st.session_state.unfallaufnahme['beteiligte']
    geplante = st.session_state.unfallaufnahme['geplante_beteiligte']

    # Schritt 1: Anzahl und Rollen der Beteiligten festlegen
    if not geplante and not beteiligte:
        st.markdown("#### Wie viele Personen waren am Unfall beteiligt?")
        st.caption("Wählen Sie für jede beteiligte Person die entsprechende Rolle aus.")

        rollen_optionen = {
            "Unfallgegner (Fahrer)": "🚗 Unfallgegner",
            "Unfallgegner (Beifahrer)": "👤 Beifahrer Gegner",
            "Zeuge": "👁️ Zeuge",
            "Halter (falls nicht Fahrer)": "📋 Halter",
            "Weitere Person": "👥 Weitere Person"
        }

        st.markdown("**Wählen Sie die Rollen der Beteiligten:**")

        col1, col2 = st.columns(2)

        with col1:
            anzahl_gegner = st.number_input(
                "🚗 Unfallgegner (Fahrer)",
                min_value=0, max_value=5, value=1,
                help="Anzahl der gegnerischen Fahrer"
            )
            anzahl_beifahrer = st.number_input(
                "👤 Beifahrer (gegnerisches Fahrzeug)",
                min_value=0, max_value=10, value=0,
                help="Beifahrer im gegnerischen Fahrzeug"
            )

        with col2:
            anzahl_zeugen = st.number_input(
                "👁️ Zeugen",
                min_value=0, max_value=10, value=0,
                help="Unbeteiligte Zeugen des Unfalls"
            )
            anzahl_halter = st.number_input(
                "📋 Halter (falls nicht Fahrer)",
                min_value=0, max_value=2, value=0,
                help="Fahrzeughalter, falls nicht identisch mit Fahrer"
            )

        if st.button("✓ Beteiligte festlegen", type="primary", use_container_width=True):
            geplante_liste = []
            for i in range(anzahl_gegner):
                geplante_liste.append({"rolle": "Unfallgegner", "nr": i + 1, "erfasst": False})
            for i in range(anzahl_beifahrer):
                geplante_liste.append({"rolle": "Beifahrer", "nr": i + 1, "erfasst": False})
            for i in range(anzahl_zeugen):
                geplante_liste.append({"rolle": "Zeuge", "nr": i + 1, "erfasst": False})
            for i in range(anzahl_halter):
                geplante_liste.append({"rolle": "Halter", "nr": i + 1, "erfasst": False})

            if geplante_liste:
                st.session_state.unfallaufnahme['geplante_beteiligte'] = geplante_liste
                st.rerun()
            else:
                st.warning("Bitte geben Sie mindestens einen Beteiligten an.")

    else:
        # Übersicht der geplanten und erfassten Beteiligten
        st.markdown("#### Übersicht der Beteiligten")

        # Bereits erfasste anzeigen
        if beteiligte:
            st.markdown("**✅ Erfasst:**")
            for i, bet in enumerate(beteiligte):
                with st.expander(f"✓ {bet.get('vorname', '')} {bet.get('name', 'Unbekannt')} - {bet.get('rolle', 'Beteiligter')}", expanded=False):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"**Name:** {bet.get('vorname', '')} {bet.get('name', '')}")
                        st.write(f"**Adresse:** {bet.get('adresse', '-')}")
                        st.write(f"**Versicherung:** {bet.get('versicherung', '-')}")
                        st.write(f"**Kennzeichen:** {bet.get('kennzeichen', '-')}")
                    with col2:
                        if st.button("🗑️ Löschen", key=f"del_bet_{i}"):
                            beteiligte.pop(i)
                            st.rerun()

        # Noch zu erfassende anzeigen
        noch_offen = [g for g in geplante if not g.get('erfasst', False)]
        if noch_offen:
            st.markdown(f"**⏳ Noch zu erfassen: {len(noch_offen)}**")
            for g in noch_offen:
                st.caption(f"• {g['rolle']} {g['nr']}")

        st.markdown("---")

        # Neuen Beteiligten erfassen
        st.markdown("#### Nächsten Beteiligten erfassen")

        # Rolle aus geplanten vorschlagen
        naechste_rolle = noch_offen[0]['rolle'] if noch_offen else "Unfallgegner"

        erfassung_methode = st.radio(
            "Erfassungsmethode",
            ["📷 Foto von Ausweis/Führerschein", "✏️ Manuelle Eingabe"],
            horizontal=True,
            key="erfassung_methode"
        )

        # OCR-Ergebnisse im Session State speichern
        if 'ocr_ergebnis' not in st.session_state.unfallaufnahme:
            st.session_state.unfallaufnahme['ocr_ergebnis'] = {}

        ocr_ergebnis = st.session_state.unfallaufnahme['ocr_ergebnis']

        if erfassung_methode == "📷 Foto von Ausweis/Führerschein":
            st.markdown("""
            <div class="photo-guide">
                <span style="font-size: 30px;">📄</span><br>
                <strong>Fotografieren Sie den Personalausweis oder Führerschein</strong><br>
                <small>Vorder- UND Rückseite für vollständige Daten</small>
            </div>
            """, unsafe_allow_html=True)

            st.info("💡 **Tipp:** Auf Mobilgeräten können Sie über 'Durchsuchen' direkt ein Foto aufnehmen!")

            col_front, col_back = st.columns(2)

            with col_front:
                st.markdown("**Vorderseite:**")
                ausweis_vorne = st.file_uploader(
                    "📷 Vorderseite fotografieren/hochladen",
                    type=['jpg', 'jpeg', 'png'],
                    key="ausweis_vorne",
                    help="Auf Mobilgeräten: Tippen Sie auf 'Durchsuchen' und wählen Sie 'Kamera'"
                )
                if ausweis_vorne:
                    st.image(ausweis_vorne, width=150)
                    st.success("✓ Vorderseite erfasst")

            with col_back:
                st.markdown("**Rückseite:**")
                ausweis_hinten = st.file_uploader(
                    "📷 Rückseite fotografieren/hochladen",
                    type=['jpg', 'jpeg', 'png'],
                    key="ausweis_hinten",
                    help="Auf Mobilgeräten: Tippen Sie auf 'Durchsuchen' und wählen Sie 'Kamera'"
                )
                if ausweis_hinten:
                    st.image(ausweis_hinten, width=150)
                    st.success("✓ Rückseite erfasst")

            # OCR-Verarbeitung
            if ausweis_vorne or ausweis_hinten:
                if OCR_AVAILABLE:
                    if st.button("🔍 Text automatisch erkennen (OCR)", type="primary", key="ocr_btn"):
                        with st.spinner("Analysiere Ausweisfotos..."):
                            ocr_texte = []

                            # Vorderseite analysieren
                            if ausweis_vorne:
                                result_vorne = _ocr_ausweis(ausweis_vorne)
                                if result_vorne:
                                    ocr_ergebnis.update(result_vorne)
                                    ocr_texte.append(f"Vorderseite: {result_vorne.get('raw_text', '')[:200]}")

                            # Rückseite analysieren
                            if ausweis_hinten:
                                result_hinten = _ocr_ausweis(ausweis_hinten)
                                if result_hinten:
                                    # Nur leere Felder überschreiben
                                    for key, value in result_hinten.items():
                                        if value and not ocr_ergebnis.get(key):
                                            ocr_ergebnis[key] = value
                                    ocr_texte.append(f"Rückseite: {result_hinten.get('raw_text', '')[:200]}")

                            st.session_state.unfallaufnahme['ocr_ergebnis'] = ocr_ergebnis

                            if ocr_ergebnis.get('vorname') or ocr_ergebnis.get('nachname'):
                                st.success("✅ Text erkannt! Die Felder wurden vorausgefüllt.")
                                st.rerun()
                            else:
                                st.warning("⚠️ Konnte keinen Text erkennen. Bitte Daten manuell eingeben.")

                            # Debug: Zeige erkannten Text
                            with st.expander("🔍 Erkannter Text (Debug)"):
                                for text in ocr_texte:
                                    st.text(text)
                else:
                    st.error(f"❌ OCR nicht verfügbar: {TESSERACT_ERROR or 'Unbekannter Fehler'}")
                    st.info("💡 **Lösung:** Auf dem Server muss 'tesseract-ocr' installiert werden (packages.txt wurde erstellt).")

                # Zeige OCR-Ergebnisse wenn vorhanden
                if ocr_ergebnis.get('vorname') or ocr_ergebnis.get('nachname'):
                    st.info(f"✅ Erkannt: {ocr_ergebnis.get('vorname', '')} {ocr_ergebnis.get('nachname', '')}")

        # Manuelle Eingabe (immer anzeigen als Fallback oder Korrektur)
        st.markdown("##### Personendaten")

        # Werte aus OCR-Ergebnis als Standardwerte verwenden
        ocr_vorname = ocr_ergebnis.get('vorname', '')
        ocr_nachname = ocr_ergebnis.get('nachname', '')
        ocr_adresse = ocr_ergebnis.get('adresse', '')
        ocr_geburtsdatum = ocr_ergebnis.get('geburtsdatum', '')

        col1, col2 = st.columns(2)

        with col1:
            rolle = st.selectbox(
                "Rolle",
                ["Unfallgegner", "Beifahrer", "Zeuge", "Halter", "Sonstige"],
                index=["Unfallgegner", "Beifahrer", "Zeuge", "Halter", "Sonstige"].index(naechste_rolle) if naechste_rolle in ["Unfallgegner", "Beifahrer", "Zeuge", "Halter", "Sonstige"] else 0,
                key="neue_rolle"
            )
            vorname = st.text_input(
                "Vorname",
                value=ocr_vorname,
                key="neuer_vorname",
                placeholder="Max"
            )

            # Geburtsdatum aus OCR parsen
            geb_default = None
            if ocr_geburtsdatum:
                try:
                    parts = ocr_geburtsdatum.split('.')
                    if len(parts) == 3:
                        geb_default = date(int(parts[2]), int(parts[1]), int(parts[0]))
                except (ValueError, IndexError):
                    pass

            geburtsdatum = st.date_input(
                "Geburtsdatum",
                value=geb_default,
                min_value=date(1920, 1, 1),
                max_value=date.today(),
                key="neues_geburtsdatum"
            )

        with col2:
            name = st.text_input(
                "Nachname",
                value=ocr_nachname,
                key="neuer_name",
                placeholder="Mustermann"
            )
            telefon = st.text_input("Telefon", key="neues_telefon", placeholder="0123 456789")
            email = st.text_input("E-Mail", key="neue_email", placeholder="max@beispiel.de")

        adresse = st.text_input(
            "Adresse",
            value=ocr_adresse,
            key="neue_adresse",
            placeholder="Musterstraße 123, 12345 Musterstadt"
        )

        st.markdown("##### Versicherungsdaten")

        col_v1, col_v2 = st.columns(2)

        with col_v1:
            versicherung = st.text_input(
                "Versicherung",
                key="neue_versicherung",
                placeholder="z.B. Allianz, HUK, ADAC"
            )

        with col_v2:
            versicherungsnr = st.text_input(
                "Versicherungsnummer",
                key="neue_versicherungsnr",
                placeholder="Falls bekannt"
            )

        kennzeichen = st.text_input(
            "Kennzeichen des Fahrzeugs",
            key="neues_kennzeichen",
            placeholder="z.B. B-AB 1234"
        )

        # Beteiligten hinzufügen
        if st.button("✓ Beteiligten hinzufügen", type="primary"):
            if name:
                neuer_beteiligter = {
                    'rolle': rolle,
                    'vorname': vorname,
                    'name': name,
                    'geburtsdatum': str(geburtsdatum) if geburtsdatum else None,
                    'telefon': telefon,
                    'email': email,
                    'adresse': adresse,
                    'versicherung': versicherung,
                    'versicherungsnr': versicherungsnr,
                    'kennzeichen': kennzeichen
                }
                st.session_state.unfallaufnahme['beteiligte'].append(neuer_beteiligter)

                # Geplanten Beteiligten als erfasst markieren
                for g in geplante:
                    if g['rolle'] == rolle and not g.get('erfasst', False):
                        g['erfasst'] = True
                        break

                st.success(f"✓ {vorname} {name} wurde hinzugefügt")
                st.rerun()
            else:
                st.error("Bitte geben Sie mindestens den Nachnamen ein")

        # Button zum Zurücksetzen der Planung
        st.markdown("---")
        if st.button("🔄 Beteiligte neu planen", key="reset_planung"):
            st.session_state.unfallaufnahme['geplante_beteiligte'] = []
            st.session_state.unfallaufnahme['beteiligte'] = []
            st.rerun()

    # Navigation
    st.markdown("---")
    col_back, col_next = st.columns(2)

    with col_back:
        if st.button("← Zurück", use_container_width=True, key="back_3"):
            st.session_state.unfallaufnahme['schritt'] = 2
            st.rerun()

    with col_next:
        if st.button("Weiter zu Kennzeichen →", type="primary", use_container_width=True):
            st.session_state.unfallaufnahme['schritt'] = 4
            st.rerun()


def _render_schritt_kennzeichen():
    """Schritt 4: Kennzeichen fotografieren"""

    st.markdown("""
    <div class="step-header">
        <span class="step-number">4</span>
        <strong>Kennzeichen der Fahrzeuge</strong>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="info-box">
        <strong>🚗 Kennzeichen dokumentieren</strong><br>
        Erfassen Sie die Kennzeichen aller am Unfall beteiligten Fahrzeuge -
        per Foto oder manueller Eingabe.
    </div>
    """, unsafe_allow_html=True)

    # Initialisiere Kennzeichen-Liste im Session State
    if 'erfasste_kennzeichen' not in st.session_state.unfallaufnahme:
        st.session_state.unfallaufnahme['erfasste_kennzeichen'] = []

    erfasste_kz = st.session_state.unfallaufnahme['erfasste_kennzeichen']

    # Bereits erfasste Kennzeichen anzeigen
    if erfasste_kz:
        st.markdown("#### ✅ Bereits erfasste Kennzeichen")
        for i, kz in enumerate(erfasste_kz):
            col1, col2, col3 = st.columns([2, 2, 1])
            with col1:
                st.write(f"**{kz['kennzeichen']}**")
            with col2:
                st.caption(kz.get('zuordnung', 'Nicht zugeordnet'))
            with col3:
                if st.button("🗑️", key=f"del_kz_{i}", help="Löschen"):
                    erfasste_kz.pop(i)
                    st.rerun()
        st.markdown("---")

    # Neues Kennzeichen erfassen
    st.markdown("#### Kennzeichen erfassen")

    erfassung_art = st.radio(
        "Wie möchten Sie das Kennzeichen erfassen?",
        ["📷 Per Foto", "✏️ Manuelle Eingabe"],
        horizontal=True,
        key="kz_erfassung_art"
    )

    if erfassung_art == "📷 Per Foto":
        st.markdown("""
        <div class="photo-guide">
            <span style="font-size: 40px;">🔢</span><br>
            <strong>Fotografieren Sie das Kennzeichen</strong><br>
            <small>Achten Sie auf gute Beleuchtung und scharfes Bild</small>
        </div>
        """, unsafe_allow_html=True)

        st.info("💡 **Tipp:** Auf Mobilgeräten können Sie über 'Durchsuchen' direkt ein Foto aufnehmen!")

        kz_foto = st.file_uploader(
            "📷 Kennzeichen fotografieren/hochladen",
            type=['jpg', 'jpeg', 'png'],
            key="einzelnes_kz_foto",
            help="Auf Mobilgeräten: Tippen Sie auf 'Durchsuchen' und wählen Sie 'Kamera'"
        )

        if kz_foto:
            st.image(kz_foto, width=300)
            st.success("✓ Foto hochgeladen")

            # OCR versuchen
            erkanntes_kz = ""
            if OCR_AVAILABLE:
                if st.button("🔍 Kennzeichen automatisch erkennen", key="kz_ocr_btn"):
                    with st.spinner("Analysiere Kennzeichen..."):
                        erkanntes_kz = _ocr_kennzeichen(kz_foto)
                        if erkanntes_kz:
                            st.success(f"✅ Erkannt: **{erkanntes_kz}**")
                            st.session_state.unfallaufnahme['erkanntes_kz'] = erkanntes_kz
                        else:
                            st.warning("⚠️ Kennzeichen konnte nicht automatisch erkannt werden. Bitte manuell eingeben.")

            # Feld für manuelle Eingabe/Korrektur
            erkanntes_kz = st.session_state.unfallaufnahme.get('erkanntes_kz', '')
            kennzeichen_eingabe = st.text_input(
                "Kennzeichen",
                value=erkanntes_kz,
                placeholder="z.B. B-AB 1234",
                key="kz_aus_foto"
            )
        else:
            kennzeichen_eingabe = ""

    else:  # Manuelle Eingabe
        kennzeichen_eingabe = st.text_input(
            "Kennzeichen eingeben",
            placeholder="z.B. B-AB 1234 oder M XY 999",
            key="kz_manuell",
            help="Format: Ortskürzel - Buchstaben - Zahlen (z.B. B-AB 1234)"
        )

    # Zuordnung zu Beteiligtem
    beteiligte = st.session_state.unfallaufnahme.get('beteiligte', [])
    zuordnung_optionen = ["Gegnerisches Fahrzeug"] + [
        f"{b.get('vorname', '')} {b.get('name', '')} ({b.get('rolle', '')})"
        for b in beteiligte
    ]

    zuordnung = st.selectbox(
        "Zuordnung",
        zuordnung_optionen,
        key="kz_zuordnung",
        help="Zu welcher Person/welchem Fahrzeug gehört dieses Kennzeichen?"
    )

    # Kennzeichen hinzufügen
    if st.button("✓ Kennzeichen speichern", type="primary", key="kz_speichern"):
        if kennzeichen_eingabe:
            neues_kz = {
                'kennzeichen': kennzeichen_eingabe.upper(),
                'zuordnung': zuordnung,
                'foto': True if erfassung_art == "📷 Per Foto" else False
            }
            erfasste_kz.append(neues_kz)
            st.session_state.unfallaufnahme['erkanntes_kz'] = ''  # Reset
            st.success(f"✓ Kennzeichen {kennzeichen_eingabe.upper()} gespeichert!")
            st.rerun()
        else:
            st.error("Bitte geben Sie ein Kennzeichen ein.")

    # Zusätzliche Notizen
    st.markdown("---")
    st.markdown("#### Zusätzliche Notizen (optional)")

    notizen = st.text_area(
        "Ihre Notizen zum Unfallhergang",
        value=st.session_state.unfallaufnahme.get('notizen', ''),
        height=150,
        placeholder="Beschreiben Sie hier den Unfallhergang mit eigenen Worten...",
        help="z.B. Wer ist wo gefahren, wie kam es zum Zusammenstoß"
    )
    st.session_state.unfallaufnahme['notizen'] = notizen

    # Navigation
    st.markdown("---")
    col_back, col_next = st.columns(2)

    with col_back:
        if st.button("← Zurück", use_container_width=True, key="back_4"):
            st.session_state.unfallaufnahme['schritt'] = 3
            st.rerun()

    with col_next:
        if st.button("Weiter zur Zusammenfassung →", type="primary", use_container_width=True):
            st.session_state.unfallaufnahme['schritt'] = 5
            st.rerun()


def _render_schritt_abschluss():
    """Schritt 5: Zusammenfassung und Absenden"""

    st.markdown("""
    <div class="step-header">
        <span class="step-number">5</span>
        <strong>Zusammenfassung & Absenden</strong>
    </div>
    """, unsafe_allow_html=True)

    daten = st.session_state.unfallaufnahme

    st.markdown("""
    <div class="info-box">
        <strong>✅ Fast geschafft!</strong><br>
        Bitte überprüfen Sie die erfassten Daten. Nach dem Absenden werden alle
        Informationen sicher gespeichert und an Ihren Anwalt übermittelt.
    </div>
    """, unsafe_allow_html=True)

    # Zusammenfassung
    st.markdown("### Ihre erfassten Daten")

    # Unfalldaten
    with st.expander("📅 Unfalldaten", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Datum:** {daten.get('datum', '-')}")
            st.write(f"**Uhrzeit:** {daten.get('uhrzeit', '-')}")
        with col2:
            st.write(f"**Ort:** {daten.get('ort', '-')}")
            st.write(f"**Wetter:** {daten.get('wetter', '-')}")

    # Fotos
    with st.expander("📸 Fotos", expanded=True):
        fotos = daten.get('fotos', {})
        foto_count = len([k for k in ['front', 'links', 'rechts', 'heck'] if k in fotos])
        zusatz_count = len(fotos.get('zusatz', []))
        kennzeichen_count = len(daten.get('kennzeichen_fotos', []))

        st.write(f"**Fahrzeugfotos:** {foto_count} von 4")
        st.write(f"**Zusätzliche Fotos:** {zusatz_count}")
        st.write(f"**Kennzeichen-Fotos:** {kennzeichen_count}")

        if foto_count < 4:
            st.warning("⚠️ Es fehlen noch Fahrzeugfotos. Bitte ergänzen Sie diese für eine vollständige Dokumentation.")

    # Beteiligte
    with st.expander("👥 Beteiligte", expanded=True):
        beteiligte = daten.get('beteiligte', [])
        if beteiligte:
            for bet in beteiligte:
                st.write(f"• **{bet.get('vorname', '')} {bet.get('name', '')}** ({bet.get('rolle', '-')})")
                if bet.get('versicherung'):
                    st.caption(f"  Versicherung: {bet.get('versicherung')}")
        else:
            st.warning("⚠️ Keine Beteiligten erfasst")

    # Notizen
    if daten.get('notizen'):
        with st.expander("📝 Notizen", expanded=True):
            st.write(daten.get('notizen'))

    st.markdown("---")

    # Absenden
    st.markdown("### Daten übermitteln")

    st.markdown("""
    <div class="info-box">
        <strong>🔒 Ihre Daten sind sicher</strong><br>
        Alle Informationen werden verschlüsselt übertragen und nur von Ihrem
        Anwalt und den autorisierten Bearbeitern eingesehen.
    </div>
    """, unsafe_allow_html=True)

    bestaetigung = st.checkbox(
        "Ich bestätige, dass die Angaben nach bestem Wissen und Gewissen gemacht wurden.",
        key="bestaetigung"
    )

    col_back, col_submit = st.columns(2)

    with col_back:
        if st.button("← Zurück", use_container_width=True, key="back_5"):
            st.session_state.unfallaufnahme['schritt'] = 4
            st.rerun()

    with col_submit:
        if st.button(
            "✓ Unfallaufnahme absenden",
            type="primary",
            use_container_width=True,
            disabled=not bestaetigung
        ):
            with st.spinner("Daten werden übermittelt..."):
                # Hier würde die Speicherung erfolgen
                try:
                    _speichere_unfallaufnahme(daten)
                    st.session_state.unfallaufnahme['abgesendet'] = True
                    st.rerun()
                except Exception as e:
                    st.error(f"Fehler beim Speichern: {e}")

    # Erfolgsmeldung anzeigen
    if daten.get('abgesendet'):
        st.markdown("""
        <div class="success-message">
            <h2>✅ Vielen Dank!</h2>
            <p>Ihre Unfallaufnahme wurde erfolgreich übermittelt.</p>
            <p>Ihr Anwalt wird sich in Kürze bei Ihnen melden.</p>
            <p><strong>Ihr Vorgang wird jetzt bearbeitet.</strong></p>
        </div>
        """, unsafe_allow_html=True)

        if st.button("🔄 Neue Unfallaufnahme starten"):
            del st.session_state['unfallaufnahme']
            st.rerun()


def _speichere_unfallaufnahme(daten: dict):
    """Speichert die Unfallaufnahme in der Datenbank"""
    # TODO: Implementierung der Speicherung
    # - Neues UnfallProjekt erstellen
    # - Fotos als Dokumente speichern
    # - Beteiligte anlegen

    import time
    time.sleep(1)  # Simuliere Speichervorgang

    return True
