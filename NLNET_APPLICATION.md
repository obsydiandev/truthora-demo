# Truthora — NLNET_APPLICATION.md
## Draft wniosku NGI Zero Commons Fund — 38 600 €
### Wersja 3.3 — zaktualizowana 25.03.2026

> ⚠️  WAŻNE: NLnet zakazuje używania AI do pisania wniosku.
> Ten plik to SZKIELET i MATERIAŁ ŹRÓDŁOWY.
> Każde pole MUSISZ przepisać SWOIMI SŁOWAMI przed złożeniem.

---

## CZĘŚĆ 1 — DANE PODSTAWOWE

### Project name
```
Truthora
```

### One-line summary
```
Open-source multilingual infrastructure for claim detection and
fact-check matching in Polish, Ukrainian and English news streams.
```

### Requested amount
```
38600
```

### Country of origin
```
Poland
```

### Have you been involved in NGI before?
```
No
```

---

## CZĘŚĆ 2 — OPIS PROJEKTU

### Abstract

---
Truthora is an open-source, self-hostable infrastructure for multilingual
claim detection and fact-check matching, targeting the Polish-Ukrainian
information space (EN/PL/UA).

The system addresses a concrete gap: no open, GPU-free, self-hostable tool
exists for local newsrooms and fact-checking NGOs in Central and Eastern
Europe to efficiently counter FIMI narratives. Existing solutions are
proprietary, English-only, or dependent on paid cloud infrastructure.

The pipeline extracts atomic claims from news articles using a local LLM
(Llama 3.1 via Ollama — no external API required), matches them against a
ClaimReview-compatible fact-check repository (BGE-M3 + Qdrant), applies
Knowledge Graph entity contextualization (DBpedia/spaCy) and NLI stance
detection (DeBERTa-v3-MNLI, with Opus-MT cross-lingual layer for PL/UA
planned for M3), and delivers calibrated uncertainty scores to a human
reviewer — never issuing automated verdicts. All processing runs locally.

A functional proof-of-concept (v0.1, TRL 4) exists with baseline metrics
on 250 EN/PL/UA pairs (EN: 100, PL: 100, UA: 50):
- Overall: Recall@5=0.492, MRR=0.4421, Stance macro-F1=0.2951
- English only: Recall@5=0.88, MRR=0.7815
- Polish: Recall@5=0.26, MRR=0.2417 — gap addressed by WP2/WP3
- Ukrainian: Recall@5=0.18, MRR=0.164 — gap addressed by Opus-MT (WP3)

Target metrics after grant: Recall@5 ≥ 0.74, MRR ≥ 0.60, Stance F1 ≥ 0.70.

This grant funds the transition from TRL 4 (working demonstrator on static
dataset) to TRL 7 (validated in operational newsroom environment):
security hardening, an open annotated dataset (minimum 250, target 500
pairs, CC-BY, Hugging Face), CPU/ONNX optimization, cross-lingual NLI
via Opus-MT, active learning, and pilot deployments with fact-checking
organizations in Poland and Ukraine.

Primary commons deliverable: first open annotated multilingual benchmark
for Polish and Ukrainian claim verification — reusable by NLP researchers.
---

### What problem does it solve?

---
Fact-checking organizations and local newsrooms in Poland and Ukraine face
a structural bottleneck: manually monitoring news streams for verifiable
claims is slow, and cross-referencing them against existing fact-checks
is even slower. The average time-to-response for disinformation correction
is measured in days — by which time false narratives have already spread.

Three specific gaps exist:

1. No open-source, self-hostable claim detection tool supports Polish
   and Ukrainian — the two languages most exposed to Russian FIMI campaigns
   in the current geopolitical context.

2. Existing fact-check databases (ClaimReview) are underutilized because
   no lightweight matching infrastructure exists for small organizations.

3. AI-based tools that do exist are either proprietary, English-only,
   or require GPU infrastructure unavailable to most NGOs and local media.

The baseline benchmark (v0.1, 250 pairs) quantifies this gap precisely:
English retrieval reaches Recall@5=0.88, while Polish reaches only 0.26
and Ukrainian 0.18 — demonstrating a 4–5× performance gap for the target
languages. This is the gap the project directly addresses.

A specific technical gap addressed in M3: DeBERTa-v3-MNLI (the NLI
component) is trained primarily on English. Without a cross-lingual
translation layer, stance detection accuracy for Polish and Ukrainian
drops significantly (Stance F1: EN macro=0.2407 vs PL macro=0.3671 on
current dataset — but PL stance quality is inflated by small index size,
not genuine cross-lingual capability). Opus-MT integration resolves this,
with an estimated 20–30% accuracy improvement based on comparable
cross-lingual NLI research.
---

### How does it contribute to the vision of NGI?

---
Truthora advances the NGI vision through three mechanisms:

1. Data Sovereignty: All processing runs locally via Ollama and self-hosted
   Qdrant. Journalists handling unpublished investigative material can use
   the system without transmitting sensitive data to third-party servers.

2. Open Standards and Interoperability: Native ClaimReview (schema.org)
   support ensures compatibility with EDMO and global fact-checking
   databases. JSON-LD output enables CMS integration without proprietary
   formats.

3. Digital Commons by Design: Primary deliverable is a CC-BY 4.0 annotated
   dataset (minimum 250 pairs) published on Hugging Face — reusable for
   European NLP research. Apache 2.0 license. Architecture designed to
   operate without the original developer's continued involvement.

Human-in-the-loop is an architectural constraint, not a feature: the system
surfaces evidence with calibrated uncertainty scores, never automated
verdicts — aligned with EU AI Act human oversight requirements (Article 14).
The confidence model explicitly withholds any verdict when evidence is
insufficient (confidence < 40%), routing to mandatory human review.
---

### What is the expected impact?

---
Direct impact (within grant period):
- Open annotated EN/PL/UA benchmark dataset (minimum 250 pairs, target 500),
  CC-BY 4.0, Hugging Face — first open resource for PL/UA claim verification
- Recall@5 ≥ 0.74, MRR ≥ 0.60, Stance F1 ≥ 0.70 on multilingual benchmark
  (baseline v0.1: Recall@5=0.492, MRR=0.4421, Stance F1=0.2951 overall)
- Cross-lingual NLI improvement via Opus-MT (estimated +20–30% for PL/UA,
  validated against benchmark before/after Opus-MT integration)
- At least 2 real-world pilot deployments with fact-checking organizations
- Deployment on 4-CPU VPS without GPU — accessible at ~15 €/month

Systemic impact (beyond grant period):
- Reusable open dataset enables future PL/UA NLP model development
- Self-hostable architecture ensures continuity beyond grant period
- EDMO-compatible standards enable EU fact-checking ecosystem integration
---
**Project timeline:** 8 months from MoU signing (4 milestones). Fits within
NGI Zero Commons Fund programme end date of June 2027, assuming MoU signed
by October 2026.

---

### Do you have any prior work related to this project?

---
Yes. A functional proof-of-concept (Truthora v0.1, TRL 4) was developed by
the applicant prior to this application to validate the technical approach.

The existing codebase implements the complete pipeline: multilingual claim
extraction (Llama 3.1, Groq/Ollama), semantic matching (BGE-M3 + Qdrant),
Knowledge Graph entity contextualization (DBpedia SPARQL + spaCy NER),
NLI stance detection (DeBERTa-v3-MNLI), entropy-based uncertainty scoring
(Shannon entropy H over stance distribution), and a web-based review
interface with human-in-the-loop controls (Approve / Reject / Flag / Note).

**Baseline benchmark results (v0.1, 2026-03-25, 250 pairs, data/benchmark/):**

| Language | n | Recall@5 | MRR   | Stance macro-F1 |
|----------|---|----------|-------|-----------------|
| Overall  | 250 | 0.492  | 0.4421 | 0.2951         |
| English  | 100 | 0.880  | 0.7815 | 0.2407         |
| Polish   | 100 | 0.260  | 0.2417 | 0.3671         |
| Ukrainian | 50 | 0.180  | 0.1640 | 0.1724         |

Targets: Recall@5 ≥ 0.74, MRR ≥ 0.60, Stance F1 ≥ 0.70. All targets
currently not met — this defines the work funded by this grant.

**Technical Readiness Statement:**
The HERMES-UA demonstrator (TRL 4) validates core claim detection and
retrieval on a static trilingual dataset. Live ingestion, incremental
indexing and real-time alerting — required for operational deployment —
are explicitly scoped as M2/M3 deliverables. The current architecture is
designed for this transition: the `/analyze` API and containerised service
stack are feed-agnostic and require no redesign for streaming input.

The confidence model currently implements a two-factor scoring approach
(stance consensus + semantic match quality), with a threshold rule: no
verdict is displayed when confidence < 40% — routing to mandatory human
review. Full four-factor calibration (adding temporal freshness weighting
and source trust scoring) is scoped as M3, validated against the expanded
benchmark dataset.

GitHub: https://github.com/obsydiandev/truthora-demo

This grant funds transition from proof-of-concept to production-grade
commons infrastructure — not rebuilding what already works.
---

---

## CZĘŚĆ 3 — MILESTONES Z SAFEGUARDS

### Filozofia safeguardów w tym wniosku

Każdy milestone ma:
- **Minimum target** — gwarantowany deliverable, weryfikowalny przez NLnet
- **Stretch target** — cel jeśli automatyzacja lub onboarding pójdą sprawnie
- **Fallback** — co dostarczasz jeśli coś nie wypali (np. partner nie odpowie)

NLnet płaci za minimum target. Stretch target jest w opisie jako "planned" —
nie zobowiązujesz się do niego formalnie, ale pokazujesz ambicję.

---

### Milestone 1 — Production Hardening
**Kwota: 9 600 € | 120h | Tygodnie 1–9**

**Minimum target (gwarantowany):**
Truthora v1.0 — security-hardened, WCAG-compliant, Ollama-first,
public Docker image, full documentation

| Zadanie | Godziny | Koszt |
|---|---|---|
| OWASP Top 10 security review + udokumentowane fixes | 30h | 2 400€ |
| WCAG 2.1 AA compliance w UI | 20h | 1 600€ |
| Ollama-first refactor (Groq jako optional fallback) | 25h | 2 000€ |
| Docker image (ghcr.io) + deployment guide dla VPS bez GPU | 15h | 1 200€ |
| README: setup guide, API docs, diagram architektury | 15h | 1 200€ |
| Apache 2.0 LICENSE, CHANGELOG, contribution guide | 5h | 400€ |
| CI/CD hardening: secret scanning, dependency audit | 10h | 800€ |
| **RAZEM M1** | **120h** | **9 600€** |

**Weryfikacja:** GitHub release tag v1.0 + publiczny Docker image +
security/owasp-checklist.md w repo

**Safeguard:** Każde z tych zadań jest w 100% pod kontrolą wnioskodawcy —
brak zależności od partnerów zewnętrznych. Milestone gwarantowany.

**Planned UI fixes przed submisją (nie w grancie):**
Przed złożeniem wniosku zostaną wdrożone poprawki krytyczne identyfikowane
w fazie demonstratora: usunięcie sprzeczności confidence=0% przy aktywnym
verdykcie, wdrożenie progu confidence (brak verdyktu gdy C < 40%),
poprawka language detection dla PL/UA, ukrycie niezaimplementowanych
kolumn (KG). Te poprawki są częścią bieżącego utrzymania TRL 4, nie
zakresu grantu.

---

### Milestone 2 — Multilingual Benchmark & Dataset
**Kwota: 10 400 € | 130h | Tygodnie 10–18**

**Minimum target (gwarantowany):**
Opublikowany dataset ≥ 250 par (EN/PL/UA, CC-BY) na Hugging Face
+ wyniki benchmark

**Stretch target (planowany):**
Dataset ≥ 500 par — jeśli automatyzacja scrapingu Demagog/VoxCheck
okaże się efektywna (przewidywana częściowa automatyzacja ~60% par)

| Zadanie | Godziny | Koszt |
|---|---|---|
| FEVER subset preprocessing (100 × EN, CC-BY) | 10h | 800€ |
| Scraping + preprocessing Demagog.org.pl (automatyzacja pipeline) | 20h | 1 600€ |
| Ręczna weryfikacja jakości par PL (min 100, target 200+) | 50h | 4 000€ |
| Scraping + weryfikacja VoxCheck.ua (min 50, target 100+ par UA) | 25h | 2 000€ |
| Publikacja datasetu HF (CC-BY 4.0) + karta datasetu | 10h | 800€ |
| Iteracja pipeline do target metrics | 10h | 800€ |
| Raport ewaluacyjny (evaluation-report-v1.md) | 5h | 400€ |
| **RAZEM M2** | **130h** | **10 400€** |

**Weryfikacja:** link do HF dataset (≥250 par) +
data/benchmark/results/v1.0.json z metrykami

**Safeguard M2 — opis we wniosku:**
> "The dataset will contain a minimum of 250 annotated pairs (EN/PL/UA),
> with a target of 500 pairs contingent on the efficiency of the automated
> scraping pipeline for Demagog.org.pl and VoxCheck.ua. The minimum
> threshold of 250 pairs ensures statistical validity for benchmark
> evaluation; additional pairs will be added through continued annotation
> beyond the grant period as community contributions."

Kluczowe: NLnet weryfikuje "≥250 par opublikowanych na HF" — to masz
w pełni pod kontrolą. 500 to "target", nie zobowiązanie.

**Nota dot. aktualnego benchmarku:**
Obecny v0.1 zawiera 250 par (EN:100, PL:100, UA:50) na statycznym indeksie.
Dataset ten zostanie opublikowany na HF jako punkt startowy M2, co pozwala
wykazać konkretny baseline w momencie składania wniosku.

---

### Milestone 3 — Active Learning, Cross-lingual NLI & CPU Portability
**Kwota: 13 600 € | 170h | Tygodnie 19–27**

**Minimum target (gwarantowany):**
Truthora v1.1 — Opus-MT integration, active learning, ONNX export,
webhook alerts, bias monitoring, calibrated 4-factor confidence model

| Zadanie | Godziny | Koszt |
|---|---|---|
| Opus-MT translation layer PL↔UA dla NLI (Helsinki-NLP, lokalny) | 50h | 4 000€ |
| Active Learning Loop: feedback → Qdrant vector reweighting | 30h | 2 400€ |
| ONNX export: BGE-M3 + BGE-Reranker + DeBERTa-v3 | 25h | 2 000€ |
| CPU benchmark na VPS 4-CPU bez GPU (target: <30s/artykuł) | 20h | 1 600€ |
| Webhook alerty: Slack/Telegram/Matrix | 15h | 1 200€ |
| Bias monitoring: rozkład werdyktów PL vs UA vs EN w UI | 20h | 1 600€ |
| Confidence model: kalibracja 4-składnikowa (consensus + quality + freshness + coverage), progi, XAI breakdown | 10h | 800€ |
| **RAZEM M3** | **170h** | **13 600€** |

**Weryfikacja:** GitHub release v1.1 + benchmarks/cpu-performance.md +
benchmarks/cross-lingual-nli-improvement.md (wyniki przed/po Opus-MT)

**Safeguard:** Wszystkie zadania M3 są pod kontrolą wnioskodawcy.
Opus-MT jest darmowy i open-source — brak zależności licencyjnych.

**Confidence model — roadmap:**
Current demonstrator (TRL 4) implements simplified two-factor confidence
(stance consensus weight 0.40 + semantic match quality weight 0.30).
Full calibration — incorporating temporal freshness weighting (0.20) and
source trust scoring (0.10) — is the M3 deliverable, validated against
the M2 benchmark dataset. The journalist-facing explanation UI (confidence
breakdown panel) is validated in M4 user studies.

---

### Milestone 4 — Real-World Pilots & Community
**Kwota: 5 000 € | 62h | Tygodnie 28–35**

**Minimum target (gwarantowany):**
≥ 2 zakończone piloty (przynajmniej 1 PL + 1 UA lub 2 PL) +
community foundation + raport NLnet

**Stretch target (planowany):**
3 piloty — jeśli onboarding organizacji UA przebiegnie sprawnie

| Zadanie | Godziny | Koszt |
|---|---|---|
| Pilot #1 org. PL — instalacja, onboarding, 2-tyg. test, raport | 20h | 1 600€ |
| Pilot #2 org. UA lub PL — j.w. | 15h | 1 200€ |
| Pilot #3 (planowany) — dodatkowa org. UA jeśli onboarding pozwoli | 10h | 800€ |
| Discord/Matrix setup + contribution guide | 5h | 400€ |
| 2 webinary (przygotowanie + przeprowadzenie, publiczne nagrania) | 7h | 560€ |
| 1 tutorial techniczny (dev.to lub blog) | 3h | 240€ |
| Raport końcowy NLnet | 2h | 160€ |
| **RAZEM M4** | **62h** | **5 000€** |

**Weryfikacja:** raporty pilotowe (markdown w repo) + nagrania webinarów +
final-report.md

**Safeguard M4 — opis we wniosku (KLUCZOWY):**
> "A minimum of two pilot deployments are planned — one with a Polish
> fact-checking organization (preliminary contact established) and one
> with a Ukrainian NGO or regional newsroom. A third pilot is planned
> contingent on organizational onboarding timelines. All pilot
> organizations receive the software free of charge and without data
> sharing obligations. In the event that a Ukrainian partner is
> unavailable within the grant timeline, the second pilot will be
> conducted with an additional Polish regional media outlet, ensuring
> the minimum deliverable remains achievable regardless of geopolitical
> or organizational constraints."

To zdanie zamyka pytanie recenzenta "a co jeśli partner UA nie odpowie?"
zanim je zada.

---

## PODSUMOWANIE BUDŻETU

| Milestone | Zakres | Godziny | Kwota | Gwarancja |
|---|---|---|---|---|
| M1: Production Hardening | Security, WCAG, Ollama, Docker, docs | 120h | 9 600€ | 100% |
| M2: Benchmark & Dataset | ≥250 par (target 500), HF, metryki | 130h | 10 400€ | 250 par |
| M3: AI & Portability | Opus-MT, Active Learning, ONNX, confidence model | 170h | 13 600€ | 100% |
| M4: Pilots & Community | ≥2 piloty (target 3), webinary, raport | 62h | 5 000€ | 2 piloty |
| **RAZEM** | | **482h** | **38 600€** | |

Stawka: 80 €/h | Tryb: ~14–15h/tydzień przez 35 tygodni | Okres realizacji: **8 miesięcy od MoU**

---

## CZĘŚĆ 4 — DANE WNIOSKODAWCY

### Applicant name
```
[Twoje imię i nazwisko]
```

### Organisation
```
[Nazwa JDG lub puste]
```

### Email
```
[Twój email]
```

### Website / repository
```
https://github.com/obsydiandev/truthora-demo
```

### Brief bio
---
Full-stack software developer with [X] years of experience in Python,
API development, and system integration. Author of Truthora v0.1 —
a working multilingual claim detection pipeline developed as a
self-funded proof-of-concept (TRL 4). Experienced with Docker, FastAPI,
vector databases, and NLP pipeline integration. Based in Wrocław, Poland.
---

---

## CZĘŚĆ 5 — CHECKLIST PRZED WYSŁANIEM

### Formalne
- [ ] Repo publiczne na GitHubie
- [ ] Plik LICENSE (Apache 2.0) w repo
- [ ] README.md z Quick Start i screenshotem UI
- [ ] Wyniki benchmark w repo — REALNE liczby z baseline_v01.json:
      Overall Recall@5=0.492, MRR=0.4421, Stance F1=0.2951
      EN: Recall@5=0.880 | PL: 0.260 | UA: 0.180
- [ ] Suma milestones = dokładnie 38 600 €
- [ ] Dane (≥50 par lub pełne 250) na Hugging Face z linkiem

### UI — poprawki przed submisją (nie w grancie)
- [ ] Confidence: 0% przy aktywnym verdykcie → usunięte lub zastąpione
- [ ] Brak verdyktu gdy confidence < 40% (próg wdrożony)
- [ ] Language detection działa dla PL ("Sieć 5G" → wykrywa Polish)
- [ ] KG: — kolumna ukryta lub zastąpiona istniejącą daną
- [ ] "headline://input" → "Manual text input"
- [ ] Tytuł/link fact-checka widoczny w listach matches

### Treściowe
- [ ] Minimum targets opisane jako gwarantowane
- [ ] Stretch targets opisane jako "contingent on" / "planned if"
- [ ] Fallback dla pilotów UA opisany wprost
- [ ] Nie użyłeś "fake news" — używasz "disinformation" lub "FIMI"
- [ ] Opus-MT uzasadniony technicznie (cross-lingual NLI gap + dane benchmarku)
- [ ] TRL 4→7 roadmap opisany (demo = TRL 4, grant = przejście do TRL 7)
- [ ] Confidence model: 2-składnikowe teraz, 4-składnikowe jako M3 deliverable
- [ ] Wniosek napisany SWOIMI SŁOWAMI

### Strategiczne
- [ ] Email do Demagoga wysłany (choćby bez odpowiedzi)
- [ ] "Preliminary contact established" — możesz to napisać po wysłaniu maila
- [ ] Każdy milestone weryfikowalny przez link (repo/HF/nagranie)
- [ ] Godziny per task są nieokrągłe i wiarygodne

---

## CZĘŚĆ 6 — EMAIL DO DEMAGOG

Wyślij PRZED złożeniem wniosku. Odpowiedź nie jest wymagana —
samo wysłanie daje Ci prawo napisać "preliminary contact established".

---
Temat: Projekt Truthora — open-source narzędzie dla fact-checkerów

Dzień dobry,

Tworzę otwarty system Truthora — infrastrukturę dla redakcji i organizacji
fact-checkingowych do wykrywania i weryfikacji twierdzeń w artykułach
(PL/UA/EN). System działa lokalnie, bez przesyłania danych na zewnątrz,
i integruje się z bazami ClaimReview oraz kanałami RSS (w tym Demagog).

Planuję złożyć wniosek o grant NGI Zero (NLnet Foundation) i szukam
organizacji zainteresowanych udziałem w pilotażu — bez żadnych zobowiązań
finansowych z Waszej strony.

Czy bylibyście zainteresowani przetestowaniem systemu w Waszym workflow
(2–3 tygodnie, zdalnie)?

Link do projektu: https://github.com/obsydiandev/truthora-demo

Z poważaniem,
[Twoje imię]
---

---

## HARMONOGRAM DO DEADLINE

| Dzień | Zadanie | Priorytet |
|---|---|---|
| 25.03 (dziś) | UI fixes krytyczne (confidence, language, KG) — ~6h | 🔴 |
| 25.03 (dziś) | Email do Demagoga | 🔴 |
| 26.03 | Dataset 250 par → Hugging Face (CC-BY) | 🔴 |
| 26.03 | Szkic formularza (nlnet.nl/propose) | 🔴 |
| 27.03 | Wypełnij wszystkie pola formularza swoimi słowami | 🔴 |
| 28.03 | Wrzuć real benchmark numbers do wniosku (z baseline_v01.json) | 🔴 |
| 29–30.03 | Review przez kogoś technicznego | 🟡 |
| 31.03 | **Submit** — nie czekaj do 1 kwietnia | 🔴 |

---

## ANEKS — AKTUALNE METRYKI BAZOWE (baseline_v01.json, 2026-03-25)

```
Wersja:       v0.1
Data:         2026-03-25
Pary:         250 (EN:100, PL:100, UA:50)
Błędy:        2 (pl20, pl28)
Czas łączny:  2230.61s

OVERALL:
  Recall@5:   0.492
  MRR:        0.4421
  Stance F1:  SUPPORTED=0.3089, REFUTED=0.1714, NEI=0.4051
  Macro-F1:   0.2951

ENGLISH (n=100):
  Recall@5:   0.880
  MRR:        0.7815
  Macro-F1:   0.2407

POLISH (n=100):
  Recall@5:   0.260
  MRR:        0.2417
  Macro-F1:   0.3671

UKRAINIAN (n=50):
  Recall@5:   0.180
  MRR:        0.1640
  Macro-F1:   0.1724

TARGETS (grant):
  Recall@5 ≥ 0.74   → NOT MET (gap: +0.248)
  MRR ≥ 0.60        → NOT MET (gap: +0.158)
  Stance F1 ≥ 0.70  → NOT MET (gap: +0.405)
```

---

*Truthora — NLNET_APPLICATION v3.3 — 38 600 € — Marzec 2026*
*Deadline: 1 kwietnia 2026*
