import subprocess
import tempfile
from pathlib import Path


def convert_docx_to_pdf(docx_bytes: bytes) -> bytes:
    with tempfile.TemporaryDirectory() as temp_dir:
        docx_path = Path(temp_dir) / "resume.docx"

        with open(docx_path, "wb") as f:
            f.write(docx_bytes)

        # ✅ Convert using LibreOffice
        subprocess.run([
            "soffice",
            "--headless",
            "--convert-to", "pdf",
            "--outdir", temp_dir,
            str(docx_path)
        ], check=True)

        pdf_path = Path(temp_dir) / "resume.pdf"

        with open(pdf_path, "rb") as f:
            return f.read()