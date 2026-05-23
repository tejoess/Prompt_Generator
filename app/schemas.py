from typing import List, Optional
from pydantic import BaseModel, Field


class GeneratePromptRequest(BaseModel):
    prompt_type: str = Field(..., min_length=1)
    placeholder_name: str = Field(..., min_length=1)

    requirement_text: Optional[str] = None
    document_types: List[str] = []
    expected_json_key: Optional[str] = "answer"
    chunk_count: Optional[int] = 8

    use_metadata_tag: bool = False
    use_tabular_tag: bool = False
    use_section_number_tag: bool = False

    # table placeholder mode
    column_header: Optional[str] = None
    filter_column: Optional[str] = None
    filter_value: Optional[str] = None
    table_header: Optional[str] = None
    exclude_table_header: Optional[str] = None
    use_wildcard_match: bool = False
    use_not_equals: bool = False
    synonyms_csv: Optional[str] = None
    grouping_placeholders_csv: Optional[str] = None

    # AI-over-table
    table_target_instruction: Optional[str] = None

    # drawing
    drawing_target_field: Optional[str] = None


class ValidationResult(BaseModel):
    status: str
    issues: List[str]


class GeneratePromptResponse(BaseModel):
    prompt_type: str
    placeholder_name: str
    extraction_family: Optional[str] = None
    output_key: Optional[str] = None
    special_tags: List[str] = []
    chunk_count: str

    ai_prompt: Optional[str] = None
    system_prompt: Optional[str] = None
    column_header: Optional[str] = None
    filters_logic: Optional[str] = None
    synonyms_logic: Optional[str] = None
    grouping_logic: Optional[str] = None
    final_prompt_text: str

    validation: ValidationResult


class SavePromptRequest(BaseModel):
    prompt_type: str
    placeholder_name: str
    requirement_text: Optional[str] = None
    extraction_family: Optional[str] = None
    output_key: Optional[str] = None
    special_tags: List[str] = []
    document_types: List[str] = []
    chunk_count: str

    ai_prompt: Optional[str] = None
    system_prompt: Optional[str] = None
    column_header: Optional[str] = None
    filters_logic: Optional[str] = None
    synonyms_logic: Optional[str] = None
    grouping_logic: Optional[str] = None
    final_prompt_text: str

    validation_status: str
    validation_issues: List[str]


class PromptRecordResponse(BaseModel):
    id: int
    placeholder_name: str
    prompt_type: str
    requirement_text: Optional[str]
    extraction_family: Optional[str]
    output_key: Optional[str]
    special_tags: Optional[str]
    document_types: Optional[str]
    chunk_count: Optional[str]

    ai_prompt: Optional[str]
    system_prompt: Optional[str]
    column_header: Optional[str]
    filters_logic: Optional[str]
    synonyms_logic: Optional[str]
    grouping_logic: Optional[str]
    final_prompt_text: str

    validation_status: str
    validation_issues: Optional[str]

    class Config:
        from_attributes = True