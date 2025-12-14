"""
Signatur-Model für digitale Unterschriften
"""
from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean, LargeBinary
from sqlalchemy.orm import relationship

from src.models.base import Base


class DigitaleSignatur(Base):
    """Digitale Unterschrift für Dokumente"""
    __tablename__ = "digitale_signatur"

    id = Column(Integer, primary_key=True)

    # Zuordnung
    dokument_id = Column(Integer, ForeignKey("dokument.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)

    # Signatur-Daten
    signatur_daten = Column(Text)  # Base64-kodierte Signatur-Grafik
    signatur_typ = Column(String(50), default="GEZEICHNET")  # GEZEICHNET, GETIPPT, HOCHGELADEN

    # Unterschrifts-Details
    name_gedruckt = Column(String(255))  # Getippter Name
    ort = Column(String(100))
    ip_adresse = Column(String(50))
    user_agent = Column(String(500))

    # Verifizierung
    verifiziert = Column(Boolean, default=False)
    verifikations_hash = Column(String(255))  # SHA-256 Hash des signierten Inhalts

    # Rechtliche Bestätigung
    agb_akzeptiert = Column(Boolean, default=False)
    datenschutz_akzeptiert = Column(Boolean, default=False)
    bestaetigung_text = Column(Text)  # Text der vom Unterzeichner bestätigt wurde

    # Timestamps
    erstellt_am = Column(DateTime, default=datetime.utcnow)

    # Relationships
    dokument = relationship("Dokument", backref="signaturen")
    user = relationship("User", backref="signaturen")

    def __repr__(self):
        return f"<DigitaleSignatur(id={self.id}, dokument_id={self.dokument_id}, user_id={self.user_id})>"

    @property
    def ist_gueltig(self) -> bool:
        """Prüft ob die Signatur gültig ist"""
        return (
            self.signatur_daten is not None and
            self.agb_akzeptiert and
            self.datenschutz_akzeptiert
        )


class SignaturAnforderung(Base):
    """Anforderung für eine digitale Unterschrift"""
    __tablename__ = "signatur_anforderung"

    id = Column(Integer, primary_key=True)

    # Zuordnung
    dokument_id = Column(Integer, ForeignKey("dokument.id"), nullable=False)
    angefordert_von_user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    angefordert_fuer_user_id = Column(Integer, ForeignKey("user.id"))  # Optional - für bestimmten Benutzer
    angefordert_fuer_email = Column(String(255))  # Oder für externe Person per E-Mail

    # Status
    status = Column(String(50), default="AUSSTEHEND")  # AUSSTEHEND, UNTERSCHRIEBEN, ABGELEHNT, ABGELAUFEN

    # Details
    nachricht = Column(Text)  # Nachricht an den Unterzeichner
    erinnerung_gesendet = Column(Boolean, default=False)
    erinnerung_gesendet_am = Column(DateTime)

    # Gültigkeit
    gueltig_bis = Column(DateTime)  # Ablaufdatum der Anforderung

    # Timestamps
    erstellt_am = Column(DateTime, default=datetime.utcnow)
    beantwortet_am = Column(DateTime)

    # Relationships
    dokument = relationship("Dokument", backref="signatur_anforderungen")
    angefordert_von = relationship("User", foreign_keys=[angefordert_von_user_id])
    angefordert_fuer = relationship("User", foreign_keys=[angefordert_fuer_user_id])

    @property
    def ist_abgelaufen(self) -> bool:
        """Prüft ob die Anforderung abgelaufen ist"""
        if not self.gueltig_bis:
            return False
        return datetime.now() > self.gueltig_bis
