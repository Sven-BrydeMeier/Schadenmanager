"""
Dark Mode / Theme Service
Verwaltung von Themes und Farbschemata
"""
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum
import json
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text
from src.models.base import Base


class ThemeTyp(str, Enum):
    """Verfügbare Themes"""
    LIGHT = "LIGHT"
    DARK = "DARK"
    SYSTEM = "SYSTEM"
    CUSTOM = "CUSTOM"


class BenutzerTheme(Base):
    """Model für Benutzer-Theme-Einstellungen"""
    __tablename__ = "benutzer_theme"

    id = Column(Integer, primary_key=True)

    user_id = Column(Integer, ForeignKey("user.id"), unique=True, nullable=False)

    # Theme
    theme_typ = Column(String(20), default=ThemeTyp.LIGHT.value)

    # Anpassungen
    _custom_farben = Column("custom_farben", Text)
    schriftgroesse = Column(String(20), default="normal")  # small, normal, large
    kompakt_modus = Column(Boolean, default=False)

    # Metadaten
    aktualisiert_am = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    @property
    def custom_farben(self) -> Dict[str, str]:
        if self._custom_farben:
            return json.loads(self._custom_farben)
        return {}

    @custom_farben.setter
    def custom_farben(self, value: Dict[str, str]):
        self._custom_farben = json.dumps(value)


class ThemeService:
    """Service für Theme-Verwaltung"""

    # Standard-Themes
    THEMES = {
        ThemeTyp.LIGHT: {
            'name': 'Hell',
            'beschreibung': 'Standard helles Theme',
            'farben': {
                'background': '#FFFFFF',
                'background_secondary': '#F5F5F5',
                'text_primary': '#1E1E1E',
                'text_secondary': '#666666',
                'accent': '#1976D2',
                'accent_light': '#BBDEFB',
                'success': '#4CAF50',
                'warning': '#FF9800',
                'error': '#F44336',
                'border': '#E0E0E0',
                'card_background': '#FFFFFF',
                'sidebar_background': '#FAFAFA',
                'header_background': '#1976D2',
                'header_text': '#FFFFFF'
            }
        },
        ThemeTyp.DARK: {
            'name': 'Dunkel',
            'beschreibung': 'Dunkles Theme für reduzierte Augenbelastung',
            'farben': {
                'background': '#121212',
                'background_secondary': '#1E1E1E',
                'text_primary': '#FFFFFF',
                'text_secondary': '#B0B0B0',
                'accent': '#90CAF9',
                'accent_light': '#1565C0',
                'success': '#81C784',
                'warning': '#FFB74D',
                'error': '#E57373',
                'border': '#333333',
                'card_background': '#1E1E1E',
                'sidebar_background': '#0D0D0D',
                'header_background': '#1565C0',
                'header_text': '#FFFFFF'
            }
        }
    }

    # CSS für Streamlit
    STREAMLIT_CSS = {
        ThemeTyp.LIGHT: """
<style>
    /* Light Theme */
    .stApp {
        background-color: #FFFFFF;
    }
    .stSidebar {
        background-color: #FAFAFA;
    }
    .stButton>button {
        background-color: #1976D2;
        color: white;
    }
    .stButton>button:hover {
        background-color: #1565C0;
    }
</style>
""",
        ThemeTyp.DARK: """
<style>
    /* Dark Theme */
    .stApp {
        background-color: #121212;
        color: #FFFFFF;
    }
    .stSidebar {
        background-color: #0D0D0D;
    }
    .stSidebar .stMarkdown {
        color: #FFFFFF;
    }
    .stButton>button {
        background-color: #1565C0;
        color: white;
    }
    .stButton>button:hover {
        background-color: #1976D2;
    }
    .stTextInput>div>div>input {
        background-color: #1E1E1E;
        color: #FFFFFF;
    }
    .stSelectbox>div>div>div {
        background-color: #1E1E1E;
        color: #FFFFFF;
    }
    .stDataFrame {
        background-color: #1E1E1E;
    }
    .stMetric {
        background-color: #1E1E1E;
        border-radius: 5px;
        padding: 10px;
    }
    .stExpander {
        background-color: #1E1E1E;
        border-color: #333333;
    }
    .stTabs [data-baseweb="tab-list"] {
        background-color: #1E1E1E;
    }
    .stTabs [data-baseweb="tab"] {
        color: #FFFFFF;
    }
    div[data-testid="stMetricValue"] {
        color: #FFFFFF;
    }
    div[data-testid="stMetricLabel"] {
        color: #B0B0B0;
    }
    .stAlert {
        background-color: #1E1E1E;
    }
    h1, h2, h3, h4, h5, h6 {
        color: #FFFFFF !important;
    }
    p, span, div {
        color: #E0E0E0;
    }
    .stMarkdown a {
        color: #90CAF9;
    }
</style>
"""
    }

    def __init__(self, db_session):
        self.db = db_session

    def theme_laden(self, user_id: int) -> Dict[str, Any]:
        """Lädt das Theme eines Benutzers"""
        einstellung = self.db.query(BenutzerTheme).filter(
            BenutzerTheme.user_id == user_id
        ).first()

        if not einstellung:
            # Standard-Theme
            return {
                'typ': ThemeTyp.LIGHT,
                **self.THEMES[ThemeTyp.LIGHT]
            }

        theme_typ = ThemeTyp(einstellung.theme_typ)

        if theme_typ == ThemeTyp.CUSTOM:
            return {
                'typ': ThemeTyp.CUSTOM,
                'name': 'Benutzerdefiniert',
                'farben': einstellung.custom_farben or self.THEMES[ThemeTyp.LIGHT]['farben']
            }

        return {
            'typ': theme_typ,
            **self.THEMES.get(theme_typ, self.THEMES[ThemeTyp.LIGHT])
        }

    def theme_speichern(
        self,
        user_id: int,
        theme_typ: ThemeTyp,
        custom_farben: Optional[Dict[str, str]] = None,
        schriftgroesse: str = "normal",
        kompakt_modus: bool = False
    ) -> BenutzerTheme:
        """Speichert Theme-Einstellungen"""
        einstellung = self.db.query(BenutzerTheme).filter(
            BenutzerTheme.user_id == user_id
        ).first()

        if not einstellung:
            einstellung = BenutzerTheme(user_id=user_id)
            self.db.add(einstellung)

        einstellung.theme_typ = theme_typ.value
        einstellung.schriftgroesse = schriftgroesse
        einstellung.kompakt_modus = kompakt_modus

        if custom_farben:
            einstellung.custom_farben = custom_farben

        self.db.flush()

        return einstellung

    def css_generieren(self, user_id: int) -> str:
        """Generiert CSS für das Benutzer-Theme"""
        einstellung = self.db.query(BenutzerTheme).filter(
            BenutzerTheme.user_id == user_id
        ).first()

        if not einstellung:
            return self.STREAMLIT_CSS[ThemeTyp.LIGHT]

        theme_typ = ThemeTyp(einstellung.theme_typ)

        if theme_typ == ThemeTyp.SYSTEM:
            # Browser-Präferenz - würde JavaScript benötigen
            return self.STREAMLIT_CSS[ThemeTyp.LIGHT]

        if theme_typ == ThemeTyp.CUSTOM and einstellung.custom_farben:
            return self._generiere_custom_css(einstellung.custom_farben)

        return self.STREAMLIT_CSS.get(theme_typ, self.STREAMLIT_CSS[ThemeTyp.LIGHT])

    def _generiere_custom_css(self, farben: Dict[str, str]) -> str:
        """Generiert CSS aus benutzerdefinierten Farben"""
        return f"""
<style>
    /* Custom Theme */
    .stApp {{
        background-color: {farben.get('background', '#FFFFFF')};
        color: {farben.get('text_primary', '#1E1E1E')};
    }}
    .stSidebar {{
        background-color: {farben.get('sidebar_background', '#FAFAFA')};
    }}
    .stButton>button {{
        background-color: {farben.get('accent', '#1976D2')};
        color: white;
    }}
    .stButton>button:hover {{
        background-color: {farben.get('accent_light', '#BBDEFB')};
    }}
    h1, h2, h3, h4, h5, h6 {{
        color: {farben.get('text_primary', '#1E1E1E')} !important;
    }}
    .stMetric {{
        background-color: {farben.get('card_background', '#FFFFFF')};
        border-radius: 5px;
        padding: 10px;
    }}
</style>
"""

    def schriftgroesse_css(self, groesse: str) -> str:
        """Generiert CSS für Schriftgröße"""
        groessen = {
            'small': '14px',
            'normal': '16px',
            'large': '18px'
        }

        font_size = groessen.get(groesse, '16px')

        return f"""
<style>
    .stApp {{
        font-size: {font_size};
    }}
</style>
"""

    def kompakt_modus_css(self, aktiviert: bool) -> str:
        """Generiert CSS für Kompakt-Modus"""
        if not aktiviert:
            return ""

        return """
<style>
    /* Kompakt-Modus */
    .stApp {
        padding: 0.5rem;
    }
    .block-container {
        padding: 1rem;
    }
    .stButton>button {
        padding: 0.25rem 0.75rem;
    }
    .stMetric {
        padding: 0.5rem;
    }
    h1 {
        font-size: 1.5rem;
    }
    h2 {
        font-size: 1.25rem;
    }
</style>
"""

    def alle_themes(self) -> Dict[str, Dict]:
        """Gibt alle verfügbaren Themes zurück"""
        return self.THEMES

    def farbe_validieren(self, farbe: str) -> bool:
        """Validiert eine Hex-Farbe"""
        import re
        return bool(re.match(r'^#[0-9A-Fa-f]{6}$', farbe))


def inject_theme_css(db_session, user_id: Optional[int] = None):
    """
    Hilfsfunktion zum Injizieren von Theme-CSS in Streamlit

    Verwendung in app.py:
    ```python
    from src.services.themes import inject_theme_css
    inject_theme_css(db, st.session_state.get('user_id'))
    ```
    """
    import streamlit as st

    service = ThemeService(db_session)

    if user_id:
        css = service.css_generieren(user_id)

        # Schriftgröße
        einstellung = db_session.query(BenutzerTheme).filter(
            BenutzerTheme.user_id == user_id
        ).first()

        if einstellung:
            css += service.schriftgroesse_css(einstellung.schriftgroesse)
            css += service.kompakt_modus_css(einstellung.kompakt_modus)
    else:
        css = service.STREAMLIT_CSS[ThemeTyp.LIGHT]

    st.markdown(css, unsafe_allow_html=True)
