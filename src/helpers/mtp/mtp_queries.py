import json
from collections import defaultdict
from pathlib import Path

project_root = Path(__file__).resolve().parents[3]
processed_dir = project_root / "data" / "processed_mtp"


### Daten Laden

_cache = {}


def load():
    _cache.clear()
    for file in processed_dir.iterdir():
        manifest = json.loads(file.read_text(encoding="utf-8"))
        _cache[manifest.get("module_name")] = manifest


def module_info(module_name: str) -> dict:
    if not _cache:
        load()
    for mod_name, manifest in _cache.items():
        if mod_name.lower() == module_name.strip().lower():
            return manifest
    raise ValueError(
        f"Unbekanntes Modul '{module_name}'. Verfügbar: {', '.join(_cache) or '(keine)'}"
    )


def data_assembly_info(manifest: dict, da_name: str) -> dict:
    for da in manifest["data_assemblies"]:
        if da["name"].lower() == da_name.strip().lower():
            return da
    close = [
        da["name"]
        for da in manifest["data_assemblies"]
        if da_name.strip().lower() in da["name"].lower()
    ]
    hint = (
        f" Ähnliche Tags: {', '.join(close[:8])}."
        if close
        else " Mit find_data_assemblies oder get_plant_overview nach dem richtigen Tag suchen."
    )
    raise ValueError(f"Baustein '{da_name}' nicht gefunden.{hint}")


def type_info(manifest: dict, type_name: str) -> dict:
    type_name = type_name.strip().rsplit("/", 1)[-1]
    for name, entry in manifest["types"].items():
        if name.lower() == type_name.lower():
            return {"name": name, **entry}
    raise ValueError(
        f"Typ '{type_name}' kommt in dieser MTP nicht vor. "
        f"Vorhandene Typen: {', '.join(manifest['types'])}."
    )


### Queries


def list_modules() -> dict:
    if not _cache:
        load()
    return {
        "modules": [
            {
                "module": mod_name,
                "product_code": m["pea_info"].get("product_code"),
                "version": m["pea_info"].get("version"),
                "data_assemblies": len(m["data_assemblies"]),
                "services": m["services"],
            }
            for mod_name, m in _cache.items()
        ]
    }


def list_data_assemblies(module: str) -> list[str]:
    if not _cache:
        load()
    manifest = module_info(module)
    data_assemblies = {
        "data_assemblies": [d["name"] for d in manifest["data_assemblies"]]
    }
    return data_assemblies["data_assemblies"]

def list_signals(module: str, da_name: str) -> list[str]:
    if not _cache:
        load()
    manifest = module_info(module)
    da = data_assembly_info(manifest, da_name)
    return list(da["signals"])


def module_overview(module_name: str) -> str:
    m = module_info(module_name)
    info = m["pea_info"]
    by_type: dict[str, list[dict]] = defaultdict(list)
    for d in m["data_assemblies"]:
        by_type[d["type"]].append(d)

    lines = [
        f"# Modul {info.get('product_code')} (ID: {m['module_name']}, MTP-Version {info.get('version')})",
        f"Bausteine / DAs: {len(m['data_assemblies'])} | Services: {m['services']}",
        "",
    ]

    process = []
    for typ, das in by_type.items():
        type_details = type_info(m, typ)
        family = type_details["family"]
        entry = (
            f"- **{type_details['name']}** ({len(das)}): "
            f"{', '.join(d['name'] for d in das)}"
        )
        if family != "PeaElement":
            process.append(entry)
    lines += process

    lines += ["", "PEA-Informationen:"]
    pea_fields = [
        ("Produktcode", "product_code"),
        ("Hersteller", "manufacturer"),
        ("Version", "version"),
        ("Geräterevision", "device_revision"),
        ("Projekt", "project"),
        ("Letzte Änderung", "last_changes"),
    ]
    for label, key in pea_fields:
        if info.get(key):
            lines.append(f"- {label}: {info[key]}")

    web_server_ref = info.get("web_server_url")
    web_server_da = next(
        (d for d in m["data_assemblies"] if d.get("id") == web_server_ref),
        None,
    )
    web_server_url = (
        web_server_da.get("static_values", {}).get("Url") if web_server_da else None
    )
    if web_server_url:
        lines.append(f"- Webserver-URL: {web_server_url}")

    limits = []
    if not m["services"]:
        limits.append(
            "Die MTP definiert keine Services (keine Prozeduren oder Prozessführungsfunktionen)."
        )
    limits += m["warnings"]
    if limits:
        lines += ["", "Bekannte Einschränkungen dieser MTP:"] + [
            f"- {w}" for w in limits
        ]
    return "\n".join(lines)


def describe_data_assembly(module_name: str, da_name: str) -> dict:
    m = module_info(module_name)
    d = data_assembly_info(m, da_name)
    type_details = type_info(m, d["type"])
    result = {
        "tag": d["name"],
        "type": type_details["name"],
        "family": type_details["family"],
        "signals": list(d["signals"]),
        "next": "Einzelnes Signal erklären: describe_signal. Alle Signale des Typs: describe_type.",
    }
    return result


def describe_signal(module: str, da_name: str, signal: str) -> dict:
    m = module_info(module)
    d = data_assembly_info(m, da_name)
    names = {s.lower(): s for s in d["signals"]}
    key = names.get(signal.strip().lower())
    if key is None:
        raise ValueError(
            f"Signal '{signal}' existiert bei {d['name']} nicht. "
            f"Verfügbar: {', '.join(d['signals'])}"
        )
    signal_info = d["signals"][key]
    return {
        "data_assembly": d["name"],
        "type": d["type"],
        "signal": key,
        "description": signal_info,
    }
