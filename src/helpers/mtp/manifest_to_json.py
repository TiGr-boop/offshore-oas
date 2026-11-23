import json
from pathlib import Path

from mtp_extraction import extract_mtp_files
from mtp_parser import parse_manifest

project_root = Path(__file__).resolve().parents[3]

extract_dir = project_root / "data" / "extracted_files"
processed_dir = project_root / "data" / "processed_mtp"


def main():
    extract_mtp_files()

    for folder in extract_dir.iterdir():
        module_name = folder.name.removesuffix(".mtp")

        manifest_path = folder / "manifest.aml"
        manifest = parse_manifest(manifest_path)

        manifest["module_name"] = module_name

        out = processed_dir / f"{module_name}.json"
        out.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )


if __name__ == "__main__":
    main()
