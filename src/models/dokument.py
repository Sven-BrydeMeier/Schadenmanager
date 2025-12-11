from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Enum, Boolean
from sqlalchemy.orm import relationship

from src.models.base import Base
from src.models.enums import DokumentTyp


class Dokument(Base):
    """Hochgeladene Dokumente mit OCR-Verarbeitung"""
    __tablename__ = "dokument"

    id = Column(Integer, primary_key=True)

    # Zuordnung
    unfallprojekt_id = Column(Integer, ForeignKey("unfallprojekt.id"), nullable=False)
    hochgeladen_von_user_id = Column(Integer, ForeignKey("user.id"))

    # Dokumentdaten
    dokument_typ = Column(Enum(DokumentTyp), default=DokumentTyp.SONSTIG)
    original_dateiname = Column(String(255))
    dateipfad = Column(String(500))
    mime_typ = Column(String(100))
    dateigroesse = Column(Integer)  # in Bytes

    # OCR und KI-Verarbeitung
    ocr_text = Column(Text)
    ocr_verarbeitet = Column(Boolean, default=False)
    ocr_verarbeitet_am = Column(DateTime)
    ki_strukturierte_daten = Column(Text)  # JSON mit extrahierten Daten
    ki_verarbeitet = Column(Boolean, default=False)
    ki_verarbeitet_am = Column(DateTime)

    # Sichtbarkeit (welche Rollen dürfen das Dokument sehen)
    sichtbarkeit = Column(String(255), default="ALLE")  # "ALLE" oder kommagetrennte Rollenliste

    # Status
    status = Column(String(50), default="HOCHGELADEN")  # HOCHGELADEN, VERARBEITET, FEHLER
    beschreibung = Column(Text)
    notizen = Column(Text)

    # Timestamps
    erstellt_am = Column(DateTime, default=datetime.utcnow)
    aktualisiert_am = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    projekt = relationship("UnfallProjekt", back_populates="dokumente")
    hochgeladen_von = relationship("User")

    def __repr__(self):
        return f"<Dokument(id={self.id}, typ={self.dokument_typ.value if self.dokument_typ else 'None'}, datei='{self.original_dateiname}')>"

    @property
    def dokument_typ_anzeige(self) -> str:
        """Gibt einen lesbaren Dokumenttyp zurück"""
        typ_namen = {
            DokumentTyp.FAHRZEUGSCHEIN: "Fahrzeugschein",
            DokumentTyp.PERSONALAUSWEIS: "Personalausweis",
            DokumentTyp.GUTACHTEN: "Gutachten",
            DokumentTyp.RECHNUNG: "Rechnung",
            DokumentTyp.VERSICHERUNGSSCHREIBEN: "Versicherungsschreiben",
            DokumentTyp.KUERZUNGSSCHREIBEN: "Kürzungsschreiben",
            DokumentTyp.ANSPRUCHSSCHREIBEN: "Anspruchsschreiben",
            DokumentTyp.SONSTIG: "Sonstiges"
        }
        return typ_namen.get(self.dokument_typ, "Unbekannt")

    def ist_sichtbar_fuer_rolle(self, rolle: str) -> bool:
        """Prüft ob das Dokument für eine bestimmte Rolle sichtbar ist"""
        if self.sichtbarkeit == "ALLE":
            return True
        erlaubte_rollen = [r.strip() for r in self.sichtbarkeit.split(",")]
        return rolle in erlaubte_rollen
