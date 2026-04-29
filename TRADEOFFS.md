# TRADEOFFS.md — MumzLens Design Decisions

---

## Why this problem

While browsing mumzworld.com I noticed every product page shows a flat list of reviews with no stage filtering. Lansinoh Nipple Cream has 730 reviews. A pregnant mom planning to breastfeed and a pumping mom of a 6-month-old are reading the same wall of text. The information to help each of them exists — it is just completely undifferentiated.

The other listed examples I considered and rejected:

| Example | Why I rejected it |
|---------|------------------|
| Moms Verdict synthesizer | Listed directly in the brief — every candidate will build this |
| Gift finder | Interesting but requires product catalog access I do not have |
| Return reason classifier | More of an ops tool — lower customer impact |
| CS email triage | No email data and less differentiated technically |

**Why MumzLens beats the listed options:**
- It is a novel angle that came from actually using the site
- It hits every technical requirement: RAG, structured output, multilingual, evals, uncertainty handling
- It is genuinely useful — the problem exists right now on mumzworld.com

---

## Model choice

**Chosen: Llama 3.3 70B via OpenRouter (free tier)**

I tested three models before settling:

| Model | JSON consistency | Arabic quality | Speed |
|-------|-----------------|----------------|-------|
| Llama 3.3 70B | ✅ High | ✅ Good | ✅ Fast |
| Qwen 2.5 72B | ⚠️ Occasional schema drift | ✅ Good | ✅ Fast |
| DeepSeek V3 | ✅ High | ⚠️ Sometimes stilted | ✅ Fast |

Llama 3.3 70B produced the most consistently valid JSON across all test cases and the most natural Arabic output. All three are free on OpenRouter.

**Temperature: 0.3**  
Lower temperature reduces creativity but improves JSON reliability and factual grounding. For a synthesis tool that must not hallucinate, this is the right tradeoff.

---

## Architecture tradeoffs

### Embeddings before LLM (chosen)
Sending all reviews to the LLM without filtering would:
- Dilute the stage signal — the LLM would average across all stages
- Increase token usage and latency
- Increase hallucination surface

The semantic filter (cosine similarity ≥ 0.35) ensures only stage-relevant reviews reach the LLM. This is the core architectural decision that makes the stage-awareness real rather than cosmetic.

### Local embeddings vs. API embeddings
I chose `all-MiniLM-L6-v2` (runs locally, free, fast) over OpenAI embeddings (paid) or OpenRouter embeddings (rate limited). For a prototype this is the right call. In production you would use a multilingual model like `paraphrase-multilingual-MiniLM-L12-v2` to handle Arabic reviews better.

### Pydantic validation (chosen)
Every output field is typed. Failures are explicit — the response always has an `error` field and `grounded: false` rather than silently passing bad output. This was non-negotiable given the brief's explicit call-out of "malformed JSON" and "silent failures" as bad outcomes.

---

## What I cut

| Feature | Why cut |
|---------|---------|
| Real-time Mumzworld scraping | Brief explicitly prohibits scraping retailer sites |
| Multilingual embedding model | `paraphrase-multilingual-MiniLM-L12-v2` is better for Arabic but slower to load. Tradeoff against 5-hour constraint. |
| User account / history | Out of scope for prototype |
| Product image input (multimodal) | Would have required a vision model — added complexity without adding to the core problem |
| Streaming responses | Streamlit supports it but adds complexity. Spinner is sufficient for prototype. |
| Fine-tuning | No labelled dataset available in this timeframe |

---

## What I would build next

1. **Multilingual embeddings** — swap `all-MiniLM-L6-v2` for `paraphrase-multilingual-MiniLM-L12-v2` so Arabic reviews score correctly against Arabic stage contexts.

2. **Real review ingestion** — connect to Mumzworld's product review API (if available) so the system works on live data rather than synthetic reviews.

3. **Sub-stage filtering** — within new_mumz, distinguish 0-3 months from 3-12 months. A mom at 2 weeks postpartum and a mom at 10 months have very different questions.

4. **Human eval loop for Arabic quality** — automated evals cannot fully assess native Arabic naturalness. A native-speaker review step would be essential before production.

5. **Confidence calibration** — current confidence scores are LLM-generated. Calibrate them against human judgements to make them meaningful rather than approximate.

---

## Uncertainty handling design

The system handles uncertainty at three levels:

**Level 1 — Input validation (Pydantic)**  
Empty reviews, missing product name, invalid stage → explicit error before LLM is called.

**Level 2 — Semantic filter**  
If fewer than 3 reviews pass the relevance threshold, `insufficient_data: true` is set and the user sees a warning in the UI. The verdict is still returned but clearly flagged as low-confidence.

**Level 3 — LLM instruction**  
The system prompt explicitly instructs the model to set fields to null rather than fabricate, and to populate `uncertainty_flags` with specific named uncertainties. This is reinforced by the prompt structure which asks for `confidence_score` as a number the model must justify with review evidence.

The design principle: **uncertainty is surfaced, never hidden.**