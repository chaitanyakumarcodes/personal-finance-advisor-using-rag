"""
rag_pipeline.py — Retrieval-Augmented Generation pipeline.

Architecture:
  Knowledge Base (text docs) → TF-IDF Vectorizer → Cosine Similarity
  (FAISS/sentence-transformers used if available; TF-IDF as production fallback)
  User query + Financial context → Retrieve top-k docs → LLM prompt → Advice
"""

import os
import numpy as np
from typing import List, Optional
from openai import OpenAI, OpenAIError

# ─── KNOWLEDGE BASE SETUP ─────────────────────────────────────────────────────

_retriever = None  # Holds either FAISS or TF-IDF retriever
_documents = None


class TFIDFRetriever:
    """
    TF-IDF based retriever using scikit-learn.
    Excellent for domain-specific text retrieval — no GPU, no heavy dependencies.
    """
    def __init__(self, documents: List[dict]):
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        self.docs = documents
        self.texts = [f"{d['title']}\n{d['content']}" for d in documents]
        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            max_features=5000,
            stop_words='english',
            sublinear_tf=True,
        )
        self.doc_matrix = self.vectorizer.fit_transform(self.texts)
        self._cosine = cosine_similarity

    def retrieve(self, query: str, top_k: int = 3) -> List[dict]:
        from sklearn.metrics.pairwise import cosine_similarity
        q_vec = self.vectorizer.transform([query])
        scores = cosine_similarity(q_vec, self.doc_matrix).flatten()
        top_indices = scores.argsort()[::-1][:top_k]
        results = []
        for idx in top_indices:
            if scores[idx] > 0.01:
                doc = self.docs[idx].copy()
                doc["relevance_score"] = float(scores[idx])
                results.append(doc)
        return results


class FAISSRetriever:
    """FAISS + sentence-transformers retriever (if available)."""
    def __init__(self, documents: List[dict]):
        import faiss
        from sentence_transformers import SentenceTransformer
        self.docs = documents
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        texts = [f"{d['title']}\n{d['content']}" for d in documents]
        embs = self.model.encode(texts, convert_to_numpy=True).astype(np.float32)
        norms = np.linalg.norm(embs, axis=1, keepdims=True)
        embs = embs / np.maximum(norms, 1e-10)
        dim = embs.shape[1]
        self.index = faiss.IndexFlatIP(dim)
        self.index.add(embs)

    def retrieve(self, query: str, top_k: int = 3) -> List[dict]:
        q = self.model.encode([query], convert_to_numpy=True).astype(np.float32)
        q = q / np.maximum(np.linalg.norm(q), 1e-10)
        scores, indices = self.index.search(q, top_k)
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx >= 0 and score > 0.05:
                doc = self.docs[idx].copy()
                doc["relevance_score"] = float(score)
                results.append(doc)
        return results


def build_knowledge_index() -> int:
    """Build retrieval index. Uses TF-IDF by default (FAISS optional for performance)."""
    global _retriever, _documents
    from knowledge_base.docs import get_all_documents
    _documents = get_all_documents()

    # Default to TF-IDF for reliability; FAISS can be enabled manually if needed
    try:
        # Try FAISS only if explicitly enabled via env var
        if os.environ.get("USE_FAISS", "").lower() == "true":
            _retriever = FAISSRetriever(_documents)
            print("✅ Using FAISS + sentence-transformers retriever")
        else:
            _retriever = TFIDFRetriever(_documents)
            print("✅ Using TF-IDF retriever (production-grade for domain text)")
    except Exception as e:
        print(f"⚠️  Retriever initialization error: {e}")
        _retriever = TFIDFRetriever(_documents)
        print("✅ Falling back to TF-IDF retriever")

    return len(_documents)


def retrieve_relevant_docs(query: str, financial_context: str = "", top_k: int = 3) -> List[dict]:
    """Retrieve top-k relevant financial documents for a given query."""
    global _retriever
    if _retriever is None:
        build_knowledge_index()

    combined_query = f"{query} {financial_context[:300]}"
    return _retriever.retrieve(combined_query, top_k=top_k)


# ─── LLM INTEGRATION ─────────────────────────────────────────────────────────

def get_openai_client() -> OpenAI:
    """Get OpenAI client — API key from env."""
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set.")
    return OpenAI(api_key=api_key)


def build_rag_prompt(
    user_query: str,
    financial_summary_text: str,
    anomaly_text: str,
    retrieved_docs: List[dict],
) -> str:
    """Construct the structured RAG prompt."""
    docs_text = ""
    for i, doc in enumerate(retrieved_docs, 1):
        docs_text += f"\n### Knowledge Source {i}: {doc['title']}\n{doc['content']}\n"

    prompt = f"""You are an expert personal finance advisor specialized in Indian personal finance.
You provide specific, actionable, numbers-driven advice — not generic tips.

## USER'S FINANCIAL DATA:
{financial_summary_text}

{anomaly_text}

## RELEVANT FINANCIAL KNOWLEDGE:
{docs_text}

## USER'S QUESTION:
{user_query}

## YOUR TASK:
Analyze the user's specific financial data above and provide personalized advice.

Respond in this EXACT structure:

**📊 KEY INSIGHTS**
(2-3 specific observations from their data with exact numbers. Example: "Your Swiggy/Zomato spend hit ₹X this month, up Y% vs last month")

**⚠️ PROBLEMS IDENTIFIED**
(Specific financial issues found in their data. Be direct. Use their actual numbers.)

**✅ RECOMMENDATIONS**
(3-5 actionable steps, each with:
- What to do (specific action)
- How much it saves (exact ₹ amount)
- Timeline to do it)

**💰 FINANCIAL IMPACT**
(Total potential monthly savings + what they could do with that money — e.g., SIP amount, EMI reduction)

**🎯 PRIORITY ACTION**
(The single most impactful thing they should do THIS WEEK — with a specific number)

Rules:
- Always use ₹ for amounts, Indian formatting (lakhs/crores not millions)
- Reference their actual spending numbers, not generic ranges
- Be specific about merchants (Swiggy, Uber, Netflix) if visible in data
- If income data is available, give savings rate advice
- Keep total response under 600 words but make every word count
- If query is about a specific topic, focus there but ground in their data
"""
    return prompt


def generate_advice(
    user_query: str,
    financial_summary_text: str,
    anomaly_text: str,
    conversation_history: Optional[List[dict]] = None,
) -> dict:
    """
    Main RAG pipeline entry point.
    Returns advice dict with response text + metadata.
    """
    try:
        client = get_openai_client()

        # Step 1: Retrieve relevant docs
        retrieved_docs = retrieve_relevant_docs(
            query=user_query,
            financial_context=financial_summary_text,
            top_k=3
        )

        # Step 2: Build prompt
        prompt = build_rag_prompt(
            user_query=user_query,
            financial_summary_text=financial_summary_text,
            anomaly_text=anomaly_text,
            retrieved_docs=retrieved_docs,
        )

        # Step 3: Build messages array (system + history + current user msg)
        system_message = {
            "role": "system",
            "content": (
                "You are a precise, numbers-driven personal finance advisor for India. "
                "Always ground your advice in the user's actual transaction data. "
                "Be specific, not generic. Speak in plain English, not jargon."
            )
        }

        messages = [system_message]
        if conversation_history:
            for h in conversation_history[-6:]:  # last 3 turns
                messages.append(h)
        messages.append({"role": "user", "content": prompt})

        # Step 4: Call OpenAI
        response = client.chat.completions.create(
            model="gpt-4o",
            max_tokens=1000,
            messages=messages,
        )

        advice_text = response.choices[0].message.content
        used_sources = [
            {
                "title": d["title"],
                "id": d["id"],
                "score": round(d["relevance_score"], 3)
            }
            for d in retrieved_docs
        ]

        return {
            "success": True,
            "response": advice_text,
            "sources": used_sources,
            "model": "gpt-4o",
            "tokens_used": response.usage.total_tokens,
        }

    except ValueError as e:
        return {"success": False, "error": str(e), "response": ""}
    except OpenAIError as e:
        return {"success": False, "error": f"OpenAI API error: {e}", "response": ""}
    except Exception as e:
        return {"success": False, "error": f"Unexpected error: {e}", "response": ""}


# ─── QUICK ANALYSIS (no user query) ──────────────────────────────────────────

def generate_initial_analysis(financial_summary_text: str, anomaly_text: str) -> dict:
    """
    Auto-generate initial analysis when user uploads their data.
    No user query needed — proactively surfaces key insights.
    """
    auto_query = (
        "Analyze my complete financial picture. What are the most important things "
        "I should know and act on immediately? Focus on my biggest spending categories, "
        "savings rate, and any red flags you see."
    )
    return generate_advice(
        user_query=auto_query,
        financial_summary_text=financial_summary_text,
        anomaly_text=anomaly_text,
    )


# ─── RETRIEVAL EVALUATION ─────────────────────────────────────────────────────

def evaluate_retrieval(test_queries: List[str]) -> List[dict]:
    """
    Basic retrieval quality evaluation.
    Returns top-k results for each query with relevance scores.
    """
    results = []
    for query in test_queries:
        docs = retrieve_relevant_docs(query, top_k=3)
        results.append({
            "query": query,
            "retrieved": [
                {"title": d["title"], "score": round(d["relevance_score"], 3)}
                for d in docs
            ]
        })
    return results