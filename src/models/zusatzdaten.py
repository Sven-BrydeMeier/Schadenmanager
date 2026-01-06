"""
Zusatzdaten-Models für erweiterte Schadensfall-Informationen

Enthält:
- TUVDaten: Hauptuntersuchung und TÜV-Status
- LeasingKreditbank: Finanzierungsdaten
- PolizeiDienststelle: Polizei-Kontaktdaten
- Bankverbindung: Mandanten-Bankdaten
"""

from datetime import datetime, date
from sqlalchemy import (
    Column, Integer, String, DateTime, Date, Text,
    ForeignKey, Enum, Boolean, Float
)
from sqlalchemy.orm import relationship
from enum import Enum as PyEnum

from src.models.base import Base


class TUVStatus(PyEnum):
    """Status der Hauptuntersuchung"""
    GUELTIG = "GUELTIG"
    ABGELAUFEN = "ABGELAUFEN"
    BALD_FAELLIG = "BALD_FAELLIG"  # < 2 Monate
    UNBEKANNT = "UNBEKANNT"


class TUVDaten(Base):
    """
    TÜV-Daten für ein Fahrzeug.

    Speichert HU-Termine, TÜV-Berichte und Prüfungsergebnisse.
    """
    __tablename__ = "tuev_daten"

    id = Column(Integer, primary_key=True)

    # Zuordnung zum Fahrzeug
    fahrzeug_id = Column(Integer, ForeignKey("fahrzeug.id"), nullable=False)

    # Hauptuntersuchung (HU)
    hu_faellig_am = Column(Date)  # Nächste HU fällig
    hu_letzte_am = Column(Date)   # Letzte HU durchgeführt
    hu_bestanden = Column(Boolean)
    hu_maengel = Column(Text)     # Festgestellte Mängel

    # Abgasuntersuchung (AU)
    au_faellig_am = Column(Date)
    au_letzte_am = Column(Date)
    au_bestanden = Column(Boolean)

    # TÜV-Prüfstelle
    pruefstelle_name = Column(String(200))  # z.B. "TÜV Süd", "DEKRA"
    pruefstelle_ort = Column(String(100))
    pruefer_name = Column(String(100))
    pruef_nummer = Column(String(50))  # Prüfberichts-Nummer

    # TÜV-Bericht Dokument
    bericht_dokument_id = Column(Integer, ForeignKey("dokument.id"))

    # Status
    status = Column(Enum(TUVStatus), default=TUVStatus.UNBEKANNT)

    # Notizen
    notizen = Column(Text)

    # Timestamps
    erstellt_am = Column(DateTime, default=datetime.utcnow)
    aktualisiert_am = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    fahrzeug = relationship("Fahrzeug", backref="tuev_daten")
    bericht_dokument = relationship("Dokument", foreign_keys=[bericht_dokument_id])

    def __repr__(self):
        return f"<TUVDaten(fahrzeug_id={self.fahrzeug_id}, hu_faellig={self.hu_faellig_am})>"

    @property
    def status_berechnet(self) -> TUVStatus:
        """Berechnet den aktuellen TÜV-Status basierend auf dem Datum"""
        if not self.hu_faellig_am:
            return TUVStatus.UNBEKANNT

        heute = date.today()
        tage_bis_faellig = (self.hu_faellig_am - heute).days

        if tage_bis_faellig < 0:
            return TUVStatus.ABGELAUFEN
        elif tage_bis_faellig <= 60:  # 2 Monate
            return TUVStatus.BALD_FAELLIG
        else:
            return TUVStatus.GUELTIG

    @property
    def hu_faellig_anzeige(self) -> str:
        """Formatierte HU-Fälligkeit für Anzeige"""
        if self.hu_faellig_am:
            return self.hu_faellig_am.strftime("%m/%Y")
        return "Unbekannt"


class FinanzierungsTyp(PyEnum):
    """Art der Fahrzeugfinanzierung"""
    LEASING = "LEASING"
    KREDIT = "KREDIT"
    BALLONFINANZIERUNG = "BALLONFINANZIERUNG"
    MIETKAUF = "MIETKAUF"


class LeasingKreditbank(Base):
    """
    Leasing- oder Kreditbank-Daten für ein Fahrzeug.

    Speichert Finanzierungsdetails für Leasingfahrzeuge
    oder kreditfinanzierte Fahrzeuge.
    """
    __tablename__ = "leasing_kreditbank"

    id = Column(Integer, primary_key=True)

    # Zuordnung
    fahrzeug_id = Column(Integer, ForeignKey("fahrzeug.id"), nullable=False)
    unfallprojekt_id = Column(Integer, ForeignKey("unfallprojekt.id"))

    # Art der Finanzierung
    finanzierungs_typ = Column(Enum(FinanzierungsTyp), default=FinanzierungsTyp.LEASING)

    # Bank/Gesellschaft
    gesellschaft_name = Column(String(200), nullable=False)
    gesellschaft_strasse = Column(String(200))
    gesellschaft_hausnummer = Column(String(20))
    gesellschaft_plz = Column(String(10))
    gesellschaft_ort = Column(String(100))
    gesellschaft_telefon = Column(String(50))
    gesellschaft_fax = Column(String(50))
    gesellschaft_email = Column(String(200))

    # Ansprechpartner
    ansprechpartner_name = Column(String(100))
    ansprechpartner_telefon = Column(String(50))
    ansprechpartner_email = Column(String(200))

    # Vertragsdaten
    vertragsnummer = Column(String(100))
    vertragsbeginn = Column(Date)
    vertragsende = Column(Date)
    restlaufzeit_monate = Column(Integer)  # Wird berechnet oder manuell

    # Finanzdaten
    monatliche_rate = Column(Float)
    restwert = Column(Float)  # Bei Leasing
    restschuld = Column(Float)  # Bei Kredit
    kaufpreis_gesamt = Column(Float)

    # Versicherung (falls über Leasinggesellschaft)
    versicherung_inkludiert = Column(Boolean, default=False)
    versicherung_details = Column(Text)

    # Sicherungsübereignung
    sicherungsuebereignung = Column(Boolean, default=False)
    brief_bei_bank = Column(Boolean, default=True)  # Fahrzeugbrief bei Bank

    # Status
    aktiv = Column(Boolean, default=True)
    gekuendigt_am = Column(Date)
    kuendigungsgrund = Column(Text)

    # Schadensfall-relevant
    regulierung_an_bank = Column(Boolean, default=False)  # Zahlung geht an Bank
    bank_informiert = Column(Boolean, default=False)
    bank_informiert_am = Column(DateTime)

    # Timestamps
    erstellt_am = Column(DateTime, default=datetime.utcnow)
    aktualisiert_am = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    fahrzeug = relationship("Fahrzeug", backref="finanzierung")
    projekt = relationship("UnfallProjekt", backref="finanzierungen")

    def __repr__(self):
        return f"<LeasingKreditbank(gesellschaft='{self.gesellschaft_name}', typ={self.finanzierungs_typ})>"

    @property
    def restlaufzeit_berechnet(self) -> int:
        """Berechnet die Restlaufzeit in Monaten"""
        if not self.vertragsende:
            return self.restlaufzeit_monate or 0

        heute = date.today()
        if self.vertragsende <= heute:
            return 0

        diff = self.vertragsende - heute
        return max(0, diff.days // 30)

    @property
    def adresse_einzeilig(self) -> str:
        """Formatierte Adresse für Anzeige"""
        teile = []
        if self.gesellschaft_strasse:
            teile.append(f"{self.gesellschaft_strasse} {self.gesellschaft_hausnummer or ''}".strip())
        if self.gesellschaft_plz or self.gesellschaft_ort:
            teile.append(f"{self.gesellschaft_plz or ''} {self.gesellschaft_ort or ''}".strip())
        return ", ".join(teile) if teile else ""


class PolizeiDienststelle(Base):
    """
    Polizei-Dienststelle und Kontaktdaten.

    Speichert die zuständige Polizeidienststelle für einen Unfall
    sowie Beamten-Kontaktdaten und Aktenzeichen.
    """
    __tablename__ = "polizei_dienststelle"

    id = Column(Integer, primary_key=True)

    # Zuordnung zum Projekt
    unfallprojekt_id = Column(Integer, ForeignKey("unfallprojekt.id"), nullable=False)

    # Dienststelle
    dienststelle_name = Column(String(200), nullable=False)
    dienststelle_typ = Column(String(100))  # "Polizeirevier", "Autobahnpolizei", etc.
    strasse = Column(String(200))
    hausnummer = Column(String(20))
    plz = Column(String(10))
    ort = Column(String(100))
    bundesland = Column(String(50))

    # Kontakt
    telefon = Column(String(50))
    telefon_durchwahl = Column(String(50))
    fax = Column(String(50))
    email = Column(String(200))

    # Sachbearbeiter/Beamter
    beamter_name = Column(String(100))
    beamter_dienstgrad = Column(String(50))  # "PHK", "POM", etc.
    beamter_telefon = Column(String(50))
    beamter_email = Column(String(200))

    # Aktenzeichen und Protokolle
    aktenzeichen = Column(String(100))  # Polizeiliches Aktenzeichen
    tagebuch_nummer = Column(String(100))  # Tagebuch-Nr.
    protokoll_nummer = Column(String(100))  # Unfallprotokoll-Nr.
    vorgang_nummer = Column(String(100))

    # Unfallaufnahme
    unfallaufnahme_am = Column(DateTime)
    unfallaufnahme_durch = Column(String(100))  # Name des aufnehmenden Beamten
    unfallaufnahme_ort = Column(String(200))  # Falls abweichend

    # Ermittlungsverfahren
    ermittlungsverfahren_eingeleitet = Column(Boolean, default=False)
    ermittlungsverfahren_aktenzeichen = Column(String(100))
    ermittlungsverfahren_behoerde = Column(String(200))  # z.B. Staatsanwaltschaft

    # Zeugenvernehmung
    zeugen_vernommen = Column(Boolean, default=False)
    anzahl_zeugen = Column(Integer, default=0)

    # Dokumente
    unfallbericht_angefordert = Column(Boolean, default=False)
    unfallbericht_angefordert_am = Column(DateTime)
    unfallbericht_erhalten = Column(Boolean, default=False)
    unfallbericht_erhalten_am = Column(DateTime)
    unfallbericht_dokument_id = Column(Integer, ForeignKey("dokument.id"))

    # Notizen
    notizen = Column(Text)

    # Timestamps
    erstellt_am = Column(DateTime, default=datetime.utcnow)
    aktualisiert_am = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    projekt = relationship("UnfallProjekt", backref="polizei_dienststellen")
    unfallbericht_dokument = relationship("Dokument", foreign_keys=[unfallbericht_dokument_id])

    def __repr__(self):
        return f"<PolizeiDienststelle(name='{self.dienststelle_name}', az='{self.aktenzeichen}')>"

    @property
    def adresse_formatiert(self) -> str:
        """Formatierte Adresse"""
        teile = []
        if self.strasse:
            teile.append(f"{self.strasse} {self.hausnummer or ''}".strip())
        if self.plz or self.ort:
            teile.append(f"{self.plz or ''} {self.ort or ''}".strip())
        return ", ".join(teile) if teile else ""

    @property
    def beamter_anzeige(self) -> str:
        """Formatierter Beamtenname mit Dienstgrad"""
        if self.beamter_dienstgrad and self.beamter_name:
            return f"{self.beamter_dienstgrad} {self.beamter_name}"
        return self.beamter_name or "Unbekannt"


class Bankverbindung(Base):
    """
    Bankverbindung für Mandanten oder Beteiligte.

    Speichert IBAN, BIC und Bankdaten für Zahlungsabwicklung.
    """
    __tablename__ = "bankverbindung"

    id = Column(Integer, primary_key=True)

    # Zuordnung (zu User/Mandant)
    user_id = Column(Integer, ForeignKey("user.id"))
    unfallprojekt_id = Column(Integer, ForeignKey("unfallprojekt.id"))

    # Kontoinhaber
    kontoinhaber = Column(String(200), nullable=False)
    kontoinhaber_abweichend = Column(Boolean, default=False)  # Abweichend vom Mandant

    # Bankdaten
    iban = Column(String(34), nullable=False)
    bic = Column(String(11))
    bank_name = Column(String(200))
    bank_ort = Column(String(100))

    # Alte Kontonummer (falls vorhanden)
    kontonummer = Column(String(20))
    blz = Column(String(10))

    # Verwendungszweck
    ist_hauptkonto = Column(Boolean, default=True)
    verwendungszweck = Column(String(100))  # z.B. "Schadensersatz", "Honorar"

    # Verifizierung
    verifiziert = Column(Boolean, default=False)
    verifiziert_am = Column(DateTime)
    verifiziert_durch = Column(String(100))

    # SEPA
    sepa_mandat_erteilt = Column(Boolean, default=False)
    sepa_mandatsreferenz = Column(String(50))
    sepa_mandat_datum = Column(Date)

    # Status
    aktiv = Column(Boolean, default=True)

    # Notizen
    notizen = Column(Text)

    # Timestamps
    erstellt_am = Column(DateTime, default=datetime.utcnow)
    aktualisiert_am = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", backref="bankverbindungen")
    projekt = relationship("UnfallProjekt", backref="bankverbindungen")

    def __repr__(self):
        return f"<Bankverbindung(inhaber='{self.kontoinhaber}', iban='{self.iban_maskiert}')>"

    @property
    def iban_maskiert(self) -> str:
        """IBAN mit maskiertem Mittelteil für Anzeige"""
        if not self.iban or len(self.iban) < 10:
            return self.iban or ""

        # Zeige erste 4 und letzte 4 Zeichen
        return f"{self.iban[:4]}{'*' * (len(self.iban) - 8)}{self.iban[-4:]}"

    @property
    def iban_formatiert(self) -> str:
        """IBAN mit Leerzeichen alle 4 Zeichen"""
        if not self.iban:
            return ""
        return ' '.join([self.iban[i:i+4] for i in range(0, len(self.iban), 4)])

    def validiere_iban(self) -> bool:
        """Validiert die IBAN (vereinfachte Prüfung)"""
        if not self.iban:
            return False

        iban = self.iban.replace(' ', '').upper()

        # Längenprüfung (deutsche IBAN = 22 Zeichen)
        if len(iban) < 15 or len(iban) > 34:
            return False

        # Muss mit Ländercode beginnen
        if not iban[:2].isalpha():
            return False

        # Prüfziffer muss numerisch sein
        if not iban[2:4].isdigit():
            return False

        return True
