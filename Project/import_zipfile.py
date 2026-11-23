import zipfile
from pathlib import Path

zip_archive = (
    Path(r"C:\Users\Tim-G\bwSyncShare\offshore-oas\Project")
    / "H2mare-2026.11.18-12.21.05.zip"
)

print("Datei vorhanden:", zip_archive.exists())

if zip_archive.exists():
    print("Dateigröße:", zip_archive.stat().st_size, "Bytes")
    print("ZIP erkannt:", zipfile.is_zipfile(zip_archive))

    with open(zip_archive, "rb") as f:
        header = f.read(32)

        f.seek(-32, 2)
        footer = f.read(32)

    print("Header:", header)
    print("Header HEX:", header.hex(" "))
    print("Footer:", footer)
    print("Footer HEX:", footer.hex(" "))
