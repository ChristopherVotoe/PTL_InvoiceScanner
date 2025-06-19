import os
import shutil
import pytesseract
from pdf2image import convert_from_path
import re
from PIL import Image

invoices = {}
output_base = 'separated_invoices'
last_used_invoice_number = None


pdf_path = "C:\\Users\\lemeo\\Downloads\\test_handwritten.pdf"

# Convert PDF to list of images (one per page)
pages = convert_from_path(pdf_path)

for i, page_image in enumerate(pages):
    try:
        text = pytesseract.image_to_string(page_image)
        print(f"--- Page {i + 1} ---\n{text}\n")

        # Match invoice pattern
        match = re.search(r"HAWB:([A-Z]+-\d+(?:-[A-Z]+)?)P[a-zA-Z]{2,}:", text)

        if match:
            invoice_num = match.group(1)
            last_used_invoice_number = invoice_num
            print(f"✅ Invoice found on page {i + 1}: {invoice_num}")
        elif last_used_invoice_number:
            invoice_num = last_used_invoice_number
            print(f"Using last known invoice number for page {i + 1}: {invoice_num}")
        else:
            print(f"Invoice number not found on page {i + 1}, and no previous invoice to use.")
            continue

        invoices.setdefault(invoice_num, []).append((i, page_image))
    except Exception as e:
        print(f"Error on page {i + 1}: {e}")

# Save PNGs and then convert to a single PDF per invoice group
for invoice_num, pages in invoices.items():
    folder_path = os.path.join(output_base, invoice_num)
    os.makedirs(folder_path, exist_ok=True)

    image_paths = []

    for i, image in pages:
        image_path = os.path.join(folder_path, f"page_{i+1}.png")
        image.save(image_path)
        image_paths.append(image_path)

    # Convert saved PNGs to PDF
    if image_paths:
        pdf_path = os.path.join(folder_path, f"{invoice_num}.pdf")
        pil_images = [Image.open(p).convert("RGB") for p in image_paths]
        pil_images[0].save(pdf_path, save_all=True, append_images=pil_images[1:])
        print(f"📄 Created PDF for invoice {invoice_num}: {pdf_path}")

# Summary Output
print("\nGrouped Invoice Pages:")
for invoice_num, pages in invoices.items():
    page_numbers = [i + 1 for i, _ in pages]
    print(f"Invoice: {invoice_num} — Pages: {page_numbers}")

print("\n✅ Done separating, saving, and generating PDFs.")
