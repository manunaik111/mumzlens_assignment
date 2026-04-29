from pydantic import BaseModel, Field, field_validator
from typing import Optional
from enum import Enum


class Stage(str, Enum):
    pregnant = "pregnant"
    new_mumz = "new_mumz"
    toddler_mumz = "toddler_mumz"


class Language(str, Enum):
    en = "en"
    ar = "ar"
    both = "both"


class MumzLensRequest(BaseModel):
    product_name: str = Field(..., min_length=2)
    stage: Stage
    language: Language = Language.both
    reviews: list[str] = Field(..., min_length=1)

    @field_validator("reviews")
    @classmethod
    def reviews_not_empty(cls, v):
        cleaned = [r.strip() for r in v if r.strip()]
        if not cleaned:
            raise ValueError("Reviews list cannot be all empty strings.")
        return cleaned


class StageVerdict(BaseModel):
    verdict_en: Optional[str] = Field(
        None, description="English verdict for this stage. Null if not enough data."
    )
    verdict_ar: Optional[str] = Field(
        None, description="Arabic verdict for this stage. Null if not enough data."
    )
    pros_en: list[str] = Field(default_factory=list)
    cons_en: list[str] = Field(default_factory=list)
    pros_ar: list[str] = Field(default_factory=list)
    cons_ar: list[str] = Field(default_factory=list)
    relevant_review_count: int = Field(
        ..., description="How many reviews were relevant to this stage."
    )
    confidence_score: float = Field(
        ..., ge=0.0, le=1.0,
        description="0.0 = no usable data, 1.0 = high confidence verdict."
    )
    uncertainty_flags: list[str] = Field(
        default_factory=list,
        description="Explicit list of what the model is uncertain about."
    )
    insufficient_data: bool = Field(
        False,
        description="True when fewer than 3 relevant reviews exist for this stage."
    )


class MumzLensResponse(BaseModel):
    product_name: str
    stage: Stage
    language: Language
    total_reviews_analyzed: int
    stage_verdict: StageVerdict
    top_themes: list[str] = Field(
        default_factory=list,
        description="Key themes that appear across reviews for this stage."
    )
    grounded: bool = Field(
        True,
        description="False if output could not be grounded in the provided reviews."
    )
    error: Optional[str] = Field(
        None,
        description="Set if the request could not be processed. All other fields may be null."
    )