# Failure Cluster Analysis — Phase A

**Sinh viên:** Quyen
**Ngày:** 2026-06-30
**Eval:** RAGAS 4 metrics · 50 câu · LLM = deepseek-chat · embeddings = paraphrase-multilingual-MiniLM-L12-v2 (local)

> Lưu ý kỹ thuật: `answer_relevancy.strictness` đặt = 1 vì DeepSeek chỉ hỗ trợ
> `n = 1` (mặc định RAGAS n = 3 → lỗi 400). Embeddings chạy local để tránh quota
> free-tier của Gemini.

---

## 1. Aggregate RAGAS Scores theo Distribution

| Metric | factual | multi_hop | adversarial |
|---|---|---|---|
| faithfulness | 0.775 | 0.549 | 0.730 |
| answer_relevancy | 0.782 | 0.551 | 0.503 |
| context_precision | 0.942 | 0.650 | 0.842 |
| context_recall | 0.775 | 0.708 | 0.517 |
| **avg_score** | **0.818** | **0.614** | **0.648** |

**Quan sát:** `factual` mạnh nhất (0.818), `multi_hop` yếu nhất (0.614). Retrieval
tốt với câu đơn-tài-liệu (context_precision factual = 0.94) nhưng sụt mạnh ở
multi_hop (0.65) — đúng kỳ vọng vì multi_hop cần ghép nhiều tài liệu.

---

## 2. Bottom 10 Questions

| Rank | Distribution | Question (tóm tắt) | avg_score | worst_metric |
|---|---|---|---|---|
| 1 | factual | Thông tin lương thuộc cấp phân loại dữ liệu nào? | 0.000 | faithfulness |
| 2 | multi_hop | Manager 12 năm: phụ cấp + phép v2024? | 0.000 | faithfulness |
| 3 | adversarial | Manager dùng VPN cá nhân (NordVPN) khi WFH? | 0.292 | faithfulness |
| 4 | multi_hop | Tạm ứng 8tr quá hạn 15 ngày: duyệt + phí phạt? | 0.354 | answer_relevancy |
| 5 | multi_hop | Senior 9 năm: phép năm + khoảng lương? | 0.375 | faithfulness |
| 6 | adversarial | Phát hiện malware, nhân viên tự xử lý? | 0.417 | faithfulness |
| 7 | adversarial | Phép cũ v2023 mấy ngày? Chính sách nào hiện hành? | 0.435 | context_precision |
| 8 | multi_hop | Mua laptop 30tr: ai duyệt + cần gì từ CNTT? | 0.476 | context_precision |
| 9 | factual | Tạm ứng <5tr ai duyệt? ≥5tr thì sao? | 0.500 | faithfulness |
| 10 | adversarial | Thâm niên bao nhiêu năm được cộng phép? | 0.500 | answer_relevancy |

Bottom-10 gồm 5 multi_hop, 4 adversarial, 1 factual → câu khó tập trung ở
multi_hop + adversarial. Hai câu avg = 0.0 (q6, q33) là retrieval/generation trượt
hoàn toàn (mọi metric ≈ 0).

---

## 3. Failure Cluster Matrix

*(Mỗi ô = số câu có worst_metric = row, thuộc distribution = col)*

| worst_metric | factual | multi_hop | adversarial | Total |
|---|---|---|---|---|
| faithfulness | 6 | 9 | 3 | **18** |
| answer_relevancy | 6 | 5 | 2 | 13 |
| context_recall | 6 | 2 | 3 | 11 |
| context_precision | 2 | 4 | 2 | 8 |

---

## 4. Dominant Failure Analysis

**Dominant metric:** **faithfulness** (18/50 câu — điểm yếu phổ biến nhất)
**Dominant distribution (theo code):** factual & multi_hop đồng hạng 20 câu → hàm chọn `factual`

> `cluster_analysis()` đếm worst_metric của **mọi** câu (không chỉ câu điểm thấp),
> nên "dominant distribution" thực chất phản ánh **số lượng câu** (factual =
> multi_hop = 20) chứ không phải mức độ tệ. Tín hiệu chất lượng thật nằm ở
> `avg_score`: **multi_hop (0.614) mới là distribution yếu nhất**.
>
> Về metric: **faithfulness** thấp nhất ở multi_hop (0.549) — LLM hay "chế" số
> liệu khi phải tính toán/ghép nhiều tài liệu (lương thử việc, phí phạt, phép
> tích lũy). Đây là rủi ro hallucination điển hình của RAG khi context bị phân
> mảnh. context_recall ở adversarial cũng thấp (0.517) vì câu bẫy v2023/v2024 kéo
> retrieval về đúng/sai phiên bản.

---

## 5. Suggested Fixes

| Metric yếu | Root cause | Suggested fix |
|---|---|---|
| faithfulness (18) | LLM hallucinating khi tính toán multi-hop | Siết system prompt ("chỉ dùng số liệu trong context"), temperature=0, thêm bước trích dẫn nguồn |
| answer_relevancy (13) | Answer lệch trọng tâm câu hỏi | Cải thiện prompt template, yêu cầu trả lời trực tiếp ý hỏi trước |
| context_recall (11) | Thiếu chunk liên quan (nhất là adversarial v2023/v2024) | Tăng top_k, thêm metadata filter theo version, cải thiện chunking |
| context_precision (8) | Lẫn chunk không liên quan | Mạnh tay rerank hơn, lọc theo metadata phiên bản |

---

## 6. Nhận xét về Adversarial Distribution

> Adversarial avg_score = **0.648** < factual **0.818** ✅ (đạt bonus Phase A) —
> pipeline **có** bị adversarial kéo điểm xuống, đúng như thiết kế bộ test.
> Điểm yếu rõ nhất của adversarial là **context_recall (0.517)** và
> **answer_relevancy (0.503)**: các câu bẫy version-conflict (q49 hỏi policy cũ
> v2023, q42 thâm niên) và negation trap (q47 "tự xử lý malware?", q50 "VPN cá
> nhân?") khiến pipeline kéo nhầm phiên bản tài liệu hoặc trả lời lệch hướng bẫy.
> 4/10 câu adversarial nằm trong bottom-10. Đáng chú ý faithfulness adversarial
> (0.730) lại khá cao — pipeline ít bịa, nhưng **lấy đúng-context-sai-phiên-bản**
> mới là lỗi chính, nên fix ưu tiên là metadata-filter theo version chứ không chỉ
> siết prompt.
