# Dokumenten-Chat Feature - Architekturplan

## 1. Übersicht

Ein KI-gestützter Chat, der es Benutzern ermöglicht, mit Dokumenten, Akten und der Datenbank zu kommunizieren. Anwälte erhalten zusätzlich die Möglichkeit, Schreiben zu generieren und zu versenden.

## 2. Architektur

```
┌─────────────────────────────────────────────────────────────────┐
│                        Chat UI (Streamlit)                       │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────┐ │
│  │ Chat-Verlauf     │  │ Dokument-Kontext │  │ Aktionen       │ │
│  │ (Nachrichten)    │  │ (ausgewählte     │  │ (nur Anwalt)   │ │
│  │                  │  │  Dokumente/Akte) │  │ - Schreiben    │ │
│  │                  │  │                  │  │ - Drucken      │ │
│  │                  │  │                  │  │ - E-Mail       │ │
│  └──────────────────┘  └──────────────────┘  └────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     DokumentenChatService                        │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ - chat(frage, projekt_id, user_rolle)                    │   │
│  │ - generiere_schreiben(typ, empfaenger, projekt_id)       │   │
│  │ - hole_relevante_dokumente(frage, projekt_id)            │   │
│  │ - speichere_zu_akte(inhalt, projekt_id)                  │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ VectorStore     │ │ Claude/OpenAI   │ │ EmailService    │
│ (ChromaDB)      │ │ (LLM)           │ │ (bestehend)     │
│                 │ │                 │ │                 │
│ - embeddings    │ │ - chat          │ │ - sende_email   │
│ - similarity    │ │ - generation    │ │                 │
│   search        │ │                 │ │                 │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

## 3. Neue Komponenten

### 3.1 VectorStoreService (`src/services/vector_store.py`)

```python
class VectorStoreService:
    """Verwaltet Vektor-Embeddings für semantische Dokumentensuche"""

    def __init__(self):
        self.client = chromadb.PersistentClient(path="./data/vectordb")
        self.collection = self.client.get_or_create_collection("dokumente")
        self.embeddings = OpenAIEmbeddings()  # oder Anthropic

    def indexiere_dokument(self, dokument_id: int, text: str, metadata: dict):
        """Fügt ein Dokument zum Vector Store hinzu"""

    def suche_aehnliche(self, query: str, projekt_id: int, limit: int = 5):
        """Findet semantisch ähnliche Dokumente"""

    def loesche_dokument(self, dokument_id: int):
        """Entfernt ein Dokument aus dem Index"""

    def reindexiere_projekt(self, projekt_id: int):
        """Reindexiert alle Dokumente eines Projekts"""
```

### 3.2 DokumentenChatService (`src/services/dokumenten_chat.py`)

```python
class DokumentenChatService:
    """Hauptservice für den Dokumenten-Chat"""

    def __init__(self, db: Session):
        self.db = db
        self.vector_store = VectorStoreService()
        self.ki_generator = KITextGenerator()
        self.email_service = EmailService()

    def chat(
        self,
        frage: str,
        projekt_id: int,
        user_id: int,
        user_rolle: Rollen,
        chat_verlauf: List[dict] = None
    ) -> ChatAntwort:
        """
        Beantwortet eine Frage zum Projekt/Dokumenten

        Returns:
            ChatAntwort mit:
            - antwort: str
            - quellen: List[Dokument]
            - vorschlaege: List[str] (nur für Anwalt)
            - schreiben_optionen: List[SchreibenOption] (nur für Anwalt)
        """

    def generiere_schreiben(
        self,
        schreiben_typ: SchreibenTyp,
        empfaenger: EmpfaengerTyp,
        projekt_id: int,
        zusatz_anweisungen: str = None
    ) -> GeneriertesDokument:
        """Generiert ein Schreiben basierend auf Typ und Empfänger"""

    def sende_als_email(
        self,
        dokument: GeneriertesDokument,
        empfaenger_email: str,
        projekt_id: int
    ) -> bool:
        """Sendet das Dokument per E-Mail und speichert zur Akte"""

    def exportiere_als_pdf(
        self,
        dokument: GeneriertesDokument,
        projekt_id: int
    ) -> bytes:
        """Exportiert als PDF und speichert zur Akte"""

    def drucken(
        self,
        dokument: GeneriertesDokument,
        projekt_id: int
    ) -> str:
        """Erstellt druckbares PDF und speichert zur Akte"""
```

### 3.3 Neue Enums und Models

```python
# In src/models/enums.py

class SchreibenTyp(PyEnum):
    """Typen von generierbaren Schreiben"""
    ANSPRUCHSSCHREIBEN = "ANSPRUCHSSCHREIBEN"
    KUERZUNGSERWIDERUNG = "KUERZUNGSERWIDERUNG"
    MAHNUNG = "MAHNUNG"
    MANDANTENINFORMATION = "MANDANTENINFORMATION"
    ANFRAGE = "ANFRAGE"
    STELLUNGNAHME = "STELLUNGNAHME"
    FREIES_SCHREIBEN = "FREIES_SCHREIBEN"

class EmpfaengerTyp(PyEnum):
    """Mögliche Empfänger von Schreiben"""
    VERSICHERUNG_GEGNER = "VERSICHERUNG_GEGNER"
    VERSICHERUNG_EIGEN = "VERSICHERUNG_EIGEN"
    POLIZEI = "POLIZEI"
    STAATSANWALTSCHAFT = "STAATSANWALTSCHAFT"
    MANDANT = "MANDANT"
    GEGNER = "GEGNER"
    WERKSTATT = "WERKSTATT"
    GUTACHTER = "GUTACHTER"
    GERICHT = "GERICHT"
    SONSTIG = "SONSTIG"


# Neues Model für Chat-Verlauf
class ChatNachricht(Base):
    """Speichert Chat-Verlauf pro Projekt"""
    __tablename__ = "chat_nachricht"

    id = Column(Integer, primary_key=True)
    unfallprojekt_id = Column(Integer, ForeignKey("unfallprojekt.id"))
    user_id = Column(Integer, ForeignKey("user.id"))

    rolle = Column(String(20))  # "user" oder "assistant"
    inhalt = Column(Text)

    # Referenzen zu verwendeten Dokumenten
    referenzierte_dokumente = Column(Text)  # JSON Array von Dokument-IDs

    # Generiertes Schreiben (falls vorhanden)
    generiertes_schreiben = Column(Text)
    schreiben_typ = Column(Enum(SchreibenTyp))
    empfaenger_typ = Column(Enum(EmpfaengerTyp))

    # Status des Schreibens
    schreiben_gesendet = Column(Boolean, default=False)
    schreiben_gedruckt = Column(Boolean, default=False)
    schreiben_gespeichert_als_dokument_id = Column(Integer, ForeignKey("dokument.id"))

    erstellt_am = Column(DateTime, default=datetime.utcnow)
```

## 4. UI-Komponenten

### 4.1 Chat-Seite (`src/ui/pages/dokumenten_chat.py`)

```python
def render_dokumenten_chat():
    """Hauptseite für den Dokumenten-Chat"""

    st.title("📝 Dokumenten-Chat")

    # Projekt-Auswahl
    projekt = _projekt_auswahl()

    if not projekt:
        st.info("Bitte wählen Sie ein Projekt aus")
        return

    # Layout: Chat links, Kontext rechts
    col_chat, col_kontext = st.columns([2, 1])

    with col_chat:
        _render_chat_bereich(projekt)

    with col_kontext:
        _render_kontext_bereich(projekt)


def _render_chat_bereich(projekt):
    """Rendert den Chat-Bereich"""

    # Chat-Verlauf anzeigen
    for msg in st.session_state.chat_verlauf:
        with st.chat_message(msg["rolle"]):
            st.markdown(msg["inhalt"])

            # Für Anwalt: Aktionen bei generierten Schreiben
            if msg.get("generiertes_schreiben") and ist_anwalt():
                _render_schreiben_aktionen(msg)

    # Eingabefeld
    if prompt := st.chat_input("Fragen Sie etwas zu diesem Fall..."):
        _verarbeite_frage(prompt, projekt)


def _render_schreiben_aktionen(nachricht):
    """Rendert Aktionen für ein generiertes Schreiben (nur Anwalt)"""

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("✏️ Bearbeiten", key=f"edit_{nachricht['id']}"):
            st.session_state.bearbeite_schreiben = nachricht

    with col2:
        if st.button("📧 Per E-Mail", key=f"email_{nachricht['id']}"):
            _sende_per_email(nachricht)

    with col3:
        if st.button("🖨️ Drucken", key=f"print_{nachricht['id']}"):
            _drucken(nachricht)

    with col4:
        if st.button("💾 Zur Akte", key=f"save_{nachricht['id']}"):
            _speichere_zur_akte(nachricht)
```

### 4.2 Anwalt-spezifische Schreiben-Generierung

```python
def _render_schreiben_generator(projekt):
    """Rendert den Schreiben-Generator (nur für Anwalt)"""

    st.markdown("### 📄 Schreiben generieren")

    col1, col2 = st.columns(2)

    with col1:
        schreiben_typ = st.selectbox(
            "Art des Schreibens",
            options=[
                ("Anspruchsschreiben", SchreibenTyp.ANSPRUCHSSCHREIBEN),
                ("Kürzungserwiderung", SchreibenTyp.KUERZUNGSERWIDERUNG),
                ("Mahnung", SchreibenTyp.MAHNUNG),
                ("Mandanteninformation", SchreibenTyp.MANDANTENINFORMATION),
                ("Anfrage", SchreibenTyp.ANFRAGE),
                ("Stellungnahme", SchreibenTyp.STELLUNGNAHME),
                ("Freies Schreiben", SchreibenTyp.FREIES_SCHREIBEN),
            ],
            format_func=lambda x: x[0]
        )

    with col2:
        empfaenger = st.selectbox(
            "Empfänger",
            options=[
                ("Gegnerische Versicherung", EmpfaengerTyp.VERSICHERUNG_GEGNER),
                ("Eigene Versicherung", EmpfaengerTyp.VERSICHERUNG_EIGEN),
                ("Polizei", EmpfaengerTyp.POLIZEI),
                ("Staatsanwaltschaft", EmpfaengerTyp.STAATSANWALTSCHAFT),
                ("Mandant", EmpfaengerTyp.MANDANT),
                ("Gegner", EmpfaengerTyp.GEGNER),
                ("Werkstatt", EmpfaengerTyp.WERKSTATT),
                ("Gutachter", EmpfaengerTyp.GUTACHTER),
                ("Gericht", EmpfaengerTyp.GERICHT),
                ("Sonstig", EmpfaengerTyp.SONSTIG),
            ],
            format_func=lambda x: x[0]
        )

    zusatz = st.text_area(
        "Zusätzliche Anweisungen (optional)",
        placeholder="z.B. 'Betone die Dringlichkeit' oder 'Erwähne das Gutachten vom 15.01.'"
    )

    if st.button("📝 Schreiben generieren", type="primary"):
        with st.spinner("Generiere Schreiben..."):
            service = DokumentenChatService(get_db())
            dokument = service.generiere_schreiben(
                schreiben_typ[1],
                empfaenger[1],
                projekt.id,
                zusatz
            )
            st.session_state.generiertes_schreiben = dokument
            st.rerun()
```

## 5. Implementierungsreihenfolge

### Phase 1: Basis-Infrastruktur (2-3 Tage)
1. ChromaDB installieren und VectorStoreService implementieren
2. Dokument-Indexierung beim Upload/OCR-Verarbeitung
3. ChatNachricht Model und Migration

### Phase 2: Chat-Service (2-3 Tage)
1. DokumentenChatService Grundstruktur
2. RAG-Pipeline: Suche + LLM-Antwort
3. Chat-Verlauf Speicherung

### Phase 3: Chat-UI (1-2 Tage)
1. Basis Chat-Interface
2. Projekt-Kontext Anzeige
3. Dokumenten-Referenzen

### Phase 4: Anwalt-Features (2-3 Tage)
1. Schreiben-Generierung erweitern
2. Empfänger-spezifische Prompts
3. Vorschläge für weiteres Vorgehen

### Phase 5: Aktionen & Integration (1-2 Tage)
1. E-Mail-Versand mit automatischer Speicherung
2. PDF-Export & Druck
3. Automatische Akte-Speicherung

### Phase 6: Testing & Feinschliff (1-2 Tage)
1. Rollenbasierte Tests
2. Performance-Optimierung
3. UI-Verbesserungen

## 6. Abhängigkeiten (requirements.txt)

```
chromadb>=0.4.0
langchain>=0.1.0
langchain-anthropic>=0.1.0
langchain-openai>=0.1.0
tiktoken>=0.5.0
```

## 7. Konfiguration (settings.py)

```python
# Vector Store
vector_store_path: str = "./data/vectordb"
embedding_model: str = "text-embedding-3-small"  # OpenAI
embedding_chunk_size: int = 1000
embedding_chunk_overlap: int = 200

# Chat
chat_max_context_docs: int = 5
chat_max_tokens: int = 4000
chat_temperature: float = 0.7
```

## 8. Sicherheit & Berechtigungen

- Jeder Benutzer sieht nur Chats zu Projekten, auf die er Zugriff hat
- Anwalt-Features sind strikt auf Rolle `ANWALT` beschränkt
- Generierte Schreiben werden mit Benutzer-ID und Zeitstempel gespeichert
- Audit-Log für alle generierten und versendeten Dokumente
