from __future__ import annotations

"""Module 3: Reranking — Cross-encoder top-20 → top-3 + latency benchmark."""

import os, sys, time
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import RERANK_TOP_K


@dataclass
class RerankResult:
    text: str
    original_score: float
    rerank_score: float
    metadata: dict
    rank: int


class CrossEncoderReranker:
    def __init__(self, model_name: str = "gemini-3-flash"):
        self.model_name = model_name
        self._client = None

    def _get_client(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI()
        return self._client

    def rerank(self, query: str, results: list[dict], top_k: int = RERANK_TOP_K) -> list[RerankResult]:
        if not results:
            return []
        
        client = self._get_client()
        scored_results = []
        
        # Để tiết kiệm thời gian/rate limit, ta chỉ dùng API rerank top 5-10
        # Nếu muốn chấm hết thì vòng lặp qua từng kết quả
        max_to_rerank = min(len(results), 5)
        
        max_to_rerank = min(len(results), 5)
        
        try:
            from config import get_llm
            import json as _json
            client = get_llm()
            
            input_docs = [{"id": i, "text": results[i]["text"]} for i in range(max_to_rerank)]
            prompt_input = _json.dumps(input_docs, ensure_ascii=False)
            
            prompt = f"""Đánh giá mức độ liên quan của các Đoạn văn với Câu hỏi.
Câu hỏi: {query}

Đầu vào là mảng JSON chứa các Đoạn văn.
Đầu ra PHẢI LÀ MỘT MẢNG JSON các số float từ 0.0 đến 1.0 (1.0 là cực kỳ liên quan), tương ứng với từng Đoạn văn theo đúng thứ tự.
Ví dụ đầu ra: [0.9, 0.2, 0.5]
Tuyệt đối không trả về bất kỳ text nào ngoài mảng JSON.

Đầu vào:
{prompt_input}"""
            response = client.invoke(prompt)
            content = response.content.strip()
            
            # Parse JSON array
            start_idx = content.find('[')
            end_idx = content.rfind(']')
            if start_idx != -1 and end_idx != -1:
                content = content[start_idx:end_idx+1]
            
            scores = _json.loads(content)
            if not isinstance(scores, list) or len(scores) != max_to_rerank:
                scores = [results[i]["score"] for i in range(max_to_rerank)]
        except Exception as e:
            print(f"  ⚠️  API Rerank batch failed: {e}")
            scores = [results[i]["score"] for i in range(max_to_rerank)]

        for i in range(max_to_rerank):
            res = results[i]
            scored_results.append(RerankResult(
                text=res["text"],
                original_score=res["score"],
                rerank_score=float(scores[i]),
                metadata=res.get("metadata", {}),
                rank=0
            ))
            
        # Thêm các kết quả còn lại với điểm 0 để không lọt top trên
        for i in range(max_to_rerank, len(results)):
            res = results[i]
            scored_results.append(RerankResult(
                text=res["text"], original_score=res["score"],
                rerank_score=0.0, metadata=res.get("metadata", {}), rank=0
            ))
            
        scored_results.sort(key=lambda x: x.rerank_score, reverse=True)
        for i, item in enumerate(scored_results):
            item.rank = i + 1
            
        return scored_results[:top_k]


class FlashrankReranker:
    """Lightweight alternative (<5ms). Optional."""
    def __init__(self):
        self._model = None

    def rerank(self, query: str, documents: list[dict], top_k: int = RERANK_TOP_K) -> list[RerankResult]:
        # TODO (optional): from flashrank import Ranker, RerankRequest
        # model = Ranker(); passages = [{"text": d["text"]} for d in documents]
        # results = model.rerank(RerankRequest(query=query, passages=passages))
        return []


def benchmark_reranker(reranker, query: str, documents: list[dict], n_runs: int = 5) -> dict:
    """Benchmark latency over n_runs. (Đã implement sẵn)"""
    times = []
    for _ in range(n_runs):
        start = time.perf_counter()
        reranker.rerank(query, documents)
        elapsed = (time.perf_counter() - start) * 1000
        times.append(elapsed)
    return {"avg_ms": sum(times) / len(times), "min_ms": min(times), "max_ms": max(times)}


if __name__ == "__main__":
    query = "Nhân viên được nghỉ phép bao nhiêu ngày?"
    docs = [
        {"text": "Nhân viên được nghỉ 12 ngày/năm.", "score": 0.8, "metadata": {}},
        {"text": "Mật khẩu thay đổi mỗi 90 ngày.", "score": 0.7, "metadata": {}},
        {"text": "Thời gian thử việc là 60 ngày.", "score": 0.75, "metadata": {}},
    ]
    reranker = CrossEncoderReranker()
    for r in reranker.rerank(query, docs):
        print(f"[{r.rank}] {r.rerank_score:.4f} | {r.text}")
