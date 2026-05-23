from typing import List

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
) -> str:
    lines: List[str] = []
    lines.append(expertise_line)
    lines.append("Recognize lists, tables, mixed paragraphs, engineering phrasing, and document structure accurately.")

    if include_table_line:
      lines.append(TABLE_CELL_LINE)

    lines.append(target_line)
    lines.extend(STANDARD_REQUIRED_LINES)

    if include_drawing_rules:
        lines.extend(DRAWING_LINES)

    lines.extend(build_json_block(output_key))
    lines.append(f'If the answer is not explicitly present in the provided context, return: {{ "{output_key}": "N/Ap" }}.')

    return "\n".join(lines)


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