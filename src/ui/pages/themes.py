"""
Dark Mode / Themes UI-Seite
Theme-Einstellungen für Benutzer
"""
import streamlit as st
from datetime import datetime

from src.config.database import get_session
from src.services.themes import (
    ThemeService, ThemeTyp, BenutzerTheme
)


def render_themes():
    """Rendert die Theme-Einstellungen"""
    st.title("🎨 Erscheinungsbild")

    st.info("""
    Passen Sie das Erscheinungsbild der Anwendung an Ihre Vorlieben an.
    Wählen Sie zwischen hellem und dunklem Design.
    """)

    with get_session() as db:
        service = ThemeService(db)
        user_id = st.session_state.get('user_id', 1)

        # Aktuelles Theme laden
        aktuelles_theme = service.theme_laden(user_id)

        # Theme auswählen
        st.subheader("Theme auswählen")

        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button(
                "☀️ Hell",
                type="primary" if aktuelles_theme['typ'] == ThemeTyp.LIGHT else "secondary",
                use_container_width=True
            ):
                service.theme_speichern(user_id, ThemeTyp.LIGHT)
                db.commit()
                st.rerun()

            st.caption("Standard helles Theme")

        with col2:
            if st.button(
                "🌙 Dunkel",
                type="primary" if aktuelles_theme['typ'] == ThemeTyp.DARK else "secondary",
                use_container_width=True
            ):
                service.theme_speichern(user_id, ThemeTyp.DARK)
                db.commit()
                st.rerun()

            st.caption("Dunkles Theme für weniger Augenbelastung")

        with col3:
            if st.button(
                "💻 System",
                type="primary" if aktuelles_theme['typ'] == ThemeTyp.SYSTEM else "secondary",
                use_container_width=True
            ):
                service.theme_speichern(user_id, ThemeTyp.SYSTEM)
                db.commit()
                st.rerun()

            st.caption("Folgt der Systemeinstellung")

        st.markdown("---")

        # Vorschau
        st.subheader("Vorschau")

        _zeige_vorschau(aktuelles_theme)

        st.markdown("---")

        # Weitere Einstellungen
        st.subheader("Weitere Einstellungen")

        col_s1, col_s2 = st.columns(2)

        # Aktuelle Einstellungen laden
        einstellung = db.query(BenutzerTheme).filter(
            BenutzerTheme.user_id == user_id
        ).first()

        with col_s1:
            schriftgroesse = st.select_slider(
                "Schriftgröße",
                options=["small", "normal", "large"],
                value=einstellung.schriftgroesse if einstellung else "normal",
                format_func=lambda x: {
                    'small': 'Klein',
                    'normal': 'Normal',
                    'large': 'Groß'
                }.get(x, x)
            )

        with col_s2:
            kompakt = st.checkbox(
                "Kompakter Modus",
                value=einstellung.kompakt_modus if einstellung else False,
                help="Reduziert Abstände für mehr Inhalt auf dem Bildschirm"
            )

        if st.button("💾 Einstellungen speichern"):
            service.theme_speichern(
                user_id=user_id,
                theme_typ=aktuelles_theme['typ'],
                schriftgroesse=schriftgroesse,
                kompakt_modus=kompakt
            )
            db.commit()
            st.success("Einstellungen gespeichert!")
            st.rerun()

        st.markdown("---")

        # Benutzerdefinierte Farben (Advanced)
        with st.expander("🎨 Benutzerdefinierte Farben (Erweitert)"):
            st.warning("Diese Funktion ist für fortgeschrittene Benutzer.")

            basis_farben = aktuelles_theme.get('farben', {})

            col_c1, col_c2 = st.columns(2)

            with col_c1:
                background = st.color_picker(
                    "Hintergrund",
                    value=basis_farben.get('background', '#FFFFFF')
                )
                text = st.color_picker(
                    "Text",
                    value=basis_farben.get('text_primary', '#1E1E1E')
                )
                accent = st.color_picker(
                    "Akzentfarbe",
                    value=basis_farben.get('accent', '#1976D2')
                )

            with col_c2:
                sidebar = st.color_picker(
                    "Seitenleiste",
                    value=basis_farben.get('sidebar_background', '#FAFAFA')
                )
                card = st.color_picker(
                    "Karten",
                    value=basis_farben.get('card_background', '#FFFFFF')
                )
                border = st.color_picker(
                    "Rahmen",
                    value=basis_farben.get('border', '#E0E0E0')
                )

            if st.button("🎨 Benutzerdefiniertes Theme speichern"):
                custom_farben = {
                    'background': background,
                    'text_primary': text,
                    'accent': accent,
                    'sidebar_background': sidebar,
                    'card_background': card,
                    'border': border
                }

                service.theme_speichern(
                    user_id=user_id,
                    theme_typ=ThemeTyp.CUSTOM,
                    custom_farben=custom_farben
                )
                db.commit()
                st.success("Benutzerdefiniertes Theme gespeichert!")
                st.rerun()


def _zeige_vorschau(theme: dict):
    """Zeigt eine Vorschau des Themes"""
    farben = theme.get('farben', {})

    # CSS für Vorschau-Box
    preview_style = f"""
    <div style="
        background-color: {farben.get('background', '#FFFFFF')};
        color: {farben.get('text_primary', '#1E1E1E')};
        padding: 20px;
        border-radius: 10px;
        border: 1px solid {farben.get('border', '#E0E0E0')};
        margin: 10px 0;
    ">
        <h3 style="color: {farben.get('text_primary', '#1E1E1E')}; margin-top: 0;">
            Vorschau: {theme.get('name', 'Theme')}
        </h3>
        <p style="color: {farben.get('text_secondary', '#666666')};">
            Dies ist ein Beispieltext in der sekundären Textfarbe.
        </p>
        <div style="
            display: flex;
            gap: 10px;
            margin-top: 15px;
        ">
            <div style="
                background-color: {farben.get('accent', '#1976D2')};
                color: white;
                padding: 8px 16px;
                border-radius: 5px;
            ">
                Primärer Button
            </div>
            <div style="
                background-color: {farben.get('success', '#4CAF50')};
                color: white;
                padding: 8px 16px;
                border-radius: 5px;
            ">
                Erfolg
            </div>
            <div style="
                background-color: {farben.get('warning', '#FF9800')};
                color: white;
                padding: 8px 16px;
                border-radius: 5px;
            ">
                Warnung
            </div>
            <div style="
                background-color: {farben.get('error', '#F44336')};
                color: white;
                padding: 8px 16px;
                border-radius: 5px;
            ">
                Fehler
            </div>
        </div>
        <div style="
            background-color: {farben.get('card_background', '#FFFFFF')};
            border: 1px solid {farben.get('border', '#E0E0E0')};
            padding: 15px;
            border-radius: 5px;
            margin-top: 15px;
        ">
            <strong>Beispiel-Karte</strong>
            <p style="margin: 5px 0 0 0; color: {farben.get('text_secondary', '#666666')};">
                Inhalt einer Karten-Komponente
            </p>
        </div>
    </div>
    """

    st.markdown(preview_style, unsafe_allow_html=True)

    # Farben-Übersicht
    with st.expander("Farben-Übersicht"):
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown(f"**Hintergrund:** `{farben.get('background', '-')}`")
            st.markdown(f"**Text primär:** `{farben.get('text_primary', '-')}`")
            st.markdown(f"**Text sekundär:** `{farben.get('text_secondary', '-')}`")

        with col2:
            st.markdown(f"**Akzent:** `{farben.get('accent', '-')}`")
            st.markdown(f"**Erfolg:** `{farben.get('success', '-')}`")
            st.markdown(f"**Warnung:** `{farben.get('warning', '-')}`")

        with col3:
            st.markdown(f"**Fehler:** `{farben.get('error', '-')}`")
            st.markdown(f"**Rahmen:** `{farben.get('border', '-')}`")
            st.markdown(f"**Karte:** `{farben.get('card_background', '-')}`")
