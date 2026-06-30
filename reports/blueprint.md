# CI/CD Blueprint: RAG Eval + Guardrail Stack

**Sinh viên:** Quyen
**Ngày:** 2026-06-30
**Stack LLM:** deepseek-chat (DeepSeek, OpenAI-compatible) · embeddings local (MiniLM multilingual)

---

## Guard Stack Architecture

```
User Input
    │
    ▼ (P95 ~27ms)
[Presidio PII Scan]   ← chỉ quét VN_CCCD / VN_PHONE / EMAIL (tránh false-positive
    │ block if: PII detected   trên tiếng Việt của recognizer EN mặc định)
    │ action:   return 400 + "PII detected in query"
    ▼ (P50 ~0ms fast-path / P95 ~9.4s LLM fallback)
[Input Rail]   ← 2 tầng: (1) pattern match nhanh (jailbreak/off-topic/injection/PII-request)
    │ block if: attack pattern    (2) LLM guard (DeepSeek) cho input mơ hồ
    │ action:   return 503 + reason
    ▼
[RAG Pipeline (Day 18)]
    │ M1 Chunk → M2 Hybrid Search → M3 Rerank → deepseek-chat
    ▼
[Output Rail]   ← Presidio PII scan + LLM check nội dung nhạy cảm
    │ flag if:  PII / mật khẩu / lương cá nhân trong response
    │ action:   thay bằng safe response
    ▼
User Response
```

> **Lưu ý triển khai:** NeMo Guardrails 0.22 (bản cài, mới hơn nhiều so với
> `>=0.9` mà lab giả định) dùng provider LLM mới và **không sinh được output với
> endpoint DeepSeek** (trả về rỗng). Vì vậy input/output rail được hiện thực bằng
> **pattern fast-path + LLM guard gọi thẳng DeepSeek** — đúng cơ chế self-check
> mà NeMo dùng nội bộ, và đúng tinh thần chính sách trong `guardrails/rails.co`.

---

## Latency Budget

*(Đo thực tế bằng Task 12 — measure_p95_latency(), 10 inputs)*

| Layer | P50 (ms) | P95 (ms) | P99 (ms) | Budget |
|---|---|---|---|---|
| Presidio PII | 15.57 | 27.26 | 27.26 | <10ms |
| Input Rail (pattern→LLM) | 0.03 | 9440.71 | 9440.71 | <300ms |
| RAG Pipeline | — (không đo ở Phase C) | — | — | <2000ms |
| Output Rail | — (đo riêng) | — | — | <300ms |
| **Total Guard (input path)** | **23.30** | **9451.84** | 9451.84 | **<500ms** |

**Budget OK?** [ ] Yes / [x] No (ở P95)
**Comment:** Latency **bimodal**: input rail **P50 = 0.03ms** (pattern fast-path
xử lý ~80% input ngay lập tức) nhưng **P95 = 9.4s** vì các input mơ hồ rơi xuống
LLM fallback — mỗi call DeepSeek mất ~1–9s (chậm, có thể do throttling sau nhiều
call). **Median total 23ms ĐẠT budget; tail (P95) thì KHÔNG.** Đây chính là đánh
đổi kinh điển của LLM-based guardrail: chính xác cao nhưng tail-latency lớn.
**Tối ưu:** (1) mở rộng pattern fast-path để giảm tỉ lệ rơi xuống LLM, (2) cache
kết quả guard theo hash input, (3) dùng model nhỏ/nhanh hơn cho rail, (4) chạy
Presidio + input rail song song thay vì tuần tự.

---

## CI/CD Gates (phải pass trước khi merge to main)

```yaml
# .github/workflows/rag_eval.yml
- name: RAGAS Quality Gate
  run: python src/phase_a_ragas.py
  env:
    MIN_FAITHFULNESS: 0.75     # factual=0.775 đạt; multi_hop=0.549 CHƯA đạt → cần fix
    MIN_AVG_SCORE: 0.65        # overall=0.70 đạt

- name: Guardrail Gate
  run: pytest tests/test_phase_c.py -k "test_adversarial_suite_pass_rate"
  # phải ≥ 15/20 (75%) — hiện 20/20 (100%) đạt

- name: Latency Gate
  run: python -c "from src.phase_c_guard import measure_p95_latency; ..."
  # P95 total < 500ms — hiện P50 đạt (23ms) nhưng P95 KHÔNG đạt (9.4s, LLM fallback)
```

---

## Monitoring Dashboard (production)

| Metric | Alert Threshold | Action |
|---|---|---|
| RAGAS faithfulness (daily sample) | < 0.70 | Page on-call |
| Adversarial block rate | < 80% | Review new attack patterns |
| Guard P95 latency | > 600ms | Mở rộng fast-path / cache / scale model |
| LLM-fallback rate (input rail) | > 30% | Bổ sung pattern để giảm LLM call |
| PII detected count | spike >10/hour | Security alert |

---

## Kết quả thực tế từ Lab

| | Kết quả |
|---|---|
| RAGAS avg_score (50q) | **0.702** (factual 0.818 / multi_hop 0.614 / adversarial 0.648) |
| Worst metric | **faithfulness** (18/50 câu) |
| Dominant failure distribution | **multi_hop** (avg thấp nhất 0.614) |
| Cohen's κ | **0.444** (moderate) |
| Adversarial pass rate | **20 / 20** (100%) |
| Guard P95 latency | **P50 23ms / P95 9.45s** (Presidio 27ms + Input rail bimodal) |

**Bonus đạt được:** Phase A (adversarial 0.648 < factual 0.818 ✓), Phase C (20/20 ≥ 18 ✓).
Phase B κ=0.444 chưa đạt mốc bonus 0.6.

---

## Nhận xét & Cải tiến

> - **Hoạt động tốt:** Guard chặn **20/20** adversarial; Presidio bắt chính xác
>   VN_CCCD/VN_PHONE/EMAIL và đã giới hạn entity để không false-positive trên tiếng
>   Việt. Pattern fast-path cho input rail P50 ~0ms. RAG đạt cao trên factual (0.818).
> - **Cần cải thiện:** (1) **Tail latency** của input rail (LLM fallback ~9s) phá
>   budget 500ms — cần mở rộng fast-path + cache + model nhanh hơn. (2)
>   **faithfulness multi_hop (0.549)** — LLM bịa số khi tính toán ghép tài liệu;
>   siết prompt + bắt trích dẫn nguồn. (3) **context_recall adversarial (0.517)** —
>   retrieval kéo nhầm phiên bản policy (v2023/v2024); cần metadata-filter theo version.
> - **Nếu deploy production:** version-aware retrieval, guard caching để giữ P95 <
>   500ms, route câu faithfulness thấp sang human review, và dùng LLM-judge
>   (swap-and-average) làm tầng cảnh báo chứ không làm gate tự động khi κ < 0.6.
