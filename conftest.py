"""pytest bootstrap — loaded before any test module.

Sets the OpenMP duplicate-lib guard + UTF-8 output so the guardrail/RAGAS native
stack (onnxruntime, spaCy, sentence-transformers) doesn't trip a Windows
init-order issue during tests.
"""
import os

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
