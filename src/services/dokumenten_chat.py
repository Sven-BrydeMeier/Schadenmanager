"""
DokumentenChatService - Hauptservice für den KI-gestützten Dokumenten-Chat

Ermöglicht das Chatten mit Dokumenten, Akten und der Datenbank.
Anwälte erhalten zusätzlich Schreiben-Generierung und Vorschläge.
"""

import json
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
from dataclasses import dataclass

from sqlalchemy.orm import Session

from src.models import (
    UnfallProjekt, Dokument, User, Rollen,
    SchreibenTyp, EmpfaengerTyp, ChatNachrichtRolle
)
from src.models.chat_nachricht import ChatNachricht
from src.config.settings import get_settings
from src.services.vector_store import VectorStoreService
from src.services.korrespondenz_embeddings import get_korrespondenz_embedding_service


@dataclass
class ChatAntwort:
    """Antwort vom Chat-Service"""
    antwort: str
    quellen: List[Dict[str, Any]]  # Referenzierte Dokumente
    vorschlaege: List[str]  # Vorschläge für weiteres Vorgehen (nur Anwalt)
    schreiben_optionen: List[Dict[str, str]]  # Mögliche Schreiben-Typen (nur Anwalt)


@dataclass
class GeneriertesDokument:
    """Ein vom Chat generiertes Dokument/Schreiben"""
    inhalt: str
    schreiben_typ: SchreibenTyp
    empfaenger_typ: EmpfaengerTyp
    empfaenger_name: Optional[str] = None
    empfaenger_email: Optional[str] = None
    empfaenger_adresse: Optional[str] = None
    betreff: Optional[str] = None


class DokumentenChatService:
    """
    Hauptservice für den Dokumenten-Chat.

    Kombiniert:
    - Semantische Suche in Dokumenten (VectorStore)
    - LLM-basierte Antwortgenerierung
    - Schreiben-Generierung für Anwälte
    - E-Mail-Versand und PDF-Export
    """

    # System-Prompts für verschiedene Rollen
    SYSTEM_PROMPTS = {
        Rollen.ANWALT: """Du bist ein KI-Assistent für einen Rechtsanwalt, spezialisiert auf Verkehrsrecht und Schadensregulierung in Deutschland.

Deine Aufgaben:
1. Beantworte Fragen zu Akten und Dokumenten präzise und fachlich
2. Schlage proaktiv nächste Schritte vor
3. Identifiziere fehlende Informationen oder Dokumente
4. Weise auf Fristen und wichtige Termine hin
5. Hilf bei der Formulierung von Schreiben

Verwende korrekte rechtliche Terminologie (BGB, StVG, etc.).
Antworte auf Deutsch.""",

        Rollen.UNFALLOPFER: """Du bist ein freundlicher KI-Assistent für Mandanten (Unfallopfer) einer Anwaltskanzlei.

Deine Aufgaben:
1. Erkläre den Stand des Verfahrens in einfacher Sprache
2. Beantworte Fragen zu hochgeladenen Dokumenten verständlich
3. Erkläre rechtliche Begriffe für Laien
4. Sei empathisch und beruhigend

Verwende KEINE komplizierte Juristensprache.
Antworte auf Deutsch.""",

        "default": """Du bist ein hilfreicher KI-Assistent für ein Schadensmanagement-System.

Beantworte Fragen zu Dokumenten und Akten präzise und hilfreich.
Antworte auf Deutsch."""
    }

    # Schreiben-Typ Beschreibungen für Prompts
    SCHREIBEN_BESCHREIBUNGEN = {
        SchreibenTyp.ANSPRUCHSSCHREIBEN: "Formelles Anspruchsschreiben zur Geltendmachung von Schadensersatzansprüchen",
        SchreibenTyp.KUERZUNGSERWIDERUNG: "Erwiderung auf ein Kürzungsschreiben der Versicherung",
        SchreibenTyp.MAHNUNG: "Mahnung wegen ausstehender Zahlung oder Reaktion",
        SchreibenTyp.MANDANTENINFORMATION: "Verständliche Information an den Mandanten über den Verfahrensstand",
        SchreibenTyp.ANFRAGE: "Höfliche Anfrage um Informationen oder Unterlagen",
        SchreibenTyp.STELLUNGNAHME: "Rechtliche Stellungnahme zu einem Sachverhalt",
        SchreibenTyp.AUFFORDERUNG: "Aufforderung zur Handlung mit Fristsetzung",
        SchreibenTyp.FREIES_SCHREIBEN: "Individuelles Schreiben nach Vorgabe"
    }

    # Empfänger-spezifische Hinweise
    EMPFAENGER_HINWEISE = {
        EmpfaengerTyp.VERSICHERUNG_GEGNER: "Formell, bestimmt, mit rechtlichen Grundlagen",
        EmpfaengerTyp.VERSICHERUNG_EIGEN: "Sachlich, kooperativ",
        EmpfaengerTyp.POLIZEI: "Formell, sachlich, mit Aktenzeichen-Referenz",
        EmpfaengerTyp.STAATSANWALTSCHAFT: "Sehr formell, juristisch präzise",
        EmpfaengerTyp.MANDANT: "Verständlich, empathisch, ohne Juristendeutsch",
        EmpfaengerTyp.GEGNER: "Sachlich, bestimmt, aber nicht aggressiv",
        EmpfaengerTyp.WERKSTATT: "Sachlich, technisch orientiert",
        EmpfaengerTyp.GUTACHTER: "Fachlich, technisch präzise",
        EmpfaengerTyp.GERICHT: "Höchst formell, juristisch korrekt, mit Aktenzeichen",
        EmpfaengerTyp.SONSTIG: "Angemessen formell"
    }

    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()
        self._vector_store = None
        self._korrespondenz_embeddings = None

    @property
    def vector_store(self) -> VectorStoreService:
        """Lazy initialization des VectorStoreService"""
        if self._vector_store is None:
            self._vector_store = VectorStoreService()
        return self._vector_store

    @property
    def korrespondenz_embeddings(self):
        """Lazy initialization des KorrespondenzEmbeddingService"""
        if self._korrespondenz_embeddings is None:
            self._korrespondenz_embeddings = get_korrespondenz_embedding_service()
        return self._korrespondenz_embeddings

    def chat(
        self,
        frage: str,
        projekt_id: int,
        user_id: int,
        user_rolle: Rollen,
        chat_verlauf: Optional[List[Dict[str, str]]] = None
    ) -> ChatAntwort:
        """
        Beantwortet eine Frage zum Projekt/Dokumenten.

        Args:
            frage: Die Benutzerfrage
            projekt_id: ID des Projekts
            user_id: ID des Benutzers
            user_rolle: Rolle des Benutzers
            chat_verlauf: Bisheriger Chat-Verlauf

        Returns:
            ChatAntwort mit Antwort, Quellen und ggf. Vorschlägen
        """
        # Projekt laden
        projekt = self.db.query(UnfallProjekt).filter(
            UnfallProjekt.id == projekt_id
        ).first()

        if not projekt:
            return ChatAntwort(
                antwort="Projekt nicht gefunden.",
                quellen=[],
                vorschlaege=[],
                schreiben_optionen=[]
            )

        # Relevante Dokumente suchen
        relevante_docs = self._suche_relevante_dokumente(frage, projekt_id)

        # Projekt-Kontext sammeln
        projekt_kontext = self._sammle_projekt_kontext(projekt)

        # Antwort generieren
        antwort, quellen_ids = self._generiere_antwort(
            frage=frage,
            projekt_kontext=projekt_kontext,
            relevante_docs=relevante_docs,
            user_rolle=user_rolle,
            chat_verlauf=chat_verlauf
        )

        # Vorschläge und Schreiben-Optionen (nur für Anwalt)
        vorschlaege = []
        schreiben_optionen = []

        if user_rolle == Rollen.ANWALT:
            vorschlaege = self._generiere_vorschlaege(projekt, frage, antwort)
            schreiben_optionen = self._get_schreiben_optionen(projekt)

        # Quellen formatieren
        quellen = self._formatiere_quellen(quellen_ids)

        # Chat-Nachricht speichern
        self._speichere_nachricht(
            projekt_id=projekt_id,
            user_id=user_id,
            rolle=ChatNachrichtRolle.USER,
            inhalt=frage
        )

        self._speichere_nachricht(
            projekt_id=projekt_id,
            user_id=user_id,
            rolle=ChatNachrichtRolle.ASSISTANT,
            inhalt=antwort,
            referenzierte_dokumente=quellen_ids,
            vorschlaege=vorschlaege
        )

        return ChatAntwort(
            antwort=antwort,
            quellen=quellen,
            vorschlaege=vorschlaege,
            schreiben_optionen=schreiben_optionen
        )

    def generiere_schreiben(
        self,
        schreiben_typ: SchreibenTyp,
        empfaenger_typ: EmpfaengerTyp,
        projekt_id: int,
        user_id: int,
        zusatz_anweisungen: Optional[str] = None
    ) -> Tuple[Optional[GeneriertesDokument], str]:
        """
        Generiert ein Schreiben basierend auf Typ und Empfänger.

        Args:
            schreiben_typ: Art des Schreibens
            empfaenger_typ: Typ des Empfängers
            projekt_id: ID des Projekts
            user_id: ID des Benutzers
            zusatz_anweisungen: Zusätzliche Anweisungen

        Returns:
            Tuple aus (GeneriertesDokument oder None, Fehlermeldung)
        """
        # Projekt laden
        projekt = self.db.query(UnfallProjekt).filter(
            UnfallProjekt.id == projekt_id
        ).first()

        if not projekt:
            return None, "Projekt nicht gefunden"

        # Empfänger-Daten ermitteln
        empfaenger_daten = self._ermittle_empfaenger(projekt, empfaenger_typ)

        # Projekt-Kontext
        kontext = self._sammle_projekt_kontext(projekt)

        # Stil-Referenzen aus vergangenen Korrespondenzen suchen
        stil_referenzen = self._hole_stil_referenzen(
            schreiben_typ=schreiben_typ,
            empfaenger_typ=empfaenger_typ,
            projekt_id=projekt_id
        )

        # Prompt erstellen
        prompt = self._erstelle_schreiben_prompt(
            schreiben_typ=schreiben_typ,
            empfaenger_typ=empfaenger_typ,
            empfaenger_daten=empfaenger_daten,
            projekt_kontext=kontext,
            zusatz_anweisungen=zusatz_anweisungen,
            stil_referenzen=stil_referenzen
        )

        # KI aufrufen
        inhalt, fehler = self._call_ki(prompt)

        if fehler:
            return None, fehler

        # Dokument erstellen
        dokument = GeneriertesDokument(
            inhalt=inhalt,
            schreiben_typ=schreiben_typ,
            empfaenger_typ=empfaenger_typ,
            empfaenger_name=empfaenger_daten.get("name"),
            empfaenger_email=empfaenger_daten.get("email"),
            empfaenger_adresse=empfaenger_daten.get("adresse"),
            betreff=self._generiere_betreff(schreiben_typ, projekt)
        )

        # Als Chat-Nachricht speichern
        self._speichere_nachricht(
            projekt_id=projekt_id,
            user_id=user_id,
            rolle=ChatNachrichtRolle.ASSISTANT,
            inhalt=f"Schreiben generiert: {schreiben_typ.value} an {empfaenger_typ.value}",
            generiertes_schreiben=inhalt,
            schreiben_typ=schreiben_typ,
            empfaenger_typ=empfaenger_typ
        )

        return dokument, ""

    def speichere_zur_akte(
        self,
        generiertes_dokument: GeneriertesDokument,
        projekt_id: int,
        user_id: int,
        aktion: str = "erstellt"  # "gesendet", "gedruckt", "geteilt"
    ) -> Optional[Dokument]:
        """
        Speichert ein generiertes Dokument zur Akte.

        Args:
            generiertes_dokument: Das zu speichernde Dokument
            projekt_id: ID des Projekts
            user_id: ID des Benutzers
            aktion: Art der Aktion (für Dateinamen)

        Returns:
            Das erstellte Dokument-Objekt oder None
        """
        import os
        from src.models.enums import DokumentTyp

        # Dateiname generieren
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        typ_name = generiertes_dokument.schreiben_typ.value.lower()
        dateiname = f"{typ_name}_{timestamp}.txt"

        # Pfad erstellen
        upload_folder = self.settings.upload_folder
        projekt_folder = os.path.join(upload_folder, str(projekt_id), "schreiben")
        os.makedirs(projekt_folder, exist_ok=True)

        dateipfad = os.path.join(projekt_folder, dateiname)

        # Inhalt mit Metadaten speichern
        inhalt_mit_meta = f"""Generiert am: {datetime.now().strftime("%d.%m.%Y %H:%M")}
Typ: {generiertes_dokument.schreiben_typ.value}
Empfänger: {generiertes_dokument.empfaenger_typ.value}
Aktion: {aktion}

---

{generiertes_dokument.inhalt}
"""

        with open(dateipfad, 'w', encoding='utf-8') as f:
            f.write(inhalt_mit_meta)

        # Dokument in DB erstellen
        dokument = Dokument(
            unfallprojekt_id=projekt_id,
            hochgeladen_von_user_id=user_id,
            dokument_typ=DokumentTyp.ANSPRUCHSSCHREIBEN,  # oder passenden Typ
            original_dateiname=dateiname,
            dateipfad=dateipfad,
            mime_typ="text/plain",
            dateigroesse=len(inhalt_mit_meta.encode('utf-8')),
            sichtbarkeit="ANWALT",  # Nur Anwalt sieht generierte Schreiben
            freigabe_erforderlich=False,
            freigabe_erteilt=True
        )

        self.db.add(dokument)
        self.db.commit()
        self.db.refresh(dokument)

        # Im VectorStore indexieren
        try:
            self.vector_store.indexiere_dokument(
                dokument_id=dokument.id,
                text=generiertes_dokument.inhalt,
                metadata={
                    "unfallprojekt_id": projekt_id,
                    "dokument_typ": "GENERIERTES_SCHREIBEN",
                    "schreiben_typ": generiertes_dokument.schreiben_typ.value,
                    "empfaenger_typ": generiertes_dokument.empfaenger_typ.value
                }
            )
        except Exception:
            pass  # Indexierung ist optional

        return dokument

    def get_chat_verlauf(
        self,
        projekt_id: int,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Lädt den Chat-Verlauf für ein Projekt.

        Args:
            projekt_id: ID des Projekts
            limit: Maximale Anzahl Nachrichten

        Returns:
            Liste von Chat-Nachrichten
        """
        nachrichten = self.db.query(ChatNachricht).filter(
            ChatNachricht.unfallprojekt_id == projekt_id
        ).order_by(
            ChatNachricht.erstellt_am.asc()
        ).limit(limit).all()

        return [
            {
                "id": n.id,
                "rolle": n.rolle.value,
                "inhalt": n.inhalt,
                "erstellt_am": n.erstellt_am.isoformat() if n.erstellt_am else None,
                "hat_schreiben": n.hat_schreiben,
                "schreiben_typ": n.schreiben_typ.value if n.schreiben_typ else None,
                "schreiben_status": n.schreiben_status,
                "vorschlaege": n.get_vorschlaege(),
                "quellen": n.get_referenzierte_dokument_ids()
            }
            for n in nachrichten
        ]

    def indexiere_dokument(self, dokument: Dokument) -> int:
        """
        Indexiert ein Dokument im VectorStore.

        Args:
            dokument: Das zu indexierende Dokument

        Returns:
            Anzahl der erstellten Chunks
        """
        text = dokument.ocr_text or ""

        if not text:
            return 0

        return self.vector_store.indexiere_dokument(
            dokument_id=dokument.id,
            text=text,
            metadata={
                "unfallprojekt_id": dokument.unfallprojekt_id,
                "dokument_typ": dokument.dokument_typ.value if dokument.dokument_typ else "SONSTIG",
                "dateiname": dokument.original_dateiname
            }
        )

    # === Private Hilfsmethoden ===

    def _suche_relevante_dokumente(
        self,
        frage: str,
        projekt_id: int
    ) -> List[Dict[str, Any]]:
        """Sucht relevante Dokumente zur Frage"""
        try:
            return self.vector_store.suche_aehnliche(
                query=frage,
                projekt_id=projekt_id,
                limit=self.settings.chat_max_context_docs
            )
        except Exception:
            return []

    def _sammle_projekt_kontext(self, projekt: UnfallProjekt) -> Dict[str, Any]:
        """Sammelt Kontext-Informationen zum Projekt"""
        # Fahrzeuge
        fahrzeug_eigen = None
        if projekt.kfz_eigen:
            fahrzeug_eigen = {
                "kennzeichen": projekt.kfz_eigen.kennzeichen,
                "hersteller": projekt.kfz_eigen.hersteller,
                "modell": projekt.kfz_eigen.modell
            }

        fahrzeug_gegner = None
        if projekt.kfz_gegner:
            fahrzeug_gegner = {
                "kennzeichen": projekt.kfz_gegner.kennzeichen,
                "hersteller": projekt.kfz_gegner.hersteller,
                "modell": projekt.kfz_gegner.modell
            }

        # Kostenpositionen
        kosten = []
        for kp in projekt.kostenpositionen:
            kosten.append({
                "kategorie": kp.kategorie.value if kp.kategorie else "SONSTIG",
                "beschreibung": kp.beschreibung,
                "betrag": kp.betrag_brutto,
                "status": kp.status_ampel.value if kp.status_ampel else "ROT"
            })

        return {
            "projektnummer": projekt.projektnummer,
            "aktenzeichen": projekt.aktenzeichen,
            "unfalldatum": projekt.datum_unfall.strftime("%d.%m.%Y") if projekt.datum_unfall else None,
            "unfallort": projekt.ort_unfall,
            "beschreibung": projekt.beschreibung_unfall,
            "schuld_prozent": projekt.schuld_eigen_prozent,
            "status": projekt.status.value if projekt.status else None,
            "fahrzeug_eigen": fahrzeug_eigen,
            "fahrzeug_gegner": fahrzeug_gegner,
            "kostenpositionen": kosten,
            "summe_gefordert": sum(k.get("betrag", 0) or 0 for k in kosten)
        }

    def _generiere_antwort(
        self,
        frage: str,
        projekt_kontext: Dict[str, Any],
        relevante_docs: List[Dict[str, Any]],
        user_rolle: Rollen,
        chat_verlauf: Optional[List[Dict[str, str]]] = None
    ) -> Tuple[str, List[int]]:
        """Generiert eine Antwort mittels LLM"""

        # Dokument-Kontext aufbereiten
        doc_context = ""
        quellen_ids = []

        for doc in relevante_docs:
            doc_context += f"\n---\nDokument {doc['dokument_id']}:\n{doc['chunk_text']}\n"
            if doc['dokument_id'] not in quellen_ids:
                quellen_ids.append(doc['dokument_id'])

        # Prompt erstellen
        system_prompt = self.SYSTEM_PROMPTS.get(user_rolle, self.SYSTEM_PROMPTS["default"])

        user_prompt = f"""AKTENKONTEXT:
{json.dumps(projekt_kontext, ensure_ascii=False, indent=2)}

RELEVANTE DOKUMENTE:
{doc_context if doc_context else "(Keine relevanten Dokumente gefunden)"}

FRAGE: {frage}

Beantworte die Frage basierend auf den verfügbaren Informationen.
Wenn du die Antwort nicht aus den Dokumenten ableiten kannst, sage das ehrlich."""

        # Chat-Verlauf einbeziehen
        messages = []
        if chat_verlauf:
            for msg in chat_verlauf[-5:]:  # Letzte 5 Nachrichten
                messages.append(msg)

        messages.append({"role": "user", "content": user_prompt})

        # KI aufrufen
        antwort, fehler = self._call_ki_with_messages(system_prompt, messages)

        if fehler:
            return f"Fehler bei der Verarbeitung: {fehler}", []

        return antwort, quellen_ids

    def _generiere_vorschlaege(
        self,
        projekt: UnfallProjekt,
        frage: str,
        antwort: str
    ) -> List[str]:
        """Generiert Vorschläge für weiteres Vorgehen (nur Anwalt)"""
        vorschlaege = []

        # Basierend auf Projekt-Status
        if projekt.status and projekt.status.value == "OFFEN":
            vorschlaege.append("Anspruchsschreiben an gegnerische Versicherung senden")

        # Prüfe auf offene Kostenpositionen
        offene_kosten = [kp for kp in projekt.kostenpositionen
                        if kp.status_ampel and kp.status_ampel.value == "ROT"]
        if offene_kosten:
            vorschlaege.append(f"{len(offene_kosten)} Kostenpositionen einreichen")

        # Prüfe auf Kürzungen
        gekuerzte = [kp for kp in projekt.kostenpositionen if kp.gekuerzt]
        if gekuerzte:
            vorschlaege.append("Kürzungserwiderung verfassen")

        # Allgemeine Vorschläge
        if not projekt.kfz_eigen:
            vorschlaege.append("Fahrzeugdaten vervollständigen")

        return vorschlaege[:5]  # Max 5 Vorschläge

    def _get_schreiben_optionen(self, projekt: UnfallProjekt) -> List[Dict[str, str]]:
        """Gibt verfügbare Schreiben-Optionen zurück"""
        optionen = []

        for typ in SchreibenTyp:
            optionen.append({
                "typ": typ.value,
                "name": typ.value.replace("_", " ").title(),
                "beschreibung": self.SCHREIBEN_BESCHREIBUNGEN.get(typ, "")
            })

        return optionen

    def _ermittle_empfaenger(
        self,
        projekt: UnfallProjekt,
        empfaenger_typ: EmpfaengerTyp
    ) -> Dict[str, Any]:
        """Ermittelt Empfänger-Daten basierend auf Typ"""
        # Hier könnten echte Daten aus der Datenbank geladen werden
        # Für jetzt: Platzhalter

        empfaenger_map = {
            EmpfaengerTyp.MANDANT: {
                "name": f"{projekt.unfallopfer.vorname} {projekt.unfallopfer.nachname}" if projekt.unfallopfer else "[Mandant]",
                "email": projekt.unfallopfer.email if projekt.unfallopfer else None
            },
            EmpfaengerTyp.VERSICHERUNG_GEGNER: {
                "name": "[Gegnerische Versicherung]",
                "email": None,
                "adresse": "[Adresse der Versicherung]"
            }
        }

        return empfaenger_map.get(empfaenger_typ, {
            "name": f"[{empfaenger_typ.value}]",
            "email": None
        })

    def _hole_stil_referenzen(
        self,
        schreiben_typ: SchreibenTyp,
        empfaenger_typ: EmpfaengerTyp,
        projekt_id: int,
        limit: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Holt Stil-Referenzen aus vergangenen Korrespondenzen.

        Args:
            schreiben_typ: Art des zu erstellenden Schreibens
            empfaenger_typ: Typ des Empfängers
            projekt_id: ID des aktuellen Projekts (wird ausgeschlossen)
            limit: Maximale Anzahl Referenzen

        Returns:
            Liste von Referenz-Texten mit Metadaten
        """
        try:
            # Kontext für die Suche
            kontext = f"{schreiben_typ.value} {empfaenger_typ.value}"

            referenzen = self.korrespondenz_embeddings.finde_stil_referenzen(
                schreiben_typ=schreiben_typ.value,
                empfaenger_typ=empfaenger_typ.value,
                kontext=kontext,
                limit=limit
            )

            # Nur Texte mit hohem Score verwenden
            return [r for r in referenzen if r.get('score', 0) > 0.5]

        except Exception:
            # Bei Fehlern einfach keine Referenzen zurückgeben
            return []

    def _erstelle_schreiben_prompt(
        self,
        schreiben_typ: SchreibenTyp,
        empfaenger_typ: EmpfaengerTyp,
        empfaenger_daten: Dict[str, Any],
        projekt_kontext: Dict[str, Any],
        zusatz_anweisungen: Optional[str] = None,
        stil_referenzen: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """Erstellt den Prompt für die Schreiben-Generierung"""

        typ_beschreibung = self.SCHREIBEN_BESCHREIBUNGEN.get(
            schreiben_typ,
            "Professionelles Schreiben"
        )

        empfaenger_hinweis = self.EMPFAENGER_HINWEISE.get(
            empfaenger_typ,
            "Angemessen formell"
        )

        # Stil-Referenzen formatieren
        referenz_text = ""
        if stil_referenzen:
            referenz_text = "\n\nSTIL-REFERENZEN (vergangene ähnliche Schreiben als Orientierung):\n"
            for i, ref in enumerate(stil_referenzen, 1):
                text = ref.get('text', '')
                # Text kürzen wenn zu lang
                if len(text) > 2000:
                    text = text[:2000] + "..."
                referenz_text += f"\n--- Referenz {i} ---\n{text}\n"
            referenz_text += "\nOrientiere dich am Stil dieser Referenzen, aber passe den Inhalt an die aktuellen Falldaten an.\n"

        prompt = f"""Erstelle ein {typ_beschreibung}.

EMPFÄNGER: {empfaenger_typ.value}
Empfänger-Name: {empfaenger_daten.get('name', '[Name]')}
Stil-Hinweis: {empfaenger_hinweis}

FALLDATEN:
{json.dumps(projekt_kontext, ensure_ascii=False, indent=2)}
{referenz_text}
ANFORDERUNGEN:
1. Professionelles Schreiben im angemessenen Stil
2. Korrektes Datum und Anrede
3. Klare Struktur mit Absätzen
4. Rechtlich korrekte Formulierungen
5. Handlungsaufforderung oder Fristsetzung wo angebracht

{f'ZUSÄTZLICHE ANWEISUNGEN: {zusatz_anweisungen}' if zusatz_anweisungen else ''}

Generiere das vollständige Schreiben:"""

        return prompt

    def _generiere_betreff(
        self,
        schreiben_typ: SchreibenTyp,
        projekt: UnfallProjekt
    ) -> str:
        """Generiert einen Betreff für das Schreiben"""
        az = projekt.aktenzeichen or projekt.projektnummer
        datum = projekt.datum_unfall.strftime("%d.%m.%Y") if projekt.datum_unfall else ""

        betreff_map = {
            SchreibenTyp.ANSPRUCHSSCHREIBEN: f"Schadensersatzansprüche - Unfall vom {datum}",
            SchreibenTyp.KUERZUNGSERWIDERUNG: f"Erwiderung auf Kürzungsschreiben - Az. {az}",
            SchreibenTyp.MAHNUNG: f"Mahnung - Az. {az}",
            SchreibenTyp.MANDANTENINFORMATION: f"Information zum Stand Ihres Verfahrens",
            SchreibenTyp.ANFRAGE: f"Anfrage - Az. {az}",
            SchreibenTyp.STELLUNGNAHME: f"Stellungnahme - Az. {az}",
            SchreibenTyp.AUFFORDERUNG: f"Aufforderung - Az. {az}"
        }

        return betreff_map.get(schreiben_typ, f"Az. {az}")

    def _speichere_nachricht(
        self,
        projekt_id: int,
        user_id: int,
        rolle: ChatNachrichtRolle,
        inhalt: str,
        referenzierte_dokumente: Optional[List[int]] = None,
        vorschlaege: Optional[List[str]] = None,
        generiertes_schreiben: Optional[str] = None,
        schreiben_typ: Optional[SchreibenTyp] = None,
        empfaenger_typ: Optional[EmpfaengerTyp] = None
    ) -> ChatNachricht:
        """Speichert eine Chat-Nachricht in der Datenbank"""

        nachricht = ChatNachricht(
            unfallprojekt_id=projekt_id,
            user_id=user_id,
            rolle=rolle,
            inhalt=inhalt,
            referenzierte_dokumente=json.dumps(referenzierte_dokumente) if referenzierte_dokumente else None,
            vorschlaege=json.dumps(vorschlaege) if vorschlaege else None,
            generiertes_schreiben=generiertes_schreiben,
            schreiben_typ=schreiben_typ,
            empfaenger_typ=empfaenger_typ
        )

        self.db.add(nachricht)
        self.db.commit()
        self.db.refresh(nachricht)

        return nachricht

    def _formatiere_quellen(self, dokument_ids: List[int]) -> List[Dict[str, Any]]:
        """Formatiert Dokument-IDs zu Quellen-Informationen"""
        if not dokument_ids:
            return []

        dokumente = self.db.query(Dokument).filter(
            Dokument.id.in_(dokument_ids)
        ).all()

        return [
            {
                "id": d.id,
                "dateiname": d.original_dateiname,
                "typ": d.dokument_typ.value if d.dokument_typ else "SONSTIG"
            }
            for d in dokumente
        ]

    def _call_ki(self, prompt: str) -> Tuple[Optional[str], str]:
        """Ruft die KI-API auf (einfacher Aufruf)"""
        return self._call_ki_with_messages(
            system_prompt=self.SYSTEM_PROMPTS[Rollen.ANWALT],
            messages=[{"role": "user", "content": prompt}]
        )

    def _call_ki_with_messages(
        self,
        system_prompt: str,
        messages: List[Dict[str, str]]
    ) -> Tuple[Optional[str], str]:
        """Ruft die KI-API mit vollständigen Messages auf"""
        try:
            if self.settings.ki_provider == "anthropic" and self.settings.anthropic_api_key:
                return self._call_anthropic(system_prompt, messages)
            elif self.settings.openai_api_key:
                return self._call_openai(system_prompt, messages)
            else:
                return None, "Keine KI-API konfiguriert. Bitte OPENAI_API_KEY oder ANTHROPIC_API_KEY setzen."
        except Exception as e:
            return None, f"KI-Fehler: {str(e)}"

    def _call_openai(
        self,
        system_prompt: str,
        messages: List[Dict[str, str]]
    ) -> Tuple[Optional[str], str]:
        """Ruft die OpenAI API auf"""
        try:
            from openai import OpenAI

            client = OpenAI(api_key=self.settings.openai_api_key)

            full_messages = [{"role": "system", "content": system_prompt}]
            full_messages.extend(messages)

            response = client.chat.completions.create(
                model="gpt-4o",
                messages=full_messages,
                temperature=self.settings.chat_temperature,
                max_tokens=self.settings.chat_max_tokens
            )

            return response.choices[0].message.content, ""

        except Exception as e:
            return None, f"OpenAI-Fehler: {str(e)}"

    def _call_anthropic(
        self,
        system_prompt: str,
        messages: List[Dict[str, str]]
    ) -> Tuple[Optional[str], str]:
        """Ruft die Anthropic API auf"""
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=self.settings.anthropic_api_key)

            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=self.settings.chat_max_tokens,
                system=system_prompt,
                messages=messages
            )

            return response.content[0].text, ""

        except Exception as e:
            return None, f"Anthropic-Fehler: {str(e)}"
