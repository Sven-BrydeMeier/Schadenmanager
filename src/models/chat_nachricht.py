"""
ChatNachricht Model - Speichert den Chat-Verlauf für den Dokumenten-Chat
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Enum, Boolean
from sqlalchemy.orm import relationship

from src.models.base import Base
from src.models.enums import SchreibenTyp, EmpfaengerTyp, ChatNachrichtRolle


class ChatNachricht(Base):
    """
    Speichert einzelne Nachrichten im Dokumenten-Chat.

    Jede Nachricht ist einem Projekt und Benutzer zugeordnet.
    Bei generierten Schreiben werden zusätzliche Metadaten gespeichert.
    """
    __tablename__ = "chat_nachricht"

    id = Column(Integer, primary_key=True)

    # Zuordnung
    unfallprojekt_id = Column(Integer, ForeignKey("unfallprojekt.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)

    # Nachrichteninhalt
    rolle = Column(Enum(ChatNachrichtRolle), nullable=False)  # user, assistant, system
    inhalt = Column(Text, nullable=False)

    # Referenzierte Dokumente (JSON Array von Dokument-IDs)
    referenzierte_dokumente = Column(Text)  # z.B. "[1, 2, 5]"

    # Generiertes Schreiben (falls vorhanden)
    generiertes_schreiben = Column(Text)  # Der generierte Text
    schreiben_typ = Column(Enum(SchreibenTyp))
    empfaenger_typ = Column(Enum(EmpfaengerTyp))

    # Empfänger-Details (für E-Mail-Versand)
    empfaenger_name = Column(String(255))
    empfaenger_email = Column(String(255))
    empfaenger_adresse = Column(Text)

    # Status des Schreibens
    schreiben_bearbeitet = Column(Boolean, default=False)  # Wurde manuell bearbeitet?
    schreiben_bearbeitet_am = Column(DateTime)
    schreiben_gesendet = Column(Boolean, default=False)  # Per E-Mail versendet?
    schreiben_gesendet_am = Column(DateTime)
    schreiben_gedruckt = Column(Boolean, default=False)  # Wurde gedruckt?
    schreiben_gedruckt_am = Column(DateTime)
    schreiben_geteilt = Column(Boolean, default=False)  # In Plattform geteilt?
    schreiben_geteilt_am = Column(DateTime)

    # Referenz zum gespeicherten Dokument (nach Versand/Druck/Teilen)
    schreiben_gespeichert_als_dokument_id = Column(Integer, ForeignKey("dokument.id"))

    # Vorschläge für weiteres Vorgehen (nur für Anwalt)
    vorschlaege = Column(Text)  # JSON Array von Vorschlägen

    # Timestamps
    erstellt_am = Column(DateTime, default=datetime.utcnow)

    # Relationships
    projekt = relationship("UnfallProjekt", backref="chat_nachrichten")
    user = relationship("User", foreign_keys=[user_id])
    gespeichertes_dokument = relationship("Dokument", foreign_keys=[schreiben_gespeichert_als_dokument_id])

    def __repr__(self):
        return f"<ChatNachricht(id={self.id}, rolle={self.rolle.value}, projekt={self.unfallprojekt_id})>"

    @property
    def hat_schreiben(self) -> bool:
        """Prüft ob diese Nachricht ein generiertes Schreiben enthält"""
        return bool(self.generiertes_schreiben)

    @property
    def schreiben_status(self) -> str:
        """Gibt den Status des Schreibens als Text zurück"""
        if not self.hat_schreiben:
            return "Kein Schreiben"

        if self.schreiben_gesendet:
            return "Versendet"
        elif self.schreiben_gedruckt:
            return "Gedruckt"
        elif self.schreiben_geteilt:
            return "Geteilt"
        elif self.schreiben_bearbeitet:
            return "Bearbeitet"
        else:
            return "Entwurf"

    def get_referenzierte_dokument_ids(self) -> list:
        """Gibt die Liste der referenzierten Dokument-IDs zurück"""
        if not self.referenzierte_dokumente:
            return []
        try:
            import json
            return json.loads(self.referenzierte_dokumente)
        except (json.JSONDecodeError, TypeError):
            return []

    def get_vorschlaege(self) -> list:
        """Gibt die Liste der Vorschläge zurück"""
        if not self.vorschlaege:
            return []
        try:
            import json
            return json.loads(self.vorschlaege)
        except (json.JSONDecodeError, TypeError):
            return []
