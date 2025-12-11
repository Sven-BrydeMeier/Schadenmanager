from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship

from src.models.base import Base
from src.models.enums import Rollen


class User(Base):
    """Benutzer im System"""
    __tablename__ = "user"

    id = Column(Integer, primary_key=True)

    # Persönliche Daten
    vorname = Column(String(100))
    nachname = Column(String(100))
    email = Column(String(255), unique=True, nullable=False)

    # Authentifizierung
    passwort_hash = Column(String(255), nullable=False)
    telefonnummer = Column(String(50))  # Für 2FA per SMS
    totp_secret = Column(String(32))    # Für TOTP-basiertes 2FA
    zwei_faktor_aktiviert = Column(Boolean, default=False)

    # Rolle und Organisation
    rolle = Column(Enum(Rollen), nullable=False)
    organisation_id = Column(Integer, ForeignKey("organisation.id"))

    # Status
    aktiv = Column(Boolean, default=True)
    email_verifiziert = Column(Boolean, default=False)
    letzter_login = Column(DateTime)
    erstellt_am = Column(DateTime, default=datetime.utcnow)
    aktualisiert_am = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Einladung
    einladungs_token = Column(String(255))
    einladung_gueltig_bis = Column(DateTime)

    # Relationships
    organisation = relationship("Organisation", backref="users")

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', rolle={self.rolle.value})>"

    @property
    def voller_name(self) -> str:
        """Gibt den vollen Namen zurück"""
        teile = [self.vorname, self.nachname]
        return " ".join(t for t in teile if t) or self.email

    @property
    def rollen_anzeige(self) -> str:
        """Gibt eine lesbare Rollenbezeichnung zurück"""
        rollen_namen = {
            Rollen.WERKSTATT: "Werkstatt",
            Rollen.GUTACHTER: "Gutachter",
            Rollen.VERSICHERUNG_EIGEN: "Eigene Versicherung",
            Rollen.VERSICHERUNG_GEGNER: "Gegnerische Versicherung",
            Rollen.ANWALT: "Rechtsanwalt",
            Rollen.UNFALLOPFER: "Unfallopfer",
            Rollen.ADMIN: "Administrator"
        }
        return rollen_namen.get(self.rolle, self.rolle.value)
