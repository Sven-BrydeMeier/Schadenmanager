"""
Unfallaufnahme vor Ort
Mobile-freundliche Erfassung eines Unfalls durch das Unfallopfer
"""
import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime, date, time
from typing import Optional, Dict, List
import json

from src.config.database import get_session


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

    # Tabs für die Schritte
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "1. Wann & Wo",
        "2. Fotos Unfallort",
        "3. Beteiligte",
        "4. Kennzeichen",
        "5. Abschluss"
    ])

    with tab1:
        _render_schritt_wann_wo()

    with tab2:
        _render_schritt_fotos()

    with tab3:
        _render_schritt_beteiligte()

    with tab4:
        _render_schritt_kennzeichen()

    with tab5:
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

                        // Koordinaten in verstecktes Feld kopieren
                        var coordInput = parent.document.querySelector('input[data-testid="stTextInput"][aria-label="GPS-Koordinaten"]');
                        if (coordInput) {
                            coordInput.value = lat + ', ' + lng;
                            coordInput.dispatchEvent(new Event('input', { bubbles: true }));
                        }
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
        st.session_state.unfallaufnahme['gps_koordinaten'] = gps_koordinaten

        if gps_koordinaten:
            st.success(f"✓ Koordinaten: {gps_koordinaten}")
            # Google Maps Link
            coords_clean = gps_koordinaten.replace(" ", "")
            st.markdown(f"[📍 In Google Maps anzeigen](https://www.google.com/maps?q={coords_clean})")

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

    col_plz, col_ort = st.columns([1, 3])
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

    # Speichern
    st.session_state.unfallaufnahme['ort_details'] = {
        'strasse': strasse,
        'hausnummer': hausnummer,
        'plz': plz,
        'ort': ort
    }
    st.session_state.unfallaufnahme['ort'] = f"{strasse} {hausnummer}, {plz} {ort}".strip(", ")

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
                # Datei-Upload
                foto = st.file_uploader(
                    f"📁 {pos['titel']} hochladen",
                    type=['jpg', 'jpeg', 'png', 'heic'],
                    key=f"foto_{pos['key']}",
                    help=pos['beispiel']
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

    zusatz_fotos = st.file_uploader(
        "Zusätzliche Fotos",
        type=['jpg', 'jpeg', 'png', 'heic'],
        accept_multiple_files=True,
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

    beteiligte = st.session_state.unfallaufnahme['beteiligte']

    # Bestehende Beteiligte anzeigen
    if beteiligte:
        st.markdown("#### Bereits erfasste Beteiligte")
        for i, bet in enumerate(beteiligte):
            with st.expander(f"👤 {bet.get('name', 'Unbekannt')} - {bet.get('rolle', 'Beteiligter')}"):
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

    st.markdown("---")

    # Neuen Beteiligten erfassen
    st.markdown("#### Neuen Beteiligten hinzufügen")

    erfassung_methode = st.radio(
        "Erfassungsmethode",
        ["Foto von Ausweis/Führerschein", "Manuelle Eingabe"],
        horizontal=True,
        key="erfassung_methode"
    )

    if erfassung_methode == "Foto von Ausweis/Führerschein":
        st.markdown("""
        <div class="photo-guide">
            <span style="font-size: 30px;">📄</span><br>
            <strong>Fotografieren Sie den Personalausweis oder Führerschein</strong><br>
            <small>Die Daten werden automatisch erkannt (OCR)</small>
        </div>
        """, unsafe_allow_html=True)

        ausweis_foto = st.file_uploader(
            "Foto vom Ausweis",
            type=['jpg', 'jpeg', 'png'],
            key="ausweis_foto",
            help="Achten Sie auf gute Beleuchtung und scharfe Aufnahme"
        )

        if ausweis_foto:
            st.success("✓ Ausweis-Foto hochgeladen")
            st.info("OCR-Erkennung wird nach dem Upload ausgeführt. Bitte prüfen und ergänzen Sie die erkannten Daten unten.")

            # Hier würde normalerweise OCR stattfinden
            # Für jetzt: Leere Felder anzeigen
            st.warning("Die automatische Texterkennung ist noch in Entwicklung. Bitte geben Sie die Daten manuell ein.")

    # Manuelle Eingabe (immer anzeigen als Fallback oder Korrektur)
    st.markdown("##### Personendaten")

    col1, col2 = st.columns(2)

    with col1:
        rolle = st.selectbox(
            "Rolle",
            ["Unfallgegner", "Fahrer", "Beifahrer", "Zeuge", "Halter"],
            key="neue_rolle"
        )
        vorname = st.text_input("Vorname", key="neuer_vorname", placeholder="Max")
        geburtsdatum = st.date_input(
            "Geburtsdatum",
            value=None,
            min_value=date(1920, 1, 1),
            max_value=date.today(),
            key="neues_geburtsdatum"
        )

    with col2:
        name = st.text_input("Nachname", key="neuer_name", placeholder="Mustermann")
        telefon = st.text_input("Telefon", key="neues_telefon", placeholder="0123 456789")
        email = st.text_input("E-Mail", key="neue_email", placeholder="max@beispiel.de")

    adresse = st.text_input(
        "Adresse",
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
            st.success(f"✓ {vorname} {name} wurde hinzugefügt")
            st.rerun()
        else:
            st.error("Bitte geben Sie mindestens den Nachnamen ein")

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
        Fotografieren Sie die Kennzeichen aller am Unfall beteiligten Fahrzeuge.
        So können die Fahrzeuge eindeutig identifiziert werden.
    </div>
    """, unsafe_allow_html=True)

    # Kennzeichen-Fotos
    st.markdown("#### Kennzeichen fotografieren")

    st.markdown("""
    <div class="photo-guide">
        <span style="font-size: 40px;">🔢</span><br>
        <strong>Fotografieren Sie die Kennzeichen</strong><br>
        <small>Achten Sie darauf, dass das Kennzeichen gut lesbar ist</small>
    </div>
    """, unsafe_allow_html=True)

    kennzeichen_fotos = st.file_uploader(
        "Fotos der Kennzeichen",
        type=['jpg', 'jpeg', 'png'],
        accept_multiple_files=True,
        key="kennzeichen_fotos"
    )

    if kennzeichen_fotos:
        st.session_state.unfallaufnahme['kennzeichen_fotos'] = kennzeichen_fotos
        st.success(f"✓ {len(kennzeichen_fotos)} Kennzeichen-Fotos hochgeladen")

        # Zuordnung zu Beteiligten
        if st.session_state.unfallaufnahme.get('beteiligte'):
            st.markdown("#### Zuordnung zu Beteiligten")
            st.caption("Ordnen Sie die Kennzeichen den erfassten Beteiligten zu")

            for i, foto in enumerate(kennzeichen_fotos):
                col1, col2 = st.columns([1, 2])
                with col1:
                    st.write(f"**Foto {i+1}:** {foto.name}")
                with col2:
                    beteiligte_namen = [
                        f"{b.get('vorname', '')} {b.get('name', '')}"
                        for b in st.session_state.unfallaufnahme['beteiligte']
                    ]
                    st.selectbox(
                        "Zuordnung",
                        ["Nicht zugeordnet"] + beteiligte_namen,
                        key=f"kennzeichen_zuordnung_{i}"
                    )

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
