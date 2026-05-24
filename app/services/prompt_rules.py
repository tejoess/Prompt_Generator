import json
from typing import List, Optional

STANDARD_REQUIRED_LINES = [
    "Answer strictly and only from the provided context.",
    "Do not infer, assume, generalize, or use external knowledge.",
    "Return exact phrases and values as they appear in the context.",
    "Do not change units, terminology, wording, spelling, or numeric values.",
    "Do not paraphrase, summarize, or standardize measurements.",
    "Any modification of units, numbers, or wording is an error.",
    "Provide no explanation, no description, no commentary.",
    "Return ONLY the JSON object and nothing else.",
]

TABLE_CELL_LINE = "'|' is a cell differentiator. Understand the table structure and interpret rows and values accurately."

DRAWING_LINES = [
    "This is engineering drawing or P&ID context and may be noisy.",
    "Extract only what is explicitly readable from the provided context.",
    "If the value is not explicitly readable, return: { \"answer\": \"N/Ap\" }.",
]

PID_SYSTEM_LINES = [
    "You are an expert in reading P&ID (Piping & Instrumentation Diagram) drawings and engineering documents.",
    "The provided context is extracted from a small, specific section of a technical drawing and may be noisy, partial, or fragmented.",
    "Extract ONLY what is explicitly and clearly readable in the provided context.",
    "Do not guess, infer, or assume values that are not clearly visible in the text.",
    "Focus on exact tiny details: tag numbers, instrument identifiers, line numbers, notes, and title block fields.",
    "When both a PID title and document number are present, treat them as a combined identifier.",
    "Do not interpret partial text or symbols beyond what is literally written.",
]


def normalize_doc_types(doc_types: List[str]) -> List[str]:
    clean = []
    for item in doc_types:
        item = item.strip()
        if item and item not in clean:
            clean.append(item)
    return clean


def parse_csv_values(raw: str | None) -> List[str]:
    if not raw:
        return []
    return [x.strip() for x in raw.split(",") if x.strip()]


def build_json_block(output_key: str) -> List[str]:
    return [
        "Return the extracted answer as valid JSON only in the following format:",
        f'{{ "{output_key}": "<extracted text here>" }}',
        "If the context does not contain information related to the query, respond with:",
        f'{{ "{output_key}": "N/Ap" }}',
    ]


def build_standard_system_prompt(
    expertise_line: str,
    target_line: str,
    output_key: str = "answer",
    include_table_line: bool = False,
    include_drawing_rules: bool = False,
    use_pid_template: bool = False,
    hint_note: Optional[str] = None,
    global_synonyms: Optional[str] = None,
) -> str:
    lines: List[str] = []

    if use_pid_template:
        lines.extend(PID_SYSTEM_LINES)
    else:
        lines.append(expertise_line)
        lines.append("Recognize lists, tables, mixed paragraphs, engineering phrasing, and document structure accurately.")

    if include_table_line:
        lines.append(TABLE_CELL_LINE)

    lines.append(target_line)
    lines.extend(STANDARD_REQUIRED_LINES)

    if include_drawing_rules and not use_pid_template:
        lines.extend(DRAWING_LINES)

    if hint_note and hint_note.strip():
        lines.append(f"Important note: {hint_note.strip()}")

    synonym_block = _build_global_synonym_block(system_text="\n".join(lines), global_synonyms_json=global_synonyms)
    if synonym_block:
        lines.append(synonym_block)

    lines.extend(build_json_block(output_key))
    lines.append(f'If the answer is not explicitly present in the provided context, return: {{ "{output_key}": "N/Ap" }}.')

    return "\n".join(lines)


def _build_global_synonym_block(system_text: str, global_synonyms_json: Optional[str]) -> str:
    if not global_synonyms_json:
        return ""
    try:
        synonyms = json.loads(global_synonyms_json)
    except Exception:
        return ""

    text_lower = system_text.lower()
    relevant = [(w, v) for w, v in synonyms.items() if w.lower() in text_lower]
    if not relevant:
        return ""

    parts = ["The following terms may appear with variant spellings — treat all variants as equivalent:"]
    for word, variants in relevant:
        if isinstance(variants, str):
            variants = [variants]
        all_forms = [word] + [v for v in variants if v]
        parts.append("  " + " | ".join(f'"{f}"' for f in all_forms))
    return "\n".join(parts)


def wrap_ai_prompt(text: str) -> str:
    return f"<ai_prompt>{text}</ai_prompt>"


def wrap_system_prompt(text: str) -> str:
    return f"<system_prompt>{text}</system_prompt>"


def build_synonyms_block(values: List[str]) -> str:
    if not values:
        return ""

    lines = ["<synonyms>"]
    for item in values:
        parts = [p.strip() for p in item.split("|") if p.strip()]
        if parts:
            joined = " | ".join([f'"{p}"' for p in parts])
            lines.append(f"  <synonym> {joined} </synonym>")
    lines.append("</synonyms>")
    return "\n".join(lines)