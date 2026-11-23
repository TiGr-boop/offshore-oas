from pathlib import Path

from lxml import etree


def get_attribute_value(parent, attribute_name, ns_const):
    attribute = parent.find(f"c:Attribute[@Name='{attribute_name}']", ns_const)

    value = attribute.findtext("c:Value", namespaces=ns_const)

    return value


def build_type_catalog(root, ns_const):
    library = root.find("c:SystemUnitClassLib[@Name='MTPDataObjectSUCLib']", ns_const)
    catalog = {}

    def walk(system_unit_class, parent_path, inherited_attributes):
        path = f"{parent_path}/{system_unit_class.get('Name')}"

        # geerbte Attribute übernehmen, eigene ergänzen bzw. überschreiben
        attributes = dict(inherited_attributes)
        for attribute in system_unit_class.findall("c:Attribute", ns_const):
            description = attribute.findtext("c:Description", namespaces=ns_const)
            attributes[attribute.get("Name")] = {
                "description": description.strip() if description else None,
                "datatype": attribute.get("AttributeDataType"),
            }

        chain = path.split("/")[1:]  # ohne Bibliotheksnamen
        catalog[path] = {
            "name": system_unit_class.get("Name"),
            "family": chain[1] if len(chain) > 1 else None,  # z. B. ActiveElement
            "chain": chain,
            "attributes": attributes,
        }

        for child in system_unit_class.findall("c:SystemUnitClass", ns_const):
            walk(child, path, attributes)

    for top_class in library.findall("c:SystemUnitClass", ns_const):
        walk(top_class, library.get("Name"), {})

    return catalog


def parse_manifest(manifest_path: Path) -> dict:

    warnings = []

    root = etree.parse(str(manifest_path)).getroot()
    ns = etree.QName(root).namespace
    ns_const = {"c": ns}

    ### Metadaten ###
    src = root.find("c:SourceDocumentInformation", ns_const)
    instance_hierarchy = root.find(
        "c:InstanceHierarchy[@Name='ModuleTypePackage']", ns_const
    )
    pea = instance_hierarchy.find("c:InternalElement", ns_const)

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

    communication = pea.find("c:InternalElement[@Name='Communication']", ns_const)
    sources = communication.find("c:InternalElement[@Name='Sources']", ns_const)

    ### OPC UA Servers ###

    opcua_servers = []
    items = {}
    for server in sources.iterfind(".//c:InternalElement", ns_const):
        name_server = server.get("Name")

        if not server.get("RefBaseSystemUnitPath").endswith(
            "ServerAssembly/OPCUAServer"
        ):
            continue

        # Nachschlagetabelle für GUID
        for ei in server.iterfind(".//c:ExternalInterface", ns_const):
            namespace_ei = get_attribute_value(ei, "Namespace", ns_const)
            identifier_ei = get_attribute_value(ei, "Identifier", ns_const)
            items[ei.get("ID")] = (namespace_ei, identifier_ei, name_server)

        server_info = {
            "name": server.get("Name"),
            "description": server.findtext("c:Description", namespaces=ns_const),
            "endpoint": get_attribute_value(server, "Endpoint", ns_const),
            "max_sessions": get_attribute_value(server, "MaxSessions", ns_const),
        }
        opcua_servers.append(server_info)

    ### Data Assemblies ###
    data_assemblies = []

    type_catalog = build_type_catalog(root, ns_const)
    types_used = {}

    instances = communication.find("c:InternalElement[@Name='Instances']", ns_const)
    inst_children = instances.findall("c:InternalElement", ns_const)

    useless_attributes = ["RefID", "TagName", "TagDescription"]

    for data_assembly in inst_children:
        type_path = data_assembly.get("RefBaseSystemUnitPath")
        type_entry = type_catalog.get(type_path)
        type_name, family = type_entry["name"], type_entry["family"]
        types_used[type_name] = {
            "family": family,
            "chain": type_entry["chain"],
            "attributes": type_entry["attributes"],
        }
        da_name = data_assembly.get("Name")

        signals = {}
        static_values = {}

        for attribute in data_assembly.findall("c:Attribute", ns_const):
            attribute_name = attribute.get("Name")
            if attribute_name in useless_attributes:
                continue

            reference = attribute.findtext("c:Value", namespaces=ns_const)
            if reference in items:
                ns_uri, identifier, server = items[reference]
                signals[attribute_name] = {
                    "namespace": ns_uri,
                    "identifier": identifier,
                    "server": server,
                }
            elif "StaticValueAttributeType" in (
                attribute.get("RefAttributeType") or ""
            ):
                static_values[attribute_name] = reference
            else:
                warnings.append(f"Reference {reference} not found in items")

        data_assemblies.append(
            {
                "name": da_name,
                "id": data_assembly.get("ID"),
                "type": type_path,
                "signals": signals,
                "static_values": static_values,
            }
        )

    ### Services ###
    services = root.find("c:InstanceHierarchy[@Name='Services']", ns_const)
    number_of_services = services.findtext(
        "c:AdditionalInformation", namespaces=ns_const
    )

    return {
        "pea_info": pea_info,
        "opcua_servers": opcua_servers,
        "types": types_used,
        "data_assemblies": data_assemblies,
        "services": number_of_services,
        "warnings": warnings,
    }
