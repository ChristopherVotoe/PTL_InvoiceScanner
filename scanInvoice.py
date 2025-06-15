import os
import shutil
import pytesseract
from pdf2image import convert_from_path
import re

invoices = {}
output_base = 'separated_invoices'
last_used_invoice_number = None



# Replace with your actual file
pdf_path = "C:\\Users\\lemeo\\Downloads\\test.pdf"

# Convert PDF to list of images (one per page)
pages = convert_from_path(pdf_path)

for i, page_image in enumerate(pages):
    text = pytesseract.image_to_string(page_image)
    print(f"--- Page {i + 1} ---\n{text}\n")

    # Regex: match something like BNA-234 or LAX-921826-2D or 987321
    match = re.search(r"HAWB:([A-Z]+-\d+-[A-Z]+)P..:", text)

    if match:
        invoice_num = match.group(1)
        last_invoice_num = invoice_num
        print(f"✅ Invoice found on page {i + 1}: {invoice_num}")
    elif last_invoice_num:
        invoice_num = last_invoice_num
        print(f"➕ Using last known invoice number for page {i + 1}: {invoice_num}")
    else:
        print(f"⚠️  Invoice number not found on page {i + 1}, and no previous invoice to use.")
        continue  # Skip this page

        # ✅ THIS LINE WAS MISSING
    invoices.setdefault(invoice_num, []).append((i, page_image))

for invoice_num, pages in invoices.items():
    folder_path = os.path.join(output_base, invoice_num)
    os.makedirs(folder_path, exist_ok=True)

    for i, image in pages:
        image_path = os.path.join(folder_path, f"page_{i+1}.png")
        image.save(image_path)

print("\n📦 Grouped Invoice Pages:")
for invoice_num, pages in invoices.items():
    page_numbers = [i + 1 for i, _ in pages]  # Convert to 1-based page numbers
    print(f"📄 Invoice: {invoice_num} — Pages: {page_numbers}")

print("✅ Done separating and saving invoice pages.")