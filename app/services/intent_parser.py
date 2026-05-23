from typing import Dict, List


def _contains_any(text: str, terms: List[str]) -> bool:
    t = text.lower()
    return any(term in t for term in terms)


def parse_requirement(
    requirement_text: str,
    force_table_mode: bool = False,
    force_metadata_mode: bool = False,
    force_section_number_mode: bool = False,
    force_drawing_mode: bool = False,
    use_tabular_tag: bool = False,
) -> Dict:
    text = requirement_text.lower()

    special_tags = []
    family = "requirements_block"
    source_hint = "paragraph_or_list"

    if force_section_number_mode or _contains_any(text, ["section number", "reference section", "which section"]):
        family = "section_number"
        special_tags.append("@sectionNumber")
        source_hint = "metadata_json"

    elif force_metadata_mode or _contains_any(text, ["title", "document number", "header", "footer", "first page", "metadata"]):
        family = "metadata"
        special_tags.append("@metadataQuery")
        source_hint = "first_pages_or_header"

    elif force_drawing_mode or _contains_any(text, ["p&id", "drawing", "dwg", "diagram", "schematic", "title block"]):
        family = "drawing"
        source_hint = "drawing"

    elif force_table_mode or _contains_any(text, ["table", "io list", "i/o list", "tag", "signal type", "row", "column"]):
        family = "tabular_lookup"
        source_hint = "table"

    if use_tabular_tag or _contains_any(text, ["list all", "steps", "cycle procedure", "utilities required", "multi row"]):
        if "@tabular" not in special_tags:
            special_tags.append("@tabular")

    target_keywords = []
    for candidate in [
        "utility", "utilities", "bom", "bill of materials", "spare parts", "components",
        "surface finish", "electropolish", "passivation", "welding", "power", "ups",
        "material of construction", "moc", "slope", "draining", "p&id", "drawing",
        "ga drawing", "title", "document number", "equipment name", "tag", "signal type",
    ]:
        if candidate in text:
            target_keywords.append(candidate)

    return {
        "extraction_family": family,
        "source_hint": source_hint,
        "special_tags": special_tags,
        "target_keywords": target_keywords,
        "table_mode": family == "tabular_lookup",
        "drawing_mode": family == "drawing",
        "metadata_mode": family == "metadata",
        "section_number_mode": family == "section_number",
    }