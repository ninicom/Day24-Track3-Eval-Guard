from __future__ import annotations

"""
Module 5: Enrichment Pipeline
==============================
Làm giàu chunks TRƯỚC khi embed: Summarize, HyQA, Contextual Prepend, Auto Metadata.

Test: pytest tests/test_m5.py
"""

import os, sys
from dataclasses import dataclass, field

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import OPENAI_API_KEY


@dataclass
class EnrichedChunk:
    """Chunk đã được làm giàu."""
    original_text: str
    enriched_text: str
    summary: str
    hypothesis_questions: list[str]
    auto_metadata: dict
    method: str  # "contextual", "summary", "hyqa", "full"


# ─── Technique 1: Chunk Summarization ────────────────────


def summarize_chunk(text: str) -> str:
    """
    Tạo summary ngắn cho chunk.
    Embed summary thay vì (hoặc cùng với) raw chunk → giảm noise.
    """
    # TODO: Implement chunk summarization
    # if OPENAI_API_KEY:
    #     try:
    #         from openai import OpenAI
    #         client = OpenAI()
    #         resp = client.chat.completions.create(
    #             model="gpt-4o-mini",
    #             messages=[
    #                 {"role": "system", "content": "Tóm tắt đoạn văn sau trong 2-3 câu ngắn gọn bằng tiếng Việt."},
    #                 {"role": "user", "content": text},
    #             ],
    #             max_tokens=150,
    #         )
    #         return resp.choices[0].message.content.strip()
    #     except Exception as e:
    #         print(f"  ⚠️  OpenAI summarize failed: {e}")
    #
    # Extractive fallback (không cần API):
    # sentences = [s.strip() for s in text.replace("\n", " ").split(". ") if s.strip()]
    # return ". ".join(sentences[:2]) + "." if sentences else text
    return text


# ─── Technique 2: Hypothesis Question-Answer (HyQA) ─────


def generate_hypothesis_questions(text: str, n_questions: int = 3) -> list[str]:
    """
    Generate câu hỏi mà chunk có thể trả lời.
    Index cả questions lẫn chunk → query match tốt hơn (bridge vocabulary gap).
    """
    # TODO: Implement HyQA generation
    # if OPENAI_API_KEY:
    #     try:
    #         from openai import OpenAI
    #         client = OpenAI()
    #         resp = client.chat.completions.create(
    #             model="gpt-4o-mini",
    #             messages=[
    #                 {"role": "system", "content": f"Dựa trên đoạn văn, tạo {n_questions} câu hỏi mà đoạn văn có thể trả lời. Trả về mỗi câu hỏi trên 1 dòng."},
    #                 {"role": "user", "content": text},
    #             ],
    #             max_tokens=200,
    #         )
    #         questions = resp.choices[0].message.content.strip().split("\n")
    #         return [q.strip().lstrip("0123456789.-) ") for q in questions if q.strip()][:n_questions]
    #     except Exception as e:
    #         print(f"  ⚠️  OpenAI HyQA failed: {e}")
    #
    # Extractive fallback:
    # import re
    # sentences = [s.strip() for s in re.split(r'[.!?\n]', text) if len(s.strip()) > 10]
    # return [f"{s.rstrip('.')}?" for s in sentences[:n_questions]]
    return []


# ─── Technique 3: Contextual Prepend (Anthropic style) ──


def contextual_prepend(text: str, document_title: str = "") -> str:
    """
    Prepend context giải thích chunk nằm ở đâu trong document.
    Anthropic benchmark: giảm 49% retrieval failure (alone).
    """
    # TODO: Implement contextual prepend
    # if OPENAI_API_KEY:
    #     try:
    #         from openai import OpenAI
    #         client = OpenAI()
    #         resp = client.chat.completions.create(
    #             model="gpt-4o-mini",
    #             messages=[
    #                 {"role": "system", "content": "Viết 1 câu ngắn mô tả đoạn văn này nằm ở đâu trong tài liệu và nói về chủ đề gì. Chỉ trả về 1 câu."},
    #                 {"role": "user", "content": f"Tài liệu: {document_title}\n\nĐoạn văn:\n{text}"},
    #             ],
    #             max_tokens=80,
    #         )
    #         context = resp.choices[0].message.content.strip()
    #         return f"{context}\n\n{text}"
    #     except Exception as e:
    #         print(f"  ⚠️  OpenAI contextual failed: {e}")
    #
    # Simple fallback:
    # prefix = f"Trích từ {document_title}. " if document_title else ""
    # return f"{prefix}{text}"
    return text


# ─── Technique 4: Auto Metadata Extraction ──────────────


def extract_metadata(text: str) -> dict:
    """
    LLM extract metadata tự động: topic, entities, date_range, category.
    """
    # TODO: Implement auto metadata extraction
    # if OPENAI_API_KEY:
    #     try:
    #         import json as _json
    #         from openai import OpenAI
    #         client = OpenAI()
    #         resp = client.chat.completions.create(
    #             model="gpt-4o-mini",
    #             messages=[
    #                 {"role": "system", "content": 'Trích xuất metadata từ đoạn văn. Trả về JSON: {"topic": "...", "entities": ["..."], "category": "policy|hr|it|finance", "language": "vi|en"}'},
    #                 {"role": "user", "content": text},
    #             ],
    #             max_tokens=150,
    #         )
    #         return _json.loads(resp.choices[0].message.content)
    #     except Exception as e:
    #         print(f"  ⚠️  OpenAI metadata failed: {e}")
    #
    # return {"topic": "general", "entities": [], "category": "policy", "language": "vi"}
    return {}


def _enrich_batch_call(texts: list[str], sources: list[str]) -> list[dict]:
    if OPENAI_API_KEY:
        try:
            import json as _json
            from config import get_llm
            import time
            time.sleep(2)
            client = get_llm()
            
            input_data = []
            for t, s in zip(texts, sources):
                input_data.append({"source": s, "text": t})
                
            prompt_input = _json.dumps(input_data, ensure_ascii=False, indent=2)
            
            resp = client.invoke([
                ("system", """Phân tích danh sách các đoạn văn dưới đây.
Đầu vào là một mảng JSON các object gồm "source" và "text".
Đầu ra PHẢI LÀ MỘT MẢNG JSON CÓ CÙNG ĐỘ DÀI, đúng thứ tự tương ứng với đầu vào.
Tuyệt đối không trả về bất kỳ text nào ngoài mảng JSON.
Định dạng mỗi phần tử trong mảng trả về:
{
  "summary": "tóm tắt 2-3 câu",
  "questions": ["câu hỏi 1", "câu hỏi 2", "câu hỏi 3"],
  "context": "1 câu mô tả đoạn văn nằm ở đâu trong tài liệu",
  "metadata": {"topic": "...", "entities": ["..."], "category": "policy|hr|it|finance", "language": "vi|en"}
}"""),
                ("user", f"Đầu vào:\n{prompt_input}")
            ])
            content = resp.content.strip()
            if content.startswith("```"):
                lines = content.split('\n')
                if lines[0].startswith("```"): lines = lines[1:]
                if lines and lines[-1].startswith("```"): lines = lines[:-1]
                content = '\n'.join(lines).strip()
            
            # Find the JSON array
            start_idx = content.find('[')
            end_idx = content.rfind(']')
            if start_idx != -1 and end_idx != -1:
                content = content[start_idx:end_idx+1]
                
            results = _json.loads(content)
            if isinstance(results, list) and len(results) == len(texts):
                return results
            else:
                print(f"  ⚠️  Batch size mismatch: expected {len(texts)}, got {len(results) if isinstance(results, list) else 0}")
                return [{}] * len(texts)
        except Exception as e:
            print(f"  ⚠️  Enrichment Batch API failed: {e}")
    return [{}] * len(texts)


def enrich_chunks(
    chunks: list[dict],
    methods: list[str] | None = None,
) -> list[EnrichedChunk]:
    if methods is None:
        methods = ["combined"]

    use_combined = "combined" in methods
    
    import json as _json
    import hashlib
    cache_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "enrichment_cache.json")
    cache = {}
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                cache = _json.load(f)
        except Exception:
            pass

    enriched = []
    
    if use_combined:
        # 1. Identify uncached chunks
        uncached_indices = []
        uncached_texts = []
        uncached_sources = []
        
        for i, chunk in enumerate(chunks):
            text = chunk["text"]
            chunk_hash = hashlib.md5(text.encode("utf-8")).hexdigest()
            if chunk_hash not in cache:
                uncached_indices.append(i)
                uncached_texts.append(text)
                uncached_sources.append(chunk.get("metadata", {}).get("source", ""))
                
        # 2. Process in batches to avoid token limits
        batch_size = 25
        for i in range(0, len(uncached_texts), batch_size):
            batch_texts = uncached_texts[i:i+batch_size]
            batch_sources = uncached_sources[i:i+batch_size]
            print(f"  Processing batch {i//batch_size + 1}/{(len(uncached_texts)+batch_size-1)//batch_size} ({len(batch_texts)} chunks)...", flush=True)
            batch_results = _enrich_batch_call(batch_texts, batch_sources)
            
            for j, result in enumerate(batch_results):
                if result:
                    text_idx = i + j
                    orig_text = batch_texts[j]
                    chunk_hash = hashlib.md5(orig_text.encode("utf-8")).hexdigest()
                    cache[chunk_hash] = result
                    
            with open(cache_file, "w", encoding="utf-8") as f:
                _json.dump(cache, f, ensure_ascii=False, indent=2)
                
    for i, chunk in enumerate(chunks):
        text = chunk["text"]
        source = chunk.get("metadata", {}).get("source", "")

        if use_combined:
            chunk_hash = hashlib.md5(text.encode("utf-8")).hexdigest()
            result = cache.get(chunk_hash, {})

            summary = result.get("summary", "")
            questions = result.get("questions", [])
            context_line = result.get("context", "")
            enriched_text = f"{context_line}\n\n{text}" if context_line else text
            auto_meta = result.get("metadata", {})
        else:
            summary = summarize_chunk(text) if "summary" in methods else ""
            questions = generate_hypothesis_questions(text) if "hyqa" in methods else []
            enriched_text = contextual_prepend(text, source) if "contextual" in methods else text
            auto_meta = extract_metadata(text) if "metadata" in methods else {}

        enriched.append(EnrichedChunk(
            original_text=text,
            enriched_text=enriched_text,
            summary=summary,
            hypothesis_questions=questions,
            auto_metadata={**chunk.get("metadata", {}), **auto_meta},
            method="+".join(methods),
        ))

    print(f"  ✓ Enriched {len(chunks)} chunks", flush=True)
    return enriched


# ─── Main ────────────────────────────────────────────────

if __name__ == "__main__":
    sample = "Nhân viên chính thức được nghỉ phép năm 12 ngày làm việc mỗi năm. Số ngày nghỉ phép tăng thêm 1 ngày cho mỗi 5 năm thâm niên công tác."

    print("=== Enrichment Pipeline Demo ===\n")
    print(f"Original: {sample}\n")

    s = summarize_chunk(sample)
    print(f"Summary: {s}\n")

    qs = generate_hypothesis_questions(sample)
    print(f"HyQA questions: {qs}\n")

    ctx = contextual_prepend(sample, "Sổ tay nhân viên VinUni 2024")
    print(f"Contextual: {ctx}\n")

    meta = extract_metadata(sample)
    print(f"Auto metadata: {meta}")
