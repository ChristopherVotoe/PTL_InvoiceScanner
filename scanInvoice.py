# scanInvoice.py
from PySide6.QtCore import QObject, Signal
import pytesseract
import re
from pathlib import Path
from pdf2image import convert_from_path
from PIL import Image


class InvoiceScanner(QObject):
    finished = Signal()
    progress = Signal(int)

    def __init__(self, pdf_path):
        super().__init__()
        self.pdf_path = pdf_path

    def run(self):
        try:
            output_base = Path.home() / "Downloads" / "separated_invoices"
            output_base.mkdir(parents=True, exist_ok=True)

            invoices = {}
            last_used_invoice_number = None

            pages = convert_from_path(self.pdf_path)
            total_pages = len(pages)

            for i, page_image in enumerate(pages):
                try:
                    text = pytesseract.image_to_string(page_image)
                    print(f"--- Page {i + 1} ---\n{text}\n")

                    # Extract invoice number from OCR text
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

                # Emit progress percentage
                percent_complete = int(((i + 1) / total_pages) * 100)
                self.progress.emit(percent_complete)

            # Save grouped pages
            for invoice_num, pages in invoices.items():
                safe_invoice = re.sub(r'[\\/*?:"<>|]', "_", invoice_num)  # sanitize folder name
                folder_path = output_base / safe_invoice
                folder_path.mkdir(parents=True, exist_ok=True)

                image_paths = []

                for i, image in pages:
                    image_path = folder_path / f"page_{i+1}.png"
                    image.save(image_path)
                    image_paths.append(image_path)

                if image_paths:
                    pdf_output_path = folder_path / f"{safe_invoice}.pdf"
                    pil_images = [Image.open(p).convert("RGB") for p in image_paths]
                    pil_images[0].save(pdf_output_path, save_all=True, append_images=pil_images[1:])
                    print(f"📄 Created PDF for invoice {invoice_num}: {pdf_output_path}")

            print("\n✅ Done separating, saving, and generating PDFs.")
        except Exception as e:
            print(f"Error during scanning: {e}")
        finally:
            self.finished.emit()
