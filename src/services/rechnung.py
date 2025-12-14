"""
Rechnungsstellung/Fakturierung Service
Erstellung und Verwaltung von Rechnungen
"""
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
from enum import Enum
from decimal import Decimal
import json
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Enum as SQLEnum, Date, Numeric
from sqlalchemy.orm import relationship
from src.models.base import Base


class RechnungsStatus(str, Enum):
    """Status einer Rechnung"""
    ENTWURF = "ENTWURF"
    ERSTELLT = "ERSTELLT"
    VERSENDET = "VERSENDET"
    BEZAHLT = "BEZAHLT"
    TEILBEZAHLT = "TEILBEZAHLT"
    MAHNUNG = "MAHNUNG"
    STORNIERT = "STORNIERT"


class RechnungsTyp(str, Enum):
    """Typ der Rechnung"""
    HONORAR = "HONORAR"
    AUSLAGEN = "AUSLAGEN"
    GEBUEHREN = "GEBUEHREN"
    GUTSCHRIFT = "GUTSCHRIFT"
    ABSCHLAG = "ABSCHLAG"
    SCHLUSSRECHNUNG = "SCHLUSSRECHNUNG"


class Rechnung(Base):
    """Model für Rechnungen"""
    __tablename__ = "rechnung"

    id = Column(Integer, primary_key=True)

    # Rechnungsnummer
    rechnungsnummer = Column(String(50), unique=True, nullable=False)
    jahr = Column(Integer)
    laufende_nummer = Column(Integer)

    # Projekt-Zuordnung (optional)
    projekt_id = Column(Integer, ForeignKey("unfallprojekt.id"))
    projekt = relationship("UnfallProjekt", backref="rechnungen")

    # Rechnungsdaten
    rechnungs_typ = Column(SQLEnum(RechnungsTyp), default=RechnungsTyp.HONORAR)
    status = Column(SQLEnum(RechnungsStatus), default=RechnungsStatus.ENTWURF)

    # Empfänger
    empfaenger_name = Column(String(200), nullable=False)
    empfaenger_adresse = Column(String(300))
    empfaenger_plz = Column(String(10))
    empfaenger_ort = Column(String(100))

    # Datum
    rechnungsdatum = Column(Date, nullable=False, default=date.today)
    leistungszeitraum_von = Column(Date)
    leistungszeitraum_bis = Column(Date)
    zahlungsziel_tage = Column(Integer, default=14)
    faellig_am = Column(Date)

    # Beträge
    netto_summe = Column(Numeric(12, 2), default=0)
    mwst_satz = Column(Numeric(5, 2), default=19.0)
    mwst_betrag = Column(Numeric(12, 2), default=0)
    brutto_summe = Column(Numeric(12, 2), default=0)

    # Positionen (JSON)
    positionen_json = Column(Text, default="[]")

    # Zahlungen
    bereits_bezahlt = Column(Numeric(12, 2), default=0)
    bezahlt_am = Column(Date)

    # Texte
    betreff = Column(String(300))
    einleitungstext = Column(Text)
    schlusstext = Column(Text)

    # Bankverbindung
    bank_iban = Column(String(50))
    bank_bic = Column(String(20))
    bank_name = Column(String(100))

    # Dokument
    pdf_pfad = Column(String(500))

    # Metadaten
    erstellt_von_user_id = Column(Integer, ForeignKey("user.id"))
    erstellt_am = Column(DateTime, default=datetime.now)
    aktualisiert_am = Column(DateTime, onupdate=datetime.now)

    @property
    def positionen(self) -> List[Dict[str, Any]]:
        """Parsed die Positionen aus JSON"""
        try:
            return json.loads(self.positionen_json) if self.positionen_json else []
        except json.JSONDecodeError:
            return []

    @positionen.setter
    def positionen(self, wert: List[Dict[str, Any]]):
        """Speichert Positionen als JSON"""
        self.positionen_json = json.dumps(wert)

    @property
    def status_anzeige(self) -> str:
        """Anzeigetext für Status"""
        return {
            RechnungsStatus.ENTWURF: "📝 Entwurf",
            RechnungsStatus.ERSTELLT: "📄 Erstellt",
            RechnungsStatus.VERSENDET: "📤 Versendet",
            RechnungsStatus.BEZAHLT: "✅ Bezahlt",
            RechnungsStatus.TEILBEZAHLT: "🔶 Teilbezahlt",
            RechnungsStatus.MAHNUNG: "⚠️ Mahnung",
            RechnungsStatus.STORNIERT: "❌ Storniert"
        }.get(self.status, "Unbekannt")

    @property
    def ist_ueberfaellig(self) -> bool:
        """Prüft ob die Rechnung überfällig ist"""
        if self.status in [RechnungsStatus.BEZAHLT, RechnungsStatus.STORNIERT]:
            return False
        return self.faellig_am and self.faellig_am < date.today()

    @property
    def offener_betrag(self) -> Decimal:
        """Berechnet den offenen Betrag"""
        return self.brutto_summe - (self.bereits_bezahlt or Decimal("0"))


class RechnungService:
    """Service für Rechnungsverwaltung"""

    def __init__(self, db_session):
        self.db = db_session

    def _naechste_rechnungsnummer(self, jahr: Optional[int] = None) -> tuple:
        """Generiert die nächste Rechnungsnummer"""
        if jahr is None:
            jahr = date.today().year

        # Finde die höchste laufende Nummer für dieses Jahr
        letzte = self.db.query(Rechnung).filter(
            Rechnung.jahr == jahr
        ).order_by(Rechnung.laufende_nummer.desc()).first()

        laufende_nummer = (letzte.laufende_nummer + 1) if letzte else 1

        # Format: RE-JJJJ-NNNN
        rechnungsnummer = f"RE-{jahr}-{laufende_nummer:04d}"

        return rechnungsnummer, jahr, laufende_nummer

    def rechnung_erstellen(
        self,
        empfaenger_name: str,
        positionen: List[Dict[str, Any]],
        projekt_id: Optional[int] = None,
        rechnungs_typ: RechnungsTyp = RechnungsTyp.HONORAR,
        zahlungsziel_tage: int = 14,
        mwst_satz: Decimal = Decimal("19.0"),
        erstellt_von_user_id: Optional[int] = None,
        **kwargs
    ) -> Rechnung:
        """Erstellt eine neue Rechnung"""

        rechnungsnummer, jahr, laufende_nummer = self._naechste_rechnungsnummer()

        # Beträge berechnen
        netto_summe = Decimal("0")
        for pos in positionen:
            menge = Decimal(str(pos.get("menge", 1)))
            einzelpreis = Decimal(str(pos.get("einzelpreis", 0)))
            netto_summe += menge * einzelpreis

        mwst_betrag = netto_summe * mwst_satz / Decimal("100")
        brutto_summe = netto_summe + mwst_betrag

        # Fälligkeit berechnen
        faellig_am = date.today() + timedelta(days=zahlungsziel_tage)

        rechnung = Rechnung(
            rechnungsnummer=rechnungsnummer,
            jahr=jahr,
            laufende_nummer=laufende_nummer,
            projekt_id=projekt_id,
            rechnungs_typ=rechnungs_typ,
            empfaenger_name=empfaenger_name,
            rechnungsdatum=date.today(),
            zahlungsziel_tage=zahlungsziel_tage,
            faellig_am=faellig_am,
            netto_summe=netto_summe,
            mwst_satz=mwst_satz,
            mwst_betrag=mwst_betrag,
            brutto_summe=brutto_summe,
            erstellt_von_user_id=erstellt_von_user_id,
            **kwargs
        )
        rechnung.positionen = positionen

        self.db.add(rechnung)
        self.db.flush()

        return rechnung

    def rechnung_aus_gebuehrenberechnung(
        self,
        gebuehren_id: int,
        empfaenger_name: str,
        empfaenger_adresse: str,
        empfaenger_plz: str,
        empfaenger_ort: str,
        erstellt_von_user_id: Optional[int] = None
    ) -> Optional[Rechnung]:
        """Erstellt eine Rechnung aus einer Gebührenberechnung"""
        from src.models import GebuehrenBerechnung

        gebuehren = self.db.query(GebuehrenBerechnung).get(gebuehren_id)
        if not gebuehren:
            return None

        positionen = [
            {
                "beschreibung": "Geschäftsgebühr gemäß Nr. 2300 VV RVG",
                "menge": 1,
                "einzelpreis": float(gebuehren.geschaeftsgebuehr),
                "einheit": "pauschal"
            },
            {
                "beschreibung": "Auslagenpauschale gemäß Nr. 7002 VV RVG",
                "menge": 1,
                "einzelpreis": float(gebuehren.auslagenpauschale),
                "einheit": "pauschal"
            }
        ]

        if gebuehren.einigungsgebuehr:
            positionen.append({
                "beschreibung": "Einigungsgebühr gemäß Nr. 1000 VV RVG",
                "menge": 1,
                "einzelpreis": float(gebuehren.einigungsgebuehr),
                "einheit": "pauschal"
            })

        return self.rechnung_erstellen(
            empfaenger_name=empfaenger_name,
            positionen=positionen,
            projekt_id=gebuehren.projekt_id,
            rechnungs_typ=RechnungsTyp.GEBUEHREN,
            empfaenger_adresse=empfaenger_adresse,
            empfaenger_plz=empfaenger_plz,
            empfaenger_ort=empfaenger_ort,
            betreff=f"Rechnung für Unfallschadenregulierung (Az.: {gebuehren.aktenzeichen})" if gebuehren.aktenzeichen else "Rechnung für Unfallschadenregulierung",
            erstellt_von_user_id=erstellt_von_user_id
        )

    def rechnungen_fuer_projekt(self, projekt_id: int) -> List[Rechnung]:
        """Holt alle Rechnungen für ein Projekt"""
        return self.db.query(Rechnung).filter(
            Rechnung.projekt_id == projekt_id
        ).order_by(Rechnung.rechnungsdatum.desc()).all()

    def offene_rechnungen(self) -> List[Rechnung]:
        """Holt alle offenen Rechnungen"""
        return self.db.query(Rechnung).filter(
            Rechnung.status.in_([
                RechnungsStatus.ERSTELLT,
                RechnungsStatus.VERSENDET,
                RechnungsStatus.TEILBEZAHLT,
                RechnungsStatus.MAHNUNG
            ])
        ).order_by(Rechnung.faellig_am).all()

    def ueberfaellige_rechnungen(self) -> List[Rechnung]:
        """Holt alle überfälligen Rechnungen"""
        heute = date.today()
        return self.db.query(Rechnung).filter(
            Rechnung.faellig_am < heute,
            Rechnung.status.in_([
                RechnungsStatus.ERSTELLT,
                RechnungsStatus.VERSENDET,
                RechnungsStatus.TEILBEZAHLT,
                RechnungsStatus.MAHNUNG
            ])
        ).order_by(Rechnung.faellig_am).all()

    def zahlung_erfassen(
        self,
        rechnung_id: int,
        betrag: Decimal,
        zahlungsdatum: Optional[date] = None
    ) -> Optional[Rechnung]:
        """Erfasst eine Zahlung für eine Rechnung"""
        rechnung = self.db.query(Rechnung).get(rechnung_id)

        if not rechnung:
            return None

        rechnung.bereits_bezahlt = (rechnung.bereits_bezahlt or Decimal("0")) + betrag
        rechnung.bezahlt_am = zahlungsdatum or date.today()

        # Status aktualisieren
        if rechnung.bereits_bezahlt >= rechnung.brutto_summe:
            rechnung.status = RechnungsStatus.BEZAHLT
        else:
            rechnung.status = RechnungsStatus.TEILBEZAHLT

        self.db.flush()
        return rechnung

    def generiere_rechnungs_pdf_text(self, rechnung: Rechnung) -> str:
        """Generiert den Text für die Rechnung (zum PDF-Export)"""
        positionen_text = ""
        for i, pos in enumerate(rechnung.positionen, 1):
            menge = pos.get("menge", 1)
            einheit = pos.get("einheit", "Stück")
            einzelpreis = pos.get("einzelpreis", 0)
            gesamt = menge * einzelpreis
            positionen_text += f"""
{i}. {pos.get('beschreibung', 'Position')}
   {menge} {einheit} à {einzelpreis:.2f} EUR = {gesamt:.2f} EUR
"""

        text = f"""
{'=' * 60}
                         RECHNUNG
{'=' * 60}

Rechnungsnummer: {rechnung.rechnungsnummer}
Rechnungsdatum:  {rechnung.rechnungsdatum.strftime('%d.%m.%Y')}
Zahlbar bis:     {rechnung.faellig_am.strftime('%d.%m.%Y') if rechnung.faellig_am else '-'}

{'─' * 60}

Empfänger:
{rechnung.empfaenger_name}
{rechnung.empfaenger_adresse or ''}
{rechnung.empfaenger_plz or ''} {rechnung.empfaenger_ort or ''}

{'─' * 60}

{rechnung.betreff or 'Rechnung für erbrachte Leistungen'}

{rechnung.einleitungstext or ''}

POSITIONEN:
{'─' * 60}
{positionen_text}
{'─' * 60}

Nettobetrag:                    {rechnung.netto_summe:>12.2f} EUR
MwSt. ({rechnung.mwst_satz}%):                   {rechnung.mwst_betrag:>12.2f} EUR
{'═' * 60}
GESAMTBETRAG:                   {rechnung.brutto_summe:>12.2f} EUR
{'═' * 60}

{rechnung.schlusstext or 'Bitte überweisen Sie den Betrag bis zum Zahlungsziel auf unser Konto.'}

Bankverbindung:
IBAN: {rechnung.bank_iban or '[IBAN eintragen]'}
BIC:  {rechnung.bank_bic or '[BIC eintragen]'}
Bank: {rechnung.bank_name or '[Bankname eintragen]'}

{'=' * 60}
"""
        return text

    def storniere_rechnung(self, rechnung_id: int) -> Optional[Rechnung]:
        """Storniert eine Rechnung"""
        rechnung = self.db.query(Rechnung).get(rechnung_id)

        if rechnung:
            rechnung.status = RechnungsStatus.STORNIERT
            rechnung.aktualisiert_am = datetime.now()
            self.db.flush()

        return rechnung
