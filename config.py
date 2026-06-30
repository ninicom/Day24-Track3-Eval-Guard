"""Shared configuration for Lab 24: Eval + Guardrail Stack."""

import os
from dotenv import load_dotenv

load_dotenv()

# --- API Keys ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
HF_TOKEN = os.getenv("HF_TOKEN", "")  # Optional: for HuggingFace models

# --- LLM provider: DeepSeek (OpenAI-compatible) ---
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"

# Bridge DeepSeek onto the OpenAI env vars so bare OpenAI() (Phase B judge) and
# NeMo's openai engine pick it up with no extra plumbing.
os.environ.setdefault("OPENAI_API_KEY", DEEPSEEK_API_KEY)
os.environ.setdefault("OPENAI_BASE_URL", DEEPSEEK_BASE_URL)   # openai sdk
os.environ.setdefault("OPENAI_API_BASE", DEEPSEEK_BASE_URL)   # langchain ChatOpenAI


def get_llm():
    """RAGAS / generation LLM → DeepSeek via the OpenAI-compatible endpoint.
    Embeddings stay on Gemini (DeepSeek has no embeddings API) — see m4_eval.py."""
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(model=LLM_MODEL, api_key=DEEPSEEK_API_KEY,
                      base_url=DEEPSEEK_BASE_URL, temperature=0, max_retries=2)

# --- Qdrant (same as Day 18) ---
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
COLLECTION_NAME = "lab24_production"

# --- Embedding (local, multilingual incl. Vietnamese; no API quota) ---
# Switched from BAAI/bge-m3 (2.3GB, slow to load on CPU) to a lighter multilingual
# model that's fast and reliable for this small corpus. Dim derived dynamically.
EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
EMBEDDING_DIM = 384

# --- Chunking (same as Day 18) ---
HIERARCHICAL_PARENT_SIZE = 2048
HIERARCHICAL_CHILD_SIZE = 256
SEMANTIC_THRESHOLD = 0.85

# --- Search (same as Day 18) ---
BM25_TOP_K = 20
DENSE_TOP_K = 20
HYBRID_TOP_K = 20
RERANK_TOP_K = 3

# --- Paths ---
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
TEST_SET_PATH = os.path.join(os.path.dirname(__file__), "test_set_50q.json")
ANSWERS_PATH = os.path.join(os.path.dirname(__file__), "answers_50q.json")
HUMAN_LABELS_PATH = os.path.join(os.path.dirname(__file__), "human_labels_10q.json")
ADVERSARIAL_SET_PATH = os.path.join(os.path.dirname(__file__), "adversarial_set_20.json")
GUARDRAILS_CONFIG_DIR = os.path.join(os.path.dirname(__file__), "guardrails")

# --- LLM Judge ---
JUDGE_MODEL = LLM_MODEL  # DeepSeek model for pairwise judge (Phase B)

# --- Guardrail latency budget ---
LATENCY_BUDGET_P95_MS = 500  # target: full guard stack P95 < 500ms
PRESIDIO_LANGUAGE = "en"    # Presidio base language; custom VN recognizers added via PatternRecognizer
