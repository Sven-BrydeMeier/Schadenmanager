"""
PDF-Export Service für Reports und Dokumentation
"""
import io
from datetime import datetime
from typing import Optional, List
from decimal import Decimal

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.platypus import PageBreak, HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

from src.models import UnfallProjekt, KostenPosition, Dokument


class PDFExportService:
    """Service für PDF-Export"""

    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        """Erstellt benutzerdefinierte Styles"""
        # Titel-Style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=18,
            spaceAfter=20,
            textColor=colors.HexColor('#1e40af'),
            alignment=TA_CENTER
        ))

        # Untertitel-Style
        self.styles.add(ParagraphStyle(
            name='CustomSubtitle',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceAfter=12,
            textColor=colors.HexColor('#1e40af')
        ))

        # Abschnitt-Style
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading3'],
            fontSize=12,
            spaceAfter=8,
            spaceBefore=15,
            textColor=colors.HexColor('#374151')
        ))

        # Info-Text Style
        self.styles.add(ParagraphStyle(
            name='InfoText',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#6b7280')
        ))

        # Betrag-Style (rechtsbündig)
        self.styles.add(ParagraphStyle(
            name='Amount',
            parent=self.styles['Normal'],
            fontSize=10,
            alignment=TA_RIGHT
        ))

    def _get_header(self, titel: str, aktenzeichen: Optional[str] = None) -> List:
        """Erstellt den Dokumenten-Header"""
        elements = []

        # Titel
        elements.append(Paragraph(f"Schadenmanager", self.styles['CustomTitle']))

        if aktenzeichen:
            elements.append(Paragraph(f"Aktenzeichen: {aktenzeichen}", self.styles['CustomSubtitle']))

        elements.append(Paragraph(titel, self.styles['CustomSubtitle']))

        # Erstellungsdatum
        elements.append(Paragraph(
            f"Erstellt am: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
            self.styles['InfoText']
        ))

        elements.append(Spacer(1, 10))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e5e7eb')))
        elements.append(Spacer(1, 15))

        return elements

    def _get_footer(self, canvas, doc):
        """Erstellt den Footer auf jeder Seite"""
        canvas.saveState()
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.HexColor('#9ca3af'))

        # Seitennummer
        page_num = canvas.getPageNumber()
        text = f"Seite {page_num}"
        canvas.drawRightString(A4[0] - 2*cm, 1.5*cm, text)

        # Footer-Text
        canvas.drawString(2*cm, 1.5*cm, f"Schadenmanager - Generiert am {datetime.now().strftime('%d.%m.%Y')}")

        canvas.restoreState()

    def exportiere_projektbericht(self, projekt: UnfallProjekt) -> bytes:
        """
        Exportiert einen vollständigen Projektbericht als PDF.

        Args:
            projekt: Das zu exportierende Unfallprojekt

        Returns:
            PDF als Bytes
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2.5*cm
        )

        elements = []

        # Header
        elements.extend(self._get_header(
            "Projektbericht",
            projekt.aktenzeichen or projekt.projektnummer
        ))

        # Projektübersicht
        elements.append(Paragraph("Projektübersicht", self.styles['SectionHeader']))

        projekt_daten = [
            ["Projektnummer:", projekt.projektnummer],
            ["Aktenzeichen:", projekt.aktenzeichen or "-"],
            ["Status:", projekt.status_anzeige],
            ["Unfalldatum:", projekt.datum_unfall.strftime('%d.%m.%Y') if projekt.datum_unfall else "-"],
            ["Unfallort:", projekt.ort_unfall or "-"],
            ["Eigene Schuld:", f"{projekt.schuld_eigen_prozent}%"],
        ]

        if projekt.polizei_aktenzeichen:
            projekt_daten.append(["Polizei-Az.:", projekt.polizei_aktenzeichen])

        table = Table(projekt_daten, colWidths=[5*cm, 10*cm])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#374151')),
        ]))
        elements.append(table)

        # Fahrzeugdaten
        if projekt.kfz_eigen:
            elements.append(Paragraph("Eigenes Fahrzeug", self.styles['SectionHeader']))
            kfz_daten = [
                ["Kennzeichen:", projekt.kfz_eigen.kennzeichen],
                ["Fahrzeug:", projekt.kfz_eigen.fahrzeug_bezeichnung],
                ["Halter:", projekt.kfz_eigen.halter_name or "-"],
            ]
            if projekt.kfz_eigen.fin:
                kfz_daten.append(["FIN:", projekt.kfz_eigen.fin])

            table = Table(kfz_daten, colWidths=[5*cm, 10*cm])
            table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            elements.append(table)

        if projekt.kfz_gegner:
            elements.append(Paragraph("Gegnerisches Fahrzeug", self.styles['SectionHeader']))
            kfz_daten = [
                ["Kennzeichen:", projekt.kfz_gegner.kennzeichen],
                ["Versicherung:", projekt.kfz_gegner.versicherung_name or "-"],
            ]
            table = Table(kfz_daten, colWidths=[5*cm, 10*cm])
            table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            elements.append(table)

        # Beschreibung
        if projekt.beschreibung_unfall:
            elements.append(Paragraph("Unfallbeschreibung", self.styles['SectionHeader']))
            elements.append(Paragraph(projekt.beschreibung_unfall, self.styles['Normal']))

        # Kostenpositionen
        if projekt.kostenpositionen:
            elements.append(PageBreak())
            elements.extend(self._render_kostenuebersicht(projekt))

        # Dokumente
        if projekt.dokumente:
            elements.append(Paragraph("Dokumentenübersicht", self.styles['SectionHeader']))
            elements.append(self._render_dokumentenliste(projekt.dokumente))

        doc.build(elements, onFirstPage=self._get_footer, onLaterPages=self._get_footer)

        buffer.seek(0)
        return buffer.getvalue()

    def exportiere_kostenuebersicht(self, projekt: UnfallProjekt) -> bytes:
        """
        Exportiert eine Kostenübersicht als PDF.

        Args:
            projekt: Das Unfallprojekt

        Returns:
            PDF als Bytes
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2.5*cm
        )

        elements = []
        elements.extend(self._get_header(
            "Kostenübersicht",
            projekt.aktenzeichen or projekt.projektnummer
        ))
        elements.extend(self._render_kostenuebersicht(projekt))

        doc.build(elements, onFirstPage=self._get_footer, onLaterPages=self._get_footer)

        buffer.seek(0)
        return buffer.getvalue()

    def _render_kostenuebersicht(self, projekt: UnfallProjekt) -> List:
        """Rendert die Kostenübersicht als PDF-Elemente"""
        elements = []

        elements.append(Paragraph("Schadenspositionen", self.styles['SectionHeader']))

        if not projekt.kostenpositionen:
            elements.append(Paragraph("Keine Kostenpositionen erfasst.", self.styles['InfoText']))
            return elements

        # Tabellenkopf
        data = [["Position", "Kategorie", "Gefordert", "Erstattet", "Differenz"]]

        # Summen
        summe_gefordert = Decimal("0")
        summe_erstattet = Decimal("0")

        for kp in sorted(projekt.kostenpositionen, key=lambda x: x.kategorie.value if x.kategorie else ""):
            gefordert = kp.betrag_gefordert or Decimal("0")
            erstattet = kp.betrag_erstattet or Decimal("0")
            differenz = gefordert - erstattet

            summe_gefordert += gefordert
            summe_erstattet += erstattet

            data.append([
                kp.bezeichnung or "-",
                kp.kategorie_anzeige if hasattr(kp, 'kategorie_anzeige') else str(kp.kategorie.value if kp.kategorie else "-"),
                f"{float(gefordert):,.2f} €",
                f"{float(erstattet):,.2f} €",
                f"{float(differenz):,.2f} €"
            ])

        # Summenzeile
        data.append([
            "GESAMT",
            "",
            f"{float(summe_gefordert):,.2f} €",
            f"{float(summe_erstattet):,.2f} €",
            f"{float(summe_gefordert - summe_erstattet):,.2f} €"
        ])

        table = Table(data, colWidths=[5*cm, 3*cm, 3*cm, 3*cm, 3*cm])
        table.setStyle(TableStyle([
            # Header
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e40af')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),

            # Body
            ('FONTSIZE', (0, 1), (-1, -2), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),

            # Summenzeile
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f3f4f6')),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),

            # Rahmen
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d1d5db')),

            # Abwechselnde Zeilenfarben
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#f9fafb')]),
        ]))

        elements.append(table)
        elements.append(Spacer(1, 20))

        # Zusammenfassung
        quote = (float(summe_erstattet) / float(summe_gefordert) * 100) if summe_gefordert > 0 else 0
        elements.append(Paragraph(
            f"<b>Erstattungsquote:</b> {quote:.1f}%",
            self.styles['Normal']
        ))

        return elements

    def _render_dokumentenliste(self, dokumente: List[Dokument]) -> Table:
        """Rendert die Dokumentenliste als Tabelle"""
        data = [["Typ", "Dateiname", "Datum", "Status"]]

        for dok in sorted(dokumente, key=lambda x: x.erstellt_am or datetime.min, reverse=True):
            status = "Freigegeben" if dok.freigabe_erteilt else "Ausstehend"
            if dok.freigabe_abgelehnt:
                status = "Abgelehnt"

            data.append([
                dok.dokument_typ_anzeige,
                dok.original_dateiname[:30] + "..." if len(dok.original_dateiname or "") > 30 else (dok.original_dateiname or "-"),
                dok.erstellt_am.strftime('%d.%m.%Y') if dok.erstellt_am else "-",
                status
            ])

        table = Table(data, colWidths=[4*cm, 6*cm, 3*cm, 3*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#374151')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d1d5db')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')]),
        ]))

        return table

    def exportiere_schadensaufstellung(
        self,
        projekt: UnfallProjekt,
        nutzungsausfall: Optional[dict] = None,
        minderwert: Optional[dict] = None
    ) -> bytes:
        """
        Exportiert eine detaillierte Schadensaufstellung für den Anwalt.

        Args:
            projekt: Das Unfallprojekt
            nutzungsausfall: Berechnete Nutzungsausfallentschädigung
            minderwert: Berechneter merkantiler Minderwert

        Returns:
            PDF als Bytes
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2.5*cm
        )

        elements = []
        elements.extend(self._get_header(
            "Schadensaufstellung",
            projekt.aktenzeichen or projekt.projektnummer
        ))

        # Anspruchsgrundlage
        elements.append(Paragraph("Anspruchsgrundlage", self.styles['SectionHeader']))
        elements.append(Paragraph(
            f"Schadensersatzanspruch gemäß §§ 7, 17 StVG, §§ 823, 249 ff. BGB",
            self.styles['Normal']
        ))
        elements.append(Paragraph(
            f"Unfalldatum: {projekt.datum_unfall.strftime('%d.%m.%Y') if projekt.datum_unfall else '-'}",
            self.styles['Normal']
        ))
        elements.append(Paragraph(
            f"Unfallort: {projekt.ort_unfall or '-'}",
            self.styles['Normal']
        ))
        elements.append(Paragraph(
            f"Haftungsquote Gegner: {100 - projekt.schuld_eigen_prozent}%",
            self.styles['Normal']
        ))

        elements.append(Spacer(1, 15))

        # Kostenpositionen
        elements.extend(self._render_kostenuebersicht(projekt))

        # Nutzungsausfall
        if nutzungsausfall:
            elements.append(Paragraph("Nutzungsausfallentschädigung", self.styles['SectionHeader']))
            na_data = [
                ["Fahrzeuggruppe:", nutzungsausfall.get('hinweis', '-')],
                ["Tagessatz:", f"{float(nutzungsausfall.get('tagessatz', 0)):,.2f} €"],
                ["Ausfalltage:", str(nutzungsausfall.get('ausfall_tage', 0))],
                ["Gesamt:", f"{float(nutzungsausfall.get('gesamt_betrag', 0)):,.2f} €"],
            ]
            table = Table(na_data, colWidths=[5*cm, 10*cm])
            table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            elements.append(table)

        # Merkantiler Minderwert
        if minderwert:
            elements.append(Paragraph("Merkantiler Minderwert", self.styles['SectionHeader']))
            mw_empfehlung = minderwert.get('empfehlung', Decimal("0"))
            elements.append(Paragraph(
                f"<b>Empfohlener Minderwert: {float(mw_empfehlung):,.2f} €</b>",
                self.styles['Normal']
            ))
            elements.append(Spacer(1, 10))

            # Methoden-Vergleich
            methoden_data = [["Methode", "Berechneter Wert"]]
            for methode in ['ruhkopf_sahm', 'halbgewachs', 'dvgt']:
                if methode in minderwert:
                    wert = minderwert[methode].get('minderwert', Decimal("0"))
                    name = minderwert[methode].get('methode', methode)
                    methoden_data.append([name, f"{float(wert):,.2f} €"])

            table = Table(methoden_data, colWidths=[8*cm, 5*cm])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#374151')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d1d5db')),
            ]))
            elements.append(table)

        doc.build(elements, onFirstPage=self._get_footer, onLaterPages=self._get_footer)

        buffer.seek(0)
        return buffer.getvalue()


def get_pdf_service() -> PDFExportService:
    """Factory-Funktion für den PDF-Service"""
    return PDFExportService()
