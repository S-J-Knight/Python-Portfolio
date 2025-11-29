"""
WTN PDF Generation
Uses ReportLab to generate professional Waste Transfer Notice PDFs
Styled to match official WTN format with Knightcycle branding
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from django.conf import settings
import os
from datetime import datetime
import base64
import io
from PIL import Image


def generate_wtn_pdf(parcel):
    """
    Generate a PDF WTN for an IncomingParcel
    Creates business-specific folders and uses WTN reference for filename
    Returns the file path relative to MEDIA_ROOT
    """
    from store.models import Customer
    
    # Get customer to create business-specific folder
    customer = None
    business_folder = 'general'
    if parcel.user:
        try:
            customer = Customer.objects.get(user=parcel.user)
            # Use sanitized business name for folder
            import re
            business_name = re.sub(r'[^a-zA-Z0-9_-]', '_', customer.name)[:50]
            business_folder = f"{customer.user.id}_{business_name}"
        except Customer.DoesNotExist:
            business_folder = f"user_{parcel.user.id}"
    
    # Create business-specific directory
    wtn_dir = os.path.join(settings.MEDIA_ROOT, 'wtn_pdfs', business_folder)
    os.makedirs(wtn_dir, exist_ok=True)
    
    # Generate filename using WTN reference to prevent overwriting
    reference = parcel.wtn_reference if parcel.wtn_reference else f'WTN-{parcel.id:06d}'
    filename = f"{reference}.pdf"
    filepath = os.path.join(wtn_dir, filename)
    
    # Create PDF
    c = canvas.Canvas(filepath, pagesize=A4)
    width, height = A4
    
    # Header with Knightcycle branding
    c.setFillColor(colors.HexColor('#10b981'))  # Green theme
    c.rect(0, height - 80, width, 80, fill=True, stroke=False)
    
    # Add logo on top right of green header
    try:
        logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'logo_v2.png')
        if not os.path.exists(logo_path):
            # Try STATIC_ROOT if BASE_DIR/static doesn't work
            logo_path = os.path.join(settings.STATIC_ROOT, 'images', 'logo_v2.png') if settings.STATIC_ROOT else None
        
        if logo_path and os.path.exists(logo_path):
            logo_reader = ImageReader(logo_path)
            # Position logo on top right (adjust size and position as needed)
            c.drawImage(logo_reader, width - 130, height - 75, width=110, height=65, preserveAspectRatio=True, mask='auto')
        else:
            print(f"Logo not found at: {logo_path}")
    except Exception as e:
        print(f"Could not load logo: {e}")
    
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 24)
    c.drawString(50, height - 40, "WASTE TRANSFER NOTE")
    
    c.setFont("Helvetica", 10)
    c.drawString(50, height - 58, "Duty of care: waste transfer note")
    c.drawString(50, height - 72, "The Waste (England and Wales) Regulations 2011")
    
    # Reset to black for content
    c.setFillColor(colors.black)
    
    # Reference and Date box (top right)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(width - 250, height - 105, f"Reference: {parcel.wtn_reference or f'WTN-{parcel.id:06d}'}")
    c.drawString(width - 250, height - 120, f"Date: {parcel.wtn_signed_date.strftime('%d/%m/%Y') if parcel.wtn_signed_date else datetime.now().strftime('%d/%m/%Y')}")
    
    # Start content
    y = height - 155
    
    c.setFillColor(colors.black)
    
    # Get customer
    customer = None
    if parcel.user:
        try:
            from store.models import Customer
            customer = Customer.objects.get(user=parcel.user)
        except:
            pass
    
    # Section A - Description of waste
    draw_section_header(c, 50, y, width - 100, "Section A - Description of waste")
    y -= 30
    
    # A1 and A3 side by side (left and right columns)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(55, y, "A1  Description of the waste being transferred")
    c.drawString(320, y, "A3  Total estimated waste")
    y -= 15
    
    c.setFont("Helvetica", 9)
    materials = parcel.materials.all()
    if materials:
        material_types = [f"Non-hazardous plastic - {m.plastic_type.name}" for m in materials]
        material_desc = ", ".join(material_types)
        # Word wrap if needed
        if len(material_desc) > 35:
            c.drawString(60, y, material_desc[:35])
            y -= 12
            c.drawString(60, y, material_desc[35:])
            y += 12
        else:
            c.drawString(60, y, material_desc)
    else:
        c.drawString(60, y, "Non-hazardous plastic - 3D Printing Waste")
    
    # Weight on the right
    material_total = sum(m.weight_kg or 0 for m in materials) if materials else 0
    total_weight = material_total if material_total > 0 else (parcel.estimated_weight or 0)
    c.drawString(325, y, f"Total weight: {total_weight}kg")
    y -= 20
    
    c.setFont("Helvetica-Bold", 9)
    c.drawString(55, y, "A2  How is the waste contained?")
    y -= 15
    c.setFont("Helvetica", 9)
    c.drawString(60, y, "Knightcycle 80L recycling collection box sealed with cable ties")
    y -= 35
    
    # Section B - Current holder of the waste (Transferor - Customer)
    draw_section_header(c, 50, y, width - 100, "Section B - Current holder of the waste - Transferor")
    y -= 30
    
    # Left column: Business info
    left_col_x = 55
    right_col_x = 320
    start_y = y
    
    c.setFont("Helvetica-Bold", 9)
    c.drawString(left_col_x, y, "B1  Full name and SIC code (if appropriate)")
    y -= 18
    
    c.setFont("Helvetica", 10)
    name_line = customer.name if customer else "Unknown"
    c.drawString(60, y, name_line)
    y -= 15
    
    if customer and customer.sic_code:
        c.setFont("Helvetica", 9)
        c.drawString(60, y, f"SIC Code: {customer.sic_code}")
        y -= 18
    else:
        y -= 5
    
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(colors.HexColor('#666666'))
    c.drawString(60, y, "Company name and address")
    c.setFillColor(colors.black)
    y -= 14
    
    c.setFont("Helvetica", 9)
    if parcel.address:
        c.drawString(60, y, parcel.address)
        y -= 12
    if parcel.city:
        city_line = parcel.city
        if parcel.county:
            city_line += f", {parcel.county}"
        c.drawString(60, y, city_line)
        y -= 12
    if parcel.postcode:
        c.drawString(60, y, f"Postcode: {parcel.postcode}")
        y -= 12
        c.drawString(60, y, f"Country: {parcel.country or 'United Kingdom'}")
    
    # Right column: Signature
    sig_y = start_y
    c.setFont("Helvetica-Bold", 9)
    c.drawString(right_col_x, sig_y, "Transferor's signature and date")
    sig_y -= 15
    c.setFont("Helvetica", 8)
    c.drawString(right_col_x + 5, sig_y, f"Signed: {parcel.wtn_signed_date.strftime('%d %B %Y %H:%M') if parcel.wtn_signed_date else 'N/A'}")
    sig_y -= 14
    
    if parcel.wtn_signature:
        try:
            if parcel.wtn_signature.startswith('data:image'):
                signature_data = parcel.wtn_signature.split(',')[1]
            else:
                signature_data = parcel.wtn_signature
            
            img_data = base64.b64decode(signature_data)
            img_reader = ImageReader(io.BytesIO(img_data))
            c.drawImage(img_reader, right_col_x + 5, sig_y - 45, width=150, height=45, preserveAspectRatio=True, mask='auto')
        except Exception as e:
            c.setFont("Helvetica-Oblique", 8)
            c.drawString(right_col_x + 5, sig_y, "[Signature on file]")
    else:
        c.setFont("Helvetica-Oblique", 8)
        c.drawString(right_col_x + 5, sig_y, "[No signature provided]")
    
    y -= 35
    
    # Section C - Person collecting the waste (Transferee - DPD)
    draw_section_header(c, 50, y, width - 100, "Section C - Person collecting the waste - Transferee")
    y -= 30
    
    # Two columns for DPD info
    c.setFont("Helvetica-Bold", 9)
    c.drawString(left_col_x, y, "C1  Full name and address")
    c.drawString(right_col_x, y, "C2  Carrier registration")
    y -= 18
    
    # Left column
    left_y = y
    c.setFont("Helvetica", 10)
    c.drawString(60, left_y, "DPDGROUP UK LTD")
    left_y -= 15
    
    c.setFont("Helvetica", 9)
    c.drawString(60, left_y, "UNIT 1, ROEBUCK LANE")
    left_y -= 12
    c.drawString(60, left_y, "SMETHWICK, B66 1BY")
    left_y -= 12
    c.drawString(60, left_y, "United Kingdom")
    left_y -= 12
    c.drawString(60, left_y, "Company: 00732993")
    
    # Right column
    right_y = y
    c.setFont("Helvetica", 9)
    c.drawString(right_col_x + 5, right_y, "☑ Carrier, Broker, Dealer - Upper Tier")
    right_y -= 12
    c.drawString(right_col_x + 5, right_y, "Registration: CBDU304362")
    right_y -= 12
    c.drawString(right_col_x + 5, right_y, "Registered: 12/08/2025")
    right_y -= 12
    c.drawString(right_col_x + 5, right_y, "Expires: 05/09/2028")
    
    y = min(left_y, right_y) - 35
    
    # Section D - The receiver of the waste (Knightcycle - Final Destination)
    draw_section_header(c, 50, y, width - 100, "Section D - The receiver of the waste - Final Destination")
    y -= 30
    
    start_y = y
    
    # Left column: Knightcycle info
    c.setFont("Helvetica-Bold", 9)
    c.drawString(left_col_x, y, "D1  Full name and address")
    y -= 18
    
    c.setFont("Helvetica", 10)
    c.drawString(60, y, "Samuel Knight")
    y -= 15
    
    c.setFont("Helvetica", 9)
    c.drawString(60, y, "Knightcycle Ltd")
    y -= 12
    c.drawString(60, y, "3D Printing Waste Recycling")
    y -= 12
    c.drawString(60, y, "United Kingdom")
    y -= 18
    
    c.setFont("Helvetica-Bold", 9)
    c.drawString(left_col_x, y, "D2  Environmental permit")
    y -= 15
    c.setFont("Helvetica", 9)
    c.drawString(60, y, "☑ Registered waste carrier")
    y -= 12
    c.drawString(60, y, "Registration: TEMP123456 (Pending verification)")
    y -= 18
    
    c.setFont("Helvetica-Bold", 9)
    c.drawString(left_col_x, y, "D3  Transfer details")
    y -= 15
    c.setFont("Helvetica", 9)
    transfer_date = parcel.wtn_signed_date.strftime('%d/%m/%Y') if parcel.wtn_signed_date else datetime.now().strftime('%d/%m/%Y')
    c.drawString(60, y, f"Date: {transfer_date}")
    y -= 12
    if parcel.collection_scheduled_date:
        c.drawString(60, y, f"Estimated collection date: {parcel.collection_scheduled_date.strftime('%d/%m/%Y')}")
    
    # Right column: Admin signature
    sig_y = start_y
    if parcel.wtn_admin_approved:
        c.setFont("Helvetica-Bold", 9)
        c.drawString(right_col_x, sig_y, "Receiver's signature and date")
        sig_y -= 15
        c.setFont("Helvetica", 8)
        c.drawString(right_col_x + 5, sig_y, f"Approved: {parcel.wtn_admin_approved_date.strftime('%d %B %Y %H:%M') if parcel.wtn_admin_approved_date else 'N/A'}")
        sig_y -= 14
        
        if parcel.wtn_admin_signature:
            try:
                print(f">>> Admin signature found, length: {len(parcel.wtn_admin_signature)}")
                if parcel.wtn_admin_signature.startswith('data:image'):
                    admin_sig_data = parcel.wtn_admin_signature.split(',')[1]
                else:
                    admin_sig_data = parcel.wtn_admin_signature
                
                admin_img_data = base64.b64decode(admin_sig_data)
                admin_img_reader = ImageReader(io.BytesIO(admin_img_data))
                c.drawImage(admin_img_reader, right_col_x + 5, sig_y - 45, width=150, height=45, preserveAspectRatio=True, mask='auto')
                print(f">>> Admin signature rendered successfully")
                sig_y -= 50
            except Exception as e:
                print(f">>> ERROR rendering admin signature: {e}")
                c.setFont("Helvetica-Oblique", 8)
                c.drawString(right_col_x + 5, sig_y, f"[Error: {str(e)[:30]}]")
                sig_y -= 15
        else:
            print(f">>> No admin signature found for parcel {parcel.id}")
            c.setFont("Helvetica-Oblique", 8)
            c.drawString(right_col_x + 5, sig_y, "[Pending]")
            sig_y -= 15
        
        sig_y -= 10
        c.setFillColor(colors.HexColor('#10b981'))
        c.setFont("Helvetica-Bold", 10)
        c.drawString(right_col_x + 5, sig_y, "✓ APPROVED")
        c.setFillColor(colors.black)
    
    # Footer
    c.setFont("Helvetica", 7)
    c.setFillColor(colors.HexColor('#666666'))
    c.drawString(50, 50, "Keep this page and copy it for future use.")
    c.drawString(50, 40, f"Generated on {datetime.now().strftime('%d %B %Y')}")
    c.drawString(50, 30, "This document serves as legal proof of waste transfer under UK Environmental Legislation.")
    c.drawString(50, 20, "Knightcycle Ltd - Sustainable 3D Printing Waste Solutions")
    
    # Save PDF
    c.save()
    
    # Return relative path for storage in database (use forward slash for cross-platform)
    return f'wtn_pdfs/{business_folder}/{filename}'


def draw_section_header(c, x, y, width, text):
    """Draw a section header box with text"""
    # Safety check for None values
    if x is None or y is None or width is None:
        raise ValueError(f"draw_section_header received None: x={x}, y={y}, width={width}")
    
    c.setFillColor(colors.HexColor('#f3f4f6'))
    c.rect(x, y - 15, width, 20, fill=True, stroke=True)
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(x + 5, y - 10, text)
