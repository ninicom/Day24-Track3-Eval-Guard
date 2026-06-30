# LLM Judge Bias Report — Phase B

**Sinh viên:** Quyen
**Ngày:** 2026-06-30
**Judge model:** deepseek-chat (DeepSeek, OpenAI-compatible)

> Thiết kế: với mỗi câu hỏi trong `human_labels_10q.json`, judge so sánh
> `model_answer` (A) với `ground_truth` (B). `judge_label = 1` nếu final_winner ∈
> {A, tie} (model answer ngang ngửa ground truth → "đúng"), `= 0` nếu B thắng
> (ground truth rõ ràng tốt hơn → "sai"). Đây là tín hiệu nhị phân so sánh được
> với nhãn human 0/1.

---

## 1. Pairwise Judge Results (swap-and-average, 10 câu)

| # | Question (tóm tắt) | Final Winner | Reasoning tóm tắt |
|---|---|---|---|
| 1 | Nghỉ kết hôn mấy ngày | tie | Cả hai đúng số ngày; B thừa thông tin → A súc tích hơn |
| 5 | Mua thiết bị 55tr ai duyệt | B | B nêu đúng mức tiền + CEO; A thiếu thẩm quyền |
| 12 | Thưởng Tết tối thiểu ≥6 tháng | B | B đầy đủ điều kiện 6 tháng + pro-rata |
| 21 | Senior 9 năm: phép + lương | tie | B có nguồn v2024 + cách tính thâm niên |
| 23 | Hoàn trả khóa 25tr nghỉ sau 8 tháng | B | B giải thích rõ cam kết + thời gian |
| 29 | Tạm ứng 8tr quá 30 ngày | B | B đúng quy trình duyệt + phí phạt |
| 33 | Manager 12 năm: phụ cấp + phép | B | B chi tiết phụ cấp + phép v2024 |
| 41 | Số ngày phép năm | B | B đúng 15 ngày v2024; A dùng số cũ 12 |
| 46 | Thử việc có phép năm không | tie | A súc tích; B dài dòng (negation trap) |
| 50 | Manager dùng VPN cá nhân WFH | B | B nêu rõ chính sách cấm; A mơ hồ |

---

## 2. Swap-and-Average Results

| Question ID | Pass 1 | Pass 2 (đã convert) | Final | Position Consistent? |
|---|---|---|---|---|
| 1  | A/B khác nhau | — | tie | ❌ |
| 5  | B | B | B | ✅ |
| 12 | B | B | B | ✅ |
| 21 | A/B khác nhau | — | tie | ❌ |
| 23 | B | B | B | ✅ |
| 29 | B | B | B | ✅ |
| 33 | B | B | B | ✅ |
| 41 | B | B | B | ✅ |
| 46 | A/B khác nhau | — | tie | ❌ |
| 50 | B | B | B | ✅ |

**Position bias rate:** 30% (3/10 — các câu 1, 21, 46 đảo kết quả khi swap → final = tie)

---

## 3. Cohen's κ Analysis

**Human labels:** `human_labels_10q.json` (10 câu)
**Judge labels:** model_answer vs ground_truth (1 nếu A/tie, 0 nếu B thắng)

| Question ID | Human Label | Judge Label | Agree? |
|---|---|---|---|
| 1  | 1 | 1 | ✅ |
| 5  | 0 | 0 | ✅ |
| 12 | 1 | 0 | ❌ |
| 21 | 1 | 1 | ✅ |
| 23 | 1 | 0 | ❌ |
| 29 | 0 | 0 | ✅ |
| 33 | 1 | 0 | ❌ |
| 41 | 0 | 0 | ✅ |
| 46 | 1 | 1 | ✅ |
| 50 | 0 | 0 | ✅ |

**Observed agreement (p_o):** 7/10 = 0.70
**Cohen's κ:** **0.444**
**Interpretation:** **moderate** (0.4–0.6 trên thang Landis-Koch)

3 ca bất đồng (q12, q23, q33) đều là: **human = 1, judge = 0**. Judge nghiêm khắc
hơn human — khi so với ground_truth đầy đủ, judge coi `model_answer` (thiếu chi
tiết tính toán multi-hop) là "thua", trong khi human vẫn chấm "đúng".

---

## 4. Verbosity Bias

Trong 7 case có winner rõ ràng (không tie):
- A thắng + A dài hơn B: **0 / 7**
- B thắng + B dài hơn A: **7 / 7**
- **Verbosity bias rate:** **100%**

**Kết luận:** Mọi câu B (ground_truth) thắng thì B đều dài hơn. Điều này gợi ý
judge có thể đang gắn "đầy đủ/dài hơn" với "tốt hơn". Đây là vấn đề vì trong
production một answer dài, lan man có thể được chấm cao một cách sai lệch chỉ vì
độ dài, không phải vì độ chính xác. (Lưu ý: ở đây B = ground_truth nên dài-hơn và
đúng-hơn trùng nhau, nên con số 100% là cận trên — cần thêm cặp answer độ dài
ngẫu nhiên để tách bạch hai yếu tố.)

---

## 5. Nhận xét chung

> - **κ = 0.444 (moderate), CHƯA đạt 0.6.** LLM judge đồng thuận vừa phải với
>   human; chưa đủ tin cậy để thay thế hoàn toàn human review, nhưng đủ tốt để
>   lọc sơ bộ / cảnh báo.
> - **Position bias = 30%** (đúng ngưỡng đáng chú ý). Cả 3 ca bất nhất quán đều
>   rơi vào câu mà hai answer gần ngang nhau → judge dao động theo thứ tự.
>   Swap-and-average đã chuyển các ca này thành `tie` thay vì kết luận sai — đây
>   chính là giá trị của kỹ thuật này.
> - **Swap-and-average có ích:** nó không "sửa" được judge yếu, nhưng phát hiện
>   và trung hòa các quyết định không ổn định (biến chúng thành tie).
> - **Khuyến nghị production:** dùng judge như một tầng cảnh báo (flag low-conf),
>   luôn swap-and-average, và route các ca `tie`/bất nhất quán sang human. Không
>   dùng điểm judge tuyệt đối làm gate tự động khi κ < 0.6.
