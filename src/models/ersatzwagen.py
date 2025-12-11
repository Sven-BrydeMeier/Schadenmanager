from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship

from src.models.base import Base


class ErsatzwagenAnbieter(Base):
    """Ersatzwagenanbieter (Mietwagen/Carsharing)"""
    __tablename__ = "ersatzwagenanbieter"

    id = Column(Integer, primary_key=True)
    organisation_id = Column(Integer, ForeignKey("organisation.id"))

    # Angebotstypen
    bietet_mietwagen = Column(Boolean, default=True)
    bietet_carsharing = Column(Boolean, default=False)

    # Konditionen
    mindestmietdauer_tage = Column(Integer, default=1)
    maximalmietdauer_tage = Column(Integer)
    kaution = Column(Float, default=0)

    # Lieferservice
    lieferung_moeglich = Column(Boolean, default=False)
    lieferung_kosten = Column(Float, default=0)
    lieferung_radius_km = Column(Integer)

    # Status
    aktiv = Column(Boolean, default=True)
    bemerkungen = Column(Text)

    # Timestamps
    erstellt_am = Column(DateTime, default=datetime.utcnow)
    aktualisiert_am = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    organisation = relationship("Organisation")
    angebote = relationship("MietfahrzeugAngebot", back_populates="anbieter", cascade="all, delete-orphan")

    def __repr__(self):
        org_name = self.organisation.name if self.organisation else "Unbekannt"
        return f"<ErsatzwagenAnbieter(id={self.id}, organisation='{org_name}')>"


class MietfahrzeugAngebot(Base):
    """Konkretes Mietfahrzeugangebot eines Anbieters"""
    __tablename__ = "mietfahrzeugangebot"

    id = Column(Integer, primary_key=True)
    ersatzwagenanbieter_id = Column(Integer, ForeignKey("ersatzwagenanbieter.id"), nullable=False)

    # Fahrzeugdetails
    fahrzeugkategorie = Column(String(100))  # z.B. "Kleinwagen", "Kompaktklasse", "SUV"
    fahrzeugklasse_schwacke = Column(String(50))  # Schwacke-Klassifizierung
    beispiel_modell = Column(String(100))  # z.B. "VW Golf oder ähnlich"

    # Preise
    tagespreis = Column(Float, nullable=False)
    wochenpreis = Column(Float)
    monatspreis = Column(Float)
    kilometerpreis = Column(Float, default=0)  # Preis pro zusätzlichem km
    freikilometer_pro_tag = Column(Integer, default=0)  # 0 = unbegrenzt

    # Zusatzkosten
    vollkasko_taeglich = Column(Float, default=0)
    zusatzfahrer_taeglich = Column(Float, default=0)

    # Verfügbarkeit
    verfuegbar = Column(Boolean, default=True)
    anzahl_fahrzeuge = Column(Integer, default=1)

    # Timestamps
    erstellt_am = Column(DateTime, default=datetime.utcnow)
    aktualisiert_am = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    anbieter = relationship("ErsatzwagenAnbieter", back_populates="angebote")

    def __repr__(self):
        return f"<MietfahrzeugAngebot(id={self.id}, kategorie='{self.fahrzeugkategorie}', tagespreis={self.tagespreis})>"

    def berechne_gesamtkosten(self, tage: int, kilometer: int = 0) -> float:
        """Berechnet die Gesamtkosten für eine Mietdauer"""
        # Grundpreis berechnen
        if self.monatspreis and tage >= 30:
            monate = tage // 30
            resttage = tage % 30
            grundpreis = (monate * self.monatspreis) + (resttage * self.tagespreis)
        elif self.wochenpreis and tage >= 7:
            wochen = tage // 7
            resttage = tage % 7
            grundpreis = (wochen * self.wochenpreis) + (resttage * self.tagespreis)
        else:
            grundpreis = tage * self.tagespreis

        # Kilometerkosten berechnen
        freikilometer = (self.freikilometer_pro_tag or 0) * tage
        zusatzkilometer = max(0, kilometer - freikilometer)
        kilometerkosten = zusatzkilometer * (self.kilometerpreis or 0)

        return round(grundpreis + kilometerkosten, 2)

    @property
    def kategorie_anzeige(self) -> str:
        """Gibt eine formatierte Kategorie-Anzeige zurück"""
        if self.beispiel_modell:
            return f"{self.fahrzeugkategorie} ({self.beispiel_modell})"
        return self.fahrzeugkategorie or "Unbekannte Kategorie"
