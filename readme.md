# FinSight — Personal Finance Advisor

FinSight is a web application that reads your bank statement (CSV or PDF), categorizes every transaction automatically, detects unusual spending patterns, and lets you chat with an AI advisor that answers questions specifically about your own financial data — not generic advice.

In short: upload your bank statement, get an instant breakdown of where your money went, and ask questions like "Where am I wasting the most money?" or "How much should I be saving?" The AI answers using your actual numbers.

---

## How It Works

1. You upload a CSV or PDF bank statement.
2. The backend parses and categorizes every transaction using a rule engine (Swiggy goes to Food & Dining, Uber goes to Transport, and so on).
3. A statistical anomaly detector flags unusual transactions, category spikes, and budget overruns.
4. A RAG (Retrieval-Augmented Generation) pipeline retrieves relevant financial knowledge (e.g., the 50/30/20 rule, SIP basics, debt management) and combines it with your data before calling the LLM.
5. You interact with the AI advisor via a chat interface that keeps your conversation history in context.

---

## Features

- Parses CSV and PDF bank statements with flexible column detection
- Auto-categorizes transactions into 13 categories (Food, Transport, Shopping, Subscriptions, Utilities, Rent, Health, Education, Entertainment, Travel, Finance, ATM, Transfers)
- Month-over-month change tracking per category
- Three anomaly detection methods: Z-score per category, absolute budget thresholds, and velocity/spike detection
- RAG pipeline backed by a curated knowledge base of 13 Indian personal finance documents
- Chat interface with conversation history and source attribution
- Dashboard with donut chart, monthly cash flow bar chart, and MoM change bars
- Auto-generated initial analysis on upload (no prompt needed)
- Sample data generator for demo purposes

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Flask (Python) |
| LLM | OpenAI GPT-4o |
| Retrieval | TF-IDF (scikit-learn) with optional FAISS + sentence-transformers |
| Data processing | pandas, numpy |
| PDF parsing | pdfplumber |
| Frontend | Vanilla JS, Chart.js |
| Deployment | Gunicorn, AWS Elastic Beanstalk-ready |

---

## Project Structure

```
finsight/
├── app.py                  # Flask routes and session management
├── data_processor.py       # CSV/PDF parsing, categorization, financial summary
├── anomaly_detector.py     # Z-score, budget, and velocity anomaly detection
├── rag_pipeline.py         # TF-IDF/FAISS retriever + OpenAI integration
├── knowledge_base/
│   └── docs.py             # 13 curated financial knowledge documents
├── templates/
│   └── index.html          # Single-page frontend
├── static/
│   ├── css/style.css
│   └── js/app.js
├── requirements.txt
└── Procfile
```

---

## Getting Started

### Prerequisites

- Python 3.10+
- An OpenAI API key

### Installation

```bash
git clone https://github.com/your-username/finsight.git
cd finsight
pip install -r requirements.txt
```

### Configuration

Create a `.env` file in the project root:

```
OPENAI_API_KEY=your_openai_api_key_here
FLASK_SECRET_KEY=your_secret_key_here
```

### Running Locally

```bash
python app.py
```

The app will be available at `http://localhost:5000`.

To use FAISS-based retrieval instead of TF-IDF (requires `faiss-cpu` and `sentence-transformers`):

```
USE_FAISS=true
```

---

## CSV Format

The parser is flexible and auto-detects columns by name. The following formats are supported:

**Separate debit/credit columns:**
```
Date, Description, Debit, Credit
01/04/2024, Swiggy, 350, 
01/04/2024, SALARY NEFT, , 75000
```

**Single signed amount column:**
```
Date, Narration, Amount
01/04/2024, Swiggy, -350
01/04/2024, SALARY NEFT, 75000
```

Accepted date column names: `Date`, `Txn Date`, `Transaction Date`, `Value Date`, `Posting Date`.
Accepted description column names: `Description`, `Narration`, `Particulars`, `Details`, `Remarks`.

---

## API Endpoints

| Method | Route | Description |
|---|---|---|
| POST | `/api/upload` | Upload CSV or PDF bank statement |
| POST | `/api/chat` | Send a message to the AI advisor |
| GET | `/api/summary` | Get the financial summary for the current session |
| GET | `/api/anomalies` | Get the full anomaly report |
| GET | `/api/sample-csv` | Download a generated sample bank statement |
| GET | `/api/health` | Health check and configuration status |

---

## Anomaly Detection Methods

**Z-Score per Category** — Flags individual transactions where the amount is more than 2 standard deviations above the category mean. Requires at least 3 transactions in the category.

**Budget Threshold** — Compares category spend against income-based benchmarks (adapted 50/30/20 rule). Alerts when a category exceeds its limit by more than 20%.

**Category Velocity (MoM)** — Flags categories with more than 30% month-over-month increase in spend, provided the absolute amount is above a minimum threshold.

---

## RAG Knowledge Base

The knowledge base contains 13 documents covering:

- 50/30/20 budgeting rule
- Food and delivery spending optimization
- SIP and mutual fund investing basics
- Emergency fund guidelines
- Transport cost optimization
- Subscription audit strategies
- Debt and credit card management
- Savings rate and wealth building
- Shopping impulse control
- Utility bill optimization
- Investment hierarchy for Indian salaried professionals
- Responding to anomalous transactions
- Goal-based financial planning

All documents are tailored to the Indian financial context (INR, EPF, PPF, NPS, ELSS, Indian platforms).

---

## Deployment

The app includes a `Procfile` for Gunicorn and is structured for AWS Elastic Beanstalk deployment. Session data is stored in-memory — for production use, replace `_sessions` in `app.py` with a Redis-backed store.

```bash
gunicorn app:app --workers 2 --timeout 120
```