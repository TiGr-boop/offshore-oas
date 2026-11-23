import zipfile
from pathlib import Path


def extract_mtp_files():
    """
    Extrahiert die Inhalte der MTP-Dateien. Vor allem interessant sind die manifest.aml-Dateien.
    """
    project_root = Path(__file__).resolve().parents[3]

    mtp_dir = project_root / "data" / "mtp_files"
    extract_dir = project_root / "data" / "extracted_files"

    for mtp_file in mtp_dir.iterdir():
        with zipfile.ZipFile(mtp_file) as zf:
            for info in zf.infolist():
                print(info.filename, info.file_size)
            out_dir = extract_dir / mtp_file.name
            zf.extractall(out_dir)
