from typing import Dict, List


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


def validate_generated_prompt(result: Dict, document_types: List[str]) -> Dict:
    issues: List[str] = []
    prompt_type = result.get("prompt_type", "")

    if prompt_type in [
        "standard",
        "title",
        "metadata",
        "section_number",
        "drawing",
        "multirow_tabular",
        "ai_over_table",
    ]:
        ai_prompt = result.get("ai_prompt") or ""
        system_prompt = result.get("system_prompt") or ""
        output_key = result.get("output_key") or "answer"

        if not ai_prompt.startswith("<ai_prompt>") or not ai_prompt.endswith("</ai_prompt>"):
            issues.append("AI prompt must use <ai_prompt> tags.")

        if not system_prompt.startswith("<system_prompt>") or not system_prompt.endswith("</system_prompt>"):
            issues.append("System prompt must use <system_prompt> tags.")

        if f'{{ "{output_key}": "<extracted text here>" }}' not in system_prompt:
            issues.append("System prompt missing JSON output example.")

        if prompt_type != "title":
            if f'{{ "{output_key}": "N/Ap" }}' not in system_prompt:
                issues.append("System prompt missing N/Ap fallback.")

            for line in STANDARD_REQUIRED_LINES:
                if line not in system_prompt:
                    issues.append(f"Missing mandatory system line: {line}")

        if prompt_type == "metadata" and len(document_types) > 1:
            issues.append("@metadataQuery should not be used with multiple document types.")

        if prompt_type == "title":
            if ai_prompt != "<ai_prompt>Extract the title of the document</ai_prompt>":
                issues.append("Title prompt AI text is incorrect.")

            if '{ "title": "<extracted title text here>" }' not in system_prompt:
                issues.append("Title prompt missing required title JSON format.")

            if "You are an expert at extracting document titles." not in system_prompt:
                issues.append("Title prompt missing title extraction expertise line.")

            if "Below are the first three pages of a document." not in system_prompt:
                issues.append("Title prompt missing first three pages instruction.")

            if "Extract ONLY main & complete title of the document." not in system_prompt:
                issues.append("Title prompt missing exact title extraction instruction.")

            if "Return just the title text, nothing else." not in system_prompt:
                issues.append("Title prompt missing title-only return instruction.")

        if prompt_type == "ai_over_table":
            if "'|' is a cell differentiator." not in system_prompt:
                issues.append("AI-over-table mode must include the table cell differentiator line.")

    elif prompt_type == "table_placeholder":
        column_header = result.get("column_header") or ""
        filters_logic = result.get("filters_logic") or ""
        ai_prompt = result.get("ai_prompt")
        system_prompt = result.get("system_prompt")

        if "<column_header>" not in column_header:
            issues.append("Table placeholder requires <column_header>.")

        if "<filters>" not in filters_logic:
            issues.append("Table placeholder requires <filters>.")

        if ai_prompt or system_prompt:
            issues.append("Table placeholder must not use <ai_prompt> or <system_prompt> as primary logic.")

        if result.get("chunk_count") != "N/A":
            issues.append("Table placeholder chunk count should be N/A.")

    else:
        issues.append("Unknown prompt type.")

    return {
        "status": "valid" if not issues else "invalid",
        "issues": issues,
    }