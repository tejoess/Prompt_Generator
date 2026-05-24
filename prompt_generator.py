"""
System Prompt Generator
-----------------------
Reads a JSON file with prompt entries, classifies each ai_prompt,
generates a structured system_prompt using local LM Studio (Qwen 2.5 3B),
and writes results back to the same JSON file.

Input JSON fields per entry:
  - placeholder   : e.g. "[URS Requirement_Utility]"
  - ai_prompt     : the query/prompt (REQUIRED to generate)
  - hint          : optional extra instruction or note
  - synonyms      : optional list of alternate terms
  - doctypes      : optional list of document types
  - chunk_count   : optional (passthrough, not used in generation)
  - system_prompt : will be overwritten with generated output

Usage:
  python prompt_generator.py --input prompts.json
  python prompt_generator.py --input prompts.json --output results.json
  python prompt_generator.py --input prompts.json --dry-run       # classify only, no LLM
  python prompt_generator.py --input prompts.json --index 3       # process single entry by index
  python prompt_generator.py --input prompts.json --force         # regenerate even if system_prompt exists
"""

import json
import re
import sys
import time
import argparse
import urllib.request
import urllib.error
from pathlib import Path

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
LM_STUDIO_URL = "http://127.0.0.1:1234/v1/chat/completions"
MODEL_NAME    = "qwen2.5-3b-instruct"
MAX_TOKENS    = 900
TEMPERATURE   = 0.2   # low = deterministic, consistent output

# ─────────────────────────────────────────────
# CATEGORY CONSTANTS
# ─────────────────────────────────────────────
CAT_REQUIREMENT   = "requirement"
CAT_SECTION_NUM   = "section_number"
CAT_METADATA      = "metadata"
CAT_IO_TABLE      = "io_table"
CAT_GENERATIVE    = "generative"
CAT_SKIP          = "skip"          # POPULATE MANUALLY or empty prompt
CAT_UNKNOWN       = "unknown"       # fallback — still generate, more generic

# ─────────────────────────────────────────────
# TEXT NORMALIZER
# ─────────────────────────────────────────────
def normalize(text: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace, basic stemming."""
    t = text.lower()
    t = re.sub(r"[^\w\s]", " ", t)   # remove punctuation → space
    t = re.sub(r"\s+", " ", t).strip()

    # Basic suffix normalization (plural/verb forms)
    stems = {
        "requirements": "requirement",
        "requires":     "requirement",
        "required":     "requirement",
        "requiring":    "requirement",
        "drawings":     "drawing",
        "numbers":      "number",
        "sections":     "section",
        "documents":    "document",
        "titles":       "title",
        "tags":         "tag",
        "extracts":     "extract",
        "extracting":   "extract",
        "identifies":   "identify",
        "identifying":  "identify",
        "drafts":       "draft",
        "drafting":     "draft",
    }
    words = t.split()
    words = [stems.get(w, w) for w in words]
    return " ".join(words)


def has_any(text: str, keywords: list) -> bool:
    """Check if any keyword phrase appears in normalized text."""
    norm = normalize(text)
    for kw in keywords:
        if kw in norm:
            return True
    return False


# ─────────────────────────────────────────────
# CLASSIFIER
# ─────────────────────────────────────────────
# Signal keywords per category — order matters: check more-specific first
SKIP_SIGNALS = [
    "populate manually",
    "populate_manually",
]

IO_TABLE_SIGNALS = [
    "@table2text",
    "@grouping",
    "column_header",
    "table2text",
    "grouping=",
]

SECTION_NUM_SIGNALS = [
    "section number",
    "section no",
    "section #",
    "@sectionnumber",
    "sectionnumber",
    "section num",
    "section of",    # "section of drawings"
    "section that is talking about",
    "section about",
    "section for",
]

REQUIREMENT_SIGNALS = [
    "requirement",
    "what are the requirement",
    "what is the requirement",
    "what is exact requirement",
    "what is requirement",
    "identify requirement",
    "extract requirement",
    "requirement of",
    "requirement for",
    "requirement about",
    "requirement that is talking",
    "require",
]

METADATA_SIGNALS = [
    "title of the document",
    "document title",
    "document number",
    "document no",
    "document #",
    "doc number",
    "doc no",
    "equipment name",
    "equipment tag",
    "system tag",
    "extract the title",
    "extract title",
    "@metadataquery",
    "metadataquery",
    "tag name",
    "serial number",
    "what is the title",
    "what is the document",
]

GENERATIVE_SIGNALS = [
    "draft yourself",
    "draft a",
    "write a",
    "write an",
    "describe",
    "introduction",
    "scope overview",
    "procedure",
    "@tabular",
    "paragraph",
    "summary",
    "approx",
    "words paragraph",
    "system description",
]

# "Extract X" patterns that are metadata-like (single value extraction)
EXTRACT_SINGLE_SIGNALS = [
    "extract the material of construction",
    "extract the surface finish",
    "extract the distribution loop",
    "extract the acceptance criteria",
    "extract acceptance criteria",
    "extract the",
    "what is the storage capacity",
    "what is the volume",
    "capacity and or volume",
    "what are the critical parameter",
    "what are the various user",
    "user level",
    "user role",
    "tag name mentioned",
]


def classify(ai_prompt: str, placeholder: str = "") -> str:
    """
    Classify ai_prompt into one of the category constants.
    Priority order: skip > io_table > section_number > requirement > metadata > generative > unknown
    """
    raw = ai_prompt.strip()

    if not raw or raw.lower() in ("nan", "none", ""):
        return CAT_SKIP

    # Check raw string first for @-prefixed tags (structural markers)
    raw_lower = raw.lower()

    if has_any(raw, SKIP_SIGNALS):
        return CAT_SKIP

    if "@table2text" in raw_lower or "@grouping" in raw_lower or "column_header" in raw_lower:
        return CAT_IO_TABLE

    if "@sectionnumber" in raw_lower:
        return CAT_SECTION_NUM

    if "@metadataquery" in raw_lower:
        return CAT_METADATA

    if "@tabular" in raw_lower:
        return CAT_GENERATIVE

    # Now use normalized matching
    if has_any(raw, SECTION_NUM_SIGNALS):
        return CAT_SECTION_NUM

    if has_any(raw, REQUIREMENT_SIGNALS):
        return CAT_REQUIREMENT

    if has_any(raw, GENERATIVE_SIGNALS):
        return CAT_GENERATIVE

    if has_any(raw, METADATA_SIGNALS):
        return CAT_METADATA

    if has_any(raw, EXTRACT_SINGLE_SIGNALS):
        return CAT_METADATA

    # Placeholder name hints (fallback signal)
    ph_lower = placeholder.lower()
    if "requirement number" in ph_lower or "section number" in ph_lower:
        return CAT_SECTION_NUM
    if "requirement" in ph_lower:
        return CAT_REQUIREMENT
    if any(x in ph_lower for x in ["title", "tag", "no.", "#"]):
        return CAT_METADATA

    return CAT_UNKNOWN


# ─────────────────────────────────────────────
# JSON KEY DERIVER  (rule-based output format)
# ─────────────────────────────────────────────
def derive_json_key(placeholder: str, ai_prompt: str, category: str) -> str | None:
    """
    Derive the JSON output key from the placeholder name.
    Returns None if no specific key can be inferred (e.g. generative, io_table).
    """
    if category in (CAT_GENERATIVE, CAT_IO_TABLE, CAT_SKIP):
        return None

    ph = re.sub(r"[\[\]]", "", placeholder).strip()  # strip brackets

    # Section number prompts always return section_number
    if category == CAT_SECTION_NUM:
        return "section_number"

    # Requirement prompts always return requirements
    if category == CAT_REQUIREMENT:
        return "requirements"

    # Metadata: infer from placeholder text
    ph_lower = ph.lower()

    if re.search(r"\btitle\b", ph_lower):
        return "title"
    if re.search(r"\bdocument.?number\b|\bdoc.?no\b|urs\s*#|manual\s*#|sat.?title|iq.?title|oq.?title|\b#\b", ph_lower):
        return "document_number"
    if re.search(r"\bequipment.?name\b", ph_lower):
        return "equipment_name"
    if re.search(r"\btag\b", ph_lower):
        return "tag"
    if re.search(r"\bmoc\b|material.of.construction", ph_lower):
        return "material_of_construction"
    if re.search(r"\bra.?value\b|surface.finish", ph_lower):
        return "surface_finish"
    if re.search(r"\bconductivity\b", ph_lower):
        return "conductivity_value"
    if re.search(r"\btoc\b|organic.carbon", ph_lower):
        return "toc_value"
    if re.search(r"\bnitrate\b", ph_lower):
        return "nitrates_value"
    if re.search(r"\bviable.count\b", ph_lower):
        return "viable_count_value"
    if re.search(r"\btank.storage\b|storage.capacity\b", ph_lower):
        return "storage_capacity"
    if re.search(r"\bcritical.param\b", ph_lower):
        return "critical_parameters"
    if re.search(r"\buser.access\b|user.level\b", ph_lower):
        return "user_access_levels"

    # Generic fallback: convert placeholder to snake_case key
    key = re.sub(r"[^a-zA-Z0-9\s]", " ", ph)
    key = "_".join(key.lower().split())
    return key


# ─────────────────────────────────────────────
# META-PROMPT BUILDER  (the actual LLM prompt)
# ─────────────────────────────────────────────
CATEGORY_ROLE = {
    CAT_REQUIREMENT: "an expert at identifying, extracting, and reformatting technical requirements from engineering and pharmaceutical documents",
    CAT_SECTION_NUM: "an expert at locating section numbers within structured document metadata and chunk JSON data",
    CAT_METADATA:    "an expert at extracting specific fields and values from technical documents",
    CAT_IO_TABLE:    "an expert at parsing I/O lists, instrument tag tables, and structured tabular data from engineering documents",
    CAT_GENERATIVE:  "a skilled technical writer with deep knowledge of pharmaceutical and engineering systems",
    CAT_UNKNOWN:     "an expert at understanding and extracting information from technical documents",
}

CATEGORY_BASE_RULES = {
    CAT_REQUIREMENT: [
        "Extract requirements EXACTLY as they appear in the source document — do NOT rephrase, summarize, or modify any requirement text.",
        "Look for requirements in BOTH table/list format (markdown tables, pipe-separated '|' cells) AND paragraph/bullet format.",
        "If requirements are in table format, convert each row into a single line item: 'parameter - value/specification'.",
        "If multiple requirements exist, format as bullet points.",
        "Do NOT include section numbers, headers, or any explanatory text — only the requirements themselves.",
        "If the topic is NOT found anywhere in the context, return exactly: { \"requirements\": \"N/Ap\" }",
        "CRITICAL: Return ONLY valid JSON. No preamble, no explanation, no markdown fences. Start immediately with { and end with }.",
    ],
    CAT_SECTION_NUM: [
        "Your task is to find the section number from the 'metadata' field of the provided document chunks.",
        "Each chunk has a 'metadata' field containing 'section_number' and 'section_title'.",
        "Return ONLY the section_number from the metadata field of the matching chunk — NOT any number found inside the content text.",
        "Ignore numbering found in the content body (e.g. 1., 2., 3. or list items). These are NOT valid section numbers.",
        "If the section number value appears invalid (e.g. a large number like 2000, 89, 29), look inside the content field of that chunk to find the correct section reference.",
        "If multiple matches are found, return the one with the most prominent and relevant content.",
        "If the topic is NOT found anywhere in the context, return exactly: { \"section_number\": \"N/Ap\" }",
        "CRITICAL: Return ONLY valid JSON. No preamble, no explanation, no markdown fences. Start immediately with { and end with }.",
    ],
    CAT_METADATA: [
        "Extract ONLY the specific requested value — return nothing else.",
        "The value is typically found on the first 1–3 pages of the document, often in the title block or header area.",
        "Do NOT include labels, prefixes, revision numbers, dates, or site-specific details unless they are part of the value itself.",
        "If multiple candidates are found, return the most prominent or complete one.",
        "CRITICAL: Return ONLY valid JSON. No preamble, no explanation, no markdown fences. Start immediately with { and end with }.",
    ],
    CAT_IO_TABLE: [
        "Parse the provided I/O list or tag table to extract the requested tag or instrument data.",
        "Apply the given column filters and description pattern matches exactly as specified.",
        "Return the matched rows with the specified column values.",
        "If no matching entries are found, return an empty list.",
        "CRITICAL: Return ONLY valid JSON. No preamble, no explanation, no markdown fences. Start immediately with { and end with }.",
    ],
    CAT_GENERATIVE: [
        "Generate content STRICTLY based on information found in the provided document context — do not fabricate or assume details.",
        "Write in clear, professional technical language appropriate for pharmaceutical/engineering validation documents.",
        "Structure the output as coherent paragraph(s) unless a specific format (table, list) is requested.",
        "Do not include placeholder text, brackets, or instructions in the output.",
    ],
    CAT_UNKNOWN: [
        "Extract or identify the requested information strictly from the provided document context.",
        "Do not fabricate, assume, or infer beyond what is present in the context.",
        "CRITICAL: Return ONLY valid JSON. No preamble, no explanation, no markdown fences. Start immediately with { and end with }.",
    ],
}



# ─────────────────────────────────────────────
# CATEGORY-SPECIFIC SYSTEM PROMPTS FOR THE GENERATOR
# ─────────────────────────────────────────────
# Each is the SYSTEM message for the LLM call that generates the system prompt.
# These teach the LLM to reason from domain knowledge, not just restate the query.

GENERATOR_SYSTEM_BY_CATEGORY = {

    CAT_REQUIREMENT: """You are a senior validation engineer in the pharmaceutical and biotech industry with 15+ years of experience reading URS, FS, and DS documents. You deeply understand how technical requirements are written, structured, and embedded in engineering specifications.

Your job: write a system prompt that will be used by an LLM to extract requirements from document chunks. The system prompt you write must demonstrate real domain expertise — it should tell the LLM exactly WHERE this type of requirement typically appears in a document, WHAT terminology and phrasing engineers use for it, HOW to handle edge cases (missing, combined, or tabular requirements), and HOW to distinguish it from other nearby content.

Output ONLY the system prompt text. Do not explain, comment, or add any preamble. Start directly with "You are".""",

    CAT_SECTION_NUM: """You are a document control specialist in the pharmaceutical and engineering industry. You have deep expertise in how URS, FS, and technical specification documents are structured — specifically how section metadata, numbering hierarchies, and JSON chunk representations work in document intelligence pipelines.

Your job: write a system prompt that will be used by an LLM to find a section number from structured JSON document chunks. The system prompt must be precise about WHERE to look (metadata field vs content field), how to validate a section number (reasonable format, not a raw list number), and how to handle ambiguity or multiple matches. It must NOT just restate the query — it should encode real knowledge about how section numbers behave in these documents.

Output ONLY the system prompt text. Do not explain, comment, or add any preamble. Start directly with "You are".""",

    CAT_METADATA: """You are a technical documentation expert with deep experience in pharmaceutical, biotech, and engineering document standards (GMP, FDA, ISO). You know exactly how document metadata — titles, document numbers, equipment tags, revision numbers — is formatted, placed, and labelled in URS, SAT, IQ/OQ/PQ, and similar documents.

Your job: write a system prompt that will be used by an LLM to extract a specific metadata value from document text. The system prompt must tell the LLM what this field typically looks like, where it typically appears, what surrounding labels or prefixes to expect, and what NOT to confuse it with. It should reflect genuine domain knowledge — not just repeat the query.

Output ONLY the system prompt text. Do not explain, comment, or add any preamble. Start directly with "You are".""",

    CAT_GENERATIVE: """You are a GMP technical writer with extensive experience authoring pharmaceutical and engineering validation documents — SOPs, URS, IQ/OQ/PQ protocols, system descriptions, and operational procedures.

Your job: write a system prompt that will guide an LLM to draft a high-quality technical paragraph or document section. The system prompt must specify the appropriate tone (formal, GMP-compliant), what content elements to include based on the topic, how to use source document context faithfully without fabricating details, and what structure or length to target.

Output ONLY the system prompt text. Do not explain, comment, or add any preamble. Start directly with "You are".""",

    CAT_UNKNOWN: """You are an expert in pharmaceutical and engineering document intelligence pipelines. You have broad knowledge of document types, extraction patterns, and data structures used in GMP environments.

Your job: write a system prompt that will guide an LLM to answer a specific question from document chunks. The system prompt must be precise, imperative, and encode real understanding of how to find and return this type of information from technical documents.

Output ONLY the system prompt text. Do not explain, comment, or add any preamble. Start directly with "You are".""",
}


def build_meta_prompt(entry: dict, category: str, json_key: str | None) -> str:
    """
    Build the USER message for the LLM call.
    This tells the LLM what it needs to generate a system prompt FOR,
    with all optional context (hint, synonyms, doctypes) injected.
    The SYSTEM message (above) is what makes it reason from domain expertise.
    """
    ai_prompt   = entry.get("ai_prompt", "").strip()
    hint        = entry.get("hint", "").strip()
    synonyms    = entry.get("synonyms", [])
    doctypes    = entry.get("doctypes", "[]")
    placeholder = entry.get("placeholder", "")

    # Output format instruction — rule-based, not LLM-derived
    if json_key and category != CAT_GENERATIVE:
        output_format = (
            f'The system prompt MUST end with this exact output instruction (copy verbatim):\n'
            f'"Return ONLY valid JSON with no extra text, preamble, or markdown. '
            f'Use this exact format: {{ \\"{json_key}\\": \\"<value here>\\" }}. '
            f'If the topic is not found in the context, return {{ \\"{json_key}\\": \\"N/Ap\\" }}."'
        )
    elif category == CAT_GENERATIVE:
        output_format = (
            'The system prompt MUST end with this output instruction:\n'
            '"Return only the generated text, ready to be inserted directly into the document. '
            'Do not include headers, labels, or any meta-commentary."'
        )
    else:
        output_format = (
            'The system prompt MUST end with an instruction to return ONLY valid JSON '
            'with no preamble, markdown, or extra text.'
        )

    # Optional context blocks
    doctype_block = ""
    try:
        dt_list = json.loads(doctypes) if isinstance(doctypes, str) else doctypes
        if dt_list:
            doctype_block = f"\nDocument type(s) this will run on: {', '.join(dt_list)}."
    except Exception:
        pass

    synonym_block = ""
    if synonyms:
        terms = ", ".join(f'"{s}"' for s in synonyms)
        synonym_block = (
            f"\nThe user has provided these synonyms/alternate terms that should also be searched for: {terms}. "
            f"The system prompt must instruct the LLM to look for ALL of these terms."
        )

    hint_block = ""
    if hint:
        hint_block = (
            f"\nAdditional hint/note from the user: {hint}. "
            f"Incorporate this context intelligently into the system prompt."
        )

    meta_prompt = f"""Write a system prompt for an LLM that will process pharmaceutical/engineering document chunks to answer this query:

QUERY: "{ai_prompt}"
PLACEHOLDER: {placeholder}
TASK TYPE: {category.upper()}{doctype_block}{synonym_block}{hint_block}

Requirements for the system prompt you write:
- Open with "You are an expert at..." appropriate to this specific task
- Use your domain knowledge to expand on the query: explain WHERE this information typically appears in such documents, WHAT terminology or labelling conventions engineers/regulators use for it, and HOW to distinguish it from adjacent or similar content
- Be imperative and specific — use "Look for", "Extract", "Do NOT", "If you find", "Return"
- Do NOT just restate the query — the LLM reading this prompt must gain domain knowledge it wouldn't have otherwise
- Write as flowing prose paragraphs (no bullet points, no numbered lists, no headers inside the system prompt)
- Length: 4–6 sentences for metadata/section tasks, 6–10 sentences for requirement/generative tasks

{output_format}"""

    return meta_prompt


# ─────────────────────────────────────────────
# LLM CALLER
# ─────────────────────────────────────────────
def call_lm_studio(system_content: str, user_content: str) -> str:
    """Call LM Studio API and return the assistant's response text."""
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_content},
            {"role": "user",   "content": user_content},
        ],
        "max_tokens": MAX_TOKENS,
        "temperature": TEMPERATURE,
        "stream": False,
    }

    data = json.dumps(payload).encode("utf-8")
    req  = urllib.request.Request(
        LM_STUDIO_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result["choices"][0]["message"]["content"].strip()
    except urllib.error.URLError as e:
        raise ConnectionError(f"Cannot reach LM Studio at {LM_STUDIO_URL}: {e}") from e


def generate_system_prompt(entry: dict, category: str, json_key: str | None) -> str:
    """Build meta-prompt and call LLM to generate the system prompt."""
    meta_prompt   = build_meta_prompt(entry, category, json_key)
    generator_sys = GENERATOR_SYSTEM_BY_CATEGORY.get(category, GENERATOR_SYSTEM_BY_CATEGORY[CAT_UNKNOWN])
    result        = call_lm_studio(generator_sys, meta_prompt)
    # Strip any accidental markdown fences the LLM might add
    result = re.sub(r"^```[^\n]*\n?", "", result)
    result = re.sub(r"\n?```$", "", result)
    # Strip "Here is the system prompt:" style preamble
    result = re.sub(r"^(here is|here\'s|below is|the following is)[^\n]*\n+", "", result, flags=re.IGNORECASE)
    return result.strip()


# ─────────────────────────────────────────────
# MAIN PROCESSOR
# ─────────────────────────────────────────────
def process_file(
    input_path: str,
    output_path: str | None = None,
    dry_run: bool = False,
    force: bool = False,
    only_index: int | None = None,
):
    input_path  = Path(input_path)
    output_path = Path(output_path) if output_path else input_path

    print(f"\n{'─'*60}")
    print(f"  Prompt Generator")
    print(f"  Input  : {input_path}")
    print(f"  Output : {output_path}")
    print(f"  Mode   : {'DRY RUN (classify only)' if dry_run else 'GENERATE'}")
    print(f"  Model  : {MODEL_NAME}  @  {LM_STUDIO_URL}")
    print(f"{'─'*60}\n")

    with open(input_path, "r", encoding="utf-8") as f:
        entries = json.load(f)

    if not isinstance(entries, list):
        print("ERROR: JSON root must be a list of objects.")
        sys.exit(1)

    total     = len(entries)
    processed = 0
    skipped   = 0
    errors    = 0

    # Category counters
    cat_counts: dict[str, int] = {}

    for idx, entry in enumerate(entries):
        if only_index is not None and idx != only_index:
            continue

        placeholder = entry.get("placeholder", f"[entry_{idx}]")
        ai_prompt   = entry.get("ai_prompt", "").strip()

        category = classify(ai_prompt, placeholder)
        cat_counts[category] = cat_counts.get(category, 0) + 1

        # Derive output JSON key
        json_key = derive_json_key(placeholder, ai_prompt, category)

        existing_sp = entry.get("system_prompt", "").strip()
        has_existing = bool(existing_sp) and existing_sp.lower() not in ("nan", "none", "")

        status_tag = f"[{idx+1:3d}/{total}]"

        if category == CAT_SKIP:
            print(f"{status_tag} SKIP      {placeholder}")
            skipped += 1
            continue

        if category == CAT_IO_TABLE:
            print(f"{status_tag} IO_TABLE  {placeholder}  (no system_prompt needed)")
            skipped += 1
            continue

        if has_existing and not force:
            print(f"{status_tag} EXISTS    {placeholder}  → use --force to regenerate")
            skipped += 1
            continue

        print(f"{status_tag} {category.upper():12s}  {placeholder}")
        print(f"           ai_prompt : {ai_prompt[:90]}{'…' if len(ai_prompt)>90 else ''}")
        print(f"           json_key  : {json_key}")

        if dry_run:
            skipped += 1
            print()
            continue

        # Call LLM
        try:
            generated = generate_system_prompt(entry, category, json_key)
            entry["system_prompt"] = generated
            processed += 1
            preview = generated[:120].replace("\n", " ")
            print(f"           ✓ generated: {preview}…\n")
        except ConnectionError as e:
            print(f"           ✗ CONNECTION ERROR: {e}\n")
            errors += 1
        except Exception as e:
            print(f"           ✗ ERROR: {e}\n")
            errors += 1

        time.sleep(0.3)  # slight delay to avoid overwhelming local server

    # Save updated file
    if not dry_run and processed > 0:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2, ensure_ascii=False)
        print(f"\n✓ Saved {output_path}")

    print(f"\n{'─'*60}")
    print(f"  Summary")
    print(f"  Total entries : {total}")
    print(f"  Generated     : {processed}")
    print(f"  Skipped       : {skipped}")
    print(f"  Errors        : {errors}")
    print(f"\n  Category breakdown:")
    for cat, count in sorted(cat_counts.items()):
        print(f"    {cat:15s} : {count}")
    print(f"{'─'*60}\n")


# ─────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────
def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate system prompts for a JSON prompt library using a local LM Studio model.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python prompt_generator.py --input prompts.json
  python prompt_generator.py --input prompts.json --output results.json
  python prompt_generator.py --input prompts.json --dry-run
  python prompt_generator.py --input prompts.json --index 5
  python prompt_generator.py --input prompts.json --force
        """,
    )
    parser.add_argument("--input",   required=True, help="Path to input JSON file")
    parser.add_argument("--output",  default=None,  help="Output path (default: overwrite input)")
    parser.add_argument("--dry-run", action="store_true", help="Classify only — do not call LLM")
    parser.add_argument("--force",   action="store_true", help="Regenerate even if system_prompt already exists")
    parser.add_argument("--index",   type=int, default=None, help="Process only entry at this index (0-based)")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    process_file(
        input_path=args.input,
        output_path=args.output,
        dry_run=args.dry_run,
        force=args.force,
        only_index=args.index,
    )