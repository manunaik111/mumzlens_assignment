# EVALS.md — MumzLens Evaluation Report

---

## Rubric

Each test case is scored across 5 dimensions:

| Dimension | What it checks |
|-----------|---------------|
| **Grounding** | Output is supported by review text. No invented facts. |
| **Uncertainty honesty** | Model says "I don't know" or flags uncertainty when evidence is weak. |
| **Schema validity** | JSON output validates against Pydantic schema. No empty-string padding. |
| **Multilingual quality** | Arabic reads as natural native copy, not a translation. |
| **Stage relevance** | Verdict is specific to the requested stage, not generic across all reviews. |

Each dimension scored: ✅ Pass / ⚠️ Partial / ❌ Fail

---

## Test Cases and Results

---

### TC01 — Strong signal: new mumz breastfeeding product
**Type:** Easy  
**Product:** Lansinoh HPA Lanolin Nipple Cream | **Stage:** new_mumz | **Language:** both

**What I expected:** High confidence verdict, both languages populated, pros/cons grounded in review text.

**Result:**

| Dimension | Score | Notes |
|-----------|-------|-------|
| Grounding | ✅ | Verdict referenced cracking, healing time, pump use — all in reviews |
| Uncertainty | ✅ | No false flags; model was appropriately confident |
| Schema | ✅ | All fields populated, JSON valid |
| Arabic quality | ✅ | Native-reading Arabic, not translated |
| Stage relevance | ✅ | Verdict focused on breastfeeding and newborn feeding — correct for stage |

**Confidence score returned:** 0.82  
**Verdict (EN):** *"For breastfeeding and pumping moms in the newborn stage, this cream consistently delivered fast relief from soreness and cracking. Multiple moms reported healing within 48 hours and noted it does not need to be removed before feeding — a key practical advantage."*  
**Overall:** ✅ Pass

---

### TC02 — Stage mismatch: toddler product asked as pregnant
**Type:** Adversarial  
**Product:** Graco Slim Spaces High Chair | **Stage:** pregnant | **Language:** en

**What I expected:** Low confidence or insufficient_data flag, since high chair reviews are almost entirely from toddler moms.

**Result:**

| Dimension | Score | Notes |
|-----------|-------|-------|
| Grounding | ✅ | Only referenced the 1 pregnant review available |
| Uncertainty | ✅ | insufficient_data: true, confidence 0.28 |
| Schema | ✅ | Valid JSON |
| Arabic quality | N/A | EN only requested |
| Stage relevance | ✅ | Correctly identified thin evidence for pregnant stage |

**Confidence score returned:** 0.28  
**Uncertainty flags:** ["Only 1 review found for pregnant stage — verdict has very limited evidence"]  
**Overall:** ✅ Pass

---

### TC03 — Empty reviews list
**Type:** Adversarial  
**Input:** Empty reviews array

**What I expected:** Pydantic validation error before LLM is even called. No hallucination.

**Result:**

| Dimension | Score | Notes |
|-----------|-------|-------|
| Grounding | ✅ | Never reached LLM |
| Uncertainty | ✅ | Explicit validation error returned |
| Schema | ✅ | Error field populated, all other fields null |
| Arabic quality | N/A | |
| Stage relevance | N/A | |

**Error returned:** `"Reviews list cannot be empty."`  
**Overall:** ✅ Pass

---

### TC04 — Single review only
**Type:** Adversarial  
**Input:** 1 review | **Stage:** new_mumz | **Language:** en

**What I expected:** insufficient_data: true, low confidence, verdict present but flagged.

**Result:**

| Dimension | Score | Notes |
|-----------|-------|-------|
| Grounding | ✅ | Verdict stayed within the single review's claims |
| Uncertainty | ✅ | insufficient_data: true, confidence 0.22 |
| Schema | ✅ | Valid |
| Arabic quality | N/A | |
| Stage relevance | ⚠️ | Verdict was slightly generic — hard to be stage-specific with 1 review |

**Confidence score returned:** 0.22  
**Overall:** ✅ Pass (with note)

---

### TC05 — Arabic-only reviews, English output requested
**Type:** Easy  
**Input:** 3 Arabic reviews | **Stage:** new_mumz | **Language:** en

**What I expected:** English verdict synthesized from Arabic source reviews. verdict_ar null.

**Result:**

| Dimension | Score | Notes |
|-----------|-------|-------|
| Grounding | ✅ | English verdict correctly captured ideas from Arabic reviews |
| Uncertainty | ✅ | No false flags |
| Schema | ✅ | verdict_ar null as instructed |
| Arabic quality | N/A | Output was English |
| Stage relevance | ✅ | Breastfeeding / bottle acceptance covered correctly |

**Overall:** ✅ Pass

---

### TC06 — Contradictory reviews: mixed acceptance signal
**Type:** Adversarial  
**Product:** Tommee Tippee | **Stage:** new_mumz | **Language:** en  
**Input:** 5 reviews — half positive, half rejection

**What I expected:** Uncertainty flags present, confidence moderate, cons include "acceptance varies by baby."

**Result:**

| Dimension | Score | Notes |
|-----------|-------|-------|
| Grounding | ✅ | Verdict acknowledged both sides |
| Uncertainty | ✅ | uncertainty_flags: ["Highly variable acceptance — some babies take it immediately, others refuse"] |
| Schema | ✅ | Valid |
| Arabic quality | N/A | |
| Stage relevance | ✅ | Correct focus on breastfeeding compatibility |

**Confidence score returned:** 0.51  
**Overall:** ✅ Pass

---

### TC07 — Toddler stage: product with toddler signal
**Type:** Easy  
**Product:** Hatch Rest Sound Machine | **Stage:** toddler_mumz | **Language:** both

**What I expected:** Confident verdict mentioning ok-to-wake clock feature — a toddler-specific use case from the reviews.

**Result:**

| Dimension | Score | Notes |
|-----------|-------|-------|
| Grounding | ✅ | Ok-to-wake clock mentioned correctly in verdict |
| Uncertainty | ✅ | Appropriate confidence |
| Schema | ✅ | Both languages populated |
| Arabic quality | ✅ | Arabic verdict natural and readable |
| Stage relevance | ✅ | Focused on toddler sleep training, not newborn white noise |

**Confidence score returned:** 0.76  
**Overall:** ✅ Pass

---

### TC08 — Spam / low-quality reviews only
**Type:** Adversarial  
**Input:** 5 reviews all under 5 words ("Great!!!", "Love it", "5 stars")

**What I expected:** Low confidence, uncertainty flags about review quality, no fabricated specifics.

**Result:**

| Dimension | Score | Notes |
|-----------|-------|-------|
| Grounding | ⚠️ | Verdict was vague but did not invent specifics — acceptable |
| Uncertainty | ✅ | uncertainty_flags: ["Reviews are too short to extract meaningful product-specific insights"] |
| Schema | ✅ | Valid |
| Arabic quality | N/A | |
| Stage relevance | ⚠️ | Could not determine stage relevance from spam reviews |

**Confidence score returned:** 0.18  
**Overall:** ✅ Pass

---

### TC09 — Arabic output only: native quality check
**Type:** Easy  
**Product:** Mustela Cleansing Gel | **Stage:** new_mumz | **Language:** ar

**What I expected:** Arabic verdict only, verdict_en null. Arabic reads naturally.

**Result:**

| Dimension | Score | Notes |
|-----------|-------|-------|
| Grounding | ✅ | References to skin sensitivity, NICU recommendation present in reviews |
| Uncertainty | ✅ | No false flags |
| Schema | ✅ | verdict_en null as expected |
| Arabic quality | ✅ | Reviewed by native Arabic speaker — reads naturally. No word-for-word translation patterns detected. |
| Stage relevance | ✅ | Newborn skin focus correct |

**Overall:** ✅ Pass

---

### TC10 — Off-topic reviews: wrong product context
**Type:** Adversarial  
**Input:** Reviews about car seats and strollers, product name is "Baby Bath Thermometer"

**What I expected:** grounded: false, high uncertainty, model should not generate a confident bath thermometer verdict from stroller reviews.

**Result:**

| Dimension | Score | Notes |
|-----------|-------|-------|
| Grounding | ✅ | Model flagged mismatch |
| Uncertainty | ✅ | uncertainty_flags: ["Reviews do not appear to be about the requested product"] |
| Schema | ✅ | grounded: false returned |
| Arabic quality | N/A | |
| Stage relevance | N/A | Could not assess |

**Confidence score returned:** 0.12  
**Overall:** ✅ Pass

---

### TC11 — Pregnant stage: product with pregnant signal
**Type:** Easy  
**Product:** Chicco Next2Me Bedside Crib | **Stage:** pregnant | **Language:** both

**What I expected:** Verdict focused on pre-birth purchase rationale, hospital bag prep, C-section recovery planning.

**Result:**

| Dimension | Score | Notes |
|-----------|-------|-------|
| Grounding | ✅ | Referenced antenatal setup, 36-week assembly, C-section recovery |
| Uncertainty | ✅ | Confidence appropriate — 3 pregnant-stage reviews found |
| Schema | ✅ | Both languages populated |
| Arabic quality | ✅ | Arabic natural |
| Stage relevance | ✅ | Did not bleed into new mumz territory |

**Overall:** ✅ Pass

---

### TC12 — Safety concern must surface in cons
**Type:** Adversarial  
**Input:** 4 reviews all mentioning glass breaking danger for toddlers

**What I expected:** Safety concern explicitly in cons_en. Model must not omit it.

**Result:**

| Dimension | Score | Notes |
|-----------|-------|-------|
| Grounding | ✅ | Safety mentioned in cons |
| Uncertainty | ✅ | No false positives |
| Schema | ✅ | Valid |
| Arabic quality | N/A | EN only |
| Stage relevance | ✅ | Correct toddler focus |

**cons_en included:** "Glass breakage is a safety risk once toddlers can drop or throw bottles"  
**Overall:** ✅ Pass

---

## Summary Scorecard

| ID | Name | Pass/Fail | Confidence |
|----|------|-----------|------------|
| TC01 | Strong signal new mumz | ✅ Pass | 0.82 |
| TC02 | Stage mismatch | ✅ Pass | 0.28 |
| TC03 | Empty reviews | ✅ Pass | N/A |
| TC04 | Single review | ✅ Pass | 0.22 |
| TC05 | Arabic reviews → EN output | ✅ Pass | 0.71 |
| TC06 | Contradictory reviews | ✅ Pass | 0.51 |
| TC07 | Toddler stage signal | ✅ Pass | 0.76 |
| TC08 | Spam reviews | ✅ Pass | 0.18 |
| TC09 | Arabic output quality | ✅ Pass | 0.79 |
| TC10 | Off-topic reviews | ✅ Pass | 0.12 |
| TC11 | Pregnant stage signal | ✅ Pass | 0.63 |
| TC12 | Safety concern surfaces | ✅ Pass | 0.84 |

**12/12 Pass**

---

## Known Failure Modes

**1. Very short reviews under-score the embedding filter.**  
Reviews like "Great product, loved it" have weak semantic signal and may not pass the cosine threshold. The fallback (top-5 by score) partially mitigates this but short reviews will always produce lower confidence verdicts.

**2. Stage boundary ambiguity.**  
A review from a mom whose baby is "almost 1 year" sits on the new_mumz / toddler_mumz boundary. The embedding model has no way to resolve this precisely.

**3. Arabic translation risk.**  
If the LLM internally reasons in English and then translates to Arabic, the output can occasionally read stilted. The system prompt explicitly instructs native Arabic generation but this is not fully verifiable without a native speaker eval on every run.

**4. JSON instability on long outputs.**  
When pros/cons lists are very long, the model occasionally truncates the JSON mid-field. The parser catches this and returns a structured error — but the user loses the output. Mitigation: max_tokens is set conservatively and list lengths are capped in the prompt.