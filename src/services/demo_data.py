"""
Demo-Daten für die Schadenmanager-Anwendung
Erstellt Testbenutzer und Beispieldaten
"""
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from src.models import (
    User, Organisation, Rollen, OrgTyp,
    UnfallProjekt, Fahrzeug, KostenPosition, KostenKategorie, KostenAmpel,
    TimelineMeilenstein, MeilensteinStatus
)
from src.services.auth import AuthService


DEMO_PASSWORD = "Demo123!"


def create_demo_data(db: Session) -> bool:
    """
    Erstellt Demo-Daten falls noch nicht vorhanden.
    Gibt True zurück wenn Daten erstellt wurden.
    """
    # Prüfen ob bereits Demo-Daten existieren
    existing_admin = db.query(User).filter(User.email == "admin@demo.de").first()
    if existing_admin:
        return False  # Demo-Daten existieren bereits

    auth_service = AuthService(db)

    # Organisationen erstellen
    org_kanzlei = Organisation(
        name="Musterkanzlei Recht & Partner",
        typ=OrgTyp.KANZLEI,
        strasse="Justizstraße",
        hausnummer="42",
        plz="80331",
        ort="München",
        telefon="+49 89 12345678",
        email="info@musterkanzlei.de",
        aktiv=True
    )
    db.add(org_kanzlei)

    org_werkstatt = Organisation(
        name="AutoFix Werkstatt GmbH",
        typ=OrgTyp.WERKSTATT,
        strasse="Industriestraße",
        hausnummer="15",
        plz="80939",
        ort="München",
        telefon="+49 89 98765432",
        email="service@autofix.de",
        aktiv=True
    )
    db.add(org_werkstatt)

    org_gutachter = Organisation(
        name="KFZ-Sachverständigenbüro Meier",
        typ=OrgTyp.GUTACHTERBUERO,
        strasse="Gutachterweg",
        hausnummer="7",
        plz="80634",
        ort="München",
        telefon="+49 89 55544433",
        email="gutachten@sv-meier.de",
        aktiv=True
    )
    db.add(org_gutachter)

    org_versicherung = Organisation(
        name="Sichere Fahrt Versicherung AG",
        typ=OrgTyp.VERSICHERUNG,
        strasse="Versicherungsplatz",
        hausnummer="1",
        plz="80333",
        ort="München",
        telefon="+49 89 11122233",
        email="schaden@sicherefahrt.de",
        aktiv=True
    )
    db.add(org_versicherung)

    db.flush()

    # Demo-Benutzer erstellen
    users = []

    # Admin
    admin, _ = auth_service.benutzer_erstellen(
        email="admin@demo.de",
        passwort=DEMO_PASSWORD,
        rolle=Rollen.ADMIN,
        vorname="System",
        nachname="Administrator"
    )
    users.append(("Admin", admin))

    # Anwalt
    anwalt, _ = auth_service.benutzer_erstellen(
        email="anwalt@demo.de",
        passwort=DEMO_PASSWORD,
        rolle=Rollen.ANWALT,
        vorname="Thomas",
        nachname="Rechtmann",
        organisation_id=org_kanzlei.id
    )
    users.append(("Anwalt", anwalt))

    # Werkstatt
    werkstatt, _ = auth_service.benutzer_erstellen(
        email="werkstatt@demo.de",
        passwort=DEMO_PASSWORD,
        rolle=Rollen.WERKSTATT,
        vorname="Klaus",
        nachname="Schrauber",
        organisation_id=org_werkstatt.id
    )
    users.append(("Werkstatt", werkstatt))

    # Gutachter
    gutachter, _ = auth_service.benutzer_erstellen(
        email="gutachter@demo.de",
        passwort=DEMO_PASSWORD,
        rolle=Rollen.GUTACHTER,
        vorname="Hans",
        nachname="Meier",
        organisation_id=org_gutachter.id
    )
    users.append(("Gutachter", gutachter))

    # Unfallopfer/Kunde
    kunde, _ = auth_service.benutzer_erstellen(
        email="kunde@demo.de",
        passwort=DEMO_PASSWORD,
        rolle=Rollen.UNFALLOPFER,
        vorname="Maria",
        nachname="Mustermann",
        telefonnummer="+49 171 1234567"
    )
    users.append(("Unfallopfer", kunde))

    # Versicherung (gegnerisch)
    versicherung, _ = auth_service.benutzer_erstellen(
        email="versicherung@demo.de",
        passwort=DEMO_PASSWORD,
        rolle=Rollen.VERSICHERUNG_GEGNER,
        vorname="Sabine",
        nachname="Sachbearbeiterin",
        organisation_id=org_versicherung.id
    )
    users.append(("Versicherung", versicherung))

    db.flush()

    # Demo-Fahrzeuge erstellen
    fahrzeug_eigen = Fahrzeug(
        halter_name="Mustermann",
        halter_vorname="Maria",
        halter_strasse="Musterstraße",
        halter_hausnummer="123",
        halter_plz="80331",
        halter_ort="München",
        fin="WVWZZZ3CZWE123456",
        kennzeichen="M-AB 1234",
        hersteller="Volkswagen",
        modell="Golf",
        typ="VIII 1.5 TSI",
        hsn="0603",
        tsn="BNP",
        erstzulassung=datetime(2021, 3, 15).date(),
        quelle="MANUELL"
    )
    db.add(fahrzeug_eigen)

    fahrzeug_gegner = Fahrzeug(
        kennzeichen="M-XY 5678",
        hersteller="BMW",
        modell="3er",
        versicherung_name="Sichere Fahrt Versicherung AG",
        versicherung_nummer="KH-123456789",
        quelle="MANUELL"
    )
    db.add(fahrzeug_gegner)

    db.flush()

    # Demo-Unfallprojekt erstellen mit Aktenzeichen
    aktuelles_jahr = datetime.now().year
    projekt = UnfallProjekt(
        projektnummer="UP-20241201-DEMO01",
        aktenzeichen=f"1/{str(aktuelles_jahr)[-2:]}",
        aktenzeichen_nummer=1,
        aktenzeichen_jahr=aktuelles_jahr,
        datum_unfall=datetime.now() - timedelta(days=14),
        ort_unfall="München, Leopoldstraße / Ecke Feilitzschstraße",
        beschreibung_unfall="Auffahrunfall an roter Ampel. Gegnerisches Fahrzeug fuhr auf stehendes Fahrzeug auf.",
        schuld_eigen_prozent=0,
        anlegende_organisation_id=org_kanzlei.id,
        angelegt_von_user_id=anwalt.id,
        kfz_eigen_id=fahrzeug_eigen.id,
        kfz_gegner_id=fahrzeug_gegner.id,
        unfallopfer_user_id=kunde.id,
        anwalt_user_id=anwalt.id,
        werkstatt_user_id=werkstatt.id,
        gutachter_user_id=gutachter.id,
        versicherung_gegner_user_id=versicherung.id,
        status="IN_BEARBEITUNG",
        einladungs_code="DEMO123456"
    )
    db.add(projekt)
    db.flush()

    # Demo-Kostenpositionen erstellen
    kostenpositionen = [
        KostenPosition(
            unfallprojekt_id=projekt.id,
            kategorie=KostenKategorie.REPARATUR,
            beschreibung="Reparatur Heckschaden (lt. Gutachten)",
            betrag_netto=4200.00,
            mwst_satz=19.0,
            betrag_brutto=4998.00,
            status_ampel=KostenAmpel.ORANGE,
            eingereicht_am=datetime.now() - timedelta(days=7)
        ),
        KostenPosition(
            unfallprojekt_id=projekt.id,
            kategorie=KostenKategorie.GUTACHTEN,
            beschreibung="Sachverständigengutachten",
            betrag_netto=650.00,
            mwst_satz=19.0,
            betrag_brutto=773.50,
            status_ampel=KostenAmpel.GRUEN,
            von_versicherung_freigegeben=True,
            von_versicherung_freigegeben_betrag=773.50
        ),
        KostenPosition(
            unfallprojekt_id=projekt.id,
            kategorie=KostenKategorie.ERSATZWAGEN,
            beschreibung="Mietwagen VW Golf, 10 Tage",
            betrag_netto=590.00,
            mwst_satz=19.0,
            betrag_brutto=702.10,
            status_ampel=KostenAmpel.ORANGE,
            gekuerzt=True,
            von_versicherung_freigegeben_betrag=500.00,
            kuerzung_betrag=202.10,
            kuerzung_grund="Nur Kosten für vergleichbare Fahrzeugklasse erstattungsfähig"
        ),
        KostenPosition(
            unfallprojekt_id=projekt.id,
            kategorie=KostenKategorie.WERTMINDERUNG,
            beschreibung="Merkantile Wertminderung",
            betrag_brutto=800.00,
            status_ampel=KostenAmpel.ROT
        ),
        KostenPosition(
            unfallprojekt_id=projekt.id,
            kategorie=KostenKategorie.NUTZUNGSAUSFALL,
            beschreibung="Nutzungsausfall 3 Tage à 59 EUR",
            betrag_brutto=177.00,
            status_ampel=KostenAmpel.ROT
        ),
    ]

    for kp in kostenpositionen:
        db.add(kp)

    # Demo-Meilensteine erstellen
    meilensteine = [
        TimelineMeilenstein(
            unfallprojekt_id=projekt.id,
            code="BASISDATEN",
            beschreibung="Basisdaten erfasst",
            reihenfolge=1,
            status=MeilensteinStatus.GRUEN,
            erledigt_am=datetime.now() - timedelta(days=13)
        ),
        TimelineMeilenstein(
            unfallprojekt_id=projekt.id,
            code="UNFALLOPFER_REGISTRIERT",
            beschreibung="Mandant registriert",
            reihenfolge=2,
            status=MeilensteinStatus.GRUEN,
            erledigt_am=datetime.now() - timedelta(days=12)
        ),
        TimelineMeilenstein(
            unfallprojekt_id=projekt.id,
            code="GUTACHTER_BEAUFTRAGT",
            beschreibung="Gutachter beauftragt",
            reihenfolge=3,
            status=MeilensteinStatus.GRUEN,
            erledigt_am=datetime.now() - timedelta(days=11)
        ),
        TimelineMeilenstein(
            unfallprojekt_id=projekt.id,
            code="GUTACHTEN_EINGEGANGEN",
            beschreibung="Gutachten erhalten",
            reihenfolge=4,
            status=MeilensteinStatus.GRUEN,
            erledigt_am=datetime.now() - timedelta(days=8)
        ),
        TimelineMeilenstein(
            unfallprojekt_id=projekt.id,
            code="ANSPRUCHSSCHREIBEN_VERSENDET",
            beschreibung="Anspruchsschreiben versendet",
            reihenfolge=5,
            status=MeilensteinStatus.GRUEN,
            erledigt_am=datetime.now() - timedelta(days=7)
        ),
        TimelineMeilenstein(
            unfallprojekt_id=projekt.id,
            code="KOMMUNIKATION_RA_VERSICHERUNG",
            beschreibung="Kommunikation mit Versicherung",
            reihenfolge=6,
            status=MeilensteinStatus.ORANGE
        ),
        TimelineMeilenstein(
            unfallprojekt_id=projekt.id,
            code="KOSTENREGULIERUNG_ABGESCHLOSSEN",
            beschreibung="Regulierung abgeschlossen",
            reihenfolge=7,
            status=MeilensteinStatus.ROT
        ),
    ]

    for ms in meilensteine:
        db.add(ms)

    db.flush()

    print("Demo-Daten erfolgreich erstellt!")
    print("\nDemo-Zugangsdaten:")
    for rolle_name, user in users:
        if user:
            print(f"  {rolle_name}: {user.email} / {DEMO_PASSWORD}")

    return True
