from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import traceback

from app.database import get_db
from app.models import PromptRecord
from app.schemas import (
    GeneratePromptRequest,
    SavePromptRequest,
    PromptRecordResponse,
)
from app.services.prompt_generator import generate_prompts
from app.services.prompt_validator import validate_generated_prompt

router = APIRouter(prefix="/api", tags=["Prompt Generator"])


@router.post("/generate")
def generate_prompt(payload: GeneratePromptRequest):
    try:
        result = generate_prompts(payload)
        validation = validate_generated_prompt(result, payload.document_types)

        response_payload = {
            "prompt_type": result.get("prompt_type"),
            "placeholder_name": result.get("placeholder_name"),
            "extraction_family": result.get("extraction_family"),
            "output_key": result.get("output_key"),
            "special_tags": result.get("special_tags", []),
            "chunk_count": str(result.get("chunk_count", "")),
            "ai_prompt": result.get("ai_prompt"),
            "system_prompt": result.get("system_prompt"),
            "column_header": result.get("column_header"),
            "filters_logic": result.get("filters_logic"),
            "synonyms_logic": result.get("synonyms_logic"),
            "grouping_logic": result.get("grouping_logic"),
            "final_prompt_text": result.get("final_prompt_text", ""),
            "validation": {
                "status": validation.get("status", "invalid"),
                "issues": validation.get("issues", []),
            },
        }

        return JSONResponse(content=response_payload)

    except Exception as e:
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"detail": f"Prompt generation failed: {str(e)}"}
        )


@router.post("/save")
def save_prompt(payload: SavePromptRequest, db: Session = Depends(get_db)):
    try:
        record = PromptRecord(
            placeholder_name=payload.placeholder_name,
            prompt_type=payload.prompt_type,
            requirement_text=payload.requirement_text,
            extraction_family=payload.extraction_family,
            output_key=payload.output_key,
            special_tags=",".join(payload.special_tags),
            document_types=",".join(payload.document_types),
            chunk_count=payload.chunk_count,
            ai_prompt=payload.ai_prompt,
            system_prompt=payload.system_prompt,
            column_header=payload.column_header,
            filters_logic=payload.filters_logic,
            synonyms_logic=payload.synonyms_logic,
            grouping_logic=payload.grouping_logic,
            final_prompt_text=payload.final_prompt_text,
            validation_status=payload.validation_status,
            validation_issues="\n".join(payload.validation_issues) if payload.validation_issues else None,
        )

        db.add(record)
        db.commit()
        db.refresh(record)

        return {"message": "Saved successfully", "id": record.id}

    except Exception as e:
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"detail": f"Save failed: {str(e)}"}
        )


@router.get("/prompts", response_model=list[PromptRecordResponse])
def list_prompts(db: Session = Depends(get_db)):
    try:
        return db.query(PromptRecord).order_by(PromptRecord.id.desc()).all()

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Fetch failed: {str(e)}"
        )