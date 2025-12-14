"""
Versicherungsdatenbank Service
Kontaktdaten aller deutschen Versicherungen
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from src.models.base import Base


class Versicherung(Base):
    """Model für Versicherungsunternehmen"""
    __tablename__ = "versicherung"

    id = Column(Integer, primary_key=True)

    # Stammdaten
    name = Column(String(200), nullable=False)
    kurzname = Column(String(50))
    vunr = Column(String(10))  # Versicherungsunternehmensnummer

    # Kontaktdaten Zentrale
    adresse = Column(String(300))
    plz = Column(String(10))
    ort = Column(String(100))
    telefon = Column(String(50))
    fax = Column(String(50))
    email = Column(String(100))
    website = Column(String(200))

    # Schadenhotline
    schaden_hotline = Column(String(50))
    schaden_email = Column(String(100))
    schaden_fax = Column(String(50))
    schaden_portal = Column(String(200))

    # Regulierungsbeauftragter
    regulierer_name = Column(String(200))
    regulierer_telefon = Column(String(50))
    regulierer_email = Column(String(100))

    # Ansprechpartner
    ansprechpartner_json = Column(Text)  # JSON für mehrere Ansprechpartner

    # Zusatzinfos
    notizen = Column(Text)
    aktiv = Column(Boolean, default=True)

    # Metadaten
    erstellt_am = Column(DateTime, default=datetime.now)
    aktualisiert_am = Column(DateTime, onupdate=datetime.now)

    @property
    def vollstaendige_adresse(self) -> str:
        """Gibt die vollständige Adresse zurück"""
        teile = [self.adresse, f"{self.plz} {self.ort}"]
        return ", ".join(t for t in teile if t)


class VersicherungService:
    """Service für Versicherungsdatenbank"""

    # Standard-Versicherungsdaten (die wichtigsten deutschen KFZ-Versicherer)
    STANDARD_VERSICHERUNGEN = [
        {
            "name": "Allianz Versicherungs-AG",
            "kurzname": "Allianz",
            "vunr": "1000",
            "adresse": "Königinstraße 28",
            "plz": "80802",
            "ort": "München",
            "telefon": "+49 89 3800-0",
            "schaden_hotline": "+49 800 1123344",
            "schaden_email": "schaden@allianz.de",
            "website": "www.allianz.de"
        },
        {
            "name": "AXA Versicherung AG",
            "kurzname": "AXA",
            "vunr": "1027",
            "adresse": "Colonia-Allee 10-20",
            "plz": "51067",
            "ort": "Köln",
            "telefon": "+49 221 148-0",
            "schaden_hotline": "+49 800 2929299",
            "schaden_email": "schaden@axa.de",
            "website": "www.axa.de"
        },
        {
            "name": "HUK-COBURG Versicherungsgruppe",
            "kurzname": "HUK-COBURG",
            "vunr": "1045",
            "adresse": "Bahnhofsplatz",
            "plz": "96450",
            "ort": "Coburg",
            "telefon": "+49 9561 96-0",
            "schaden_hotline": "+49 800 2153153",
            "schaden_email": "schaden@huk.de",
            "website": "www.huk.de"
        },
        {
            "name": "DEVK Versicherungen",
            "kurzname": "DEVK",
            "vunr": "1125",
            "adresse": "Riehler Straße 190",
            "plz": "50735",
            "ort": "Köln",
            "telefon": "+49 221 757-0",
            "schaden_hotline": "+49 800 4440070",
            "schaden_email": "schaden@devk.de",
            "website": "www.devk.de"
        },
        {
            "name": "ERGO Versicherung AG",
            "kurzname": "ERGO",
            "vunr": "1168",
            "adresse": "ERGO-Platz 1",
            "plz": "40198",
            "ort": "Düsseldorf",
            "telefon": "+49 211 477-0",
            "schaden_hotline": "+49 800 3746000",
            "schaden_email": "schaden@ergo.de",
            "website": "www.ergo.de"
        },
        {
            "name": "Generali Deutschland Versicherung AG",
            "kurzname": "Generali",
            "vunr": "1250",
            "adresse": "Adenauerring 7",
            "plz": "81737",
            "ort": "München",
            "telefon": "+49 89 5121-0",
            "schaden_hotline": "+49 800 8118118",
            "schaden_email": "schaden@generali.de",
            "website": "www.generali.de"
        },
        {
            "name": "HDI Versicherung AG",
            "kurzname": "HDI",
            "vunr": "1320",
            "adresse": "HDI-Platz 1",
            "plz": "30659",
            "ort": "Hannover",
            "telefon": "+49 511 645-0",
            "schaden_hotline": "+49 800 4234234",
            "schaden_email": "schaden@hdi.de",
            "website": "www.hdi.de"
        },
        {
            "name": "LVM Versicherung",
            "kurzname": "LVM",
            "vunr": "1455",
            "adresse": "Kolde-Ring 21",
            "plz": "48151",
            "ort": "Münster",
            "telefon": "+49 251 702-0",
            "schaden_hotline": "+49 800 5862580",
            "schaden_email": "schaden@lvm.de",
            "website": "www.lvm.de"
        },
        {
            "name": "R+V Versicherung AG",
            "kurzname": "R+V",
            "vunr": "1600",
            "adresse": "Raiffeisenplatz 1",
            "plz": "65189",
            "ort": "Wiesbaden",
            "telefon": "+49 611 533-0",
            "schaden_hotline": "+49 800 5332255",
            "schaden_email": "schaden@ruv.de",
            "website": "www.ruv.de"
        },
        {
            "name": "VHV Versicherungen",
            "kurzname": "VHV",
            "vunr": "1750",
            "adresse": "VHV-Platz 1",
            "plz": "30177",
            "ort": "Hannover",
            "telefon": "+49 511 907-0",
            "schaden_hotline": "+49 800 1808018",
            "schaden_email": "schaden@vhv.de",
            "website": "www.vhv.de"
        },
        {
            "name": "Württembergische Versicherung AG",
            "kurzname": "Württembergische",
            "vunr": "1820",
            "adresse": "Gutenbergstraße 30",
            "plz": "70176",
            "ort": "Stuttgart",
            "telefon": "+49 711 662-0",
            "schaden_hotline": "+49 800 8082030",
            "schaden_email": "schaden@wuerttembergische.de",
            "website": "www.wuerttembergische.de"
        },
        {
            "name": "Zurich Insurance plc",
            "kurzname": "Zurich",
            "vunr": "1900",
            "adresse": "Solmsstraße 27-37",
            "plz": "60486",
            "ort": "Frankfurt am Main",
            "telefon": "+49 69 7115-0",
            "schaden_hotline": "+49 800 1115999",
            "schaden_email": "schaden@zurich.de",
            "website": "www.zurich.de"
        },
        {
            "name": "ADAC Versicherung AG",
            "kurzname": "ADAC",
            "vunr": "1010",
            "adresse": "Hansastraße 19",
            "plz": "80686",
            "ort": "München",
            "telefon": "+49 89 7676-0",
            "schaden_hotline": "+49 800 2232323",
            "schaden_email": "schaden@adac.de",
            "website": "www.adac.de/versicherungen"
        },
        {
            "name": "Gothaer Versicherung AG",
            "kurzname": "Gothaer",
            "vunr": "1280",
            "adresse": "Gothaer Allee 1",
            "plz": "50969",
            "ort": "Köln",
            "telefon": "+49 221 308-00",
            "schaden_hotline": "+49 800 4684237",
            "schaden_email": "schaden@gothaer.de",
            "website": "www.gothaer.de"
        },
        {
            "name": "Provinzial Versicherung",
            "kurzname": "Provinzial",
            "vunr": "1580",
            "adresse": "Provinzialplatz 1",
            "plz": "40591",
            "ort": "Düsseldorf",
            "telefon": "+49 211 978-0",
            "schaden_hotline": "+49 800 7768464",
            "schaden_email": "schaden@provinzial.de",
            "website": "www.provinzial.de"
        },
        {
            "name": "Signal Iduna Gruppe",
            "kurzname": "Signal Iduna",
            "vunr": "1680",
            "adresse": "Joseph-Scherer-Straße 3",
            "plz": "44139",
            "ort": "Dortmund",
            "telefon": "+49 231 135-0",
            "schaden_hotline": "+49 800 5554544",
            "schaden_email": "schaden@signal-iduna.de",
            "website": "www.signal-iduna.de"
        },
        {
            "name": "Sparkassen Versicherung",
            "kurzname": "SV",
            "vunr": "1700",
            "adresse": "Löwentorstraße 65",
            "plz": "70376",
            "ort": "Stuttgart",
            "telefon": "+49 711 898-0",
            "schaden_hotline": "+49 800 5776667",
            "schaden_email": "schaden@sv.de",
            "website": "www.sparkassenversicherung.de"
        },
        {
            "name": "Cosmos Direkt",
            "kurzname": "CosmosDirekt",
            "vunr": "1095",
            "adresse": "Halbergstraße 50-60",
            "plz": "66121",
            "ort": "Saarbrücken",
            "telefon": "+49 681 966-6666",
            "schaden_hotline": "+49 800 2676767",
            "schaden_email": "schaden@cosmosdirekt.de",
            "website": "www.cosmosdirekt.de"
        },
        {
            "name": "DA Direkt",
            "kurzname": "DA Direkt",
            "vunr": "1115",
            "adresse": "Poppelsdorfer Allee 25-33",
            "plz": "53115",
            "ort": "Bonn",
            "telefon": "+49 800 3272487",
            "schaden_hotline": "+49 800 3272487",
            "schaden_email": "schaden@da-direkt.de",
            "website": "www.da-direkt.de"
        },
        {
            "name": "Verti Versicherung AG",
            "kurzname": "Verti",
            "vunr": "1760",
            "adresse": "Rheinstraße 7a",
            "plz": "14513",
            "ort": "Teltow",
            "telefon": "+49 30 890021-0",
            "schaden_hotline": "+49 30 890021-100",
            "schaden_email": "schaden@verti.de",
            "website": "www.verti.de"
        },
    ]

    def __init__(self, db_session):
        self.db = db_session

    def initialisiere_standard_versicherungen(self):
        """Fügt die Standard-Versicherungen in die Datenbank ein"""
        for vs_daten in self.STANDARD_VERSICHERUNGEN:
            # Prüfe ob schon vorhanden
            existiert = self.db.query(Versicherung).filter(
                Versicherung.name == vs_daten["name"]
            ).first()

            if not existiert:
                versicherung = Versicherung(**vs_daten)
                self.db.add(versicherung)

        self.db.flush()

    def alle_versicherungen(self, nur_aktive: bool = True) -> List[Versicherung]:
        """Holt alle Versicherungen"""
        query = self.db.query(Versicherung)

        if nur_aktive:
            query = query.filter(Versicherung.aktiv == True)

        return query.order_by(Versicherung.name).all()

    def suche_versicherung(self, suchbegriff: str) -> List[Versicherung]:
        """Sucht nach Versicherungen"""
        from sqlalchemy import or_

        suche = f"%{suchbegriff}%"
        return self.db.query(Versicherung).filter(
            or_(
                Versicherung.name.ilike(suche),
                Versicherung.kurzname.ilike(suche),
                Versicherung.vunr.ilike(suche)
            ),
            Versicherung.aktiv == True
        ).order_by(Versicherung.name).all()

    def versicherung_nach_vunr(self, vunr: str) -> Optional[Versicherung]:
        """Findet eine Versicherung anhand der VUNR"""
        return self.db.query(Versicherung).filter(
            Versicherung.vunr == vunr,
            Versicherung.aktiv == True
        ).first()

    def versicherung_erstellen(
        self,
        name: str,
        **kwargs
    ) -> Versicherung:
        """Erstellt einen neuen Versicherungseintrag"""
        versicherung = Versicherung(name=name, **kwargs)
        self.db.add(versicherung)
        self.db.flush()
        return versicherung

    def versicherung_aktualisieren(
        self,
        versicherung_id: int,
        **kwargs
    ) -> Optional[Versicherung]:
        """Aktualisiert eine Versicherung"""
        versicherung = self.db.query(Versicherung).get(versicherung_id)

        if versicherung:
            for key, value in kwargs.items():
                if hasattr(versicherung, key):
                    setattr(versicherung, key, value)
            versicherung.aktualisiert_am = datetime.now()
            self.db.flush()

        return versicherung

    def generiere_anschreiben_adresse(self, versicherung: Versicherung) -> str:
        """Generiert die Adresse für ein Anschreiben"""
        return f"""{versicherung.name}
{versicherung.adresse}
{versicherung.plz} {versicherung.ort}"""

    def generiere_schaden_kontakt(self, versicherung: Versicherung) -> Dict[str, str]:
        """Generiert Kontaktdaten für Schadenmeldung"""
        return {
            "name": versicherung.name,
            "hotline": versicherung.schaden_hotline or versicherung.telefon,
            "email": versicherung.schaden_email or versicherung.email,
            "fax": versicherung.schaden_fax or versicherung.fax,
            "portal": versicherung.schaden_portal or versicherung.website
        }
