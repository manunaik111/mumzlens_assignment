import streamlit as st
import json
import os
from pathlib import Path
from src.schemas import MumzLensRequest, Stage, Language
from src.synthesizer import synthesize

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="MumzLens",
    page_icon="🔍",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Styling
# ---------------------------------------------------------------------------

st.markdown("""
<style>
    .main { background-color: #0f0f0f; }
    .verdict-box {
        background: #1a1a2e;
        border-left: 4px solid #e91e8c;
        border-radius: 8px;
        padding: 1.2rem;
        margin-bottom: 1rem;
    }
    .confidence-high { color: #4caf50; font-weight: bold; }
    .confidence-mid  { color: #ff9800; font-weight: bold; }
    .confidence-low  { color: #f44336; font-weight: bold; }
    .tag {
        display: inline-block;
        background: #e91e8c22;
        border: 1px solid #e91e8c55;
        border-radius: 20px;
        padding: 2px 12px;
        margin: 3px;
        font-size: 0.82rem;
        color: #e91e8c;
    }
    .warning-box {
        background: #2a1a00;
        border-left: 4px solid #ff9800;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.markdown("## 🔍 MumzLens")
st.markdown("*Reviews filtered for your stage. Not everyone's experience — yours.*")
st.divider()

# ---------------------------------------------------------------------------
# Load sample reviews from data/reviews.json
# ---------------------------------------------------------------------------

@st.cache_data
def load_sample_reviews():
    data_path = Path("data/reviews.json")
    if data_path.exists():
        with data_path.open(encoding="utf-8") as f:
            return json.load(f)
    return []

all_reviews = load_sample_reviews()
product_names = sorted(set(r["product"] for r in all_reviews)) if all_reviews else []

# ---------------------------------------------------------------------------
# Sidebar — inputs
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("### Your situation")

    input_mode = st.radio(
        "How do you want to add reviews?",
        ["Use sample product", "Paste your own reviews"],
        index=0,
    )

    if input_mode == "Use sample product":
        selected_product = st.selectbox("Product", product_names)
        product_reviews = [
            r["text"] for r in all_reviews if r["product"] == selected_product
        ]
        st.caption(f"{len(product_reviews)} reviews available for this product.")
        product_name_input = selected_product
    else:
        product_name_input = st.text_input("Product name", placeholder="e.g. Mustela Cleansing Gel")
        raw_text = st.text_area(
            "Paste reviews (one per line)",
            height=200,
            placeholder="Paste each review on a new line...",
        )
        product_reviews = [r.strip() for r in raw_text.split("\n") if r.strip()]
        st.caption(f"{len(product_reviews)} reviews detected.")

    st.divider()

    stage = st.selectbox(
        "Your stage",
        options=[s.value for s in Stage],
        format_func=lambda x: {
            "pregnant": "🤰 Pregnant",
            "new_mumz": "👶 New Mumz (0–12 months)",
            "toddler_mumz": "🧒 Toddler Mumz (1–3 years)",
        }[x],
    )

    language = st.selectbox(
        "Language",
        options=[l.value for l in Language],
        format_func=lambda x: {
            "en": "English only",
            "ar": "Arabic only — عربي فقط",
            "both": "Both — EN + AR",
        }[x],
    )

    run = st.button("Get My Verdict →", type="primary", use_container_width=True)

# ---------------------------------------------------------------------------
# Main — results
# ---------------------------------------------------------------------------

if run:
    if not product_reviews:
        st.error("No reviews found. Please select a product or paste reviews.")
        st.stop()

    if not product_name_input:
        st.error("Please enter a product name.")
        st.stop()

    with st.spinner("Filtering reviews for your stage and synthesizing verdict..."):
        request = MumzLensRequest(
            product_name=product_name_input,
            stage=Stage(stage),
            language=Language(language),
            reviews=product_reviews,
        )
        result = synthesize(request)

    # Error state
    if result.error:
        st.error(f"Something went wrong: {result.error}")
        st.stop()

    v = result.stage_verdict
    conf = v.confidence_score
    conf_label = (
        f'<span class="confidence-high">High ({conf:.0%})</span>' if conf >= 0.7
        else f'<span class="confidence-mid">Moderate ({conf:.0%})</span>' if conf >= 0.4
        else f'<span class="confidence-low">Low ({conf:.0%})</span>'
    )

    # Summary row
    col1, col2, col3 = st.columns(3)
    col1.metric("Reviews analysed", result.total_reviews_analyzed)
    col2.metric("Relevant to your stage", v.relevant_review_count)
    col3.markdown(f"**Confidence**<br>{conf_label}", unsafe_allow_html=True)

    st.divider()

    # Insufficient data warning
    if v.insufficient_data:
        st.markdown(f"""
        <div class="warning-box">
        ⚠️ <strong>Not enough data for your stage.</strong><br>
        Only {v.relevant_review_count} review(s) matched your stage out of {result.total_reviews_analyzed} total.
        The verdict below is based on limited evidence — treat it with caution.
        </div>
        """, unsafe_allow_html=True)

    # Verdict — English
    if v.verdict_en:
        st.markdown("### Verdict (English)")
        st.markdown(f'<div class="verdict-box">{v.verdict_en}</div>', unsafe_allow_html=True)

        col_p, col_c = st.columns(2)
        with col_p:
            st.markdown("**✅ Pros**")
            for pro in v.pros_en:
                st.markdown(f"- {pro}")
        with col_c:
            st.markdown("**⚠️ Cons**")
            for con in v.cons_en:
                st.markdown(f"- {con}")

    # Verdict — Arabic
    if v.verdict_ar:
        st.divider()
        st.markdown("### الحكم (عربي)")
        st.markdown(
            f'<div class="verdict-box" dir="rtl" style="text-align:right;">{v.verdict_ar}</div>',
            unsafe_allow_html=True,
        )

        col_p2, col_c2 = st.columns(2)
        with col_p2:
            st.markdown("**✅ الإيجابيات**")
            for pro in v.pros_ar:
                st.markdown(f"- {pro}")
        with col_c2:
            st.markdown("**⚠️ السلبيات**")
            for con in v.cons_ar:
                st.markdown(f"- {con}")

    # Themes
    if result.top_themes:
        st.divider()
        st.markdown("**Key themes in reviews for your stage**")
        theme_html = "".join(f'<span class="tag">{t}</span>' for t in result.top_themes)
        st.markdown(theme_html, unsafe_allow_html=True)

    # Uncertainty flags
    if v.uncertainty_flags:
        st.divider()
        with st.expander("⚠️ What MumzLens is uncertain about"):
            for flag in v.uncertainty_flags:
                st.markdown(f"- {flag}")

    # Grounding warning
    if not result.grounded:
        st.warning("This verdict could not be fully grounded in the provided reviews.")

    # Raw JSON for debugging / transparency
    with st.expander("🔍 Raw structured output (JSON)"):
        st.json(result.model_dump())

else:
    # Landing state
    st.markdown("""
    ### How it works

    Mumzworld has hundreds of reviews per product — but a **pregnant mom** and a 
    **toddler mom** are asking completely different questions from the same reviews.

    **MumzLens** filters and re-synthesizes reviews for *your* stage, so you only 
    see what's relevant to where you are right now.

    **→ Pick a product, select your stage, and get your verdict.**
    """)

    if product_names:
        st.markdown("**Available sample products:**")
        for p in product_names:
            count = len([r for r in all_reviews if r["product"] == p])
            st.markdown(f"- {p} *({count} reviews)*")
