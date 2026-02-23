# Schadenmanager - Vollständige Systemdokumentation
## Für die React-Migration / Neuentwicklung

---

## 1. SYSTEMÜBERSICHT

Der Schadenmanager ist ein **Verkehrsunfall-Schadensmanagement-System** für Rechtsanwälte, Werkstätten, Gutachter, Versicherungen und Unfallopfer. Es verwaltet den gesamten Regulierungsprozess von der Unfallaufnahme bis zur Abrechnung.

**Tech-Stack (aktuell):**
- Frontend: Streamlit (Python)
- Backend: SQLAlchemy ORM
- DB: SQLite/PostgreSQL
- KI: OpenAI GPT-4, Anthropic Claude
- Vector-DB: ChromaDB (Embeddings/RAG)
- OCR: Tesseract
- PDF: pdfplumber, PyMuPDF, PyPDF2
- Auth: bcrypt, pyotp (2FA), Twilio (SMS)
- Storage: Local / Supabase
- Export: DATEV, PDF (ReportLab)

---

## 2. ROLLEN-SYSTEM (7 Rollen)

### 2.1 Rollendefinition

| Rolle | Beschreibung | Schlüsselfeld im Projekt |
|-------|-------------|--------------------------|
| **ADMIN** | Systemadministrator, voller Zugriff | - (sieht alles) |
| **ANWALT** | Rechtsanwalt, Case-Management | `anwalt_user_id` |
| **WERKSTATT** | KFZ-Werkstatt, Reparatur | `werkstatt_user_id` |
| **GUTACHTER** | KFZ-Sachverständiger | `gutachter_user_id` |
| **VERSICHERUNG_EIGEN** | Eigene Versicherung | `versicherung_eigen_user_id` |
| **VERSICHERUNG_GEGNER** | Gegnerische Versicherung | `versicherung_gegner_user_id` |
| **UNFALLOPFER** | Geschädigter/Mandant | `unfallopfer_user_id` |

### 2.2 Berechtigungsmatrix

| Funktion | ADMIN | ANWALT | WERKSTATT | GUTACHTER | VERS_EIGEN | VERS_GEGNER | OPFER |
|----------|:-----:|:------:|:---------:|:---------:|:----------:|:-----------:|:-----:|
| **Dashboard** | Admin-View | Akten-View | Werkstatt-View | Gutachter-View | Versicherungs-View | Versicherungs-View | Mandanten-Portal |
| **Projekte** | Alle | Eigene | Eigene | Eigene | Eigene | Eigene | Eigenes |
| **Dokumente** | Alle | Alle im Fall | Eigene im Fall | Eigene im Fall | Eingeschränkt | Eingeschränkt | Freigegebene |
| **Korrespondenz** | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| **Nachrichten** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| **E-Mail** | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ |
| **Serienbriefe** | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| **Kalender** | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ |
| **Wiedervorlagen** | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ |
| **Fristen** | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ |
| **Schadensbilder** | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ |
| **Unfallskizze** | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ |
| **Unfallort-Karte** | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ |
| **Fahrzeugbewertung** | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ |
| **Sprachnotizen** | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ |
| **Restwertbörse** | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ |
| **Gutachten-Prüfung** | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| **Kosten** | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | Eingeschränkt |
| **Gebührenberechnung** | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| **Schadensrechner** | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| **Haftungsquote** | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| **Vergleichsrechner** | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| **Rechnungen** | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| **DATEV-Export** | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| **RA-Micro Import** | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| **Aktenimport** | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| **Ermittlungsakte** | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| **Prozessmodul** | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| **Fallberichte** | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| **Ersatzwagen** | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ | ✓ |
| **Versicherungen** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ |
| **Dokumenten-Chat (KI)** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| **Werkzeuge** | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ |
| **KI-Analyse** | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| **Statistik** | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| **Audit-Log** | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| **Signatur** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| **Datenschutz** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| **DSGVO** | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ |
| **Papierkorb** | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ |
| **Admin-Tools** | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| **API-Verwaltung** | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| **Backup** | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| **Mandanten/Orgs** | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| **Erscheinungsbild** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| **Unfallaufnahme** | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ |

---

## 3. DATENMODELL (46 Tabellen)

### 3.1 Kernmodelle

#### User (`user`)
| Feld | Typ | Beschreibung |
|------|-----|-------------|
| id | Integer PK | |
| vorname | String(100) | |
| nachname | String(100) | |
| email | String(255), unique, NOT NULL | Login-E-Mail |
| passwort_hash | String(255), NOT NULL | bcrypt-Hash |
| telefonnummer | String(50) | |
| totp_secret | String(32) | 2FA-Secret |
| zwei_faktor_aktiviert | Boolean, default=False | |
| rolle | Enum(Rollen), NOT NULL | WERKSTATT/GUTACHTER/VERSICHERUNG_EIGEN/VERSICHERUNG_GEGNER/ANWALT/UNFALLOPFER/ADMIN |
| organisation_id | FK → organisation.id | |
| aktiv | Boolean, default=True | |
| email_verifiziert | Boolean, default=False | |
| letzter_login | DateTime | |
| einladungs_token | String(255) | Einladungslink |
| einladung_gueltig_bis | DateTime | |
| erstellt_am | DateTime | |
| aktualisiert_am | DateTime | |
| **Properties:** voller_name, rollen_anzeige | | |

#### Organisation (`organisation`)
| Feld | Typ | Beschreibung |
|------|-----|-------------|
| id | Integer PK | |
| name | String(255), NOT NULL | |
| typ | Enum(OrgTyp) | KANZLEI/WERKSTATT/VERSICHERUNG/GUTACHTERBUERO/ERSATZWAGENANBIETER |
| strasse, hausnummer, plz, ort, land | Adresse | |
| geo_lat, geo_lon | Float | GPS-Koordinaten |
| telefon, email, website | String | Kontakt |
| aktiv | Boolean | |
| **Properties:** vollstaendige_adresse | | |

#### UnfallProjekt (`unfallprojekt`) - ZENTRALES MODELL
| Feld | Typ | Beschreibung |
|------|-----|-------------|
| id | Integer PK | |
| projektnummer | String(50), unique | Format: "UP-YYYYMMDD-XXXXXX" |
| aktenzeichen | String(20) | Format: "NNN/YY" (z.B. "777/25") |
| aktenzeichen_nummer | Integer | Die Nummer (777) |
| aktenzeichen_jahr | Integer | Das Jahr (2025) |
| datum_unfall | DateTime | |
| uhrzeit_unfall | String(10) | |
| ort_unfall | String(255) | |
| beschreibung_unfall | Text | |
| polizei_aktenzeichen | String(100) | |
| schuld_eigen_prozent | Integer, default=0 | 0=keine Schuld, 100=volle |
| schuld_begruendung | Text | |
| anlegende_organisation_id | FK → organisation.id | |
| angelegt_von_user_id | FK → user.id | |
| kfz_eigen_id | FK → fahrzeug.id | Eigenes Fahrzeug |
| kfz_gegner_id | FK → fahrzeug.id | Gegner-Fahrzeug |
| **unfallopfer_user_id** | FK → user.id | Zuordnung: Opfer |
| **anwalt_user_id** | FK → user.id | Zuordnung: Anwalt |
| **werkstatt_user_id** | FK → user.id | Zuordnung: Werkstatt |
| **gutachter_user_id** | FK → user.id | Zuordnung: Gutachter |
| **versicherung_eigen_user_id** | FK → user.id | Zuordnung: Eigene Vers. |
| **versicherung_gegner_user_id** | FK → user.id | Zuordnung: Gegner-Vers. |
| ersatzwagenanbieter_id | FK → organisation.id | |
| ersatzwagen_von, ersatzwagen_bis | DateTime | Mietdauer |
| status | String(50) | OFFEN/IN_BEARBEITUNG/ABGESCHLOSSEN/STORNIERT |
| abgeschlossen, abgeschlossen_am | Boolean/DateTime | |
| einladungs_code | String(100) | Mandanten-Einladung |
| einladung_gueltig_bis | DateTime | |
| **Relationships:** dokumente, kostenpositionen, gebuehrenberechnungen, korrespondenzen, timeline_meilensteine | | cascade delete |
| **Properties:** status_anzeige | | |

#### Fahrzeug (`fahrzeug`)
| Feld | Typ | Beschreibung |
|------|-----|-------------|
| id | Integer PK | |
| halter_name, halter_vorname | String | Halter |
| halter_strasse, halter_hausnummer, halter_plz, halter_ort | String | Halteradresse |
| fin | String(50) | Fahrgestellnummer |
| kennzeichen | String(20) | |
| hersteller, modell, typ | String | Fahrzeugdaten |
| hsn, tsn | String | Herstellerschlüssel |
| erstzulassung | Date | |
| hubraum | Integer | |
| leistung_kw | Integer | |
| kraftstoff | String(50) | |
| farbe | String(50) | |
| versicherung_name | String(255) | |
| versicherung_nummer | String(100) | |
| quelle | String(50) | MANUELL/OCR/IMPORT |
| ocr_rohdaten | Text | |
| **Properties:** halter_vollstaendig, fahrzeug_bezeichnung | | |

#### Dokument (`dokument`)
| Feld | Typ | Beschreibung |
|------|-----|-------------|
| id | Integer PK | |
| unfallprojekt_id | FK → unfallprojekt.id, NOT NULL | |
| hochgeladen_von_user_id | FK → user.id | |
| dokument_typ | Enum(DokumentTyp) | FAHRZEUGSCHEIN/PERSONALAUSWEIS/GUTACHTEN/RECHNUNG/VERSICHERUNGSSCHREIBEN/KUERZUNGSSCHREIBEN/ANSPRUCHSSCHREIBEN/VOLLMACHT/SONSTIG |
| original_dateiname | String(255) | |
| dateipfad | String(500) | |
| mime_typ | String(100) | |
| dateigroesse | Integer | |
| ocr_text | Text | OCR-extrahierter Text |
| ocr_verarbeitet | Boolean | |
| ocr_manuell_korrigiert | Boolean | |
| ki_strukturierte_daten | Text (JSON) | KI-extrahierte Daten |
| ki_daten_uebernommen | Boolean | |
| **sichtbarkeit** | String(255), default="ALLE" | Kommagetrennte Rollen oder "ALLE" |
| **freigabe_erforderlich** | Boolean, default=True | |
| **freigabe_erteilt** | Boolean, default=False | |
| freigabe_erteilt_von_user_id | FK → user.id | |
| freigabe_abgelehnt | Boolean | |
| status | String(50) | HOCHGELADEN/OCR_VERARBEITET/KI_EXTRAHIERT |
| storage_provider | String(50) | "local" oder "supabase" |
| storage_key | String(500) | |
| geloescht, geloescht_am | Boolean/DateTime | Soft-Delete |
| **Methods:** ist_sichtbar_fuer_rolle(rolle), get_bytes(), get_signed_url() | | |

#### KostenPosition (`kostenposition`)
| Feld | Typ | Beschreibung |
|------|-----|-------------|
| id | Integer PK | |
| unfallprojekt_id | FK → unfallprojekt.id | |
| kategorie | Enum(KostenKategorie) | REPARATUR/GUTACHTEN/ERSATZWAGEN/NUTZUNGSAUSFALL/WERTMINDERUNG/SONSTIG/RA_GEBUEHREN |
| beschreibung | String(255) | |
| betrag_netto | Float | |
| mwst_satz | Float, default=19.0 | |
| betrag_brutto | Float, NOT NULL | |
| **status_ampel** | Enum(KostenAmpel) | ROT/ORANGE/GRUEN |
| eingereicht_am | DateTime | |
| von_versicherung_freigegeben | Boolean | |
| von_versicherung_freigegeben_betrag | Float | |
| gekuerzt | Boolean | |
| kuerzung_betrag, kuerzung_grund | Float/Text | |
| bezahlt, bezahlt_betrag, bezahlt_am | Boolean/Float/DateTime | |
| referenz_dokument_id | FK → dokument.id | |
| **Properties:** ampel_farbe, ampel_icon, differenz_betrag | | |

#### Korrespondenz (`korrespondenz`)
| Feld | Typ | Beschreibung |
|------|-----|-------------|
| id | Integer PK | |
| unfallprojekt_id | FK → unfallprojekt.id | |
| erstellt_von_user_id | FK → user.id | |
| richtung | Enum | RA_AN_VERSICHERUNG/VERSICHERUNG_AN_RA/RA_AN_MANDANT/MANDANT_AN_RA/WERKSTATT_AN_VERSICHERUNG/SONSTIG |
| betreff | String(255) | |
| text_entwurf, text_final | Text | |
| ki_generiert | Boolean | |
| status | String(50) | ENTWURF/FREIGEGEBEN/VERSENDET |
| versendet_am, versendet_via | DateTime/String | |
| antwort_erwartet, antwort_frist | Boolean/DateTime | |
| embedding_erstellt | Boolean | Für Stil-Referenz |
| **Properties:** richtung_anzeige, status_anzeige, aktueller_text | | |

#### GebuehrenBerechnung (`gebuehrberechnung`)
| Feld | Typ | Beschreibung |
|------|-----|-------------|
| streitwert | Float, NOT NULL | Streitwert/Gegenstandswert |
| geschaeftsgebuehr_faktor | Float, default=1.3 | RVG-Faktor |
| geschaeftsgebuehr | Float | Berechnete Gebühr |
| einigungsgebuehr_faktor | Float | |
| auslagenpauschale | Float, default=20.0 | |
| umsatzsteuer_satz | Float, default=19.0 | |
| gesamt_brutto | Float, NOT NULL | |
| **Methods:** get_gebuehrenwert(streitwert) (static), berechne() | | Nach RVG-Tabelle |

#### TimelineMeilenstein (`timeline_meilenstein`)
| Feld | Typ | Beschreibung |
|------|-----|-------------|
| unfallprojekt_id | FK | |
| code | String(100) | Meilenstein-Code |
| beschreibung | String(255) | |
| reihenfolge | Integer | |
| status | Enum(MeilensteinStatus) | ROT/ORANGE/GRUEN/ERLEDIGT/IN_BEARBEITUNG/AUSSTEHEND |
| partei_zustaendig | String(50) | Welche Rolle zuständig |
| faelligkeitsdatum | DateTime | |
| automatisch_berechnet | String(10) | JA/NEIN |
| **Properties:** status_farbe, status_icon, ist_erledigt | | |

### 3.2 Weitere Modelle

#### Wiedervorlage (`wiedervorlage`)
- Fälligkeiten und Erinnerungen
- Typen: ERINNERUNG, FRIST, WIEDERVORLAGE, TERMIN
- Prioritäten: NIEDRIG, NORMAL, HOCH, DRINGEND
- E-Mail-Benachrichtigung

#### Notiz (`notiz`)
- Projekt-gebundene Notizen
- Kategorien, wichtig-Flag, angeheftet-Flag

#### Mahnung (`mahnung`)
- Mahnstufen 1-3
- Zahlungsfrist, Bezahlt-Status

#### ChatNachricht (`chat_nachricht`)
- Dokumenten-Chat mit KI
- Rollen: USER, ASSISTANT, SYSTEM
- Generierte Schreiben mit Versandstatus

#### Nachricht (`nachricht`) - Internes Messaging
- Konversations-basiert
- Typen: TEXT, SYSTEM, DOKUMENT
- Prioritäten: NIEDRIG, NORMAL, HOCH, DRINGEND

#### Email (`email`)
- IMAP/SMTP-Integration
- Auto-Zuordnung zu Projekten (Aktenzeichen, E-Mail-Adresse, Kennzeichen)
- KI-Zusammenfassung

#### AktenImport (`akten_import`)
- PDF-Import mit Dokumenttrennung
- Inhaltsverzeichnis-Extraktion
- Beteiligte-Erkennung

#### Ermittlungsakte (`ermittlungsakte`)
- Staatsanwaltschaft-Aktenanforderung
- KI-Zusammenfassung
- Weitergabe an Beteiligte

#### Sprachnotiz (`sprachnotiz`)
- Audio-Aufnahme mit Transkription
- Kategorien: NOTIZ, DIKTAT, TELEFONAT, ZEUGENBEFRAGUNG, ORTSTERMIN

#### DigitaleSignatur (`digitale_signatur`)
- Dokumenten-Unterschrift
- Verifikations-Hash
- AGBs/Datenschutz-Akzeptanz

#### RestwertAnfrage/Angebot (`restwert_anfrage`, `restwert_angebot`)
- Restwert-Börsen-Management
- Fahrzeugdaten, Gebote, Akzeptanz

#### Fallbericht (`fallbericht`)
- Automatische Berichtgenerierung
- Typen: VOLLSTAENDIG, ZUSAMMENFASSUNG, KOSTENAUFSTELLUNG, TIMELINE, VERSICHERUNG, GERICHT, MANDANT

#### DATEVExport (`datev_export`)
- Buchhaltungsexport
- SKR03-Kontenrahmen

#### TUVDaten (`tuev_daten`)
- HU/AU-Daten am Fahrzeug

#### LeasingKreditbank (`leasing_kreditbank`)
- Finanzierung: LEASING, KREDIT, BALLONFINANZIERUNG, MIETKAUF

#### PolizeiDienststelle (`polizei_dienststelle`)
- Unfallaufnahme-Daten, Ermittlungsverfahren

#### Bankverbindung (`bankverbindung`)
- IBAN, BIC, SEPA-Mandat

#### ChecklistenItem (`checklisten_item`)
- Vordefinierte Checklisten pro Projekt

#### AuditLog (`audit_log`)
- Komplett-Protokoll aller Aktionen
- Kategorien: AUTH, PROJEKT, DOKUMENT, KOSTEN, WIEDERVORLAGE

#### DatenschutzZustimmung (`datenschutz_zustimmung`)
- DSGVO-konform: Datenschutz, AGBs, Widerrufsbelehrung

#### BenutzerTheme (`benutzer_theme`)
- Dark/Light Mode, Schriftgröße, Kompakt-Modus

#### Dokumentvorlage/GeneriertesDokument (`dokumentvorlage`, `generiertes_dokument`)
- Serienbrief-Vorlagen mit Platzhaltern
- {{aktenzeichen}}, {{mandant_name}}, {{kennzeichen}}, etc.

#### ErsatzwagenAnbieter/MietfahrzeugAngebot
- Mietwagen-Verwaltung mit Preisen pro Fahrzeugklasse

---

## 4. SERVICES (Business-Logik)

### 4.1 Authentifizierung & Benutzerverwaltung

| Service | Datei | Funktionen |
|---------|-------|-----------|
| **AuthService** | auth.py | Login, Registrierung, 2FA (TOTP + SMS via Twilio), Einladungen, Passwort-Hashing |
| **AuditService** | audit.py | Alle Aktionen protokollieren, Audit-Trail |

### 4.2 Dokumentenmanagement

| Service | Datei | Funktionen |
|---------|-------|-----------|
| **OCRService** | ocr.py | Tesseract OCR für PDF/Bilder, seitenweise Verarbeitung |
| **KIExtraktor** | ocr.py | KI-basierte Datenextraktion aus OCR-Text (Fahrzeugschein, Personalausweis, Gutachten, Rechnung) |
| **VectorStoreService** | vector_store.py | ChromaDB Embeddings, semantische Suche, Dokument-Chunking (1000 Zeichen, 200 Overlap) |
| **PapierkorbService** | papierkorb.py | Soft-Delete mit 48h Wiederherstellung |
| **DokumentenKlassifizierungsService** | dokumentenklassifizierung.py | Automatische Dokumenttyp-Erkennung |

### 4.3 KI & Text-Generierung

| Service | Datei | Funktionen |
|---------|-------|-----------|
| **DokumentenChatService** | dokumenten_chat.py | RAG-basiertes Q&A über Dokumente, Schreiben-Generierung |
| **KITextGenerator** | ki_textgenerator.py | Anspruchsschreiben, Kürzungserwiderung, Mandanteninformation mit BGB/StVG-Referenzen |
| **KorrespondenzEmbeddingService** | korrespondenz_embeddings.py | Stil-Referenz für KI-Schreibassistent |
| **KIAnalyseService** | ki_analyse.py | Dokumentanalyse (Gutachten, Kürzungsschreiben, etc.) |

### 4.4 Schadenberechnung

| Service | Datei | Funktionen |
|---------|-------|-----------|
| **NutzungsausfallRechner** | schadensrechner.py | Fahrzeuggruppen A-K + SUV, Tagessätze €23-€175 |
| **MerkantilerMinderwertRechner** | schadensrechner.py | 3 Methoden: Ruhkopf-Sahm, Halbgewachs, DVGT |
| **SchmerzensgeldRechner** | schmerzensgeld.py | Schmerzensgeldbemessung |
| **HaftungsquotenRechner** | haftungsquote.py | Haftungsquote berechnen |
| **GebuehrenBerechnung** | (Modell) | RVG-Tabelle, Streitwert → Gebühren |

### 4.5 Import & Export

| Service | Datei | Funktionen |
|---------|-------|-----------|
| **AktenImportService** | aktenimport.py | PDF-Import mit Lesezeichen-/TOC-basierter Dokumenttrennung, Beteiligte-Extraktion |
| **RAMicroParser** | ramicro_parser.py | RA-Micro Aktengestalter PDF-Import, Beteiligter-Erkennung, Kosten-Extraktion |
| **RAMicroTrainingManager** | ramicro_training.py | Lern-System für RA-Micro Parser (Korrekturen als Trainingsbeispiele) |
| **DATEVService** | datev.py | DATEV-Export mit SKR03-Kontenrahmen |
| **FallberichtService** | fallbericht.py | PDF-Fallberichte (7 Typen) |
| **BackupService** | backup.py | Vollständige/Teil-Backups in ZIP/JSON/CSV |
| **SerienbriefeService** | serienbriefe.py | Vorlagen mit Platzhaltern, Batch-Generierung |

### 4.6 Kommunikation

| Service | Datei | Funktionen |
|---------|-------|-----------|
| **NachrichtenService** | nachrichten.py | Internes Messaging, Konversationen, Gelesen-Status |
| **EmailIntegrationService** | email_integration.py | IMAP/SMTP, Auto-Zuordnung, .eml/.msg Import, Drag&Drop |

### 4.7 Spezial-Services

| Service | Datei | Funktionen |
|---------|-------|-----------|
| **MeilensteinEngine** | meilenstein_engine.py | Automatische Ampel-Berechnung basierend auf Dokumenten/Kosten/Korrespondenz |
| **RestwertService** | restwert.py | Restwertbörse, Gebote verwalten |
| **ErmittlungsakteService** | ermittlungsakte.py | Staatsanwaltschaft-Akten verwalten |
| **SprachnotizService** | sprachnotizen.py | Audio-Aufnahmen mit Transkription |
| **ThemeService** | themes.py | Dark/Light Mode |
| **AktenmanagementService** | aktenmanagement.py | Aktenzeichen-Generierung, Aktenverwaltung |

---

## 5. SEITENSTRUKTUR & NAVIGATION

### 5.1 Menü-Struktur

```
📋 HAUPTBEREICH
├── Dashboard (rollenspezifisch)
├── Projekte (Übersicht + Neues Projekt)
└── Dokumente (Upload, Übersicht, OCR-Prüfung, Freigaben, Verarbeitung)

💬 KOMMUNIKATION
├── Korrespondenz [ANWALT, ADMIN]
├── Nachrichten [ALLE]
├── E-Mail [ADMIN, ANWALT, WERKSTATT]
└── Serienbriefe [ADMIN, ANWALT]

📅 TERMINE & FRISTEN
├── Kalender [ADMIN, ANWALT, WERKSTATT, GUTACHTER]
├── Wiedervorlagen [ADMIN, ANWALT, WERKSTATT, GUTACHTER]
└── Fristen [ADMIN, ANWALT, WERKSTATT, GUTACHTER]

🔍 SCHADEN & BEGUTACHTUNG
├── Schadensbilder [ADMIN, ANWALT, WERKSTATT, GUTACHTER]
├── Unfallskizze [ADMIN, ANWALT, WERKSTATT, GUTACHTER]
├── Unfallort-Karte [ADMIN, ANWALT, WERKSTATT, GUTACHTER]
├── Fahrzeugbewertung [ADMIN, ANWALT, WERKSTATT, GUTACHTER]
├── Sprachnotizen [ADMIN, ANWALT, WERKSTATT, GUTACHTER]
├── Restwertbörse [ADMIN, ANWALT, WERKSTATT]
└── Gutachten-Prüfung [ADMIN, ANWALT]

💰 FINANZEN
├── Kosten [ANWALT, WERKSTATT, VERS_EIGEN, VERS_GEGNER, ADMIN]
├── Gebührenberechnung [ANWALT, ADMIN]
├── Schadensrechner [ANWALT, ADMIN]
├── Haftungsquote [ANWALT, ADMIN]
├── Vergleichsrechner [ANWALT, ADMIN]
├── Rechnungen [ANWALT, ADMIN]
└── DATEV-Export [ANWALT, ADMIN]

⚖️ RECHTSBEREICH
├── RA-Micro Import [ANWALT, ADMIN]
├── Aktenimport [ANWALT, ADMIN]
├── Ermittlungsakte [ANWALT, ADMIN]
├── Prozessmodul [ANWALT, ADMIN]
└── Fallberichte [ANWALT, ADMIN]

🚗 FAHRZEUG & VERSICHERUNG
├── Ersatzwagen [WERKSTATT, UNFALLOPFER, ADMIN]
├── Versicherungen [nicht UNFALLOPFER]
└── Ersatzwagen-Verwaltung [ADMIN]

🛠️ WERKZEUGE & KI
├── Dokumenten-Chat [ALLE]
├── Werkzeuge [ANWALT, WERKSTATT, ADMIN]
└── KI-Analyse [ANWALT, ADMIN]

⚙️ SYSTEM
├── Statistik [ANWALT, ADMIN]
├── Audit-Log [ANWALT, ADMIN]
├── Signatur [ALLE]
├── Datenschutz [ALLE]
├── DSGVO [ANWALT, WERKSTATT, ADMIN]
├── Papierkorb [ANWALT, WERKSTATT, ADMIN, GUTACHTER]
├── Admin-Tools [ANWALT, ADMIN]
├── API-Verwaltung [ADMIN]
├── Backup [ADMIN]
├── Mandanten [ADMIN]
└── Erscheinungsbild [ALLE]
```

### 5.2 Dashboard pro Rolle

**ADMIN:**
- Metriken: Offene Projekte, In Bearbeitung, Abgeschlossen, Aktive Benutzer
- Alle Projekte aufgelistet

**ANWALT:**
- Aktenzeichen-Auswahl (NNN/YY)
- Letzter Dokumenteneingang
- Status-Timeline (Meilensteine)
- Tabs: Kosten, Dokumente, Korrespondenz, Gebühren

**WERKSTATT:**
- Metriken: Offene Reparaturen, Aktive Ersatzwagen, Projekte gesamt
- Projektliste mit Fahrzeug-Info

**GUTACHTER:**
- Metriken: Gutachten ausstehend, Aufträge gesamt
- Upload-Button für fehlende Gutachten

**UNFALLOPFER (Mandanten-Portal):**
- "Mein Schadensfall" - vereinfachte Sprache
- Fortschrittsbalken, Regulierungsstatus
- Kosten-Übersicht (Gesamt, Übernommen, Offen)
- Letzter Dokumenteneingang

**VERSICHERUNG:**
- Metriken: Offene Fälle, Offene Forderungen, Abgeschlossen
- Kostenpositionen mit Freigabe-Buttons
- Ampel-System (Rot/Orange/Grün)

---

## 6. ZENTRALE VERKNÜPFUNGEN

### 6.1 Entity-Relationship (vereinfacht)

```
User ──────────────┐
  │                │
  │ rolle          │ organisation_id
  ▼                ▼
Rollen(Enum)   Organisation
                   │
                   │ typ
                   ▼
               OrgTyp(Enum)

UnfallProjekt ◄──── ZENTRALER KNOTEN
  │
  ├── anwalt_user_id ──► User
  ├── werkstatt_user_id ──► User
  ├── gutachter_user_id ──► User
  ├── unfallopfer_user_id ──► User
  ├── versicherung_eigen_user_id ──► User
  ├── versicherung_gegner_user_id ──► User
  │
  ├── kfz_eigen_id ──► Fahrzeug ──► TUVDaten
  ├── kfz_gegner_id ──► Fahrzeug     LeasingKreditbank
  │
  ├──► Dokument[] (cascade)
  │      ├── sichtbarkeit (rollenbasiert)
  │      ├── freigabe_erforderlich/erteilt
  │      ├── OCR + KI-Extraktion
  │      └── DigitaleSignatur[]
  │
  ├──► KostenPosition[] (cascade)
  │      └── status_ampel (ROT/ORANGE/GRUEN)
  │
  ├──► Korrespondenz[] (cascade)
  │      └── richtung (RA↔Versicherung, RA↔Mandant, etc.)
  │
  ├──► TimelineMeilenstein[] (cascade)
  │      └── status (ROT/ORANGE/GRUEN/ERLEDIGT)
  │
  ├──► GebuehrenBerechnung[]
  ├──► Wiedervorlage[]
  ├──► Notiz[]
  ├──► Mahnung[]
  ├──► ChatNachricht[]
  ├──► Nachricht[]
  ├──► Email[]
  ├──► AktenImport[]
  ├──► Ermittlungsakte[]
  ├──► Sprachnotiz[]
  ├──► PolizeiDienststelle[]
  ├──► Bankverbindung[]
  ├──► ChecklistenItem[]
  ├──► RestwertAnfrage[]
  ├──► Fallbericht[]
  ├──► GeneriertesDokument[]
  └──► AuditLog[]
```

### 6.2 Datenfluss

```
PDF Upload
  │
  ├─► Dokument erstellen
  ├─► OCR-Verarbeitung (Tesseract)
  ├─► KI-Extraktion (GPT-4/Claude)
  ├─► Vector-Store indexieren (ChromaDB)
  └─► Meilenstein-Status aktualisieren

Korrespondenz-Erstellung
  │
  ├─► KI-Textgenerator (mit Stil-Referenz)
  ├─► Entwurf → Freigabe → Versand
  └─► Embedding erstellen (Stil-Lernen)

RA-Micro Import
  │
  ├─► PDF parsen (pdfplumber/PyMuPDF)
  ├─► Lesezeichen → Dokumentstruktur
  ├─► Aktenvorblatt → Beteiligte extrahieren
  ├─► Editierbare Vorschau anzeigen
  ├─► Bei Korrektur → Trainingsbeispiel speichern
  └─► Projekt + Dokumente erstellen
```

---

## 7. AUTHENTIFIZIERUNG

### Login-Flow
```
Email + Passwort
  │
  ├─► bcrypt-Verifizierung
  │
  ├─► 2FA aktiviert?
  │     ├─ JA: TOTP-Code oder SMS-Code
  │     └─ NEIN: Direkt-Login
  │
  └─► Session State setzen:
        user_id, user_email, user_name,
        user_rolle, user_organisation_id, logged_in
```

### Demo-Benutzer
| E-Mail | Rolle |
|--------|-------|
| admin@demo.de | ADMIN |
| anwalt@demo.de | ANWALT |
| werkstatt@demo.de | WERKSTATT |
| gutachter@demo.de | GUTACHTER |
| kunde@demo.de | UNFALLOPFER |

---

## 8. EXTERNE ABHÄNGIGKEITEN

| Paket | Version | Zweck |
|-------|---------|-------|
| streamlit | ≥1.28.0 | Web-UI |
| sqlalchemy | ≥2.0.0 | ORM |
| psycopg2-binary | - | PostgreSQL |
| bcrypt | - | Passwort-Hashing |
| pyotp | - | TOTP 2FA |
| twilio | ≥8.0.0 | SMS 2FA |
| openai | ≥1.0.0 | GPT-4 API |
| anthropic | ≥0.18.0 | Claude API |
| chromadb | ≥0.4.0 | Vector-DB |
| langchain | ≥0.1.0 | LLM-Framework |
| tiktoken | - | Token-Zählung |
| pdfplumber | ≥0.10.0 | PDF-Text |
| PyMuPDF | ≥1.23.0 | PDF-Lesezeichen |
| PyPDF2 | - | PDF-Verarbeitung |
| pytesseract | ≥0.3.10 | OCR |
| Pillow | ≥10.0.0 | Bildverarbeitung |
| reportlab | - | PDF-Generierung |
| pandas | ≥2.0.0 | Datenanalyse |
| plotly | - | Visualisierung |
| geopy | ≥2.4.0 | Geocoding |
| qrcode | ≥7.4.0 | QR-Codes |
| pydantic | ≥2.0.0 | Settings/Validation |
| supabase | ≥2.0.0 | Cloud Storage |
| extract-msg | ≥0.48.0 | .msg E-Mail |
| jinja2 | ≥3.1.0 | Templates |

---

## 9. API-ENDPUNKTE (für React-Frontend)

### Empfohlene REST-API Struktur:

```
POST   /api/auth/login
POST   /api/auth/logout
POST   /api/auth/2fa/verify
POST   /api/auth/register

GET    /api/projekte                    # Projektliste (rollenbasiert)
POST   /api/projekte                    # Neues Projekt
GET    /api/projekte/{id}               # Projekt-Details
PUT    /api/projekte/{id}               # Projekt aktualisieren
DELETE /api/projekte/{id}               # Projekt löschen

GET    /api/projekte/{id}/dokumente     # Dokumente zum Projekt
POST   /api/projekte/{id}/dokumente     # Upload
GET    /api/dokumente/{id}              # Dokument-Details
GET    /api/dokumente/{id}/download     # Download
PUT    /api/dokumente/{id}/freigabe     # Freigabe erteilen
DELETE /api/dokumente/{id}              # Soft-Delete

GET    /api/projekte/{id}/kosten        # Kostenpositionen
POST   /api/projekte/{id}/kosten        # Neue Position
PUT    /api/kosten/{id}                 # Position bearbeiten
PUT    /api/kosten/{id}/freigabe        # Versicherung: Freigabe

GET    /api/projekte/{id}/korrespondenz
POST   /api/projekte/{id}/korrespondenz
PUT    /api/korrespondenz/{id}
POST   /api/korrespondenz/{id}/versenden

GET    /api/projekte/{id}/meilensteine
PUT    /api/meilensteine/{id}

GET    /api/projekte/{id}/wiedervorlagen
POST   /api/projekte/{id}/wiedervorlagen
PUT    /api/wiedervorlagen/{id}

GET    /api/projekte/{id}/nachrichten
POST   /api/projekte/{id}/nachrichten
PUT    /api/nachrichten/{id}/gelesen

GET    /api/projekte/{id}/emails
POST   /api/projekte/{id}/emails/import
POST   /api/emails/senden

POST   /api/ki/chat                     # Dokumenten-Chat
POST   /api/ki/schreiben-generieren     # Brief-Generierung
POST   /api/ki/analyse                  # Dokument-Analyse

POST   /api/import/ramicro              # RA-Micro Import
POST   /api/import/akte                 # Standard-Import

GET    /api/rechner/nutzungsausfall
GET    /api/rechner/minderwert
GET    /api/rechner/gebuehren

POST   /api/signatur/anfordern
POST   /api/signatur/unterschreiben

GET    /api/admin/audit-log
GET    /api/admin/statistik
POST   /api/admin/backup
GET    /api/admin/users
```

---

## 10. DESIGN-SYSTEM

### Farbpalette
| Name | Hex | Verwendung |
|------|-----|-----------|
| primary | #2563eb | Hauptfarbe (Blau) |
| success | #28a745 | Erfolg (Grün) |
| warning | #fd7e14 | Warnung (Orange) |
| danger | #dc3545 | Fehler (Rot) |
| info | #0dcaf0 | Info (Cyan) |
| secondary | #64748b | Sekundär (Grau) |

### Ampel-System
| Status | Farbe | Bedeutung |
|--------|-------|-----------|
| ROT | #dc3545 | Offen/Probleme |
| ORANGE | #fd7e14 | In Bearbeitung |
| GRÜN | #28a745 | Erledigt/Freigegeben |

### Komponenten
- **Metric Cards** - Übersichtskarten mit Gradient-Hintergrund
- **Badge** - Status-Badges (success/warning/danger/info/secondary)
- **Timeline** - Horizontale Meilenstein-Anzeige mit Ampel-Punkten
- **Ampel-Punkt** - Kreis-Indikator (Rot/Orange/Grün)
- **Kosten-Übersicht** - Tabelle mit Ampel und Durchstreich bei Kürzung
- **Projekt-Header** - Projektnummer, Fahrzeug, Unfalldaten, Status
- **Fortschritts-Anzeige** - Progressbar mit Prozent
- **Bestätigungs-Dialog** - Ja/Nein Modal

---

*Erstellt am: 23.02.2026*
*Repository: Sven-BrydeMeier/Schadenmanager*
*Branch: claude/fix-streamlit-import-error-MiiSY*
