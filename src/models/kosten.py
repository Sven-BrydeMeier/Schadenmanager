from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, Enum, Boolean
from sqlalchemy.orm import relationship

from src.models.base import Base
from src.models.enums import KostenKategorie, KostenAmpel


class KostenPosition(Base):
    """Kostenposition mit Ampelstatus"""
    __tablename__ = "kostenposition"

    id = Column(Integer, primary_key=True)
    unfallprojekt_id = Column(Integer, ForeignKey("unfallprojekt.id"), nullable=False)

    # Kostendaten
    kategorie = Column(Enum(KostenKategorie), nullable=False)
    beschreibung = Column(String(255))
    betrag_netto = Column(Float)
    mwst_satz = Column(Float, default=19.0)
    betrag_brutto = Column(Float, nullable=False)

    # Ampelstatus
    status_ampel = Column(Enum(KostenAmpel), default=KostenAmpel.ROT)

    # Versicherungsentscheidung
    eingereicht_am = Column(DateTime)
    von_versicherung_freigegeben = Column(Boolean, default=False)
    von_versicherung_freigegeben_betrag = Column(Float)
    gekuerzt = Column(Boolean, default=False)
    kuerzung_betrag = Column(Float)
    kuerzung_grund = Column(Text)
    bemerkung_versicherung = Column(Text)
    entscheidung_am = Column(DateTime)

    # Zahlung
    bezahlt = Column(Boolean, default=False)
    bezahlt_betrag = Column(Float)
    bezahlt_am = Column(DateTime)

    # Referenzen
    referenz_dokument_id = Column(Integer, ForeignKey("dokument.id"))
    erstellt_von_user_id = Column(Integer, ForeignKey("user.id"))

    # Timestamps
    erstellt_am = Column(DateTime, default=datetime.utcnow)
    aktualisiert_am = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    projekt = relationship("UnfallProjekt", back_populates="kostenpositionen")
    referenz_dokument = relationship("Dokument")
    erstellt_von = relationship("User")

    def __repr__(self):
        return f"<KostenPosition(id={self.id}, kategorie={self.kategorie.value}, betrag={self.betrag_brutto}, ampel={self.status_ampel.value})>"

    @property
    def kategorie_anzeige(self) -> str:
        """Gibt einen lesbaren Kategorienamen zurück"""
        kategorie_namen = {
            KostenKategorie.REPARATUR: "Reparaturkosten",
            KostenKategorie.GUTACHTEN: "Gutachterkosten",
            KostenKategorie.ERSATZWAGEN: "Ersatzwagen/Mietwagen",
            KostenKategorie.NUTZUNGSAUSFALL: "Nutzungsausfall",
            KostenKategorie.WERTMINDERUNG: "Wertminderung",
            KostenKategorie.SONSTIG: "Sonstige Kosten",
            KostenKategorie.RA_GEBUEHREN: "Rechtsanwaltsgebühren"
        }
        return kategorie_namen.get(self.kategorie, self.kategorie.value)

    @property
    def ampel_farbe(self) -> str:
        """Gibt die CSS-Farbe für die Ampel zurück"""
        farben = {
            KostenAmpel.ROT: "#dc3545",
            KostenAmpel.ORANGE: "#fd7e14",
            KostenAmpel.GRUEN: "#28a745"
        }
        return farben.get(self.status_ampel, "#6c757d")

    @property
    def ampel_icon(self) -> str:
        """Gibt ein Icon für die Ampel zurück"""
        icons = {
            KostenAmpel.ROT: "🔴",
            KostenAmpel.ORANGE: "🟠",
            KostenAmpel.GRUEN: "🟢"
        }
        return icons.get(self.status_ampel, "⚪")

    @property
    def differenz_betrag(self) -> float:
        """Berechnet die Differenz zwischen gefordertem und freigegebenem Betrag"""
        freigegeben = self.von_versicherung_freigegeben_betrag or 0
        return self.betrag_brutto - freigegeben

    def berechne_brutto(self) -> float:
        """Berechnet den Bruttobetrag aus Netto und MwSt."""
        if self.betrag_netto:
            return round(self.betrag_netto * (1 + self.mwst_satz / 100), 2)
        return self.betrag_brutto or 0
