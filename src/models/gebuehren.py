from datetime import date, datetime
from sqlalchemy import Column, Integer, Float, Date, DateTime, Text, ForeignKey, String
from sqlalchemy.orm import relationship

from src.models.base import Base


class GebuehrenBerechnung(Base):
    """Berechnung der Rechtsanwaltsgebühren nach RVG"""
    __tablename__ = "gebuehrenberechnung"

    id = Column(Integer, primary_key=True)
    unfallprojekt_id = Column(Integer, ForeignKey("unfallprojekt.id"), nullable=False)

    # Streitwert (Basis für Gebührenberechnung)
    streitwert = Column(Float, nullable=False)

    # Gebührenbestandteile
    gebuehrenwert = Column(Float)  # Wert aus Gebührentabelle
    geschaeftsgebuehr_faktor = Column(Float, default=1.3)  # Standardmäßig 1,3
    geschaeftsgebuehr = Column(Float, nullable=False)

    einigungsgebuehr_faktor = Column(Float, default=0)  # Falls Einigung erzielt
    einigungsgebuehr = Column(Float, default=0)

    auslagenpauschale = Column(Float, default=20.0)  # Pauschale für Post/Telekommunikation
    dokumentenpauschale = Column(Float, default=0)
    reisekosten = Column(Float, default=0)
    sonstige_auslagen = Column(Float, default=0)

    # MwSt
    umsatzsteuer_satz = Column(Float, default=19.0)
    umsatzsteuer = Column(Float, default=0.0)

    # Gesamt
    zwischensumme_netto = Column(Float)
    gesamt_brutto = Column(Float, nullable=False)

    # Metadaten
    berechnungsart = Column(String(50), default="STANDARD")  # STANDARD, MANUELL
    bemerkungen = Column(Text)
    stand_datum = Column(Date, default=date.today)

    # Timestamps
    erstellt_am = Column(DateTime, default=datetime.utcnow)
    aktualisiert_am = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    projekt = relationship("UnfallProjekt", back_populates="gebuehrenberechnungen")

    def __repr__(self):
        return f"<GebuehrenBerechnung(id={self.id}, streitwert={self.streitwert}, gesamt={self.gesamt_brutto})>"

    @staticmethod
    def get_gebuehrenwert(streitwert: float) -> float:
        """
        Ermittelt den Gebührenwert aus der RVG-Tabelle (vereinfacht).
        Basiert auf Anlage 2 zu § 13 Abs. 1 RVG.
        """
        # Vereinfachte RVG-Gebührentabelle (Stand 2024)
        tabelle = [
            (500, 49.00),
            (1000, 88.00),
            (1500, 127.00),
            (2000, 166.00),
            (3000, 222.00),
            (4000, 278.00),
            (5000, 334.00),
            (6000, 390.00),
            (7000, 446.00),
            (8000, 502.00),
            (9000, 558.00),
            (10000, 614.00),
            (13000, 666.00),
            (16000, 718.00),
            (19000, 770.00),
            (22000, 822.00),
            (25000, 874.00),
            (30000, 955.00),
            (35000, 1036.00),
            (40000, 1117.00),
            (45000, 1198.00),
            (50000, 1279.00),
            (65000, 1373.00),
            (80000, 1467.00),
            (95000, 1561.00),
            (110000, 1655.00),
            (125000, 1749.00),
            (140000, 1843.00),
            (155000, 1937.00),
            (170000, 2031.00),
            (185000, 2125.00),
            (200000, 2219.00),
        ]

        for grenze, wert in tabelle:
            if streitwert <= grenze:
                return wert

        # Über 200.000 EUR: Formel anwenden
        return 2219.00 + ((streitwert - 200000) // 50000) * 198.00

    def berechne(self) -> None:
        """Führt die vollständige Gebührenberechnung durch"""
        # Gebührenwert aus Tabelle
        self.gebuehrenwert = self.get_gebuehrenwert(self.streitwert)

        # Geschäftsgebühr (Nr. 2300 VV RVG)
        faktor = self.geschaeftsgebuehr_faktor if self.geschaeftsgebuehr_faktor is not None else 1.3
        self.geschaeftsgebuehr = round(self.gebuehrenwert * faktor, 2)

        # Einigungsgebühr falls zutreffend (Nr. 1000 VV RVG)
        if self.einigungsgebuehr_faktor and self.einigungsgebuehr_faktor > 0:
            self.einigungsgebuehr = round(self.gebuehrenwert * self.einigungsgebuehr_faktor, 2)
        else:
            self.einigungsgebuehr = 0.0

        # Zwischensumme
        self.zwischensumme_netto = (
            (self.geschaeftsgebuehr or 0) +
            (self.einigungsgebuehr or 0) +
            (self.auslagenpauschale or 0) +
            (self.dokumentenpauschale or 0) +
            (self.reisekosten or 0) +
            (self.sonstige_auslagen or 0)
        )

        # Umsatzsteuer
        ust_satz = self.umsatzsteuer_satz if self.umsatzsteuer_satz is not None else 19.0
        self.umsatzsteuer = round(self.zwischensumme_netto * ust_satz / 100, 2)

        # Gesamtbetrag
        self.gesamt_brutto = round(self.zwischensumme_netto + self.umsatzsteuer, 2)

    @property
    def aufstellung(self) -> list:
        """Gibt eine detaillierte Aufstellung der Gebühren zurück"""
        positionen = [
            ("Gegenstandswert", f"{self.streitwert:,.2f} €"),
            ("Gebührenwert (aus Tabelle)", f"{self.gebuehrenwert:,.2f} €"),
            ("", ""),
            (f"Geschäftsgebühr ({self.geschaeftsgebuehr_faktor:.1f}-fach)", f"{self.geschaeftsgebuehr:,.2f} €"),
        ]

        if self.einigungsgebuehr > 0:
            positionen.append(
                (f"Einigungsgebühr ({self.einigungsgebuehr_faktor:.1f}-fach)", f"{self.einigungsgebuehr:,.2f} €")
            )

        positionen.extend([
            ("Auslagenpauschale (Nr. 7002 VV RVG)", f"{self.auslagenpauschale:,.2f} €"),
        ])

        if self.dokumentenpauschale > 0:
            positionen.append(("Dokumentenpauschale", f"{self.dokumentenpauschale:,.2f} €"))
        if self.reisekosten > 0:
            positionen.append(("Reisekosten", f"{self.reisekosten:,.2f} €"))
        if self.sonstige_auslagen > 0:
            positionen.append(("Sonstige Auslagen", f"{self.sonstige_auslagen:,.2f} €"))

        positionen.extend([
            ("", ""),
            ("Zwischensumme (netto)", f"{self.zwischensumme_netto:,.2f} €"),
            (f"Umsatzsteuer ({self.umsatzsteuer_satz:.0f}%)", f"{self.umsatzsteuer:,.2f} €"),
            ("", ""),
            ("Gesamtbetrag (brutto)", f"{self.gesamt_brutto:,.2f} €"),
        ])

        return positionen
