from sqlalchemy import Column, Integer, String, Text, DateTime, func
from app.database import Base


class PromptRecord(Base):
    __tablename__ = "prompts"

    id = Column(Integer, primary_key=True, index=True)
    placeholder_name = Column(String(255), nullable=False, index=True)
    prompt_type = Column(String(100), nullable=False)
    requirement_text = Column(Text, nullable=True)

    extraction_family = Column(String(100), nullable=True)
    output_key = Column(String(100), nullable=True)
    special_tags = Column(String(255), nullable=True)
    document_types = Column(String(255), nullable=True)
    chunk_count = Column(String(50), nullable=True)

    ai_prompt = Column(Text, nullable=True)
    system_prompt = Column(Text, nullable=True)

    column_header = Column(Text, nullable=True)
    filters_logic = Column(Text, nullable=True)
    synonyms_logic = Column(Text, nullable=True)
    grouping_logic = Column(Text, nullable=True)
    final_prompt_text = Column(Text, nullable=False)

    validation_status = Column(String(50), default="valid")
    validation_issues = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())