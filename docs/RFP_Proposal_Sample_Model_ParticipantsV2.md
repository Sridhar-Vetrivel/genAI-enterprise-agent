# IMPACT pSIDDHI — RFP + PROPOSAL MODEL v2
**S2-DA-07 · ₹2,500 Budget**

---

# IMPACT pSIDDHI
## RFP + PROPOSAL + VALIDATION
### COMPLETE SAMPLE MODEL (v2)

**Sample Use Case:** S2-DA-07 — NLP-Based Customer Feedback Analyser  
**Semester 2 · Data Track · pSiddhi-2026-01**  
**Budget: ₹2,500 (Fixed Ceiling) · QA Mandatory · AI Core**

---

## Document Structure

| Part | Document | Who Creates It |
|------|----------|----------------|
| A | RFP Document | L&D Team (the Customer) |
| B | Participant Proposal (with QA + Budget Strategy) | Participant (the Vendor) |
| C | AI Validation Report | AI Engine (automated) |
| D | L&D Final Decision | L&D Team (human sign-off) |

---

# PART A — RFP ISSUED BY L&D (THE CUSTOMER)

# Request for Proposal (RFP)
**Impact pSiddhi — pSiddhi-2026-01 · Semester 2 · Data Track**

| RFP Field | Content |
|-----------|---------|
| Program | Impact pSiddhi — pSiddhi-2026-01 |
| RFP Issued By | L&D Team (acting as Customer) |
| Topic ID | S2-DA-07 |
| Topic Title | NLP-Based Customer Feedback Analyser |
| Semester & Category | Semester 2 — Data |
| Budget Ceiling | ₹2,500 per participant for the semester (FIXED — non-negotiable) |
| Timeline | Weeks 4–17 (Development Phase 1 + Phase 2) |
| Proposal Due Date | End of Week 2 |

---

## Problem Statement

Companies collect thousands of customer feedback entries from surveys, reviews, support tickets, and social media channels every month. However, processing this feedback at scale is impractical with manual methods. Insights are delayed by weeks, subjective in interpretation, and often miss emerging patterns. L&D requires a solution that can ingest unstructured customer feedback from multiple sources, perform automated sentiment analysis and topic clustering using NLP/AI, and produce a structured weekly insights report with actionable recommendations.

---

## Requirements

- Solution must address the problem end-to-end — from data ingestion to insight delivery
- AI/NLP must be a core component (not a bolt-on feature)
- A working POC/demo must be delivered by Week 17
- All tools and costs must be justified and stay within ₹2,500
- QA is mandatory — proposal must include a comprehensive QA strategy
- Documentation and evidence must be submitted on Moodle at each checkpoint
- The solution must handle at least 3 feedback sources (e.g., survey CSV, review API, support tickets)

---

## Budget Guidance (₹2,500 Fixed Ceiling)

> ⚠️ **The budget ceiling of ₹2,500 per participant per semester is FIXED. Proposals exceeding this ceiling will be automatically rejected. Design your solution to maximize free tiers and open-source tools.**

---

## QA Mandate

> 🔴 **QA is mandatory in every semester. Your proposal MUST include a QA Strategy section. Proposals without QA strategy will be rejected as incomplete.**

Your QA Strategy must cover:

- **Test approach:** How will you verify your solution works correctly?
- **Test types:** Unit tests, integration tests, E2E tests — which apply to your use case?
- **AI-assisted QA:** How will you use AI to improve testing? (Applying Sem 1 QA skills)
- **Test coverage target:** What percentage of your code/pipeline will be tested?
- **Data validation:** How will you ensure input data quality and output accuracy?

---

## Evaluation Criteria

| Criterion | What We Look For | Weight |
|-----------|------------------|--------|
| Problem Understanding | Genuine grasp of business context, not just paraphrasing the RFP | 15% |
| Solution Quality | Sound architecture, practical approach, clear data flow | 20% |
| AI Integration Depth | AI is genuinely core to the solution, not a bolt-on | 20% |
| QA Strategy | Comprehensive testing approach with AI-assisted QA | 15% |
| Budget & Cost Justification | Within ₹2,500 ceiling, free tiers maximized, every cost justified | 15% |
| Timeline Feasibility | Realistic week-by-week plan with meaningful milestones | 15% |

---

## Deliverables Expected

| Checkpoint | Expected Deliverable |
|------------|----------------------|
| Week 10 | Working data ingestion pipeline + initial NLP model with sentiment scoring on sample data + unit tests passing + mid-term documentation on Moodle |
| Week 17 | Complete E2E solution: multi-source ingestion, NLP sentiment + topic clustering, automated weekly report, QA test suite with results, live demo. All evidence on Moodle. |

---

# PART B — PROPOSAL SUBMITTED BY PARTICIPANT (THE VENDOR)

# Use Case Proposal
**Response to RFP: S2-DA-07 — NLP-Based Customer Feedback Analyser**

---

## 1. Topic ID & Title

| Field | Detail |
|-------|--------|
| Topic ID | S2-DA-07 |
| Topic Title | NLP-Based Customer Feedback Analyser |

---

## 2. Participant Details

| Field | Detail |
|-------|--------|
| Full Name | Ragasandhya |
| Employee ID | EMP-2024-0847 |
| Semester History | Sem 1 completed in pSiddhi-2025-02 (AI Enabled QA — Data QA track) |

---

## 3. Semester & Category

Semester 2 — Data Track (E2E Development with AI, QA Mandatory)

---

## 4. Problem Understanding

In most organizations, customer feedback is collected across multiple channels — post-purchase surveys (Google Forms/Typeform), app store reviews, customer support emails, and social media mentions. While the data exists in abundance, it sits in disconnected silos and is reviewed manually by a small team, often weeks after collection.

This creates three core business problems:

**Delayed insights** — By the time feedback is aggregated and reviewed manually, the window for corrective action has closed. A product defect reported in Week 1 may only surface in the monthly report in Week 4.

**Subjective interpretation** — Different team members classify the same feedback differently. There is no standardized sentiment or topic taxonomy, making trend analysis unreliable.

**Missed patterns** — Manual review focuses on individual complaints rather than detecting emerging clusters. A slow rise in "delivery delay" mentions across 3 channels simultaneously goes unnoticed until it becomes a crisis.

The business needs an automated, AI-driven pipeline that can ingest feedback from multiple sources, classify sentiment and extract topics using NLP, and surface weekly trend reports — reducing human review time from 20+ hours/week to under 2 hours of report validation.

---

## 5. Proposed Solution

I propose building **FeedbackIQ** — an end-to-end NLP pipeline with three layers, designed entirely within the ₹2,500 budget using free tiers and open-source tools:

### Layer 1: Multi-Source Data Ingestion
- CSV upload module for survey data (Google Forms / Typeform exports)
- REST API connector for app store reviews (Apple App Store / Google Play via public APIs)
- Email parser for support ticket data (parsing forwarded email exports in .eml/.csv format)
- All data normalized into a unified schema: `[source, timestamp, text, metadata]`
- Data stored in SQLite (zero cost) for POC; PostgreSQL-ready for production

### Layer 2: NLP Processing Engine (AI Core)
- **Sentiment Analysis:** DistilBERT (HuggingFace, free open-source) classifying Positive / Neutral / Negative with confidence scores
- **Topic Extraction:** BERTopic (free, open-source) for unsupervised topic clustering — auto-discovers themes like "delivery delays", "pricing concerns"
- **Keyword Extraction:** KeyBERT (free, open-source) to surface top keywords per cluster
- **Trend Detection:** Week-over-week comparison of topic volumes and sentiment shifts
- All models run locally on AWS EC2 t3.micro (free tier) or Google Colab (free) during development

### Layer 3: Reporting & Dashboard
- Streamlit Community Cloud (free) dashboard: sentiment distribution, topic clusters, source breakdown, drill-down
- Weekly PDF report auto-generated using Claude Sonnet API for narrative summaries (low-cost, ₹200–400 for entire semester)
- Alert system: email notification when negative sentiment spikes >20% vs previous week

### Architecture
```
Sources (CSV/API/Email)
    → Python Scripts
    → SQLite
    → NLP Pipeline (DistilBERT + BERTopic + KeyBERT) on EC2 Free Tier
    → Streamlit Dashboard (free) + Claude API (report only)
    → Weekly PDF
```

---

## 6. Tools, Subscriptions & Cost Breakdown

| Tool / Service | Purpose | Tier | Cost/Sem | Justification |
|----------------|---------|------|----------|---------------|
| AWS EC2 t3.micro | Compute + NLP models | Free tier | ₹0 | 750 hrs/month free for 12 months. Sufficient for batch NLP. |
| SQLite | Database | Free | ₹0 | Embedded DB, no server needed. Handles 100K+ records for POC. |
| AWS S3 (5GB) | Raw file storage | Free tier | ₹0 | 5GB free for 12 months. Sufficient for CSV/email files. |
| HuggingFace Models | DistilBERT, BERTopic, KeyBERT | Free | ₹0 | Open-source models. Downloaded once, run locally. |
| Streamlit Community Cloud | Dashboard hosting | Free | ₹0 | Free hosting for public Streamlit apps from GitHub. |
| GitHub (free tier) | Version control + CI/CD | Free | ₹0 | Unlimited repos. GitHub Actions: 2,000 min/month free. |
| Gemini API | Weekly report narratives | Pay-per-use | ₹300 | ~14 weekly reports. Gemini is cost-efficient. Not used for core NLP. |
| AWS CloudWatch | Monitoring + alerts | Free tier | ₹0 | 10 alarms + 1M API calls free. |
| Pytest + Selenium | QA test suite | Free | ₹0 | Open-source testing frameworks. |
| AWS SES (email alerts) | Sentiment spike alerts | Free tier | ₹0 | 62,000 emails/month free from EC2. |
| Domain + SSL (optional) | Custom URL for dashboard | Paid | ₹400 | Optional. Streamlit default URL works for POC demo. |
| Contingency Buffer | Unexpected overages | — | ₹800 | Reserved for API overages or additional compute if needed. |
| **TOTAL** | | | **₹1,700** | **68% of ceiling used. ₹800 buffer remaining.** |

> **Budget Efficiency:** 8 of 11 tools are FREE (open-source or free tier). Only Claude API and optional domain cost money. Core NLP is 100% free.

---

## 7. Timeline & Effort

### Phase 1: Weeks 4–9 — Foundation + Core NLP + Initial QA

| Week | Task | Deliverable | QA Activity |
|------|------|-------------|-------------|
| Wk 4 | AWS setup (EC2, S3, CloudWatch). Design unified feedback schema. Build CSV ingestion. | Infra ready + CSV pipeline | Unit tests for schema validation |
| Wk 5 | API connector for app store reviews. Email parser for support tickets. Store in SQLite. | All 3 ingestion sources working | Integration tests for each source |
| Wk 6 | Implement DistilBERT sentiment model. Fine-tune on sample data. Validate accuracy. | Sentiment model >85% accuracy | Model accuracy test suite (precision, recall, F1) |
| Wk 7 | BERTopic for topic clustering. KeyBERT for keywords. Test on real data. | Meaningful topic clusters | Topic coherence validation tests |
| Wk 8 | E2E integration: ingestion → NLP pipeline → results DB. Test with 500+ entries. | Full pipeline running E2E | E2E pipeline test + data integrity checks |
| Wk 9 | Bug fixes. Mid-term documentation. Prepare demo. Upload evidence to Moodle. | Mid-term ready | All Phase 1 tests passing in CI |

### Phase 2: Weeks 11–16 — Dashboard + Reporting + Full QA Suite

| Week | Task | Deliverable | QA Activity |
|------|------|-------------|-------------|
| Wk 11 | Incorporate mid-term feedback. Streamlit dashboard skeleton with sentiment overview. | Dashboard v1 live | Dashboard rendering tests |
| Wk 12 | Topic cluster visualization. Source-wise breakdown. Drill-down. | Full dashboard visualizations | Cross-browser UI validation |
| Wk 13 | Weekly PDF report generator with Claude Sonnet API for narratives. | Auto-generated weekly reports | Report content accuracy tests |
| Wk 14 | Trend detection (WoW comparison). Alert system for sentiment spikes. | Trend + alert system working | Alert trigger threshold tests |
| Wk 15 | Scale testing with 2,000+ entries across all sources. Performance optimization. | System validated at scale | Load testing + performance benchmarks |
| Wk 16 | Final documentation. Demo video. Presentation prep. Upload all to Moodle. | Final review ready | Full regression suite + QA report |

**Total Effort:** ~150 hours across 12 weeks (~12.5 hrs/week). QA activities embedded in every week.

---

## 8. Tech Stack

| Layer | Technologies | Cost |
|-------|-------------|------|
| Language | Python 3.11 | Free |
| NLP / AI Models | DistilBERT, BERTopic, KeyBERT (all HuggingFace open-source) | Free |
| AI API (reports only) | Claude Sonnet API — ONLY for weekly report narrative generation | ₹300/sem |
| Database | SQLite (embedded, zero-config) | Free |
| Cloud Compute | AWS EC2 t3.micro (free tier) | Free |
| Dashboard | Streamlit Community Cloud | Free |
| Data Processing | Pandas, NumPy, scikit-learn | Free |
| Visualization | Plotly, Matplotlib | Free |
| QA Framework | Pytest + Selenium + GitHub Actions CI | Free |
| Monitoring | AWS CloudWatch free tier | Free |
| Version Control | Git + GitHub | Free |

> **10 of 12 tech stack components are completely FREE.** Only Claude API (₹300) and optional domain (₹400) have costs.

---

## 9. Expected Deliverable / POC

At the Week 17 Final Review, I will demonstrate:

- Live data ingestion from 3 sources (CSV upload, API pull, email parse) into SQLite
- Real-time NLP processing: sentiment classification with confidence scores + automatic topic clustering
- Interactive Streamlit dashboard with sentiment trends, topic clusters, source breakdowns, drill-down
- Automated weekly PDF report with AI-generated narrative summaries (Claude Sonnet)
- Alert demonstration: email alert triggered when negative sentiment spikes >20% WoW
- Scale demo: 2,000+ feedback entries processed end-to-end
- QA test suite: all tests passing in GitHub Actions CI with >80% code coverage
- Complete documentation: architecture, API docs, test results, user guide on Moodle

---

## 10. QA Strategy (Mandatory)

> This section is **MANDATORY** for Sem 2, 3, and 4 proposals. QA skills from Sem 1 must be applied.

### 10.1 Test Approach

I will apply a multi-layered testing strategy covering every component of the FeedbackIQ pipeline. Testing is embedded in every development week (see Timeline), not bolted on at the end. CI/CD via GitHub Actions ensures all tests run automatically on every code push.

### 10.2 Test Types & Coverage

| Test Type | What It Covers | Tool | Target Coverage |
|-----------|---------------|------|-----------------|
| Unit Tests | Schema validation, data normalization functions, sentiment scoring logic, topic extraction functions | Pytest | >80% code coverage |
| Integration Tests | CSV ingestion → DB, API → DB, Email → DB, NLP pipeline → results DB | Pytest + fixtures | All 3 sources tested |
| E2E Tests | Full pipeline: raw input → processed output → dashboard → report | Pytest + Selenium | 3 E2E scenarios |
| Model Accuracy Tests | Sentiment precision/recall/F1 on held-out test set, topic coherence score | scikit-learn metrics | >85% F1 score |
| Data Validation | Input schema compliance, null/duplicate detection, output completeness | Great Expectations (free) | Zero invalid records |
| Load Testing | Pipeline performance with 2,000+ records, dashboard response time | Locust (free) | <30s for 2K records |
| Regression Suite | All above tests run automatically on every push via GitHub Actions | GitHub Actions CI | 100% pass on merge |

### 10.3 AI-Assisted QA (Applying Sem 1 Skills)

Drawing from my Sem 1 (AI Enabled QA — Data QA track) experience, I will apply AI to the QA process itself:

- **AI-powered test data generation:** Use Claude to generate diverse synthetic feedback entries covering edge cases (multilingual, sarcastic, ambiguous sentiment)
- **Anomaly detection in pipeline outputs:** Use statistical checks to flag when NLP results deviate from expected distributions (e.g., if 95% of entries suddenly classify as neutral)
- **Automated regression analysis:** Compare NLP model outputs before/after code changes to detect accuracy drift

### 10.4 QA Deliverables

- Pytest test suite with >80% code coverage (uploaded to GitHub)
- GitHub Actions CI pipeline running all tests on every push
- QA Report: test results summary, coverage metrics, model accuracy benchmarks
- Load test results: pipeline throughput and latency benchmarks
- All QA evidence uploaded to Moodle at Week 10 (partial) and Week 17 (complete)

---

## 11. Risk & Mitigations

| # | Risk | Impact | Mitigation | Fallback |
|---|------|--------|------------|----------|
| 1 | Model accuracy <85% on real data | Unreliable sentiment classification | Fine-tune on domain data. Use ensemble of 2 models. | Fall back to TextBlob + manual rules |
| 2 | AWS free tier limits exceeded | Unexpected cost, approaching ₹2,500 | CloudWatch budget alert at ₹1,200. Use on-demand only. | Switch to Google Colab (free) for compute |
| 3 | App store API rate limiting | Cannot ingest review data | Pre-download review datasets as CSV. | Use web scraping (BeautifulSoup) as backup |
| 4 | BERTopic produces incoherent clusters | Meaningless topic groups in reports | Test multiple min_topic_size values. | Semi-supervised mode with seed topics |
| 5 | Claude API downtime during report generation | Weekly report not generated on time | Cache last successful report as template. | Generate report without narrative (data-only PDF) |

---

## 12. Semester Alignment

This use case aligns with Semester 2 (E2E Development + AI, QA Mandatory) and the Data track because:

- It is a full end-to-end data solution — from ingestion to insights delivery
- AI (NLP) is the core engine. Without DistilBERT + BERTopic, the solution does not function.
- It covers the complete data lifecycle: collection → storage → processing → analysis → visualization → reporting
- QA is embedded throughout — applying Sem 1 AI-QA skills with a comprehensive test strategy
- Budget is efficiently managed at ₹1,700 of ₹2,500 ceiling using free tiers and open-source tools
- Real business impact: 20+ hrs/week manual review reduced to <2 hrs of report validation
