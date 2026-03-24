"""Truthora — Streamlit Human-in-the-Loop Review Dashboard.

Layer 7 — full implementation:
  - Language switcher (EN / PL / UA)
  - URL or headline/text input tabs
  - Verdict banner (VERIFIED / UNVERIFIED / LIKELY_FALSE / NO_DATA) with confidence bar
  - Claims with checkworthiness priority, source quotes, KG signals
  - Top matches with stance labels, scores, freshness badges
  - Uncertainty bar
  - Operator review actions (✓ Approve | ✗ Reject | ⚑ Flag | ✎ Note)
  - Audit log saved to Qdrant
"""

import os
from datetime import datetime, timezone

import httpx
import streamlit as st
import streamlit.components.v1 as components

# ── Page Config ────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Truthora", page_icon="🔍", layout="wide")

# ── Disable Deploy popup items (visible but non-interactive) ──────────────────
st.markdown(
    """
    <style>
    /* Keep Streamlit deploy-popup items visible but non-interactive */
    [data-testid="stDeployButton"] a,
    [data-testid="stDeployButton"] button:not([data-testid]),
    a[href*="share.streamlit.io"],
    a[href*="app.snowflake.com"],
    a[href*="snowflake.com"],
    header ul a,
    header ul button {
        pointer-events: none !important;
        opacity: 0.45 !important;
        cursor: not-allowed !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)
components.html(
    """
    <script>
    (function () {
        var parentDoc = window.parent.document;

        function disableDeployItems() {
            var selectors = [
                '[data-testid="stDeployButton"] a',
                '[data-testid="stDeployButton"] button:not([data-testid])',
                'a[href*="share.streamlit.io"]',
                'a[href*="app.snowflake.com"]',
                'a[href*="snowflake.com"]',
                'header ul a',
                'header ul button'
            ];
            selectors.forEach(function (sel) {
                try {
                    parentDoc.querySelectorAll(sel).forEach(function (el) {
                        el.style.pointerEvents = 'none';
                        el.style.opacity = '0.45';
                        el.style.cursor = 'not-allowed';
                        el.setAttribute('tabindex', '-1');
                        if (el.tagName === 'A') {
                            el.onclick = function (e) { e.preventDefault(); return false; };
                        }
                    });
                } catch (e) {}
            });
        }

        disableDeployItems();
        var observer = new MutationObserver(disableDeployItems);
        observer.observe(parentDoc.body, { childList: true, subtree: true });
    })();
    </script>
    """,
    height=0,
)

API_URL = os.getenv("API_URL", "http://localhost:8000")

# ── i18n strings ───────────────────────────────────────────────────────────────
LABELS: dict[str, dict[str, str]] = {
    "en": {
        "title": "🔍 Truthora — Claim Review Dashboard",
        "subtitle": "Open Multilingual Claim Detection & Matching — *Human-in-the-Loop*",
        "tab_url": "🔗 URL",
        "tab_headline": "📝 Headline / Text",
        "url_placeholder": "https://example.com/article",
        "headline_placeholder": "Paste a headline or short text to verify…",
        "btn_analyze": "🔎 Analyze",
        "spinner": "Analyzing…",
        "no_claims": "No verifiable claims detected.",
        "claims_header": "📋 Detected Claims",
        "label_source": "Source",
        "label_language": "Language",
        "label_time": "Processing Time",
        "label_priority": "Priority",
        "label_negation": "⚠️ Negation",
        "label_top_matches": "🔗 Top Matches",
        "label_no_matches": "No fact-check matches found for this claim.",
        "label_uncertainty": "Uncertainty",
        "label_high_unc": "⚠️ High uncertainty — mandatory manual review required",
        "btn_approve": "✓ Approve",
        "btn_reject": "✗ Reject",
        "btn_flag": "⚑ Flag",
        "btn_note": "✎ Note",
        "btn_save_note": "Save Note",
        "note_label": "Add note:",
        "audit_header": "📝 Audit Log",
        "verdict_title": "Overall Verdict",
        "verdict_confidence": "Confidence",
        "verdict_VERIFIED": "✅ Verified",
        "verdict_UNVERIFIED": "⚠️ Unverified",
        "verdict_LIKELY_FALSE": "🔴 Likely False",
        "verdict_NO_DATA": "⚪ No Data",
        "verdict_desc_VERIFIED": (
            "At least 40% of matched fact-checks support the claims in this article. "
            "The information is consistent with known verified sources. "
            "Always cross-check with the original sources listed below."
        ),
        "verdict_desc_UNVERIFIED": (
            "The claims could not be conclusively confirmed or refuted against "
            "the available fact-check database. "
            "Treat this content with caution and seek additional sources."
        ),
        "verdict_desc_LIKELY_FALSE": (
            "At least 40% of matched fact-checks contradict the claims in this article. "
            "This content is likely false or misleading. "
            "Review the individual claim cards below for details."
        ),
        "verdict_desc_NO_DATA": (
            "No relevant fact-checks were found for this content, "
            "or uncertainty is too high to form a verdict. "
            "Manual expert review is recommended."
        ),
        "expand_cw": "📊 Checkworthiness Dimensions",
        "footer": "Truthora v0.1.0 — Open Multilingual Claim Detection & Matching — Apache 2.0",
    },
    "pl": {
        "title": "🔍 Truthora — Weryfikacja Twierdzeń",
        "subtitle": "Otwarta wielojęzyczna detekcja twierdzeń i dopasowywanie fact-checków — *człowiek w pętli*",
        "tab_url": "🔗 URL",
        "tab_headline": "📝 Nagłówek / Tekst",
        "url_placeholder": "https://example.pl/artykul",
        "headline_placeholder": "Wklej nagłówek lub krótki tekst do weryfikacji…",
        "btn_analyze": "🔎 Analizuj",
        "spinner": "Analizuję…",
        "no_claims": "Nie wykryto weryfikowalnych twierdzeń.",
        "claims_header": "📋 Wykryte Twierdzenia",
        "label_source": "Źródło",
        "label_language": "Język",
        "label_time": "Czas przetwarzania",
        "label_priority": "Priorytet",
        "label_negation": "⚠️ Negacja",
        "label_top_matches": "🔗 Najlepsze dopasowania",
        "label_no_matches": "Brak dopasowań fact-check dla tego twierdzenia.",
        "label_uncertainty": "Niepewność",
        "label_high_unc": "⚠️ Wysoka niepewność — wymagana ręczna weryfikacja",
        "btn_approve": "✓ Zatwierdź",
        "btn_reject": "✗ Odrzuć",
        "btn_flag": "⚑ Flaga",
        "btn_note": "✎ Notatka",
        "btn_save_note": "Zapisz notatkę",
        "note_label": "Dodaj notatkę:",
        "audit_header": "📝 Dziennik audytu",
        "verdict_title": "Ogólny werdykt",
        "verdict_confidence": "Pewność",
        "verdict_VERIFIED": "✅ Zweryfikowane",
        "verdict_UNVERIFIED": "⚠️ Niezweryfikowane",
        "verdict_LIKELY_FALSE": "🔴 Prawdopodobnie fałszywe",
        "verdict_NO_DATA": "⚪ Brak danych",
        "verdict_desc_VERIFIED": (
            "Co najmniej 40% dopasowanych fact-checków potwierdza twierdzenia z tego artykułu. "
            "Informacje są spójne ze zweryfikowanymi źródłami. "
            "Zawsze sprawdzaj oryginalne źródła wymienione poniżej."
        ),
        "verdict_desc_UNVERIFIED": (
            "Nie udało się jednoznacznie potwierdzić ani obalić twierdzeń "
            "na podstawie dostępnej bazy fact-checków. "
            "Traktuj tę treść ostrożnie i poszukaj dodatkowych źródeł."
        ),
        "verdict_desc_LIKELY_FALSE": (
            "Co najmniej 40% dopasowanych fact-checków zaprzecza twierdzeniom z tego artykułu. "
            "Ta treść jest prawdopodobnie fałszywa lub wprowadzająca w błąd. "
            "Sprawdź poniższe karty twierdzeń, aby uzyskać szczegóły."
        ),
        "verdict_desc_NO_DATA": (
            "Nie znaleziono istotnych fact-checków dla tej treści "
            "lub niepewność jest zbyt wysoka, aby wydać werdykt. "
            "Zalecana jest ręczna weryfikacja eksperta."
        ),
        "expand_cw": "📊 Wymiary wiarygodności",
        "footer": "Truthora v0.1.0 — Otwarta wielojęzyczna weryfikacja twierdzeń — Apache 2.0",
    },
    "ua": {
        "title": "🔍 Truthora — Перевірка Тверджень",
        "subtitle": "Відкрита багатомовна система виявлення та перевірки тверджень — *людина в контурі*",
        "tab_url": "🔗 URL",
        "tab_headline": "📝 Заголовок / Текст",
        "url_placeholder": "https://example.ua/stattia",
        "headline_placeholder": "Вставте заголовок або короткий текст для перевірки…",
        "btn_analyze": "🔎 Аналізувати",
        "spinner": "Аналізую…",
        "no_claims": "Твердження, що підлягають перевірці, не виявлено.",
        "claims_header": "📋 Виявлені Твердження",
        "label_source": "Джерело",
        "label_language": "Мова",
        "label_time": "Час обробки",
        "label_priority": "Пріоритет",
        "label_negation": "⚠️ Заперечення",
        "label_top_matches": "🔗 Найкращі збіги",
        "label_no_matches": "Збігів у базі fact-check не знайдено.",
        "label_uncertainty": "Невизначеність",
        "label_high_unc": "⚠️ Висока невизначеність — обов'язкова ручна перевірка",
        "btn_approve": "✓ Схвалити",
        "btn_reject": "✗ Відхилити",
        "btn_flag": "⚑ Позначити",
        "btn_note": "✎ Нотатка",
        "btn_save_note": "Зберегти нотатку",
        "note_label": "Додати нотатку:",
        "audit_header": "📝 Журнал аудиту",
        "verdict_title": "Загальний вердикт",
        "verdict_confidence": "Впевненість",
        "verdict_VERIFIED": "✅ Підтверджено",
        "verdict_UNVERIFIED": "⚠️ Не підтверджено",
        "verdict_LIKELY_FALSE": "🔴 Ймовірно хибне",
        "verdict_NO_DATA": "⚪ Немає даних",
        "verdict_desc_VERIFIED": (
            "Щонайменше 40% відповідних fact-check підтверджують твердження у цій статті. "
            "Інформація відповідає відомим перевіреним джерелам. "
            "Обов'язково перевіряйте оригінальні джерела, перелічені нижче."
        ),
        "verdict_desc_UNVERIFIED": (
            "Твердження не вдалося однозначно підтвердити або спростувати "
            "на основі наявної бази fact-check. "
            "Ставтеся до цього контенту обережно та шукайте додаткові джерела."
        ),
        "verdict_desc_LIKELY_FALSE": (
            "Щонайменше 40% відповідних fact-check заперечують твердження у цій статті. "
            "Цей контент, ймовірно, є хибним або оманливим. "
            "Перегляньте картки тверджень нижче для отримання деталей."
        ),
        "verdict_desc_NO_DATA": (
            "Відповідних fact-check для цього контенту не знайдено, "
            "або невизначеність надто висока для винесення вердикту. "
            "Рекомендується ручна експертна перевірка."
        ),
        "expand_cw": "📊 Виміри надійності",
        "footer": "Truthora v0.1.0 — Відкрита багатомовна перевірка тверджень — Apache 2.0",
    },
}

VERDICT_BG: dict[str, str] = {
    "VERIFIED": "#1a472a",
    "UNVERIFIED": "#4a3800",
    "LIKELY_FALSE": "#4a0000",
    "NO_DATA": "#2d2d2d",
}
VERDICT_BORDER: dict[str, str] = {
    "VERIFIED": "#2ecc71",
    "UNVERIFIED": "#f1c40f",
    "LIKELY_FALSE": "#e74c3c",
    "NO_DATA": "#95a5a6",
}

# ── Session State ──────────────────────────────────────────────────────────────
if "lang" not in st.session_state:
    st.session_state.lang = "en"
if "analysis_results" not in st.session_state:
    st.session_state.analysis_results = None
if "audit_log" not in st.session_state:
    st.session_state.audit_log = []

L = LABELS[st.session_state.lang]


# ── Helper Functions ───────────────────────────────────────────────────────────

def freshness_emoji(badge: str) -> str:
    return {"fresh": "🟢", "aging": "🟡", "outdated": "🔴"}.get(badge, "⚪")


def stance_emoji(stance: str) -> str:
    return {"SUPPORTED": "✅", "REFUTED": "❌", "NEI": "❓"}.get(stance, "❓")


def uncertainty_color(level: str) -> str:
    return {"LOW": "green", "MODERATE": "orange", "HIGH": "red"}.get(level, "gray")


def kg_emoji(signal: str | None) -> str:
    if signal is None:
        return "—"
    return {"KG_FOUND": "✅", "KG_NOT_FOUND": "—", "KG_MISMATCH": "⚠️"}.get(signal, "—")


def call_analyze_api(url: str | None = None, headline: str | None = None) -> dict | None:
    try:
        body: dict = {}
        if url:
            body["url"] = url
        if headline:
            body["headline"] = headline
        with httpx.Client(timeout=120) as client:
            resp = client.post(f"{API_URL}/analyze", json=body)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        st.error(f"API error: {e}")
        return None


def call_review_api(claim_id: str, action: str, note: str = "") -> dict | None:
    try:
        with httpx.Client(timeout=15) as client:
            body: dict = {"action": action}
            if note:
                body["note"] = note
            resp = client.patch(f"{API_URL}/claims/{claim_id}", json=body)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        st.error(f"Review API error: {e}")
        return None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def render_verdict_banner(verdict: str, confidence: float) -> None:
    bg = VERDICT_BG.get(verdict, "#2d2d2d")
    border = VERDICT_BORDER.get(verdict, "#95a5a6")
    label = L.get(f"verdict_{verdict}", verdict)
    desc = L.get(f"verdict_desc_{verdict}", "")
    conf_pct = int(confidence * 100)

    st.markdown(
        f"""
        <div style="
            background:{bg};
            border-left:6px solid {border};
            border-radius:6px;
            padding:16px 20px;
            margin-bottom:16px;
        ">
            <div style="font-size:1.6rem;font-weight:700;margin-bottom:6px;">{label}</div>
            <div style="font-size:0.95rem;opacity:0.88;margin-bottom:10px;">{desc}</div>
            <div style="font-size:0.85rem;margin-bottom:4px;">
                {L['verdict_confidence']}: <strong>{conf_pct}%</strong>
            </div>
            <div style="background:#ffffff22;border-radius:4px;height:10px;overflow:hidden;">
                <div style="
                    background:{border};
                    width:{conf_pct}%;
                    height:100%;
                    border-radius:4px;
                    transition:width .4s ease;
                "></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Language Switcher ──────────────────────────────────────────────────────────
lang_col, _, title_col = st.columns([2, 1, 5])
with lang_col:
    btn_cols = st.columns(3)
    for idx, (code, flag) in enumerate([("en", "🇬🇧 EN"), ("pl", "🇵🇱 PL"), ("ua", "🇺🇦 UA")]):
        with btn_cols[idx]:
            is_active = st.session_state.lang == code
            if st.button(
                flag,
                key=f"lang_{code}",
                type="primary" if is_active else "secondary",
                use_container_width=True,
            ):
                st.session_state.lang = code
                st.rerun()

# refresh labels after potential language change
L = LABELS[st.session_state.lang]

with title_col:
    st.title(L["title"])

st.markdown(f">{L['subtitle']}")

# ── Input Tabs ─────────────────────────────────────────────────────────────────
tab_url, tab_headline = st.tabs([L["tab_url"], L["tab_headline"]])

with tab_url:
    col_inp, col_btn = st.columns([4, 1])
    with col_inp:
        url_input = st.text_input(
            "url",
            placeholder=L["url_placeholder"],
            label_visibility="collapsed",
            key="url_input",
        )
    with col_btn:
        url_analyze = st.button(
            L["btn_analyze"], key="url_btn", type="primary", use_container_width=True
        )
    if url_analyze and url_input:
        if not url_input.startswith(("http://", "https://")):
            st.info("ℹ️ Enter a valid URL starting with https://  —  to check a headline or text use the '📝 Headline / Text' tab.")
        else:
            with st.spinner(L["spinner"]):
                result = call_analyze_api(url=url_input)
                if result:
                    st.session_state.analysis_results = result

with tab_headline:
    headline_input = st.text_area(
        "headline",
        placeholder=L["headline_placeholder"],
        height=100,
        label_visibility="collapsed",
        key="headline_input",
    )
    headline_analyze = st.button(
        L["btn_analyze"], key="headline_btn", type="primary"
    )
    if headline_analyze and headline_input:
        with st.spinner(L["spinner"]):
            result = call_analyze_api(headline=headline_input)
            if result:
                st.session_state.analysis_results = result

# ── Results ────────────────────────────────────────────────────────────────────
results = st.session_state.analysis_results

if results:
    st.divider()

    # ── Verdict Banner ─────────────────────────────────────────────────────────
    verdict = results.get("verdict", "NO_DATA")
    confidence = results.get("confidence", 0.0) or 0.0
    render_verdict_banner(verdict, confidence)

    # ── Article Metadata ───────────────────────────────────────────────────────
    col_meta1, col_meta2, col_meta3 = st.columns(3)
    with col_meta1:
        source_url = results.get("url", "—")
        display_url = source_url[:60] + "..." if len(source_url) > 60 else source_url
        st.metric(L["label_source"], display_url)
    with col_meta2:
        st.metric(L["label_language"], results.get("language", "—"))
    with col_meta3:
        st.metric(L["label_time"], f"{results.get('processing_time_ms', 0):.0f} ms")

    claims = results.get("claims", [])
    if not claims:
        st.info(L["no_claims"])
    else:
        st.subheader(f"{L['claims_header']} ({len(claims)})")

        for i, claim_result in enumerate(claims):
            claim = claim_result.get("claim", {})
            matches = claim_result.get("matches", [])
            uncertainty = claim_result.get("uncertainty", 0)
            uncertainty_level = claim_result.get("uncertainty_level", "MODERATE")

            cw = claim.get("checkworthiness", {})
            composite = cw.get("composite", 0)
            claim_id = claim.get("claim_id", f"claim_{i}")

            with st.container(border=True):
                # Header row
                col_num, col_priority, col_neg = st.columns([1, 2, 1])
                with col_num:
                    st.markdown(f"### Claim #{i + 1}")
                with col_priority:
                    st.progress(composite, text=f"{L['label_priority']}: {composite:.2f}")
                with col_neg:
                    if claim.get("has_negation"):
                        st.warning(L["label_negation"])

                # Claim text
                st.markdown(f"**\"{claim.get('claim_text', '')}\"**")

                # Source quote
                source_quote = claim.get("source_quote", "")
                if source_quote:
                    char_start = claim.get("char_start", 0)
                    char_end = claim.get("char_end", 0)
                    st.markdown(
                        f"📎 **{L['label_source']}:** \"{source_quote}\" "
                        f"[char {char_start}–{char_end}]"
                    )

                # Checkworthiness dimensions
                with st.expander(L["expand_cw"]):
                    cw_cols = st.columns(5)
                    dims = [
                        ("Harm", cw.get("harm_potential", 0), "0.35"),
                        ("Virality", cw.get("virality_potential", 0), "0.25"),
                        ("Verifiability", cw.get("verifiability", 0), "0.20"),
                        ("Specificity", cw.get("specificity", 0), "0.12"),
                        ("Public Int.", cw.get("public_interest", 0), "0.08"),
                    ]
                    for col, (name, val, weight) in zip(cw_cols, dims):
                        with col:
                            st.metric(f"{name} (w={weight})", f"{val:.2f}")

                # Matches
                if matches:
                    st.markdown(f"**{L['label_top_matches']}:**")
                    for j, match in enumerate(matches[:5]):
                        stance = match.get("stance", "NEI")
                        score = match.get("final_score", 0)
                        source = match.get("source_name", "Unknown")
                        badge = match.get("freshness_badge", "aging")
                        url_match = match.get("matched_url", "")
                        sim = match.get("similarity_score", 0)
                        rerank = match.get("reranker_score")
                        nli_conf = match.get("nli_confidence")
                        kg = match.get("kg_signal")

                        cols = st.columns([1, 2, 1, 1, 1])
                        with cols[0]:
                            st.markdown(f"{stance_emoji(stance)} **{stance}**")
                        with cols[1]:
                            st.markdown(f"[{source}]({url_match})")
                        with cols[2]:
                            st.markdown(f"Score: **{score:.2f}**")
                        with cols[3]:
                            st.markdown(f"{freshness_emoji(badge)} {badge.title()}")
                        with cols[4]:
                            st.markdown(f"KG: {kg_emoji(kg)}")

                        with st.expander(f"Match #{j+1} details"):
                            detail_cols = st.columns(4)
                            with detail_cols[0]:
                                st.metric("Similarity", f"{sim:.3f}")
                            with detail_cols[1]:
                                st.metric("Reranker", f"{rerank:.3f}" if rerank else "—")
                            with detail_cols[2]:
                                st.metric("NLI Conf.", f"{nli_conf:.3f}" if nli_conf else "—")
                            with detail_cols[3]:
                                st.metric("Freshness", f"{match.get('freshness_decay', 0):.3f}")
                            st.markdown(f"**Reviewed claim:** {match.get('claim_reviewed', '')}")
                else:
                    st.info(L["label_no_matches"])

                # Uncertainty bar
                st.markdown(f"**{L['label_uncertainty']}:** {uncertainty_level}")
                st.progress(uncertainty, text=f"H = {uncertainty:.2f}")
                if uncertainty_level == "HIGH":
                    st.error(L["label_high_unc"])

                # ── Operator Actions ───────────────────────────────────────────
                st.markdown("---")
                action_cols = st.columns([1, 1, 1, 1, 3])
                with action_cols[0]:
                    if st.button(L["btn_approve"], key=f"approve_{claim_id}"):
                        resp = call_review_api(claim_id, "approve")
                        if resp:
                            st.session_state.audit_log.append({
                                "claim_id": claim_id,
                                "action": "approve",
                                "timestamp": _now_iso(),
                            })
                            st.success("Approved ✓")
                with action_cols[1]:
                    if st.button(L["btn_reject"], key=f"reject_{claim_id}"):
                        resp = call_review_api(claim_id, "reject")
                        if resp:
                            st.session_state.audit_log.append({
                                "claim_id": claim_id,
                                "action": "reject",
                                "timestamp": _now_iso(),
                            })
                            st.success("Rejected ✗")
                with action_cols[2]:
                    if st.button(L["btn_flag"], key=f"flag_{claim_id}"):
                        resp = call_review_api(claim_id, "flag")
                        if resp:
                            st.session_state.audit_log.append({
                                "claim_id": claim_id,
                                "action": "flag",
                                "timestamp": _now_iso(),
                            })
                            st.warning("Flagged ⚑")
                with action_cols[3]:
                    if st.button(L["btn_note"], key=f"notebtn_{claim_id}"):
                        st.session_state[f"show_note_{claim_id}"] = True

                if st.session_state.get(f"show_note_{claim_id}"):
                    note_text = st.text_area(L["note_label"], key=f"notetext_{claim_id}")
                    if st.button(L["btn_save_note"], key=f"savenote_{claim_id}"):
                        resp = call_review_api(claim_id, "flag", note=note_text)
                        if resp:
                            st.session_state.audit_log.append({
                                "claim_id": claim_id,
                                "action": "flag",
                                "note": note_text,
                                "timestamp": _now_iso(),
                            })
                            st.success("Note saved ✎")
                            st.session_state[f"show_note_{claim_id}"] = False

    # ── Audit Log ──────────────────────────────────────────────────────────────
    if st.session_state.audit_log:
        st.divider()
        st.subheader(L["audit_header"])
        for entry in reversed(st.session_state.audit_log):
            action_emoji = {"approve": "✓", "reject": "✗", "flag": "⚑"}.get(entry["action"], "?")
            note = f" — {entry.get('note', '')}" if entry.get("note") else ""
            st.markdown(
                f"`{entry['timestamp'][:19]}` {action_emoji} "
                f"**{entry['action'].upper()}** claim `{entry['claim_id']}`{note}"
            )

# ── Footer ─────────────────────────────────────────────────────────────────────
st.divider()
st.caption(L["footer"])
