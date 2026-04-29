# MumzLens 🔍
### Stage-Aware Review Intelligence for Mumzworld

---

## What problem does this solve?

While browsing [mumzworld.com](https://mumzworld.com), I noticed something: the Lansinoh Nipple Cream has 730 reviews and the Pigeon Softouch bottle has 194. But there is no way to filter them by who you are.

A 34-week pregnant first-time mom and a pumping mom of a 6-month-old are reading the exact same wall of text. A toddler mom looking at a baby carrier sees infant reviews. A new mom looking at a high chair sees toddler reviews. The information exists — but it is completely undifferentiated.

**MumzLens** fixes this. You tell the system your stage — pregnant, new mumz, or toddler mumz — and it filters the review corpus semantically, then synthesizes a verdict specifically for moms like you. In English, Arabic, or both.

---

## Setup and Run (under 5 minutes)

### 1. Clone and install

```bash
git clone https://github.com/manunaik111/mumzlens.git
cd mumzlens
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux
pip install -r requirements.txt
```

### 2. Add your OpenRouter key

Create a `.env` file in the root:

```env
OPENROUTER_API_KEY=sk-or-v1-your-key-here
```

Get a free key at [openrouter.ai](https://openrouter.ai). No payment required.

### 3. Run the Streamlit app

```bash
streamlit run app.py
```

Opens at `http://localhost:8501`

### 4. Or run the FastAPI backend

```bash
uvicorn src.api:app --reload
```

API docs at `http://localhost:8000/docs`

### 5. Example API call

```bash
curl -X POST http://localhost:8000/verdict \
  -H "Content-Type: application/json" \
  -d '{
    "product_name": "Mustela Gentle Cleansing Gel",
    "stage": "new_mumz",
    "language": "both",
    "reviews": [
      "My newborn has really sensitive skin and this gel has been a lifesaver.",
      "The NICU nurse recommended Mustela specifically for sensitive newborn skin.",
      "My baby had eczema flares. Dermatologist suggested Mustela and it helped within two weeks."
    ]
  }'
```

---

## Architecture

```
User Input (product + stage + reviews)
        │
        ▼
┌─────────────────────────────┐
│  Sentence Transformer       │  ← all-MiniLM-L6-v2 (free, local)
│  Semantic Stage Filter      │  ← cosine similarity vs stage context
└─────────────────────────────┘
        │  relevant reviews only
        ▼
┌─────────────────────────────┐
│  Prompt Builder             │  ← stage label + language instruction
│  + LLM via OpenRouter       │  ← Llama 3.3 70B (free tier)
└─────────────────────────────┘
        │  raw JSON
        ▼
┌─────────────────────────────┐
│  Pydantic Validator         │  ← schema enforcement
│  + Fallback on parse error  │  ← explicit error, never silent fail
└─────────────────────────────┘
        │
        ▼
   MumzLensResponse
   (verdict EN/AR, confidence, uncertainty_flags, grounded)
```

### Why this architecture

- **Embeddings before LLM**: Sending all 150 reviews to the LLM every time would be expensive and noisy. The semantic filter ensures the LLM only sees reviews relevant to the requested stage. This also reduces hallucination surface.
- **Llama 3.3 70B via OpenRouter**: Free tier, strong multilingual capability, and good instruction following for JSON output. Tested against Qwen and Llama — Llama 3.3 70B produced the most consistent JSON and best Arabic.
- **Pydantic validation**: The model is explicitly told to return null rather than fabricate. The validator enforces the schema. Any JSON parse failure returns a structured error response — it never silently passes malformed output.
- **`grounded` field**: If reviews do not support the verdict, this is set to false. The system does not pad output with generic claims.

---

## Evals

See `EVALS.md` for full rubric, 12 test cases, scores, and honest failure analysis.

---

## Tradeoffs

See `TRADEOFFS.md` for problem selection rationale, model choice, what was cut, and what comes next.

---

## Tooling

| Tool | Role |
|------|------|
| Claude (claude.ai) | Problem scoping, architecture design, initial code structure |
| OpenRouter + Llama 3.3 70B | LLM inference for synthesis — free tier |
| sentence-transformers (all-MiniLM-L6-v2) | Local embedding model for semantic stage filtering |
| FastAPI | REST API layer |
| Streamlit | Demo UI |
| Pydantic v2 | Output schema validation |
| Python-dotenv | API key management |

**How AI tools were used:**
- Architecture and problem framing: reasoned through with Claude in conversation
- Code: written and iterated manually, with Claude used for review and edge case identification
- Prompt engineering: iterated manually — the system prompt went through 4 versions before JSON output became consistent
- Evals: test cases written manually based on real failure modes observed during testing

**What did not work:**
- First version sent all reviews to the LLM without filtering — output was generic and not stage-specific
- Early prompts without explicit null instructions caused the model to fill empty fields with placeholder strings
- Qwen 2.5 72B produced less consistent JSON structure than Llama 3.3 70B

**Where I stepped in:**
- The relevance threshold (0.35 cosine similarity) was tuned manually after observing that the default was too strict for short reviews
- Arabic prompt instruction was rewritten after the first version produced Arabic that read like a direct translation

---

## Time log

| Phase | Time |
|-------|------|
| Problem discovery and scoping | 45 min |
| Data generation (synthetic reviews) | 30 min |
| Core pipeline (embeddings + LLM) | 90 min |
| FastAPI + Streamlit UI | 60 min |
| Prompt iteration and testing | 45 min |
| Evals + README | 30 min |
| **Total** | **~5 hours** |