from typing import Dict, List

from app.services.prompt_rules import (
    normalize_doc_types,
    parse_csv_values,
    build_standard_system_prompt,
    wrap_ai_prompt,
    wrap_system_prompt,
    build_synonyms_block,
)


def generate_standard_prompt(payload) -> Dict:
    doc_types = normalize_doc_types(payload.document_types)
    special_tags: List[str] = []

    if payload.use_metadata_tag:
        special_tags.append("@metadataQuery")
    if payload.use_tabular_tag:
        special_tags.append("@tabular")
    if payload.use_section_number_tag:
        special_tags.append("@sectionNumber")

    ai_text = (payload.requirement_text or "").strip()
    if special_tags:
        ai_text = " ".join(special_tags) + " " + ai_text

    ai_prompt = wrap_ai_prompt(ai_text)

    system_text = build_standard_system_prompt(
        expertise_line="You are an expert at identifying technical requirements from engineering and technical documents.",
        target_line=f"Identify and extract the exact answer for this requirement: {ai_text.strip()}",
        output_key=payload.expected_json_key or "answer",
        include_table_line=("table" in ai_text.lower()),
        include_drawing_rules=False,
        hint_note=getattr(payload, "hint_note", None),
        global_synonyms=getattr(payload, "global_synonyms", None),
    )
    system_prompt = wrap_system_prompt(system_text)

    final_text = f"{ai_prompt}\n\n{system_prompt}"

    return {
        "prompt_type": "standard",
        "placeholder_name": payload.placeholder_name,
        "extraction_family": "standard",
        "output_key": payload.expected_json_key or "answer",
        "special_tags": special_tags,
        "chunk_count": str(payload.chunk_count or 8),
        "ai_prompt": ai_prompt,
        "system_prompt": system_prompt,
        "column_header": None,
        "filters_logic": None,
        "synonyms_logic": None,
        "grouping_logic": None,
        "document_types": doc_types,
        "final_prompt_text": final_text,
    }


def generate_title_prompt(payload) -> Dict:
    doc_types = normalize_doc_types(payload.document_types)
    output_key = payload.expected_json_key or "title"

    ai_prompt = wrap_ai_prompt("Extract the title of the document")

    system_prompt_text = (
        "You are an expert at extracting document titles. "
        "Below are the first three pages of a document. "
        "The document title typically appears on the first page, often at the top. "
        "Extract ONLY main & complete title of the document. "
        "Return just the title text, nothing else. "
        "If the title is split across multiple lines, combine them into a single coherent title. "
        "Do NOT include project numbers, revision numbers, dates, or site details in the title. "
        "Return the extracted title as valid JSON only in the following format:\n"
        f'{{ "{output_key}": "<extracted title text here>" }}'
    )

    system_prompt = wrap_system_prompt(system_prompt_text)
    final_text = f"{ai_prompt}\n\n{system_prompt}"

    return {
        "prompt_type": "title",
        "placeholder_name": payload.placeholder_name,
        "extraction_family": "title_extraction",
        "output_key": output_key,
        "special_tags": [],
        "chunk_count": str(payload.chunk_count or 3),
        "ai_prompt": ai_prompt,
        "system_prompt": system_prompt,
        "column_header": None,
        "filters_logic": None,
        "synonyms_logic": None,
        "grouping_logic": None,
        "document_types": doc_types,
        "final_prompt_text": final_text,
    }


def generate_ai_over_table_prompt(payload) -> Dict:
    doc_types = normalize_doc_types(payload.document_types)
    ai_text = (payload.requirement_text or "").strip()
    ai_prompt = wrap_ai_prompt(ai_text)

    target = (payload.table_target_instruction or payload.requirement_text or "").strip()

    system_text = build_standard_system_prompt(
        expertise_line="You are an expert in finding exact values from engineering tables and tabular document excerpts.",
        target_line=f"Locate the relevant row or rows in the table and extract the exact matching value. Extraction target: {target}",
        output_key=payload.expected_json_key or "answer",
        include_table_line=True,
        include_drawing_rules=False,
        hint_note=getattr(payload, "hint_note", None),
        global_synonyms=getattr(payload, "global_synonyms", None),
    )
    system_prompt = wrap_system_prompt(system_text)

    final_text = f"{ai_prompt}\n\n{system_prompt}"

    return {
        "prompt_type": "ai_over_table",
        "placeholder_name": payload.placeholder_name,
        "extraction_family": "tabular_lookup",
        "output_key": payload.expected_json_key or "answer",
        "special_tags": [],
        "chunk_count": str(payload.chunk_count or 8),
        "ai_prompt": ai_prompt,
        "system_prompt": system_prompt,
        "column_header": None,
        "filters_logic": None,
        "synonyms_logic": None,
        "grouping_logic": None,
        "document_types": doc_types,
        "final_prompt_text": final_text,
    }


def generate_metadata_prompt(payload) -> Dict:
    doc_types = normalize_doc_types(payload.document_types)
    req_text = (payload.requirement_text or "").strip()
    ai_text = f"@metadataQuery {req_text}"
    ai_prompt = wrap_ai_prompt(ai_text)

    system_text = build_standard_system_prompt(
        expertise_line="You are an expert at extracting exact metadata values from engineering and technical documents.",
        target_line=f"Locate the exact metadata field value requested in the requirement, usually from headers, footers, title area, or the first three pages. Extraction target: {req_text}",
        output_key=payload.expected_json_key or "answer",
        include_table_line=False,
        include_drawing_rules=False,
        hint_note=getattr(payload, "hint_note", None),
        global_synonyms=getattr(payload, "global_synonyms", None),
    )
    system_prompt = wrap_system_prompt(system_text)

    final_text = f"{ai_prompt}\n\n{system_prompt}"

    return {
        "prompt_type": "metadata",
        "placeholder_name": payload.placeholder_name,
        "extraction_family": "metadata",
        "output_key": payload.expected_json_key or "answer",
        "special_tags": ["@metadataQuery"],
        "chunk_count": str(payload.chunk_count or 8),
        "ai_prompt": ai_prompt,
        "system_prompt": system_prompt,
        "column_header": None,
        "filters_logic": None,
        "synonyms_logic": None,
        "grouping_logic": None,
        "document_types": doc_types,
        "final_prompt_text": final_text,
    }


def generate_section_number_prompt(payload) -> Dict:
    doc_types = normalize_doc_types(payload.document_types)
    req_text = (payload.requirement_text or "").strip()
    ai_text = f"@sectionNumber {req_text}"
    ai_prompt = wrap_ai_prompt(ai_text)

    system_text = build_standard_system_prompt(
        expertise_line="You are an expert at identifying exact section references from structured engineering document context.",
        target_line=f"Find the exact section number explicitly associated with the requested topic. Extraction target: {req_text}",
        output_key=payload.expected_json_key or "answer",
        include_table_line=False,
        include_drawing_rules=False,
        hint_note=getattr(payload, "hint_note", None),
        global_synonyms=getattr(payload, "global_synonyms", None),
    )
    system_prompt = wrap_system_prompt(system_text)

    final_text = f"{ai_prompt}\n\n{system_prompt}"

    return {
        "prompt_type": "section_number",
        "placeholder_name": payload.placeholder_name,
        "extraction_family": "section_number",
        "output_key": payload.expected_json_key or "answer",
        "special_tags": ["@sectionNumber"],
        "chunk_count": str(payload.chunk_count or 8),
        "ai_prompt": ai_prompt,
        "system_prompt": system_prompt,
        "column_header": None,
        "filters_logic": None,
        "synonyms_logic": None,
        "grouping_logic": None,
        "document_types": doc_types,
        "final_prompt_text": final_text,
    }


def generate_drawing_prompt(payload) -> Dict:
    doc_types = normalize_doc_types(payload.document_types)
    # @metadataQuery is always required for drawing/P&ID prompts
    special_tags: List[str] = ["@metadataQuery"]

    req_text = (payload.requirement_text or "").strip()
    ai_text = "@metadataQuery " + req_text

    ai_prompt = wrap_ai_prompt(ai_text)

    target = (payload.drawing_target_field or payload.requirement_text or "").strip()

    system_text = build_standard_system_prompt(
        expertise_line="",  # overridden by PID template
        target_line=f"Locate the exact readable text for this drawing/P&ID field. Extraction target: {target}",
        output_key=payload.expected_json_key or "answer",
        include_table_line=False,
        include_drawing_rules=False,
        use_pid_template=True,
        hint_note=getattr(payload, "hint_note", None),
        global_synonyms=getattr(payload, "global_synonyms", None),
    )
    system_prompt = wrap_system_prompt(system_text)

    final_text = f"{ai_prompt}\n\n{system_prompt}"

    return {
        "prompt_type": "drawing",
        "placeholder_name": payload.placeholder_name,
        "extraction_family": "drawing",
        "output_key": payload.expected_json_key or "answer",
        "special_tags": special_tags,
        "chunk_count": str(payload.chunk_count or 8),
        "ai_prompt": ai_prompt,
        "system_prompt": system_prompt,
        "column_header": None,
        "filters_logic": None,
        "synonyms_logic": None,
        "grouping_logic": None,
        "document_types": doc_types,
        "final_prompt_text": final_text,
    }


def generate_multirow_tabular_prompt(payload) -> Dict:
    doc_types = normalize_doc_types(payload.document_types)
    req_text = (payload.requirement_text or "").strip()
    ai_text = f"@tabular {req_text}"
    ai_prompt = wrap_ai_prompt(ai_text)

    output_key = payload.expected_json_key or "answer"

    system_text = build_standard_system_prompt(
        expertise_line="You are an expert at extracting repeated technical values and lists from engineering and technical documents.",
        target_line=f"Extract the exact repeated values or rows requested. Extraction target: {req_text}",
        output_key=output_key,
        include_table_line=("table" in req_text.lower()),
        include_drawing_rules=False,
        hint_note=getattr(payload, "hint_note", None),
        global_synonyms=getattr(payload, "global_synonyms", None),
    )
    system_prompt = wrap_system_prompt(system_text)

    final_text = f"{ai_prompt}\n\n{system_prompt}"

    return {
        "prompt_type": "multirow_tabular",
        "placeholder_name": payload.placeholder_name,
        "extraction_family": "multirow_tabular",
        "output_key": output_key,
        "special_tags": ["@tabular"],
        "chunk_count": str(payload.chunk_count or 8),
        "ai_prompt": ai_prompt,
        "system_prompt": system_prompt,
        "column_header": None,
        "filters_logic": None,
        "synonyms_logic": None,
        "grouping_logic": None,
        "document_types": doc_types,
        "final_prompt_text": final_text,
    }


def generate_table_placeholder(payload) -> Dict:
    doc_types = normalize_doc_types(payload.document_types)
    synonyms = parse_csv_values(payload.synonyms_csv)
    grouping = parse_csv_values(payload.grouping_placeholders_csv)

    operator = "!=" if payload.use_not_equals else "="
    filter_value = payload.filter_value or ""

    if payload.use_wildcard_match and "*" not in filter_value:
        filter_value = f"*{filter_value}*"

    filters = []
    if payload.filter_column and filter_value:
        filters.append(f'"{payload.filter_column}"{operator}"{filter_value}"')
    if payload.table_header:
        filters.append(f'"table_header"="{payload.table_header}"')
    if payload.exclude_table_header:
        filters.append(f'"table_header" != "{payload.exclude_table_header}"')

    if len(filters) == 0:
        filters_joined = ""
    elif len(filters) <= 2:
        filters_joined = " | ".join(filters)
    else:
        filters_joined = f'{filters[0]} | {filters[1]} and {filters[2]}'

    column_header_logic = f'<column_header> "{payload.column_header}" </column_header>'
    filters_logic = f"<filters> ({filters_joined}) </filters>"
    synonyms_logic = build_synonyms_block(synonyms)

    grouping_logic = ""
    if grouping:
        joined = ",".join([f'"{item}"' for item in grouping])
        grouping_logic = f"@grouping=[{joined}]"

    parts = []
    if grouping_logic:
        parts.append(grouping_logic)
    parts.append(column_header_logic)
    parts.append(filters_logic)
    if synonyms_logic:
        parts.append(synonyms_logic)

    final_text = "\n".join(parts)

    return {
        "prompt_type": "table_placeholder",
        "placeholder_name": payload.placeholder_name,
        "extraction_family": "table_placeholder",
        "output_key": None,
        "special_tags": ["@grouping"] if grouping_logic else [],
        "chunk_count": "N/A",
        "ai_prompt": None,
        "system_prompt": None,
        "column_header": column_header_logic,
        "filters_logic": filters_logic,
        "synonyms_logic": synonyms_logic or None,
        "grouping_logic": grouping_logic or None,
        "document_types": doc_types,
        "final_prompt_text": final_text,
    }


def generate_prompts(payload) -> Dict:
    prompt_type = payload.prompt_type

    if prompt_type == "standard":
        return generate_standard_prompt(payload)
    if prompt_type == "title":
        return generate_title_prompt(payload)
    if prompt_type == "metadata":
        return generate_metadata_prompt(payload)
    if prompt_type == "section_number":
        return generate_section_number_prompt(payload)
    if prompt_type == "drawing":
        return generate_drawing_prompt(payload)
    if prompt_type == "multirow_tabular":
        return generate_multirow_tabular_prompt(payload)
    if prompt_type == "ai_over_table":
        return generate_ai_over_table_prompt(payload)
    if prompt_type == "table_placeholder":
        return generate_table_placeholder(payload)

    raise ValueError(f"Unsupported prompt type: {prompt_type}")