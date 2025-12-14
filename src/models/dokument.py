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
    ocr_manuell_korrigiert = Column(Boolean, default=False)  # Wurde OCR manuell korrigiert?
    ocr_korrigiert_von_user_id = Column(Integer, ForeignKey("user.id"))
    ocr_korrigiert_am = Column(DateTime)
    ki_strukturierte_daten = Column(Text)  # JSON mit extrahierten Daten
    ki_daten_uebernommen = Column(Boolean, default=False)  # Wurden KI-Daten übernommen?
    ki_verarbeitet = Column(Boolean, default=False)
    ki_verarbeitet_am = Column(DateTime)

    # Sichtbarkeit (welche Rollen dürfen das Dokument sehen)
    sichtbarkeit = Column(String(255), default="ALLE")  # "ALLE" oder kommagetrennte Rollenliste

    # Freigabe-Status für Beteiligte
    freigabe_erforderlich = Column(Boolean, default=True)  # Muss freigegeben werden?
    freigabe_erteilt = Column(Boolean, default=False)      # Wurde Freigabe erteilt?
    freigabe_erteilt_von_user_id = Column(Integer, ForeignKey("user.id"))
    freigabe_erteilt_am = Column(DateTime)
    freigabe_abgelehnt = Column(Boolean, default=False)    # Freigabe dauerhaft abgelehnt?
    freigabe_abgelehnt_am = Column(DateTime)
    # User-IDs die Freigabe übersprungen haben (kommagetrennt) - diese werden nicht erneut gefragt
    freigabe_uebersprungen_von = Column(Text, default="")

    # Status
    status = Column(String(50), default="HOCHGELADEN")  # HOCHGELADEN, VERARBEITET, FEHLER
    beschreibung = Column(Text)
    notizen = Column(Text)

    # Papierkorb (Soft-Delete)
    geloescht = Column(Boolean, default=False)
    geloescht_am = Column(DateTime)
    geloescht_von_user_id = Column(Integer, ForeignKey("user.id"))
    urspruenglicher_pfad = Column(String(500))  # Original-Pfad vor dem Löschen

    # Timestamps
    erstellt_am = Column(DateTime, default=datetime.utcnow)
    aktualisiert_am = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    projekt = relationship("UnfallProjekt", back_populates="dokumente")
    hochgeladen_von = relationship("User", foreign_keys=[hochgeladen_von_user_id])
    ocr_korrigiert_von = relationship("User", foreign_keys=[ocr_korrigiert_von_user_id])
    freigabe_erteilt_von = relationship("User", foreign_keys=[freigabe_erteilt_von_user_id])
    geloescht_von = relationship("User", foreign_keys=[geloescht_von_user_id])

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

    def hat_freigabe_uebersprungen(self, user_id: int) -> bool:
        """Prüft ob ein Benutzer die Freigabe für dieses Dokument übersprungen hat"""
        if not self.freigabe_uebersprungen_von:
            return False
        uebersprungen_ids = [int(x.strip()) for x in self.freigabe_uebersprungen_von.split(",") if x.strip()]
        return user_id in uebersprungen_ids

    def freigabe_ueberspringen(self, user_id: int):
        """Markiert, dass ein Benutzer die Freigabe übersprungen hat"""
        if self.hat_freigabe_uebersprungen(user_id):
            return  # Bereits übersprungen

        if self.freigabe_uebersprungen_von:
            self.freigabe_uebersprungen_von += f",{user_id}"
        else:
            self.freigabe_uebersprungen_von = str(user_id)
