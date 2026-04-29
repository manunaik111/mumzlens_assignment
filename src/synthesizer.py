import json
import os
import re

from dotenv import load_dotenv
from openai import APIError, OpenAI, RateLimitError

from src.schemas import Language, MumzLensRequest, MumzLensResponse, Stage, StageVerdict

load_dotenv()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "openai/gpt-oss-120b:free"
DEFAULT_FALLBACK_MODELS = [
    "qwen/qwen3-next-80b-a3b-instruct:free",
    "google/gemma-3-27b-it:free",
    "minimax/minimax-m2.5:free",
]
MIN_REVIEWS_FOR_CONFIDENCE = 3
RELEVANCE_THRESHOLD = 0.30

# Stage keywords used for lightweight filtering.
STAGE_KEYWORDS = {
    Stage.pregnant: [
        "pregnant",
        "pregnancy",
        "expecting",
        "antenatal",
        "hospital bag",
        "trimester",
        "before birth",
        "pre-baby",
        "due date",
        "bought before",
        "prepared",
        "preparing",
        "delivery",
        "birth",
        "unborn",
    ],
    Stage.new_mumz: [
        "newborn",
        "breastfeeding",
        "breastfed",
        "formula",
        "pumping",
        "pump",
        "nipple",
        "latch",
        "postpartum",
        "colic",
        "newborn",
        "infant",
        "0 months",
        "1 month",
        "2 months",
        "3 months",
        "4 months",
        "5 months",
        "6 months",
        "sleep deprivation",
        "night feed",
        "night waking",
        "new born",
        "new baby",
        "first baby",
        "nicu",
        "preemie",
        "week old",
        "month old",
        "new mum",
        "new mom",
        "just had",
        "just delivered",
        "after birth",
        "postpartum",
        "c-section",
        "cesarean",
        "recovery",
    ],
    Stage.toddler_mumz: [
        "toddler",
        "1 year",
        "2 year",
        "18 months",
        "walking",
        "crawler",
        "weaning",
        "solid",
        "baby led",
        "blw",
        "older baby",
        "preschool",
        "tantrum",
        "independent",
        "active",
        "running",
        "climbing",
        "year old",
        "years old",
        "months old",
    ],
}


# ---------------------------------------------------------------------------
# Lightweight keyword-based stage relevance scoring
# ---------------------------------------------------------------------------

def score_review_for_stage(review: str, stage: Stage) -> float:
    """
    Returns a relevance score 0.0-1.0 based on keyword overlap.
    Higher means more relevant to that stage.
    """
    text = review.lower()
    keywords = STAGE_KEYWORDS[stage]
    matches = sum(1 for kw in keywords if kw in text)
    return min(matches / 3.0, 1.0)


def filter_reviews_by_stage(reviews: list[str], stage: Stage) -> tuple[list[str], int]:
    """
    Returns (relevant_reviews, total_count).
    Falls back to top 5 scored reviews if too few pass the threshold.
    """
    scores = [(review, score_review_for_stage(review, stage)) for review in reviews]
    relevant = [review for review, score in scores if score >= RELEVANCE_THRESHOLD]

    if (
        len(relevant) < MIN_REVIEWS_FOR_CONFIDENCE
        and len(reviews) >= MIN_REVIEWS_FOR_CONFIDENCE
    ):
        sorted_reviews = sorted(scores, key=lambda item: item[1], reverse=True)
        relevant = [review for review, _score in sorted_reviews[:5]]

    return relevant, len(reviews)


# ---------------------------------------------------------------------------
# LLM call via OpenRouter
# ---------------------------------------------------------------------------

def call_llm(system_prompt: str, user_prompt: str) -> str:
    primary_model = os.getenv("OPENROUTER_MODEL", DEFAULT_MODEL).strip()
    fallback_models_raw = os.getenv(
        "OPENROUTER_FALLBACK_MODELS",
        ",".join(DEFAULT_FALLBACK_MODELS),
    )
    fallback_models = [
        model.strip()
        for model in fallback_models_raw.split(",")
        if model.strip() and model.strip() != primary_model
    ]

    client = OpenAI(
        api_key=os.getenv("OPENROUTER_API_KEY"),
        base_url=OPENROUTER_BASE_URL,
    )
    response = client.chat.completions.create(
        model=primary_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
        max_tokens=1500,
        extra_body={"models": fallback_models} if fallback_models else None,
    )
    return response.choices[0].message.content.strip()


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are MumzLens, a review intelligence engine for Mumzworld,
the largest e-commerce platform for mothers in the Middle East.

Your job: given a set of product reviews and a mother's life stage,
synthesize an honest, grounded verdict that tells her exactly what moms
like her experienced with this product.

Rules you must follow without exception:
1. Only use information present in the provided reviews. Do not invent facts.
2. If the reviews do not contain enough information to answer confidently, say so explicitly.
3. Arabic output must read as natural native Arabic - never translate from English word for word.
4. Return ONLY valid JSON. No preamble, no markdown fences, no explanation outside the JSON.
5. If a field cannot be filled from the reviews, set it to null or an empty list. Never fabricate.
6. confidence_score must reflect actual review evidence:
   - 0.0-0.3: very few or contradictory reviews
   - 0.4-0.6: moderate evidence with some uncertainty
   - 0.7-1.0: strong consistent evidence from multiple reviews
7. insufficient_data must be true if fewer than 3 reviews were relevant to this stage.
"""


def build_user_prompt(
    product_name: str,
    stage: Stage,
    language: Language,
    relevant_reviews: list[str],
    total_reviews: int,
) -> str:
    stage_labels = {
        Stage.pregnant: "Pregnant (buying before birth)",
        Stage.new_mumz: "New Mumz (newborn to 12 months)",
        Stage.toddler_mumz: "Toddler Mumz (1-3 years)",
    }

    lang_instruction = {
        Language.en: (
            "Provide verdict_en, pros_en, cons_en only. "
            "Set verdict_ar, pros_ar, cons_ar to null/empty."
        ),
        Language.ar: (
            "Provide verdict_ar, pros_ar, cons_ar only. "
            "Set verdict_en, pros_en, cons_en to null/empty."
        ),
        Language.both: "Provide all fields in both English and Arabic.",
    }

    review_block = "\n".join(
        f"[Review {i + 1}]: {review}" for i, review in enumerate(relevant_reviews)
    )
    insufficient = len(relevant_reviews) < MIN_REVIEWS_FOR_CONFIDENCE

    return f"""Product: {product_name}
Mother's Stage: {stage_labels[stage]}
Language instruction: {lang_instruction[language]}
Total reviews in database: {total_reviews}
Reviews relevant to this stage: {len(relevant_reviews)}
Insufficient data flag should be: {str(insufficient).lower()}

--- RELEVANT REVIEWS ---
{review_block if relevant_reviews else "No reviews found for this stage."}
--- END REVIEWS ---

Return a JSON object with exactly these fields:
{{
  "verdict_en": "2-3 sentence honest verdict in English, or null",
  "verdict_ar": "2-3 sentence honest verdict in natural Arabic, or null",
  "pros_en": ["up to 4 pros from review evidence"],
  "cons_en": ["up to 4 cons from review evidence"],
  "pros_ar": ["same pros in natural Arabic"],
  "cons_ar": ["same cons in natural Arabic"],
  "relevant_review_count": {len(relevant_reviews)},
  "confidence_score": 0.0,
  "uncertainty_flags": ["list any specific things you are uncertain about"],
  "insufficient_data": {str(insufficient).lower()},
  "top_themes": ["up to 5 themes that appear across these reviews"]
}}

Be honest. If you are not sure about something, add it to uncertainty_flags.
If there are no reviews, set verdict to null and confidence_score to 0.0.
"""


def build_error_response(
    request: MumzLensRequest,
    total_count: int,
    relevant_reviews: list[str],
    error_message: str,
    uncertainty_flag: str,
) -> MumzLensResponse:
    return MumzLensResponse(
        product_name=request.product_name,
        stage=request.stage,
        language=request.language,
        total_reviews_analyzed=total_count,
        stage_verdict=StageVerdict(
            relevant_review_count=len(relevant_reviews),
            confidence_score=0.0,
            insufficient_data=True,
            uncertainty_flags=[uncertainty_flag],
        ),
        grounded=False,
        error=error_message,
    )


# ---------------------------------------------------------------------------
# Main synthesis entry point
# ---------------------------------------------------------------------------

def synthesize(request: MumzLensRequest) -> MumzLensResponse:
    relevant_reviews, total_count = filter_reviews_by_stage(
        request.reviews, request.stage
    )

    user_prompt = build_user_prompt(
        product_name=request.product_name,
        stage=request.stage,
        language=request.language,
        relevant_reviews=relevant_reviews,
        total_reviews=total_count,
    )

    try:
        raw_output = call_llm(SYSTEM_PROMPT, user_prompt)
    except RateLimitError:
        return build_error_response(
            request=request,
            total_count=total_count,
            relevant_reviews=relevant_reviews,
            error_message=(
                "The OpenRouter provider for the selected free model is temporarily "
                "rate-limited. Please retry shortly or switch to another model/provider."
            ),
            uncertainty_flag="Upstream model provider returned a 429 rate limit.",
        )
    except APIError as exc:
        return build_error_response(
            request=request,
            total_count=total_count,
            relevant_reviews=relevant_reviews,
            error_message=f"OpenRouter request failed: {exc}",
            uncertainty_flag="Upstream model provider request failed.",
        )

    try:
        cleaned = raw_output.strip()
        cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        return build_error_response(
            request=request,
            total_count=total_count,
            relevant_reviews=relevant_reviews,
            error_message="LLM output could not be parsed as JSON.",
            uncertainty_flag="LLM returned malformed JSON and could not be parsed.",
        )

    verdict = StageVerdict(
        verdict_en=parsed.get("verdict_en"),
        verdict_ar=parsed.get("verdict_ar"),
        pros_en=parsed.get("pros_en") or [],
        cons_en=parsed.get("cons_en") or [],
        pros_ar=parsed.get("pros_ar") or [],
        cons_ar=parsed.get("cons_ar") or [],
        relevant_review_count=parsed.get(
            "relevant_review_count", len(relevant_reviews)
        ),
        confidence_score=float(parsed.get("confidence_score", 0.0)),
        uncertainty_flags=parsed.get("uncertainty_flags") or [],
        insufficient_data=parsed.get(
            "insufficient_data",
            len(relevant_reviews) < MIN_REVIEWS_FOR_CONFIDENCE,
        ),
    )

    return MumzLensResponse(
        product_name=request.product_name,
        stage=request.stage,
        language=request.language,
        total_reviews_analyzed=total_count,
        stage_verdict=verdict,
        top_themes=parsed.get("top_themes") or [],
        grounded=True,
        error=None,
    )
