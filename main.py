import os
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal, QObject, QSize
from PySide6.QtGui import QPixmap, QIcon
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QFileDialog, QProgressBar,
    QListWidget, QListWidgetItem, QMessageBox, QStackedWidget,
    QSplitter, QScrollArea, QCheckBox, QButtonGroup
)

from pdf2image import convert_from_path
from PIL.ImageQt import ImageQt
from pypdf import PdfReader, PdfWriter


OUTPUT_BASE = Path.home() / "Downloads" / "PrimeTimeLogistics_Invoices"


# ---------------------------
#render PDF to thumbnails (so UI doesn’t freeze)
# ---------------------------
class RenderWorker(QObject):
    finished = Signal(list)          # list of QPixmap thumbnails
    progress = Signal(int)
    error = Signal(str)

    def __init__(self, pdf_path: str, dpi: int = 90):
        super().__init__()
        self.pdf_path = pdf_path
        self.dpi = dpi

    def run(self):
        try:
            pages = convert_from_path(self.pdf_path, dpi=self.dpi)
            total = len(pages)
            thumbs = []

            for i, pil_img in enumerate(pages):
                qimg = ImageQt(pil_img.convert("RGB"))
                pix = QPixmap.fromImage(qimg)

                pix = pix.scaled(180, 240, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                thumbs.append(pix)

                pct = int(((i + 1) / total) * 100)
                self.progress.emit(pct)

            self.finished.emit(thumbs)

        except Exception as e:
            self.error.emit(str(e))


# ---------------------------
# Main Window
# ---------------------------
class InvoiceSorter(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Invoice Page Sorter (Manual Airway Grouping)")
        self.resize(1300, 780)

        self.pdf_path: str | None = None
        self.reader: PdfReader | None = None
        self.thumbnails: list[QPixmap] = []

        # Track how many times each page has been used (0-based index -> count)
        self.page_use_counts: dict[int, int] = {}


        self.preview_zoom = 1.0
        self.preview_cache: dict[tuple[int, int], QPixmap] = {}  # (page_index, dpi) -> QPixmap
        self.preview_dpi = 240


        self.selected_year = "2026"

        # stacked screens
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.screen_upload = self._build_upload_screen()
        self.screen_select = self._build_select_screen()

        self.stack.addWidget(self.screen_upload)
        self.stack.addWidget(self.screen_select)
        self.stack.setCurrentWidget(self.screen_upload)

        # thread stuff
        self.thread: QThread | None = None
        self.worker: RenderWorker | None = None

    # ---------------------------
    # Screen 1: Upload
    # ---------------------------
    def _build_upload_screen(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setAlignment(Qt.AlignTop)

        title = QLabel("1) Upload your scanned PDF")
        title.setStyleSheet("font-size: 22px; font-weight: 700;")
        layout.addWidget(title)

        row = QHBoxLayout()
        layout.addLayout(row)

        self.input_path = QLineEdit()
        self.input_path.setPlaceholderText("Choose a scanned PDF...")
        row.addWidget(self.input_path)

        btn_browse = QPushButton("Browse")
        btn_browse.clicked.connect(self.browse_pdf)
        row.addWidget(btn_browse)

        btn_load = QPushButton("Load Files")
        btn_load.clicked.connect(self.load_pdf)
        row.addWidget(btn_load)

        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        self.status = QLabel("")
        layout.addWidget(self.status)

        # hint = QLabel(
        #     "Tip: Thumbnails are low-res for speed.\n"
        #     "Click a page to preview it at high resolution, then check pages and Save.\n"
        #     "Pages can be reused; the app tracks how many times each page was used."
        # )
        # hint.setStyleSheet("opacity: 0.8;")
        # layout.addWidget(hint)

        return w

    def browse_pdf(self):
        file, _ = QFileDialog.getOpenFileName(self, "Select PDF", "", "PDF Files (*.pdf)")
        if file:
            self.input_path.setText(file)

    def load_pdf(self):
        path = self.input_path.text().strip()
        if not path or not os.path.isfile(path) or not path.lower().endswith(".pdf"):
            QMessageBox.warning(self, "Invalid file", "Please choose a valid PDF file.")
            return

        self.pdf_path = path
        self.status.setText("Rendering Files...")
        self.progress.setVisible(True)
        self.progress.setValue(0)

        try:
            self.reader = PdfReader(self.pdf_path)
        except Exception as e:
            QMessageBox.critical(self, "PDF Read Error", str(e))
            self.progress.setVisible(False)
            return

        # reset caches + usage counts
        self.preview_cache.clear()
        self.preview_zoom = 1.0
        self.page_use_counts = {}

        # Start worker thread
        self.thread = QThread()
        self.worker = RenderWorker(self.pdf_path, dpi=90)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.progress.setValue)
        self.worker.error.connect(self._render_error)
        self.worker.finished.connect(self._render_done)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        self.thread.start()

    def _render_error(self, msg: str):
        self.progress.setVisible(False)
        QMessageBox.critical(self, "Render Error", msg)

    def _render_done(self, thumbs: list):
        self.thumbnails = thumbs

        self.progress.setVisible(False)
        self.status.setText(f"Loaded {len(self.thumbnails)} pages.")
        self._populate_page_list()

        if self.page_list.count() > 0:
            self.page_list.setCurrentRow(0)

        self.stack.setCurrentWidget(self.screen_select)

    # ---------------------------
    # Screen 2: Select pages + save + preview
    # ---------------------------
    def _build_select_screen(self) -> QWidget:
        w = QWidget()
        outer = QVBoxLayout(w)

        header = QLabel("2) Type an Airway #, check pages, choose Year + Client, then Save")
        header.setStyleSheet("font-size: 20px; font-weight: 700;")
        outer.addWidget(header)

        # Row: Airway + actions
        top_row = QHBoxLayout()
        outer.addLayout(top_row)

        top_row.addWidget(QLabel("Airway #:"))
        self.airway_input = QLineEdit()
        self.airway_input.setPlaceholderText('Example: LAX-904991')
        top_row.addWidget(self.airway_input)

        # btn_select_all = QPushButton("Select All")
        # btn_select_all.clicked.connect(self.select_all_visible)
        # top_row.addWidget(btn_select_all)

        btn_clear = QPushButton("Clear Selection")
        btn_clear.clicked.connect(self.clear_selection)
        top_row.addWidget(btn_clear)

        btn_save = QPushButton("Save Selected Pages")
        btn_save.clicked.connect(self.save_selected_pages)
        top_row.addWidget(btn_save)

        btn_back = QPushButton("Back to Upload")
        btn_back.clicked.connect(lambda: self.stack.setCurrentWidget(self.screen_upload))
        top_row.addWidget(btn_back)

        # Row: Year buttons
        year_row = QHBoxLayout()
        outer.addLayout(year_row)

        year_row.addWidget(QLabel("Year:"))
        self.btn_2026 = QPushButton("2026")
        self.btn_2027 = QPushButton("2027")
        self.btn_2028 = QPushButton("2028")

        self.btn_2026.clicked.connect(lambda: self.set_year("2026"))
        self.btn_2027.clicked.connect(lambda: self.set_year("2027"))
        self.btn_2028.clicked.connect(lambda: self.set_year("2028"))

        year_row.addWidget(self.btn_2026)
        year_row.addWidget(self.btn_2027)
        year_row.addWidget(self.btn_2028)
        year_row.addStretch(1)

        self.year_label = QLabel("Selected: 2026")
        year_row.addWidget(self.year_label)

        # Row: Client checkboxes (exclusive)
        client_row = QHBoxLayout()
        outer.addLayout(client_row)

        client_row.addWidget(QLabel("Client:"))

        self.client_group = QButtonGroup(self)
        self.client_group.setExclusive(True)

        self.client_checks: dict[str, QCheckBox] = {}
        for name in ["ALG", "DSV", "ICAT", "ROCKIT CARGO", "RXO","Other"]:
            cb = QCheckBox(name)
            self.client_group.addButton(cb)
            self.client_checks[name] = cb
            client_row.addWidget(cb)

        # --- "Other" text input
        self.other_input = QLineEdit()
        self.other_input.setPlaceholderText("Other client name...")
        self.other_input.setEnabled(False)
        self.other_input.setFixedWidth(220)  # optional
        client_row.addWidget(self.other_input)

        # When client selection changes, toggle the textbox
        self.client_group.buttonToggled.connect(self.on_client_toggled)

        self.client_checks["ALG"].setChecked(True)
        client_row.addStretch(1)

        # Split: left thumbnails, right preview
        split = QSplitter(Qt.Horizontal)
        outer.addWidget(split, 1)

        # LEFT: page thumbs
        self.page_list = QListWidget()
        self.page_list.setViewMode(QListWidget.IconMode)
        self.page_list.setIconSize(QSize(180, 240))
        self.page_list.setResizeMode(QListWidget.Adjust)
        self.page_list.setMovement(QListWidget.Static)
        self.page_list.setSelectionMode(QListWidget.SingleSelection)
        split.addWidget(self.page_list)

        # RIGHT: preview pane
        right = QWidget()
        right_layout = QVBoxLayout(right)

        preview_controls = QHBoxLayout()
        self.btn_select_all = QPushButton("Select All")
        self.btn_prev = QPushButton("Prev")
        self.btn_next = QPushButton("Next")
        self.btn_zoom_out = QPushButton("Zoom -")
        self.btn_zoom_in = QPushButton("Zoom +")
        preview_controls.addWidget(self.btn_select_all)
        preview_controls.addWidget(self.btn_prev)
        preview_controls.addWidget(self.btn_next)
        preview_controls.addSpacing(12)
        preview_controls.addWidget(self.btn_zoom_out)
        preview_controls.addWidget(self.btn_zoom_in)
        preview_controls.addStretch(1)
        right_layout.addLayout(preview_controls)

        self.preview_scroll = QScrollArea()
        self.preview_scroll.setWidgetResizable(True)

        self.preview_label = QLabel("Click a page to preview")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_scroll.setWidget(self.preview_label)

        right_layout.addWidget(self.preview_scroll, 1)
        split.addWidget(right)

        split.setSizes([380, 820])

        # bottom status
        self.bottom_status = QLabel("")
        outer.addWidget(self.bottom_status)

        # connections
        self.page_list.currentItemChanged.connect(self.on_page_selected)
        self.btn_zoom_in.clicked.connect(lambda: self.change_zoom(1.25))
        self.btn_zoom_out.clicked.connect(lambda: self.change_zoom(0.8))
        self.btn_next.clicked.connect(self.next_page)
        self.btn_prev.clicked.connect(self.prev_page)
        self.btn_select_all.clicked.connect(self.select_all_visible)

        # apply default year highlight
        self._update_year_buttons()

        return w

    def on_client_toggled(self, button, checked: bool):
        if not checked:
            return
        is_other = (button.text() == "Other")
        self.other_input.setEnabled(is_other)
        if is_other:
            self.other_input.setFocus()
            self.other_input.selectAll()


    def set_year(self, year: str):
        self.selected_year = year
        self.year_label.setText(f"Selected: {year}")
        self._update_year_buttons()

    def _update_year_buttons(self):
        # simple visual cue using enabled/disabled (no stylesheet required)
        self.btn_2026.setEnabled(self.selected_year != "2026")
        self.btn_2027.setEnabled(self.selected_year != "2027")
        self.btn_2028.setEnabled(self.selected_year != "2028")

    def _populate_page_list(self):
        self.page_list.clear()

        for i, pix in enumerate(self.thumbnails):
            use_count = self.page_use_counts.get(i, 0)
            label = f"Page {i + 1}  (used: {use_count})"

            item = QListWidgetItem(label)
            item.setIcon(QIcon(pix))
            item.setFlags(item.flags() | Qt.ItemIsSelectable | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            item.setCheckState(Qt.Unchecked)
            item.setData(Qt.UserRole, i)
            self.page_list.addItem(item)

        self._update_bottom_status()

    def _update_bottom_status(self):
        total = len(self.thumbnails)
        total_used = sum(self.page_use_counts.values())
        self.bottom_status.setText(f"Total pages: {total} | Total page-uses recorded: {total_used}")

    def on_page_selected(self, current, previous):
        if not current:
            return
        page_index = int(current.data(Qt.UserRole))
        self.show_preview(page_index)

    def show_preview(self, page_index: int, force: bool = False):
        if not self.pdf_path:
            return

        try:
            cache_key = (page_index, self.preview_dpi)

            if force or cache_key not in self.preview_cache:
                images = convert_from_path(
                    self.pdf_path,
                    dpi=self.preview_dpi,
                    first_page=page_index + 1,
                    last_page=page_index + 1
                )
                pil_img = images[0].convert("RGB")
                qimg = ImageQt(pil_img)
                pix = QPixmap.fromImage(qimg)
                self.preview_cache[cache_key] = pix

            base_pix = self.preview_cache[cache_key]

            target_w = int(base_pix.width() * self.preview_zoom)
            target_h = int(base_pix.height() * self.preview_zoom)
            scaled = base_pix.scaled(target_w, target_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)

            self.preview_label.setPixmap(scaled)
            self.preview_label.setAlignment(Qt.AlignCenter)

        except Exception as e:
            QMessageBox.critical(self, "Preview Error", str(e))

    def change_zoom(self, factor: float):
        self.preview_zoom *= factor
        self.preview_zoom = max(0.5, min(self.preview_zoom, 3.0))
        item = self.page_list.currentItem()
        if item:
            self.show_preview(int(item.data(Qt.UserRole)), force=False)

    def next_page(self):
        row = self.page_list.currentRow()
        if row < self.page_list.count() - 1:
            self.page_list.setCurrentRow(row + 1)

    def prev_page(self):
        row = self.page_list.currentRow()
        if row > 0:
            self.page_list.setCurrentRow(row - 1)

    def select_all_visible(self):
        for idx in range(self.page_list.count()):
            self.page_list.item(idx).setCheckState(Qt.Checked)

    def clear_selection(self):
        for idx in range(self.page_list.count()):
            self.page_list.item(idx).setCheckState(Qt.Unchecked)

    def _get_checked_page_indices(self) -> list[int]:
        checked = []
        for idx in range(self.page_list.count()):
            item = self.page_list.item(idx)
            if item.checkState() == Qt.Checked:
                checked.append(int(item.data(Qt.UserRole)))
        return sorted(checked)

    def _sanitize_folder_name(self, name: str) -> str:
        name = name.strip()
        if not name:
            return ""

        return "".join(c if (c.isalnum() or c in " -_().") else "_" for c in name).strip()

    def _get_selected_client_folder(self) -> str:
        for name, cb in self.client_checks.items():
            if cb.isChecked():
                if name == "Other":
                    custom = self._sanitize_folder_name(self.other_input.text())
                    return custom
                return name
        return "ALG"

    def save_selected_pages(self):
        client_folder = self._get_selected_client_folder()
        if not client_folder:
            QMessageBox.warning(self, "Missing client name", "You selected 'Other' — please type a client name.")
            self.other_input.setFocus()
            return

        airway = self.airway_input.text().strip()
        if not airway:
            QMessageBox.warning(self, "Missing airway number", "Please type the airway number.")
            return

        page_indices = self._get_checked_page_indices()
        if not page_indices:
            QMessageBox.warning(self, "No pages selected", "Check the pages that belong to this airway number.")
            return

        client_folder = self._get_selected_client_folder()
        year_folder = self.selected_year

        safe_airway = "".join(c if c.isalnum() or c in "-_." else "_" for c in airway)

        # NEW STRUCTURE:
        # separated_invoices / <YEAR> / <CLIENT> / <AIRWAY>.pdf
        folder = OUTPUT_BASE / year_folder / client_folder
        folder.mkdir(parents=True, exist_ok=True)
        out_pdf = folder / f"{safe_airway}.pdf"

        try:
            writer = PdfWriter()
            for i in page_indices:
                writer.add_page(self.reader.pages[i])

            with open(out_pdf, "wb") as f:
                writer.write(f)

            # Increment usage counts (allow reuse)
            for i in page_indices:
                self.page_use_counts[i] = self.page_use_counts.get(i, 0) + 1

            # refresh UI list labels
            self._populate_page_list()
            self.airway_input.clear()

            QMessageBox.information(
                self,
                "Saved",
                f"Saved {len(page_indices)} pages to:\n{out_pdf}"
            )

            self._open_folder(folder)

        except Exception as e:
            QMessageBox.critical(self, "Save Error", str(e))

    def _open_folder(self, folder: Path):
        try:
            if sys.platform.startswith("win"):
                os.startfile(str(folder))
            elif sys.platform == "darwin":
                os.system(f"open '{folder}'")
            else:
                os.system(f"xdg-open '{folder}'")
        except Exception:
            pass


def main():
    app = QApplication(sys.argv)
    win = InvoiceSorter()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
