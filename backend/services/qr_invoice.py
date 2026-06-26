#!/usr/bin/env python3
"""
backend/services/qr_invoice.py — Génération de QR-factures suisses (standard SIX) pour Merito.

Créancier : PEP's Swiss SA. Paiement par virement via QR-IBAN.
Le QR-IBAN (CH26 3080…, ≠ IBAN normal CH95 8080…) impose une QR-référence (QRR),
ce qui permet le RAPPROCHEMENT AUTOMATIQUE des paiements (synergie MATCHO).

Dépendances (à ajouter au requirements lors du branchement) : qrbill, svglib, reportlab.

Usage :
    from services.qr_invoice import generate_qr_invoice
    path = generate_qr_invoice(
        invoice_no="2026-0042",
        invoice_date="25.06.2026", due_date="25.07.2026",
        debtor={"name": "Entreprise Cliente SA", "street": "Rue du Commerce",
                "house_num": "10", "pcode": "1003", "city": "Lausanne", "country": "CH"},
        lines=[("Merito — Pack 50 analyses de CV anonymisées",
                "Matching prédictif + passeport de confiance", 290.00)],
        vat_rate=0.0,                       # 0 = pas de TVA (non assujetti)
        output_path="/tmp/facture.pdf",
    )
"""
from __future__ import annotations

# ── Constantes créancier (PEP's Swiss SA) ──
QR_IBAN = "CH26 3080 8004 7066 1115 1"   # QR-IBAN — JAMAIS l'IBAN normal CH95 8080…
CREDITOR = {
    "name": "PEP's Swiss SA",
    "street": "Bellevue", "house_num": "7",
    "pcode": "2950", "city": "Courgenay", "country": "CH",
}
CREDITOR_EXTRA = ["contact@peps.swiss", "UID CHE-476.484.632"]


def mod10r(number: str) -> str:
    """Chiffre de contrôle « Modulo 10 récursif » (norme suisse QR-référence / ESR)."""
    table = [0, 9, 4, 6, 8, 2, 7, 1, 3, 5]
    carry = 0
    for d in number:
        carry = table[(carry + int(d)) % 10]
    return str((10 - carry) % 10)


def qr_reference(invoice_no: str) -> str:
    """QR-référence (27 chiffres) dérivée du numéro de facture → unique, rapprochable."""
    digits = "".join(ch for ch in invoice_no if ch.isdigit())[:26].rjust(26, "0")
    return digits + mod10r(digits)


def generate_qr_invoice(invoice_no, invoice_date, due_date, debtor, lines,
                        vat_rate: float = 0.0, output_path: str = "facture.pdf") -> str:
    """Génère une QR-facture A4 conforme SIX. `lines` = [(label, sous_label, montant), …]."""
    from qrbill import QRBill
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas
    from reportlab.lib.colors import HexColor
    from svglib.svglib import svg2rlg
    from reportlab.graphics import renderPDF
    import tempfile, os

    net = round(sum(amount for *_, amount in lines), 2)
    vat = round(net * vat_rate / 100, 2) if vat_rate else 0.0
    total = round(net + vat, 2)
    ref = qr_reference(invoice_no)

    svg_tmp = tempfile.NamedTemporaryFile(suffix=".svg", delete=False).name
    QRBill(
        account=QR_IBAN, creditor=CREDITOR,
        amount=f"{total:.2f}", currency="CHF", reference_number=ref,
        additional_information=f"Facture {invoice_no}",
        debtor=debtor,
    ).as_svg(svg_tmp)

    NAVY = HexColor("#1f3a5f"); GREY = HexColor("#555555"); LIGHT = HexColor("#888888")
    DARK = HexColor("#222222")
    c = canvas.Canvas(output_path, pagesize=A4)
    W, H = A4

    c.setFillColor(NAVY); c.setFont("Helvetica-Bold", 17)
    c.drawString(20*mm, H-25*mm, CREDITOR["name"])
    c.setFillColor(GREY); c.setFont("Helvetica", 9.5)
    head = [f'{CREDITOR["street"]} {CREDITOR["house_num"]}', f'{CREDITOR["pcode"]} {CREDITOR["city"]}'] + CREDITOR_EXTRA
    for i, l in enumerate(head):
        c.drawString(20*mm, H-(31+i*4.5)*mm, l)

    c.setFillColor(NAVY); c.setFont("Helvetica-Bold", 22); c.drawRightString(W-20*mm, H-25*mm, "FACTURE")
    c.setFillColor(GREY); c.setFont("Helvetica", 9.5)
    c.drawRightString(W-20*mm, H-32*mm, f"N° {invoice_no}")
    c.drawRightString(W-20*mm, H-37*mm, f"Date : {invoice_date}")
    c.drawRightString(W-20*mm, H-42*mm, f"Échéance : {due_date}")

    c.setFillColor(LIGHT); c.setFont("Helvetica", 8); c.drawString(120*mm, H-60*mm, "FACTURÉ À")
    c.setFillColor(DARK); c.setFont("Helvetica", 10.5)
    db = [debtor["name"], f'{debtor["street"]} {debtor["house_num"]}', f'{debtor["pcode"]} {debtor["city"]}']
    for i, l in enumerate(db):
        c.drawString(120*mm, H-(66+i*5)*mm, l)

    ty = H-95*mm
    c.setFillColor(NAVY); c.rect(20*mm, ty, W-40*mm, 8*mm, fill=1, stroke=0)
    c.setFillColor(HexColor("#ffffff")); c.setFont("Helvetica-Bold", 9)
    c.drawString(23*mm, ty+2.5*mm, "DÉSIGNATION"); c.drawRightString(W-23*mm, ty+2.5*mm, "MONTANT CHF")
    yrow = ty-7*mm
    for label, sub, amount in lines:
        c.setFillColor(DARK); c.setFont("Helvetica", 10); c.drawString(23*mm, yrow, label)
        c.drawRightString(W-23*mm, yrow, f"{amount:,.2f}")
        if sub:
            c.setFillColor(LIGHT); c.setFont("Helvetica", 8.5); c.drawString(23*mm, yrow-4.5*mm, sub)
        yrow -= 12*mm

    c.setStrokeColor(HexColor("#dddddd")); c.line(120*mm, ty-18*mm, W-20*mm, ty-18*mm)
    c.setFillColor(GREY); c.setFont("Helvetica", 9.5)
    yt = ty-24*mm
    if vat_rate:
        c.drawString(120*mm, yt, "Sous-total HT"); c.drawRightString(W-23*mm, yt, f"{net:,.2f}")
        c.drawString(120*mm, yt-6*mm, f"TVA {vat_rate}%"); c.drawRightString(W-23*mm, yt-6*mm, f"{vat:,.2f}")
        yt -= 14*mm
    c.setFillColor(NAVY); c.setFont("Helvetica-Bold", 11)
    c.drawString(120*mm, yt, "TOTAL CHF"); c.drawRightString(W-23*mm, yt, f"{total:,.2f}")

    c.setFillColor(LIGHT); c.setFont("Helvetica", 8)
    c.drawString(20*mm, ty-52*mm, "Paiement à 30 jours via la QR-facture ci-dessous. Rapprochement automatique grâce à la QR-référence.")

    d = svg2rlg(svg_tmp)
    s = W / d.width; d.width *= s; d.height *= s; d.scale(s, s)
    renderPDF.draw(d, c, 0, 0)
    c.showPage(); c.save()
    os.unlink(svg_tmp)
    return output_path


if __name__ == "__main__":
    out = generate_qr_invoice(
        invoice_no="2026-0042", invoice_date="25.06.2026", due_date="25.07.2026",
        debtor={"name": "Entreprise Cliente SA", "street": "Rue du Commerce",
                "house_num": "10", "pcode": "1003", "city": "Lausanne", "country": "CH"},
        lines=[("Merito — Pack 50 analyses de CV anonymisées",
                "Matching prédictif + passeport de confiance · facturation par QR-facture", 290.00)],
        vat_rate=0.0,
        output_path="/home/claude/qr-facture-merito.pdf",
    )
    print("Facture générée :", out)
