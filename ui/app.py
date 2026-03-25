"""Streamlit Human-in-the-Loop Review Dashboard."""

import os
from datetime import datetime, timezone

import httpx
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Truthora", page_icon="🔍", layout="wide")


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

VERDICT_STYLES: dict[str, dict[str, str]] = {
    "VERIFIED": {"bg": "rgba(46,204,113,0.12)", "border": "#2ecc71", "text": "#1a7a3a"},
    "UNVERIFIED": {"bg": "rgba(241,196,15,0.12)", "border": "#f1c40f", "text": "#7a6800"},
    "LIKELY_FALSE": {"bg": "rgba(231,76,60,0.12)", "border": "#e74c3c", "text": "#a01a0a"},
    "NO_DATA": {"bg": "rgba(149,165,166,0.12)", "border": "#95a5a6", "text": "#555555"},
}

if "lang" not in st.session_state:
    st.session_state.lang = "en"
if "analysis_results" not in st.session_state:
    st.session_state.analysis_results = None
if "audit_log" not in st.session_state:
    st.session_state.audit_log = []

L = LABELS[st.session_state.lang]



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


def render_verdict_banner(verdict: str, confidence: float, explanation: str = "") -> None:
    style = VERDICT_STYLES.get(verdict, VERDICT_STYLES["NO_DATA"])
    bg = style["bg"]
    border = style["border"]
    text_color = style["text"]
    label = L.get(f"verdict_{verdict}", verdict)
    desc = L.get(f"verdict_desc_{verdict}", "")
    conf_pct = int(confidence * 100)

    # Confidence display: hide bar at 0%, show informative message instead
    if conf_pct == 0:
        confidence_html = (
            '<div style="font-size:0.85rem;opacity:0.75;margin-top:6px;">'
            'Insufficient data for confidence scoring — manual review required'
            '</div>'
        )
    else:
        confidence_html = (
            f'<div style="font-size:0.85rem;margin-bottom:4px;">'
            f'{L["verdict_confidence"]}: <strong>{conf_pct}%</strong>'
            f'</div>'
            f'<div style="background:rgba(0,0,0,0.1);border-radius:4px;height:10px;overflow:hidden;">'
            f'<div style="background:{border};width:{conf_pct}%;height:100%;'
            f'border-radius:4px;transition:width .4s ease;"></div></div>'
        )

    # Explanation block
    explanation_html = ""
    if explanation:
        explanation_html = (
            f'<div style="font-size:0.85rem;opacity:0.85;margin-top:8px;'
            f'border-top:1px solid {border}33;padding-top:8px;">'
            f'📋 {explanation}</div>'
        )

    st.markdown(
        f"""
        <div style="
            background:{bg};
            border-left:6px solid {border};
            border-radius:6px;
            padding:16px 20px;
            margin-bottom:16px;
            color:{text_color};
        ">
            <div style="font-size:1.6rem;font-weight:700;margin-bottom:6px;">{label}</div>
            <div style="font-size:0.95rem;opacity:0.88;margin-bottom:10px;">{desc}</div>
            {confidence_html}
            {explanation_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


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

tab_url, tab_headline, tab_test = st.tabs([L["tab_url"], L["tab_headline"], "🧪 Test Cases"])

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

TEST_CASES = [
    # EN — REFUTED
    {"claim": "The COVID-19 vaccine causes infertility", "lang": "en", "stance": "REFUTED",
     "source": "Full Fact",
     "url": "https://fullfact.org/health/covid-vaccine-infertility/"},
    {"claim": "5G networks spread coronavirus", "lang": "en", "stance": "REFUTED",
     "source": "Full Fact",
     "url": "https://fullfact.org/online/5g-not-connected-to-coronavirus/"},
    {"claim": "Vaccines contain microchips for tracking people", "lang": "en", "stance": "REFUTED",
     "source": "FactCheck.org",
     "url": "https://www.factcheck.org/2020/12/covid-19-vaccines-dont-have-patient-tracking-devices/"},
    {"claim": "Bill Gates wants to implant microchips via vaccines", "lang": "en", "stance": "REFUTED",
     "source": "FactCheck.org",
     "url": "https://www.factcheck.org/2020/04/conspiracy-theory-misinterprets-goals-of-gates-foundation/"},
    {"claim": "Climate change is a hoax", "lang": "en", "stance": "REFUTED",
     "source": "Washington Post",
     "url": "https://www.washingtonpost.com/politics/2023/08/25/vivek-ramaswamy-says-hoax-agenda-kills-more-people-than-climate-change/"},
    {"claim": "Mail-in voting leads to massive election fraud", "lang": "en", "stance": "REFUTED",
     "source": "BBC",
     "url": "https://www.bbc.co.uk/news/world-us-canada-53353404"},
    {"claim": "NATO promised Russia it would not expand eastward", "lang": "en", "stance": "REFUTED",
     "source": "DW",
     "url": "https://www.dw.com/en/nato-expansion-east-russia-putin-ukraine/a-73030670"},
    {"claim": "COVID-19 is actually a bacterial infection, not a viral one", "lang": "en", "stance": "REFUTED",
     "source": "AFP Fact Check",
     "url": "https://factcheck.afp.com/doc.afp.com.9W42LC"},
    # EN — SUPPORTED
    {"claim": "Russia deployed coordinated social media bot networks targeting EU elections", "lang": "en", "stance": "SUPPORTED",
     "source": "AFP Fact Check",
     "url": "https://factcheck.afp.com/doc.afp.com.33TU8BA"},
    {"claim": "NATO member states increased defence spending after 2022", "lang": "en", "stance": "SUPPORTED",
     "source": "Reuters",
     "url": "https://www.reuters.com/world/europe/nato-allies-ramp-up-defence-spending-russia-threat-looms-2024-02-14/"},
    {"claim": "The WHO declared COVID-19 a pandemic in March 2020", "lang": "en", "stance": "SUPPORTED",
     "source": "Reuters",
     "url": "https://www.reuters.com/article/us-health-coronavirus-who-idUSKBN2110GP"},
    {"claim": "Arctic sea ice extent has declined significantly since 1979", "lang": "en", "stance": "SUPPORTED",
     "source": "NASA",
     "url": "https://climate.nasa.gov/vital-signs/arctic-sea-ice/"},
    # EN — NEI
    {"claim": "Ivermectin is a proven cure for COVID-19", "lang": "en", "stance": "NEI",
     "source": "FactCheck.org",
     "url": "https://www.factcheck.org/2022/03/scicheck-evidence-still-lacking-to-support-ivermectin-as-treatment-for-covid-19/"},
    {"claim": "There is overwhelming evidence that ivermectin cures COVID-19", "lang": "en", "stance": "NEI",
     "source": "FactCheck.org",
     "url": "https://www.factcheck.org/2022/03/scicheck-evidence-still-lacking-to-support-ivermectin-as-treatment-for-covid-19/"},
    {"claim": "EU sanctions against Russia caused inflation in Europe", "lang": "en", "stance": "NEI",
     "source": "DW",
     "url": "https://www.dw.com/en/fact-check-are-eu-sanctions-the-cause-of-european-inflation/a-63041505"},
    {"claim": "Ocean temperatures declining between 2013 and 2022 proves global warming is fake", "lang": "en", "stance": "NEI",
     "source": "AAP FactCheck",
     "url": "https://www.aap.com.au/factcheck/cherry-picked-ocean-data-does-not-prove-climate-change-is-a-hoax/"},
    # PL — REFUTED
    {"claim": "Sieć 5G rozprzestrzenia koronawirusa", "lang": "pl", "stance": "REFUTED",
     "source": "Demagog",
     "url": "https://demagog.org.pl/fake_news/wdrozenie-5g-ma-zwiazek-z-pandemia-covid-19-fake-news/"},
    {"claim": "Szczepionki przeciw COVID-19 są trujące", "lang": "pl", "stance": "REFUTED",
     "source": "Demagog",
     "url": "https://demagog.org.pl/fake_news/miliony-polakow-otrzymalo-trucizne-jak-dezinformuje-lukasz-andryszczak/"},
    {"claim": "Iwermektyna jest skutecznym lekiem na COVID", "lang": "pl", "stance": "REFUTED",
     "source": "Demagog",
     "url": "https://demagog.org.pl/fake_news/teorie-spiskowe-wokol-covid-19-sprawdzamy-film-z-wojciechem-cejrowskim/"},
    {"claim": "Polska powinna wyjść z Unii Europejskiej", "lang": "pl", "stance": "REFUTED",
     "source": "Demagog",
     "url": "https://demagog.org.pl/analizy_i_raporty/polexit-fakty-i-mity/"},
    # PL — SUPPORTED
    {"claim": "Inflacja w Polsce wyniosła 2,3% w Q4 2025", "lang": "pl", "stance": "SUPPORTED",
     "source": "Konkret24",
     "url": "https://konkret24.tvn24.pl/gospodarka/inflacja-w-polsce/"},
    {"claim": "Polska jest jednym z największych dawców pomocy wojskowej dla Ukrainy", "lang": "pl", "stance": "SUPPORTED",
     "source": "Demagog",
     "url": "https://demagog.org.pl/wypowiedzi/polska-pomoc-wojskowa-ukraina-ranking/"},
    {"claim": "Wydatki NATO na obronność wzrosły po 2022 roku", "lang": "pl", "stance": "SUPPORTED",
     "source": "Demagog",
     "url": "https://demagog.org.pl/wypowiedzi/wydatki-nato-na-obronnosc-po-2022/"},
    # PL — NEI
    {"claim": "Węgiel brunatny jest najtańszym źródłem energii w Polsce", "lang": "pl", "stance": "NEI",
     "source": "Fakenews.pl",
     "url": "https://fakenews.pl/srodowisko/wegiel-brunatny-nie-jest-najtanszym-zrodlem-energii-w-polsce/"},
    {"claim": "Sankcje wobec Rosji spowodowały wzrost cen w Polsce", "lang": "pl", "stance": "NEI",
     "source": "Konkret24",
     "url": "https://konkret24.tvn24.pl/polityka/sankcje-rosja-inflacja-polska/"},
    # UA — REFUTED
    {"claim": "Генсек НАТО підтвердив членство України в Альянсі", "lang": "ua", "stance": "REFUTED",
     "source": "VoxCheck",
     "url": "https://voxukraine.org/manipulyatsiya-gensek-nato-pidtverdyv-shho-chlenstvo-ukrayiny-v-alyansi-bilshe-ne-rozglyadayetsya"},
    {"claim": "Україна продає західне озброєння на чорному ринку", "lang": "ua", "stance": "REFUTED",
     "source": "StopFake",
     "url": "https://www.stopfake.org/uk/fejk-zahidna-zbroya-pereprodayetsya-z-ukrayiny-na-chornomu-rynku/"},
    {"claim": "Біженці з України отримують більше допомоги ніж громадяни ЄС", "lang": "ua", "stance": "REFUTED",
     "source": "StopFake",
     "url": "https://www.stopfake.org/uk/fejk-bizhentsi-z-ukrayiny-otrymuyut-bilshe-pilg-nizh-gromadyany-yes/"},
    # UA — SUPPORTED
    {"claim": "Росія використовує соціальні мережі для поширення дезінформації", "lang": "ua", "stance": "SUPPORTED",
     "source": "VoxCheck",
     "url": "https://voxukraine.org/rosijski-boty-v-sotsialnykh-merezhakh/"},
    # UA — NEI
    {"claim": "Україна підписала нову угоду з ЄС про вільну торгівлю", "lang": "ua", "stance": "NEI",
     "source": "VoxCheck",
     "url": "https://voxukraine.org/ugoda-pro-asotsiatsiyu-eksport-ukrayiny-do-yes/"},
    {"claim": "Зерновий коридор повністю відновив експорт української пшениці", "lang": "ua", "stance": "NEI",
     "source": "StopFake",
     "url": "https://www.stopfake.org/uk/zernovyj-korydor-eksport-ukrayinskoyi-pshenytsi/"},
]

with tab_test:
    st.caption("Curated test claims with known fact-checks indexed in the database. "
               "Click a claim to run it through the pipeline.")

    # Legend
    st.markdown(
        "<div style='font-size:0.85rem;opacity:0.75;margin-bottom:8px;'>"
        "🟢 SUPPORTED — claim confirmed by fact-checkers &nbsp;|&nbsp; "
        "🔴 REFUTED — claim debunked &nbsp;|&nbsp; "
        "🟡 NEI — not enough information / inconclusive"
        "</div>",
        unsafe_allow_html=True,
    )

    lang_filter = st.radio(
        "Filter by language:",
        ["All", "EN", "PL", "UA"],
        horizontal=True,
        key="test_lang_filter",
    )
    lang_map = {"EN": "en", "PL": "pl", "UA": "ua"}
    selected_lang = lang_map.get(lang_filter)

    for idx, tc in enumerate(TEST_CASES):
        if selected_lang and tc["lang"] != selected_lang:
            continue

        _stance_dot = {"REFUTED": "🔴", "SUPPORTED": "🟢", "NEI": "🟡"}.get(tc["stance"], "⚪")

        col_info, col_btn = st.columns([5, 1])
        with col_info:
            st.markdown(
                f"{_stance_dot} **{tc['claim']}**  \n"
                f"<small style='opacity:0.6'>"
                f"<a href='{tc['url']}' target='_blank' style='text-decoration:none;opacity:0.8;'>"
                f"{tc['source']}</a></small>",
                unsafe_allow_html=True,
            )
        with col_btn:
            if st.button("▶ Run", key=f"test_{idx}", use_container_width=True):
                with st.spinner(L["spinner"]):
                    result = call_analyze_api(headline=tc["claim"])
                    if result:
                        st.session_state.analysis_results = result
                        st.rerun()


results = st.session_state.analysis_results

if results:
    st.divider()

    verdict = results.get("verdict", "NO_DATA")
    confidence = results.get("confidence", 0.0) or 0.0
    explanation = results.get("verdict_explanation", "")
    render_verdict_banner(verdict, confidence, explanation)

    col_meta1, col_meta2, col_meta3 = st.columns(3)
    with col_meta1:
        source_url = results.get("url", "—")
        if source_url == "headline://input":
            display_url = "Direct text input"
        else:
            display_url = source_url[:60] + "..." if len(source_url) > 60 else source_url
        st.metric(L["label_source"], display_url)
    with col_meta2:
        detected_lang = results.get("language")
        lang_display = {"en": "English", "pl": "Polski", "uk": "Українська", "ua": "Українська"}.get(
            detected_lang or "", detected_lang or "Auto-detect"
        )
        st.metric(L["label_language"], lang_display)
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
                col_num, col_priority, col_neg = st.columns([1, 2, 1])
                with col_num:
                    st.markdown(f"### Claim #{i + 1}")
                with col_priority:
                    st.progress(composite, text=f"{L['label_priority']}: {composite:.2f}")
                with col_neg:
                    if claim.get("has_negation"):
                        st.warning(L["label_negation"])

                st.markdown(f"**\"{claim.get('claim_text', '')}\"**")

                source_quote = claim.get("source_quote", "")
                if source_quote:
                    char_start = claim.get("char_start", 0)
                    char_end = claim.get("char_end", 0)
                    st.markdown(
                        f"📎 **{L['label_source']}:** \"{source_quote}\" "
                        f"[char {char_start}–{char_end}]"
                    )

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
                        claim_reviewed = match.get("claim_reviewed", "")

                        cols = st.columns([1, 3, 1, 1])
                        with cols[0]:
                            st.markdown(f"{stance_emoji(stance)} **{stance}**")
                        with cols[1]:
                            # Show fact-check title + source
                            display_title = claim_reviewed[:80] + "…" if len(claim_reviewed) > 80 else claim_reviewed
                            if url_match:
                                st.markdown(f"[{display_title}]({url_match})  \n"
                                            f"<small style='opacity:0.6'>{source}</small>",
                                            unsafe_allow_html=True)
                            else:
                                st.markdown(f"**{display_title}**  \n"
                                            f"<small style='opacity:0.6'>{source}</small>",
                                            unsafe_allow_html=True)
                        with cols[2]:
                            st.markdown(f"Score: **{score:.2f}**")
                        with cols[3]:
                            badge_title = badge.title() if isinstance(badge, str) else str(badge)
                            fresh_icon = freshness_emoji(badge if isinstance(badge, str) else str(badge))
                            st.markdown(f"{fresh_icon} {badge_title}")

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
                else:
                    st.info(L["label_no_matches"])

                st.markdown(f"**{L['label_uncertainty']}:** {uncertainty_level}")
                st.progress(uncertainty, text=f"H = {uncertainty:.2f}")
                if uncertainty_level == "HIGH":
                    # Build conflict explanation
                    match_stances = [m.get("stance", "NEI") for m in matches[:5]]
                    sup_c = sum(1 for s in match_stances if s == "SUPPORTED")
                    ref_c = sum(1 for s in match_stances if s == "REFUTED")
                    nei_c = len(match_stances) - sup_c - ref_c
                    conflict_parts = []
                    if sup_c: conflict_parts.append(f"{sup_c} SUPPORTED")
                    if ref_c: conflict_parts.append(f"{ref_c} REFUTED")
                    if nei_c: conflict_parts.append(f"{nei_c} NEI")
                    conflict_detail = " vs ".join(conflict_parts)
                    st.error(
                        f"{L['label_high_unc']}\n\n"
                        f"Top {len(match_stances)} matches conflict in stance "
                        f"({conflict_detail}). Human verification required before publishing."
                    )


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


st.divider()
st.caption(L["footer"])
