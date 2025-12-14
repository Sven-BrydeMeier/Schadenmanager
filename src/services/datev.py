"""
DATEV-Export Service
Export für Buchhaltung im DATEV-Format
"""
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from enum import Enum
from decimal import Decimal
import csv
import io
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from src.models.base import Base


class ExportTyp(str, Enum):
    """Typen von DATEV-Exporten"""
    BUCHUNGSSTAPEL = "BUCHUNGSSTAPEL"
    DEBITOREN = "DEBITOREN"
    KREDITOREN = "KREDITOREN"
    SACHKONTEN = "SACHKONTEN"


class DATEVExport(Base):
    """Model für DATEV-Exporte"""
    __tablename__ = "datev_export"

    id = Column(Integer, primary_key=True)

    # Export-Daten
    export_typ = Column(String(50), default=ExportTyp.BUCHUNGSSTAPEL.value)
    export_datum = Column(DateTime, default=datetime.now)
    zeitraum_von = Column(DateTime)
    zeitraum_bis = Column(DateTime)

    # Datei
    dateiname = Column(String(255))
    dateipfad = Column(String(500))
    dateiinhalt = Column(Text)  # CSV-Inhalt

    # Statistik
    anzahl_buchungen = Column(Integer, default=0)
    summe_soll = Column(String(50))
    summe_haben = Column(String(50))

    # Metadaten
    erstellt_von_user_id = Column(Integer, ForeignKey("user.id"))
    erstellt_am = Column(DateTime, default=datetime.now)


class DATEVService:
    """Service für DATEV-Export"""

    # Standard-Kontenrahmen SKR03
    KONTEN_SKR03 = {
        # Erlöskonten
        "8400": "Erlöse 19% USt",
        "8300": "Erlöse 7% USt",
        "8120": "Steuerfreie Umsätze",

        # Aufwandskonten
        "4900": "Sonstige betriebliche Aufwendungen",
        "4930": "Bürobedarf",
        "4940": "Zeitschriften, Bücher",
        "4950": "Rechts- und Beratungskosten",
        "4960": "Beiträge",

        # Forderungen/Verbindlichkeiten
        "1400": "Forderungen aus Lieferungen und Leistungen",
        "1600": "Verbindlichkeiten aus Lieferungen und Leistungen",

        # Durchlaufende Posten
        "1590": "Durchlaufende Posten",

        # Geldkonten
        "1200": "Bank",
        "1000": "Kasse",

        # Umsatzsteuer
        "1776": "Umsatzsteuer 19%",
        "1571": "Abziehbare Vorsteuer 19%"
    }

    # Belegarten
    BELEGARTEN = {
        "RE": "Rechnung",
        "GU": "Gutschrift",
        "ZA": "Zahlung",
        "BU": "Buchung"
    }

    def __init__(self, db_session):
        self.db = db_session

    def exportiere_rechnungen(
        self,
        zeitraum_von: date,
        zeitraum_bis: date,
        beraternummer: str = "12345",
        mandantennummer: str = "10001",
        erstellt_von_user_id: Optional[int] = None
    ) -> DATEVExport:
        """Exportiert Rechnungen im DATEV-Format"""
        from src.services.rechnung import Rechnung, RechnungsStatus

        # Rechnungen im Zeitraum laden
        rechnungen = self.db.query(Rechnung).filter(
            Rechnung.rechnungsdatum >= zeitraum_von,
            Rechnung.rechnungsdatum <= zeitraum_bis,
            Rechnung.status != RechnungsStatus.ENTWURF
        ).order_by(Rechnung.rechnungsdatum).all()

        # DATEV-Header erstellen
        header = self._erstelle_header(
            beraternummer=beraternummer,
            mandantennummer=mandantennummer,
            zeitraum_von=zeitraum_von,
            zeitraum_bis=zeitraum_bis
        )

        # Buchungszeilen erstellen
        buchungen = []
        summe_soll = Decimal("0")
        summe_haben = Decimal("0")

        for rechnung in rechnungen:
            # Hauptbuchung: Forderung an Erlös
            buchung = self._erstelle_buchungszeile(
                umsatz=float(rechnung.brutto_summe),
                soll_konto="1400",  # Forderungen
                haben_konto="8400",  # Erlöse 19%
                datum=rechnung.rechnungsdatum,
                beleg_nr=rechnung.rechnungsnummer,
                buchungstext=f"Rechnung {rechnung.rechnungsnummer} {rechnung.empfaenger_name}",
                gegenkonto_name=rechnung.empfaenger_name
            )
            buchungen.append(buchung)
            summe_soll += rechnung.brutto_summe

            # Bei Zahlung: Bankbuchung
            if rechnung.bezahlt_am and rechnung.bereits_bezahlt:
                zahlung = self._erstelle_buchungszeile(
                    umsatz=float(rechnung.bereits_bezahlt),
                    soll_konto="1200",  # Bank
                    haben_konto="1400",  # Forderungen
                    datum=rechnung.bezahlt_am,
                    beleg_nr=f"ZA-{rechnung.rechnungsnummer}",
                    buchungstext=f"Zahlung zu {rechnung.rechnungsnummer}",
                    gegenkonto_name=rechnung.empfaenger_name
                )
                buchungen.append(zahlung)
                summe_haben += rechnung.bereits_bezahlt

        # CSV erstellen
        csv_inhalt = self._erstelle_csv(header, buchungen)

        # Export speichern
        dateiname = f"DATEV_Export_{zeitraum_von.strftime('%Y%m%d')}_{zeitraum_bis.strftime('%Y%m%d')}.csv"

        export = DATEVExport(
            export_typ=ExportTyp.BUCHUNGSSTAPEL.value,
            zeitraum_von=datetime.combine(zeitraum_von, datetime.min.time()),
            zeitraum_bis=datetime.combine(zeitraum_bis, datetime.max.time()),
            dateiname=dateiname,
            dateiinhalt=csv_inhalt,
            anzahl_buchungen=len(buchungen),
            summe_soll=str(summe_soll),
            summe_haben=str(summe_haben),
            erstellt_von_user_id=erstellt_von_user_id
        )

        self.db.add(export)
        self.db.flush()

        return export

    def exportiere_kosten(
        self,
        projekt_id: int,
        beraternummer: str = "12345",
        mandantennummer: str = "10001",
        erstellt_von_user_id: Optional[int] = None
    ) -> DATEVExport:
        """Exportiert Kostenpositionen eines Projekts"""
        from src.models import KostenPosition, UnfallProjekt

        projekt = self.db.query(UnfallProjekt).get(projekt_id)
        kosten = self.db.query(KostenPosition).filter(
            KostenPosition.projekt_id == projekt_id
        ).order_by(KostenPosition.erstellt_am).all()

        heute = date.today()

        header = self._erstelle_header(
            beraternummer=beraternummer,
            mandantennummer=mandantennummer,
            zeitraum_von=heute,
            zeitraum_bis=heute
        )

        buchungen = []
        summe_soll = Decimal("0")

        for kp in kosten:
            if kp.brutto_betrag:
                buchung = self._erstelle_buchungszeile(
                    umsatz=float(kp.brutto_betrag),
                    soll_konto="1400",  # Forderungen
                    haben_konto="8400",  # Erlöse
                    datum=kp.erstellt_am.date() if kp.erstellt_am else heute,
                    beleg_nr=f"KP-{kp.id}",
                    buchungstext=f"{kp.kategorie_anzeige}: {kp.beschreibung or 'Kostenposition'}",
                    gegenkonto_name=projekt.aktenzeichen if projekt else ""
                )
                buchungen.append(buchung)
                summe_soll += kp.brutto_betrag

        csv_inhalt = self._erstelle_csv(header, buchungen)

        dateiname = f"DATEV_Projekt_{projekt_id}_{heute.strftime('%Y%m%d')}.csv"

        export = DATEVExport(
            export_typ=ExportTyp.BUCHUNGSSTAPEL.value,
            zeitraum_von=datetime.combine(heute, datetime.min.time()),
            zeitraum_bis=datetime.combine(heute, datetime.max.time()),
            dateiname=dateiname,
            dateiinhalt=csv_inhalt,
            anzahl_buchungen=len(buchungen),
            summe_soll=str(summe_soll),
            summe_haben="0",
            erstellt_von_user_id=erstellt_von_user_id
        )

        self.db.add(export)
        self.db.flush()

        return export

    def _erstelle_header(
        self,
        beraternummer: str,
        mandantennummer: str,
        zeitraum_von: date,
        zeitraum_bis: date
    ) -> Dict[str, Any]:
        """Erstellt den DATEV-Header"""
        return {
            "DATEV-Format-KZ": "EXTF",
            "Versionsnummer": "700",
            "Datenkategorie": "21",  # Buchungsstapel
            "Formatname": "Buchungsstapel",
            "Formatversion": "12",
            "Erzeugt_am": datetime.now().strftime("%Y%m%d%H%M%S000"),
            "Beraternummer": beraternummer,
            "Mandantennummer": mandantennummer,
            "WJ_Beginn": f"{zeitraum_von.year}0101",
            "Sachkontenlänge": "4",
            "Datum_von": zeitraum_von.strftime("%Y%m%d"),
            "Datum_bis": zeitraum_bis.strftime("%Y%m%d"),
            "Bezeichnung": f"Export {zeitraum_von.strftime('%d.%m.%Y')} - {zeitraum_bis.strftime('%d.%m.%Y')}"
        }

    def _erstelle_buchungszeile(
        self,
        umsatz: float,
        soll_konto: str,
        haben_konto: str,
        datum: date,
        beleg_nr: str,
        buchungstext: str,
        gegenkonto_name: str = ""
    ) -> Dict[str, Any]:
        """Erstellt eine DATEV-Buchungszeile"""
        return {
            "Umsatz (ohne Soll/Haben-Kz)": f"{umsatz:.2f}".replace(".", ","),
            "Soll/Haben-Kennzeichen": "S",  # Soll
            "WKZ Umsatz": "EUR",
            "Kurs": "",
            "Basis-Umsatz": "",
            "WKZ Basis-Umsatz": "",
            "Konto": soll_konto,
            "Gegenkonto (ohne BU-Schlüssel)": haben_konto,
            "BU-Schlüssel": "",
            "Belegdatum": datum.strftime("%d%m"),
            "Belegfeld 1": beleg_nr[:36] if beleg_nr else "",
            "Belegfeld 2": "",
            "Skonto": "",
            "Buchungstext": buchungstext[:60] if buchungstext else "",
            "Postensperre": "",
            "Diverse Adressnummer": "",
            "Geschäftspartnerbank": "",
            "Sachverhalt": "",
            "Zinssperre": "",
            "Beleglink": "",
            "Beleginfo - Art 1": "",
            "Beleginfo - Inhalt 1": "",
            "Beleginfo - Art 2": "",
            "Beleginfo - Inhalt 2": "",
            "Beleginfo - Art 3": "",
            "Beleginfo - Inhalt 3": "",
            "Beleginfo - Art 4": "",
            "Beleginfo - Inhalt 4": "",
            "Beleginfo - Art 5": "",
            "Beleginfo - Inhalt 5": "",
            "Beleginfo - Art 6": "",
            "Beleginfo - Inhalt 6": "",
            "Beleginfo - Art 7": "",
            "Beleginfo - Inhalt 7": "",
            "Beleginfo - Art 8": "",
            "Beleginfo - Inhalt 8": "",
            "KOST1 - Kostenstelle": "",
            "KOST2 - Kostenstelle": "",
            "Kost-Menge": "",
            "EU-Land u. UStID": "",
            "EU-Steuersatz": "",
            "Abw. Versteuerungsart": "",
            "Sachverhalt L+L": "",
            "Funktionsergänzung L+L": "",
            "BU 49 Hauptfunktionstyp": "",
            "BU 49 Hauptfunktionsnummer": "",
            "BU 49 Funktionsergänzung": "",
            "Zusatzinformation - Art 1": "",
            "Zusatzinformation - Inhalt 1": "",
            "Zusatzinformation - Art 2": "",
            "Zusatzinformation - Inhalt 2": "",
            "Zusatzinformation - Art 3": "",
            "Zusatzinformation - Inhalt 3": "",
            "Zusatzinformation - Art 4": "",
            "Zusatzinformation - Inhalt 4": "",
            "Zusatzinformation - Art 5": "",
            "Zusatzinformation - Inhalt 5": "",
            "Zusatzinformation - Art 6": "",
            "Zusatzinformation - Inhalt 6": "",
            "Zusatzinformation - Art 7": "",
            "Zusatzinformation - Inhalt 7": "",
            "Zusatzinformation - Art 8": "",
            "Zusatzinformation - Inhalt 8": "",
            "Zusatzinformation - Art 9": "",
            "Zusatzinformation - Inhalt 9": "",
            "Zusatzinformation - Art 10": "",
            "Zusatzinformation - Inhalt 10": "",
            "Zusatzinformation - Art 11": "",
            "Zusatzinformation - Inhalt 11": "",
            "Zusatzinformation - Art 12": "",
            "Zusatzinformation - Inhalt 12": "",
            "Zusatzinformation - Art 13": "",
            "Zusatzinformation - Inhalt 13": "",
            "Zusatzinformation - Art 14": "",
            "Zusatzinformation - Inhalt 14": "",
            "Zusatzinformation - Art 15": "",
            "Zusatzinformation - Inhalt 15": "",
            "Zusatzinformation - Art 16": "",
            "Zusatzinformation - Inhalt 16": "",
            "Zusatzinformation - Art 17": "",
            "Zusatzinformation - Inhalt 17": "",
            "Zusatzinformation - Art 18": "",
            "Zusatzinformation - Inhalt 18": "",
            "Zusatzinformation - Art 19": "",
            "Zusatzinformation - Inhalt 19": "",
            "Zusatzinformation - Art 20": "",
            "Zusatzinformation - Inhalt 20": "",
            "Stück": "",
            "Gewicht": "",
            "Zahlweise": "",
            "Forderungsart": "",
            "Veranlagungsjahr": "",
            "Zugeordnete Fälligkeit": "",
            "Skontotyp": "",
            "Auftragsnummer": "",
            "Buchungstyp": "",
            "USt-Schlüssel (Anzahlungen)": "",
            "EU-Land (Anzahlungen)": "",
            "Sachverhalt L+L (Anzahlungen)": "",
            "EU-Steuersatz (Anzahlungen)": "",
            "Erlöskonto (Anzahlungen)": "",
            "Herkunft-Kz": "",
            "Buchungs GUID": "",
            "KOST-Datum": "",
            "SEPA-Mandatsreferenz": "",
            "Skontosperre": "",
            "Gesellschaftername": "",
            "Beteiligtennummer": "",
            "Identifikationsnummer": "",
            "Zeichnernummer": "",
            "Postensperre bis": "",
            "Bezeichnung SoBil-Sachverhalt": "",
            "Kennzeichen SoBil-Buchung": "",
            "Festschreibung": "",
            "Leistungsdatum": "",
            "Datum Zuord. Steuerperiode": ""
        }

    def _erstelle_csv(self, header: Dict[str, Any], buchungen: List[Dict[str, Any]]) -> str:
        """Erstellt die CSV-Datei"""
        output = io.StringIO()

        # Header-Zeile
        header_values = [
            header.get("DATEV-Format-KZ", "EXTF"),
            header.get("Versionsnummer", "700"),
            header.get("Datenkategorie", "21"),
            header.get("Formatname", "Buchungsstapel"),
            header.get("Formatversion", "12"),
            header.get("Erzeugt_am", ""),
            "",  # Importiert
            "SV",  # Herkunft
            "",  # Exportiert von
            "",  # Importiert von
            header.get("Beraternummer", ""),
            header.get("Mandantennummer", ""),
            header.get("WJ_Beginn", ""),
            header.get("Sachkontenlänge", "4"),
            header.get("Datum_von", ""),
            header.get("Datum_bis", ""),
            header.get("Bezeichnung", ""),
            "",  # Diktatkürzel
            "1",  # Buchungstyp
            "0",  # Rechnungslegungszweck
            "",  # Festschreibung
            "EUR"  # WKZ
        ]
        output.write(";".join(f'"{v}"' for v in header_values) + "\n")

        # Spaltenüberschriften
        if buchungen:
            spalten = list(buchungen[0].keys())
            output.write(";".join(spalten) + "\n")

            # Buchungszeilen
            for buchung in buchungen:
                zeile = [str(buchung.get(s, "")) for s in spalten]
                output.write(";".join(f'"{v}"' for v in zeile) + "\n")

        return output.getvalue()

    def alle_exporte(self, limit: int = 50) -> List[DATEVExport]:
        """Holt alle DATEV-Exporte"""
        return self.db.query(DATEVExport).order_by(
            DATEVExport.erstellt_am.desc()
        ).limit(limit).all()

    def export_herunterladen(self, export_id: int) -> Optional[Dict[str, Any]]:
        """Bereitet einen Export zum Download vor"""
        export = self.db.query(DATEVExport).get(export_id)

        if not export:
            return None

        return {
            "dateiname": export.dateiname,
            "inhalt": export.dateiinhalt,
            "content_type": "text/csv; charset=utf-8"
        }
