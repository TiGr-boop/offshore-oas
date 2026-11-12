from pathlib import Path
from lxml import etree

def get_attribute_value(parent, attribute_name, ns_const):
    attribute = parent.find(
        f"c:Attribute[@Name='{attribute_name}']",
        ns_const
    )

    value = attribute.findtext("c:Value", namespaces=ns_const)

    return value


def parse_manifest(manifest_path: Path) -> dict:

    root = etree.parse(str(manifest_path)).getroot()
    ns = etree.QName(root).namespace
    ns_const = {"c": ns}

    ### Metadaten ###
    src = root.find("c:SourceDocumentInformation", ns_const)
    instance_hierarchy = root.find("c:InstanceHierarchy[@Name='ModuleTypePackage']", ns_const)
    pea = instance_hierarchy.find("c:InternalElement", ns_const)
    communication = pea.find("c:InternalElement[@Name='Communication']", ns_const)

    pea_info = {
        "version": get_attribute_value(pea, "Version", ns_const),
        "device_revision": get_attribute_value(pea, "DeviceRevision", ns_const),
        "manufacturer": get_attribute_value(pea, "ManufacturerUri", ns_const),
        "product_code": get_attribute_value(pea, "ProductCode", ns_const),
        "pea_information": get_attribute_value(pea, "PeaInformation", ns_const),
        "web_server_url": get_attribute_value(pea, "WebServerUrl", ns_const),

        "origin_name": src.get("OriginName"),
        "origin_id": src.get("OriginID"),
        "origin_version": src.get("OriginVersion"),
        "project": src.get("OriginProjectTitle"),
        "last_changes": src.get("LastWritingDateTime"),
    }

    ### OPC UA Server Information ###
    opcua_servers = []
    for item in communication.iterfind(".//c:InternalElement", ns_const):
        if not item.get("RefBaseSystemUnitPath").endswith("ServerAssembly/OPCUAServer"):
            continue
        server_info = {
            "name": item.get("Name"),
            "description": item.findtext("c:Description", namespaces=ns_const),
            "endpoint": get_attribute_value(item, "Endpoint", ns_const),
            "max_sessions": get_attribute_value(item, "MaxSessions", ns_const),
        }
        opcua_servers.append(server_info)


    return {
        "pea_info": pea_info,
        "opcua_servers": opcua_servers,
    }
