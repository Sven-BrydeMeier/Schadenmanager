"""
Digitale Signatur Service
Ermöglicht das digitale Unterschreiben von Dokumenten
"""
import hashlib
import base64
from datetime import datetime, timedelta
from typing import Optional, Tuple, List

from sqlalchemy.orm import Session

from src.models import Dokument, User
from src.models.signatur import DigitaleSignatur, SignaturAnforderung


class SignaturService:
    """Service für digitale Signaturen"""

    def __init__(self, db: Session):
        self.db = db

    def signatur_erstellen(
        self,
        dokument_id: int,
        user_id: int,
        signatur_daten: str,
        signatur_typ: str = "GEZEICHNET",
        name_gedruckt: Optional[str] = None,
        ort: Optional[str] = None,
        ip_adresse: Optional[str] = None,
        user_agent: Optional[str] = None,
        bestaetigung_text: Optional[str] = None,
        agb_akzeptiert: bool = False,
        datenschutz_akzeptiert: bool = False
    ) -> Tuple[bool, str, Optional[DigitaleSignatur]]:
        """
        Erstellt eine digitale Signatur für ein Dokument.

        Args:
            dokument_id: ID des zu signierenden Dokuments
            user_id: ID des signierenden Benutzers
            signatur_daten: Base64-kodierte Signatur-Grafik
            signatur_typ: Art der Signatur (GEZEICHNET, GETIPPT, HOCHGELADEN)
            name_gedruckt: Getippter Name (bei GETIPPT)
            ort: Ort der Unterschrift
            ip_adresse: IP-Adresse des Unterzeichners
            user_agent: Browser-Info
            bestaetigung_text: Text der bestätigt wurde
            agb_akzeptiert: AGB wurden akzeptiert
            datenschutz_akzeptiert: Datenschutz wurde akzeptiert

        Returns:
            Tuple (Erfolg, Nachricht, Signatur-Objekt)
        """
        # Dokument prüfen
        dokument = self.db.query(Dokument).filter(Dokument.id == dokument_id).first()
        if not dokument:
            return False, "Dokument nicht gefunden", None

        # Prüfen ob bereits signiert
        bestehende = self.db.query(DigitaleSignatur).filter(
            DigitaleSignatur.dokument_id == dokument_id,
            DigitaleSignatur.user_id == user_id
        ).first()

        if bestehende:
            return False, "Sie haben dieses Dokument bereits unterschrieben", None

        # Rechtliche Bestätigungen prüfen
        if not agb_akzeptiert or not datenschutz_akzeptiert:
            return False, "Bitte akzeptieren Sie die rechtlichen Bestimmungen", None

        # Verifikations-Hash erstellen
        hash_input = f"{dokument_id}:{user_id}:{datetime.now().isoformat()}:{signatur_daten[:100]}"
        verifikations_hash = hashlib.sha256(hash_input.encode()).hexdigest()

        # Signatur erstellen
        signatur = DigitaleSignatur(
            dokument_id=dokument_id,
            user_id=user_id,
            signatur_daten=signatur_daten,
            signatur_typ=signatur_typ,
            name_gedruckt=name_gedruckt,
            ort=ort,
            ip_adresse=ip_adresse,
            user_agent=user_agent,
            bestaetigung_text=bestaetigung_text,
            agb_akzeptiert=agb_akzeptiert,
            datenschutz_akzeptiert=datenschutz_akzeptiert,
            verifikations_hash=verifikations_hash,
            verifiziert=True
        )

        self.db.add(signatur)

        # Signatur-Anforderung als erledigt markieren
        anforderung = self.db.query(SignaturAnforderung).filter(
            SignaturAnforderung.dokument_id == dokument_id,
            SignaturAnforderung.angefordert_fuer_user_id == user_id,
            SignaturAnforderung.status == "AUSSTEHEND"
        ).first()

        if anforderung:
            anforderung.status = "UNTERSCHRIEBEN"
            anforderung.beantwortet_am = datetime.now()

        self.db.flush()

        return True, "Dokument erfolgreich unterschrieben", signatur

    def signatur_anfordern(
        self,
        dokument_id: int,
        angefordert_von_user_id: int,
        angefordert_fuer_user_id: Optional[int] = None,
        angefordert_fuer_email: Optional[str] = None,
        nachricht: Optional[str] = None,
        gueltig_tage: int = 14
    ) -> Tuple[bool, str, Optional[SignaturAnforderung]]:
        """
        Fordert eine Unterschrift für ein Dokument an.

        Args:
            dokument_id: ID des Dokuments
            angefordert_von_user_id: ID des Anfordernden
            angefordert_fuer_user_id: ID des Unterzeichners (intern)
            angefordert_fuer_email: E-Mail des Unterzeichners (extern)
            nachricht: Nachricht an den Unterzeichner
            gueltig_tage: Gültigkeit in Tagen

        Returns:
            Tuple (Erfolg, Nachricht, Anforderung-Objekt)
        """
        # Dokument prüfen
        dokument = self.db.query(Dokument).filter(Dokument.id == dokument_id).first()
        if not dokument:
            return False, "Dokument nicht gefunden", None

        # Prüfen ob bereits eine offene Anforderung existiert
        bestehende = self.db.query(SignaturAnforderung).filter(
            SignaturAnforderung.dokument_id == dokument_id,
            SignaturAnforderung.status == "AUSSTEHEND"
        )

        if angefordert_fuer_user_id:
            bestehende = bestehende.filter(
                SignaturAnforderung.angefordert_fuer_user_id == angefordert_fuer_user_id
            )
        elif angefordert_fuer_email:
            bestehende = bestehende.filter(
                SignaturAnforderung.angefordert_fuer_email == angefordert_fuer_email
            )

        if bestehende.first():
            return False, "Es existiert bereits eine offene Signatur-Anforderung", None

        # Anforderung erstellen
        anforderung = SignaturAnforderung(
            dokument_id=dokument_id,
            angefordert_von_user_id=angefordert_von_user_id,
            angefordert_fuer_user_id=angefordert_fuer_user_id,
            angefordert_fuer_email=angefordert_fuer_email,
            nachricht=nachricht,
            gueltig_bis=datetime.now() + timedelta(days=gueltig_tage)
        )

        self.db.add(anforderung)
        self.db.flush()

        return True, "Signatur-Anforderung erstellt", anforderung

    def get_ausstehende_anforderungen(self, user_id: int) -> List[SignaturAnforderung]:
        """Holt alle ausstehenden Signatur-Anforderungen für einen Benutzer"""
        return self.db.query(SignaturAnforderung).filter(
            SignaturAnforderung.angefordert_fuer_user_id == user_id,
            SignaturAnforderung.status == "AUSSTEHEND"
        ).order_by(SignaturAnforderung.erstellt_am.desc()).all()

    def get_signaturen_fuer_dokument(self, dokument_id: int) -> List[DigitaleSignatur]:
        """Holt alle Signaturen für ein Dokument"""
        return self.db.query(DigitaleSignatur).filter(
            DigitaleSignatur.dokument_id == dokument_id
        ).order_by(DigitaleSignatur.erstellt_am.desc()).all()

    def signatur_verifizieren(self, signatur_id: int) -> Tuple[bool, str]:
        """
        Verifiziert eine digitale Signatur.

        Args:
            signatur_id: ID der Signatur

        Returns:
            Tuple (Gültig, Nachricht)
        """
        signatur = self.db.query(DigitaleSignatur).filter(
            DigitaleSignatur.id == signatur_id
        ).first()

        if not signatur:
            return False, "Signatur nicht gefunden"

        # Prüfungen
        if not signatur.signatur_daten:
            return False, "Keine Signatur-Daten vorhanden"

        if not signatur.agb_akzeptiert:
            return False, "AGB wurden nicht akzeptiert"

        if not signatur.datenschutz_akzeptiert:
            return False, "Datenschutz wurde nicht akzeptiert"

        if not signatur.verifikations_hash:
            return False, "Kein Verifikations-Hash vorhanden"

        return True, f"Signatur gültig. Hash: {signatur.verifikations_hash[:16]}..."

    def anforderung_ablehnen(
        self,
        anforderung_id: int,
        user_id: int
    ) -> Tuple[bool, str]:
        """
        Lehnt eine Signatur-Anforderung ab.

        Args:
            anforderung_id: ID der Anforderung
            user_id: ID des ablehnenden Benutzers

        Returns:
            Tuple (Erfolg, Nachricht)
        """
        anforderung = self.db.query(SignaturAnforderung).filter(
            SignaturAnforderung.id == anforderung_id,
            SignaturAnforderung.angefordert_fuer_user_id == user_id
        ).first()

        if not anforderung:
            return False, "Anforderung nicht gefunden"

        anforderung.status = "ABGELEHNT"
        anforderung.beantwortet_am = datetime.now()
        self.db.flush()

        return True, "Signatur-Anforderung abgelehnt"


def get_signatur_service(db: Session) -> SignaturService:
    """Factory-Funktion für den Signatur-Service"""
    return SignaturService(db)
