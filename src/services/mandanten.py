"""
Multi-Mandanten Service
Verwaltung mehrerer Mandanten/Kanzleien in einer Installation
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
import json
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from src.models.base import Base


class MandantStatus(str, Enum):
    """Status eines Mandanten"""
    AKTIV = "AKTIV"
    INAKTIV = "INAKTIV"
    TESTPHASE = "TESTPHASE"
    GESPERRT = "GESPERRT"


class LizenzTyp(str, Enum):
    """Lizenz-Typen"""
    BASIC = "BASIC"
    PROFESSIONAL = "PROFESSIONAL"
    ENTERPRISE = "ENTERPRISE"
    UNLIMITED = "UNLIMITED"


class Mandant(Base):
    """Model für Mandanten (Kanzleien/Unternehmen)"""
    __tablename__ = "mandant"

    id = Column(Integer, primary_key=True)

    # Stammdaten
    name = Column(String(200), nullable=False)
    kurzbezeichnung = Column(String(50), unique=True)
    rechtsform = Column(String(50))  # GmbH, PartG mbB, etc.

    # Kontakt
    strasse = Column(String(200))
    plz = Column(String(10))
    ort = Column(String(100))
    telefon = Column(String(50))
    fax = Column(String(50))
    email = Column(String(200))
    website = Column(String(200))

    # Rechtliches
    steuernummer = Column(String(50))
    ustid = Column(String(20))
    handelsregister = Column(String(100))
    berufsbezeichnung = Column(String(100))
    aufsichtsbehoerde = Column(String(200))

    # Bankverbindung
    bank_name = Column(String(100))
    bank_iban = Column(String(34))
    bank_bic = Column(String(11))

    # Lizenz
    lizenz_typ = Column(SQLEnum(LizenzTyp), default=LizenzTyp.BASIC)
    lizenz_gueltig_bis = Column(DateTime)
    max_benutzer = Column(Integer, default=5)
    max_projekte = Column(Integer, default=100)
    max_speicher_mb = Column(Integer, default=1000)

    # Status
    status = Column(SQLEnum(MandantStatus), default=MandantStatus.TESTPHASE)

    # Einstellungen
    _einstellungen = Column("einstellungen", Text)

    # Branding
    logo_url = Column(String(500))
    primaerfarbe = Column(String(7))  # Hex-Farbe
    sekundaerfarbe = Column(String(7))

    # Metadaten
    erstellt_am = Column(DateTime, default=datetime.now)
    aktualisiert_am = Column(DateTime, onupdate=datetime.now)

    @property
    def einstellungen(self) -> Dict[str, Any]:
        if self._einstellungen:
            return json.loads(self._einstellungen)
        return {}

    @einstellungen.setter
    def einstellungen(self, value: Dict[str, Any]):
        self._einstellungen = json.dumps(value)

    @property
    def vollstaendige_adresse(self) -> str:
        teile = []
        if self.strasse:
            teile.append(self.strasse)
        if self.plz or self.ort:
            teile.append(f"{self.plz or ''} {self.ort or ''}".strip())
        return ", ".join(teile)

    @property
    def lizenz_aktiv(self) -> bool:
        if self.status != MandantStatus.AKTIV:
            return False
        if self.lizenz_gueltig_bis and self.lizenz_gueltig_bis < datetime.now():
            return False
        return True


class MandantBenutzer(Base):
    """Zuordnung von Benutzern zu Mandanten"""
    __tablename__ = "mandant_benutzer"

    id = Column(Integer, primary_key=True)

    mandant_id = Column(Integer, ForeignKey("mandant.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)

    # Rolle innerhalb des Mandanten
    ist_admin = Column(Boolean, default=False)
    ist_aktiv = Column(Boolean, default=True)

    # Metadaten
    hinzugefuegt_am = Column(DateTime, default=datetime.now)
    hinzugefuegt_von_user_id = Column(Integer, ForeignKey("user.id"))


class MandantenService:
    """Service für Multi-Mandanten-Verwaltung"""

    # Lizenz-Limits
    LIZENZ_LIMITS = {
        LizenzTyp.BASIC: {
            'max_benutzer': 3,
            'max_projekte': 50,
            'max_speicher_mb': 500,
            'features': ['projekte', 'dokumente', 'kosten']
        },
        LizenzTyp.PROFESSIONAL: {
            'max_benutzer': 10,
            'max_projekte': 500,
            'max_speicher_mb': 5000,
            'features': ['projekte', 'dokumente', 'kosten', 'timeline',
                        'fristen', 'berichte', 'export']
        },
        LizenzTyp.ENTERPRISE: {
            'max_benutzer': 50,
            'max_projekte': 5000,
            'max_speicher_mb': 50000,
            'features': ['alle']
        },
        LizenzTyp.UNLIMITED: {
            'max_benutzer': -1,
            'max_projekte': -1,
            'max_speicher_mb': -1,
            'features': ['alle']
        }
    }

    def __init__(self, db_session):
        self.db = db_session

    def mandant_erstellen(
        self,
        name: str,
        kurzbezeichnung: str,
        lizenz_typ: LizenzTyp = LizenzTyp.BASIC,
        **kwargs
    ) -> Mandant:
        """Erstellt einen neuen Mandanten"""
        # Prüfe ob Kurzbezeichnung eindeutig
        existiert = self.db.query(Mandant).filter(
            Mandant.kurzbezeichnung == kurzbezeichnung
        ).first()

        if existiert:
            raise ValueError(f"Kurzbezeichnung '{kurzbezeichnung}' bereits vergeben")

        # Lizenz-Limits setzen
        limits = self.LIZENZ_LIMITS.get(lizenz_typ, self.LIZENZ_LIMITS[LizenzTyp.BASIC])

        mandant = Mandant(
            name=name,
            kurzbezeichnung=kurzbezeichnung,
            lizenz_typ=lizenz_typ,
            max_benutzer=limits['max_benutzer'],
            max_projekte=limits['max_projekte'],
            max_speicher_mb=limits['max_speicher_mb']
        )

        # Zusätzliche Felder setzen
        for key, value in kwargs.items():
            if hasattr(mandant, key):
                setattr(mandant, key, value)

        self.db.add(mandant)
        self.db.flush()

        return mandant

    def mandant_aktualisieren(
        self,
        mandant_id: int,
        **kwargs
    ) -> Optional[Mandant]:
        """Aktualisiert einen Mandanten"""
        mandant = self.db.query(Mandant).get(mandant_id)

        if mandant:
            for key, value in kwargs.items():
                if hasattr(mandant, key):
                    setattr(mandant, key, value)
            self.db.flush()

        return mandant

    def benutzer_hinzufuegen(
        self,
        mandant_id: int,
        user_id: int,
        ist_admin: bool = False,
        hinzugefuegt_von_user_id: Optional[int] = None
    ) -> MandantBenutzer:
        """Fügt einen Benutzer zu einem Mandanten hinzu"""
        # Prüfe ob bereits zugeordnet
        existiert = self.db.query(MandantBenutzer).filter(
            MandantBenutzer.mandant_id == mandant_id,
            MandantBenutzer.user_id == user_id
        ).first()

        if existiert:
            existiert.ist_aktiv = True
            existiert.ist_admin = ist_admin
            self.db.flush()
            return existiert

        # Prüfe Benutzer-Limit
        mandant = self.db.query(Mandant).get(mandant_id)
        if mandant and mandant.max_benutzer > 0:
            aktuelle_benutzer = self.db.query(MandantBenutzer).filter(
                MandantBenutzer.mandant_id == mandant_id,
                MandantBenutzer.ist_aktiv == True
            ).count()

            if aktuelle_benutzer >= mandant.max_benutzer:
                raise ValueError(f"Benutzer-Limit ({mandant.max_benutzer}) erreicht")

        zuordnung = MandantBenutzer(
            mandant_id=mandant_id,
            user_id=user_id,
            ist_admin=ist_admin,
            hinzugefuegt_von_user_id=hinzugefuegt_von_user_id
        )

        self.db.add(zuordnung)
        self.db.flush()

        return zuordnung

    def benutzer_entfernen(
        self,
        mandant_id: int,
        user_id: int
    ) -> bool:
        """Entfernt einen Benutzer von einem Mandanten"""
        zuordnung = self.db.query(MandantBenutzer).filter(
            MandantBenutzer.mandant_id == mandant_id,
            MandantBenutzer.user_id == user_id
        ).first()

        if zuordnung:
            zuordnung.ist_aktiv = False
            self.db.flush()
            return True

        return False

    def mandanten_fuer_benutzer(self, user_id: int) -> List[Mandant]:
        """Holt alle Mandanten eines Benutzers"""
        zuordnungen = self.db.query(MandantBenutzer).filter(
            MandantBenutzer.user_id == user_id,
            MandantBenutzer.ist_aktiv == True
        ).all()

        mandant_ids = [z.mandant_id for z in zuordnungen]

        return self.db.query(Mandant).filter(
            Mandant.id.in_(mandant_ids),
            Mandant.status.in_([MandantStatus.AKTIV, MandantStatus.TESTPHASE])
        ).all()

    def benutzer_fuer_mandant(self, mandant_id: int) -> List[MandantBenutzer]:
        """Holt alle Benutzer eines Mandanten"""
        return self.db.query(MandantBenutzer).filter(
            MandantBenutzer.mandant_id == mandant_id,
            MandantBenutzer.ist_aktiv == True
        ).all()

    def ist_benutzer_admin(self, mandant_id: int, user_id: int) -> bool:
        """Prüft ob ein Benutzer Admin eines Mandanten ist"""
        zuordnung = self.db.query(MandantBenutzer).filter(
            MandantBenutzer.mandant_id == mandant_id,
            MandantBenutzer.user_id == user_id,
            MandantBenutzer.ist_aktiv == True
        ).first()

        return zuordnung.ist_admin if zuordnung else False

    def lizenz_pruefen(
        self,
        mandant_id: int,
        feature: str
    ) -> Dict[str, Any]:
        """Prüft ob ein Feature für den Mandanten verfügbar ist"""
        mandant = self.db.query(Mandant).get(mandant_id)

        if not mandant:
            return {'erlaubt': False, 'grund': 'Mandant nicht gefunden'}

        if not mandant.lizenz_aktiv:
            return {'erlaubt': False, 'grund': 'Lizenz nicht aktiv'}

        limits = self.LIZENZ_LIMITS.get(mandant.lizenz_typ, self.LIZENZ_LIMITS[LizenzTyp.BASIC])

        if 'alle' in limits['features'] or feature in limits['features']:
            return {'erlaubt': True}

        return {
            'erlaubt': False,
            'grund': f"Feature '{feature}' nicht in Lizenz {mandant.lizenz_typ.value} enthalten"
        }

    def nutzungs_statistik(self, mandant_id: int) -> Dict[str, Any]:
        """Erstellt Nutzungsstatistik für einen Mandanten"""
        from src.models import UnfallProjekt, Dokument

        mandant = self.db.query(Mandant).get(mandant_id)

        if not mandant:
            return {}

        # Projekte zählen (wenn mandant_id in Projekten existiert)
        # Hinweis: In einer echten Implementierung würde UnfallProjekt.mandant_id existieren
        anzahl_projekte = 0
        anzahl_dokumente = 0
        speicher_mb = 0

        # Benutzer zählen
        anzahl_benutzer = self.db.query(MandantBenutzer).filter(
            MandantBenutzer.mandant_id == mandant_id,
            MandantBenutzer.ist_aktiv == True
        ).count()

        return {
            'mandant': mandant.name,
            'lizenz': mandant.lizenz_typ.value,
            'benutzer': {
                'aktuell': anzahl_benutzer,
                'limit': mandant.max_benutzer,
                'prozent': round(anzahl_benutzer / mandant.max_benutzer * 100, 1) if mandant.max_benutzer > 0 else 0
            },
            'projekte': {
                'aktuell': anzahl_projekte,
                'limit': mandant.max_projekte,
                'prozent': round(anzahl_projekte / mandant.max_projekte * 100, 1) if mandant.max_projekte > 0 else 0
            },
            'speicher': {
                'aktuell_mb': speicher_mb,
                'limit_mb': mandant.max_speicher_mb,
                'prozent': round(speicher_mb / mandant.max_speicher_mb * 100, 1) if mandant.max_speicher_mb > 0 else 0
            },
            'lizenz_gueltig_bis': mandant.lizenz_gueltig_bis.isoformat() if mandant.lizenz_gueltig_bis else None
        }

    def alle_mandanten(self, nur_aktive: bool = True) -> List[Mandant]:
        """Holt alle Mandanten"""
        query = self.db.query(Mandant)

        if nur_aktive:
            query = query.filter(
                Mandant.status.in_([MandantStatus.AKTIV, MandantStatus.TESTPHASE])
            )

        return query.order_by(Mandant.name).all()

    def lizenz_upgrade(
        self,
        mandant_id: int,
        neuer_typ: LizenzTyp,
        gueltig_bis: Optional[datetime] = None
    ) -> Optional[Mandant]:
        """Führt ein Lizenz-Upgrade durch"""
        mandant = self.db.query(Mandant).get(mandant_id)

        if mandant:
            limits = self.LIZENZ_LIMITS.get(neuer_typ, self.LIZENZ_LIMITS[LizenzTyp.BASIC])

            mandant.lizenz_typ = neuer_typ
            mandant.max_benutzer = limits['max_benutzer']
            mandant.max_projekte = limits['max_projekte']
            mandant.max_speicher_mb = limits['max_speicher_mb']

            if gueltig_bis:
                mandant.lizenz_gueltig_bis = gueltig_bis

            mandant.status = MandantStatus.AKTIV

            self.db.flush()

        return mandant

    def einstellung_speichern(
        self,
        mandant_id: int,
        schluessel: str,
        wert: Any
    ) -> bool:
        """Speichert eine Mandanten-Einstellung"""
        mandant = self.db.query(Mandant).get(mandant_id)

        if mandant:
            einstellungen = mandant.einstellungen
            einstellungen[schluessel] = wert
            mandant.einstellungen = einstellungen
            self.db.flush()
            return True

        return False

    def einstellung_lesen(
        self,
        mandant_id: int,
        schluessel: str,
        standard: Any = None
    ) -> Any:
        """Liest eine Mandanten-Einstellung"""
        mandant = self.db.query(Mandant).get(mandant_id)

        if mandant:
            return mandant.einstellungen.get(schluessel, standard)

        return standard
