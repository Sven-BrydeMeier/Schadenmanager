"""
CSS-Styles für die Streamlit-Anwendung
"""

# Hauptfarben
COLORS = {
    "primary": "#2563eb",      # Blau
    "secondary": "#64748b",    # Grau
    "success": "#28a745",      # Grün
    "warning": "#fd7e14",      # Orange
    "danger": "#dc3545",       # Rot
    "info": "#0dcaf0",         # Cyan
    "light": "#f8f9fa",        # Hellgrau
    "dark": "#212529",         # Dunkelgrau
    "background": "#f0f2f6",   # Hintergrund
    "card": "#ffffff",         # Card-Hintergrund
}

# Ampelfarben
AMPEL_COLORS = {
    "ROT": "#dc3545",
    "ORANGE": "#fd7e14",
    "GRUEN": "#28a745"
}

# Globales CSS
GLOBAL_CSS = """
<style>
/* Hintergrund der Hauptseite */
.stApp {
    background-color: #f0f2f6;
}

/* Sidebar-Styling */
[data-testid="stSidebar"] {
    background-color: #1e293b;
}

[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
    color: #e2e8f0;
}

[data-testid="stSidebar"] .stSelectbox label {
    color: #e2e8f0;
}

/* Card-Container */
.card {
    background-color: white;
    border-radius: 12px;
    padding: 1.5rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.08);
    margin-bottom: 1rem;
}

.card-header {
    font-size: 1.25rem;
    font-weight: 600;
    color: #1e293b;
    margin-bottom: 1rem;
    padding-bottom: 0.75rem;
    border-bottom: 1px solid #e2e8f0;
}

.card-body {
    color: #475569;
}

/* Status-Badges */
.badge {
    display: inline-block;
    padding: 0.25rem 0.75rem;
    border-radius: 9999px;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
}

.badge-success { background-color: #dcfce7; color: #166534; }
.badge-warning { background-color: #fef3c7; color: #92400e; }
.badge-danger { background-color: #fee2e2; color: #991b1b; }
.badge-info { background-color: #e0f2fe; color: #075985; }
.badge-secondary { background-color: #f1f5f9; color: #475569; }

/* Ampel-Punkte */
.ampel {
    display: inline-block;
    width: 12px;
    height: 12px;
    border-radius: 50%;
    margin-right: 8px;
}

.ampel-rot { background-color: #dc3545; }
.ampel-orange { background-color: #fd7e14; }
.ampel-gruen { background-color: #28a745; }

/* Timeline */
.timeline {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem 0;
    overflow-x: auto;
}

.timeline-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    min-width: 100px;
    text-align: center;
}

.timeline-dot {
    width: 24px;
    height: 24px;
    border-radius: 50%;
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-size: 12px;
}

.timeline-label {
    font-size: 0.75rem;
    color: #64748b;
    max-width: 80px;
}

.timeline-connector {
    flex-grow: 1;
    height: 2px;
    background-color: #e2e8f0;
    margin: 0 8px;
}

/* Kosten-Tabelle */
.kosten-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.75rem 0;
    border-bottom: 1px solid #e2e8f0;
}

.kosten-row:last-child {
    border-bottom: none;
}

.kosten-label {
    display: flex;
    align-items: center;
    color: #1e293b;
}

.kosten-betrag {
    font-weight: 600;
    color: #1e293b;
}

.kosten-betrag.gekuerzt {
    color: #dc3545;
    text-decoration: line-through;
}

/* Metric Cards */
.metric-card {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-radius: 12px;
    padding: 1.5rem;
    color: white;
}

.metric-card.success {
    background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
}

.metric-card.warning {
    background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
}

.metric-card.info {
    background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
}

.metric-value {
    font-size: 2rem;
    font-weight: 700;
    margin-bottom: 0.25rem;
}

.metric-label {
    font-size: 0.875rem;
    opacity: 0.9;
}

/* Button-Styling */
.stButton > button {
    border-radius: 8px;
    font-weight: 500;
    transition: all 0.2s ease;
}

.stButton > button:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
}

/* Form-Inputs */
.stTextInput > div > div > input,
.stSelectbox > div > div > div,
.stTextArea > div > div > textarea {
    border-radius: 8px;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
}

.stTabs [data-baseweb="tab"] {
    border-radius: 8px 8px 0 0;
    padding: 0.75rem 1.5rem;
}

/* Expander */
.streamlit-expanderHeader {
    font-weight: 600;
    color: #1e293b;
}

/* Alert-Boxen */
.alert {
    padding: 1rem;
    border-radius: 8px;
    margin-bottom: 1rem;
}

.alert-success {
    background-color: #dcfce7;
    border-left: 4px solid #28a745;
    color: #166534;
}

.alert-warning {
    background-color: #fef3c7;
    border-left: 4px solid #fd7e14;
    color: #92400e;
}

.alert-danger {
    background-color: #fee2e2;
    border-left: 4px solid #dc3545;
    color: #991b1b;
}

.alert-info {
    background-color: #e0f2fe;
    border-left: 4px solid #0dcaf0;
    color: #075985;
}

/* Responsive Anpassungen */
@media (max-width: 768px) {
    .card {
        padding: 1rem;
    }

    .timeline {
        flex-wrap: wrap;
    }

    .timeline-item {
        min-width: 80px;
    }
}
</style>
"""


def inject_css():
    """Injiziert das globale CSS in die Streamlit-App"""
    import streamlit as st
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)
