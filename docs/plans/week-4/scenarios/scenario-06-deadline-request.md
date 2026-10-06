# Scenario 6: Yêu cầu có deadline - Báo cáo cần gấp (Fixed Deadline)

**Class of Service:** Fixed Deadline  
**Trọng tâm:** Clarify scope, đánh giá khả thi, đàm phán “MVP vs nice-to-have”, quản lý kỳ vọng (không hứa bừa)

> **📌 Lưu ý (training):** Bạn sẽ **giả định** khả năng truy cập dữ liệu/BI. Tập trung vào: hỏi đúng, đưa plan đúng, và giao tiếp đúng với stakeholder.

---

## Bối cảnh

Một Director cần báo cáo cho cuộc họp quan trọng. Deadline cứng, nhưng yêu cầu ban đầu còn mơ hồ và có rủi ro về scope.

## Tình huống

**Email nhận được (ví dụ):**

```
From: director@mindx.edu.vn
To: support@mindx.edu.vn
Subject: Cần báo cáo tuyển sinh trước 09:00 sáng ngày kia

Mình cần báo cáo tuyển sinh để trình bày lúc 09:00 sáng ngày kia.
Cần lọc theo cơ sở + chương trình + thời gian, và có breakdown theo khoá.
Nhờ team hỗ trợ gấp.
```

**Dữ liệu thực tế mô phỏng:**

- Deadline: **09:00 sáng ngày kia** (còn 2 ngày)
- Dữ liệu liên quan: enrollment, revenue, completion (có thể nằm nhiều nguồn)
- Rủi ro: dữ liệu nhạy cảm (PII), query nặng, định nghĩa metric không rõ

---

## Nhiệm vụ của bạn

### 1. Triage (< 10 phút)

- Class: **Fixed Deadline**
- Mục tiêu: chốt scope tối thiểu cần để “đủ dùng cho họp”

### 2. Ghi ticket trong Odoo (< 15 phút)

- Title: “Fixed Deadline - Enrollment report for Director (Due 09:00 tomorrow)”
- Ghi rõ:
  - Deadline cứng
  - Audience/impact (business impact cao)
  - Phạm vi dữ liệu dự kiến
  - Rủi ro (permission/PII/định nghĩa metric)
- Tag gợi ý: `fixed-deadline`, `reporting`, `enrollment`, `director`

### 3. Phản hồi ban đầu (ACK + hỏi đúng) (< 30 phút)

Mục tiêu: **không** hỏi lan man, hỏi để chốt scope.

Hỏi để ra được scope (Ví dụ):

- Dữ liệu được trích xuất trong khoảng thời gian nào (tháng này hay cả năm 2025)
- Thông tin cần trong báo cáo bao gồm trường thông tin nào (có bao gồm danh tính khách hàng không)
- Vì thời gian tương đối gấp, báo cáo có ưu tiên xử lý phần nào trước không (VD: Lọc theo cơ sở / chương trình cụ thể nào)

### 4. Đánh giá khả thi & đề xuất plan, timeline

- Sau khi có đủ thông tin, gửi lại template dữ liệu và phạm vi dữ liệu đề xuất để xác nhận

### 5. Xin phê duyệt

- Request tới quản lý trực tiếp về phạm vi dữ liệu, thông tin nhạy cảm, đề xuất yêu cầu duyệt dữ liệu cần trích xuất

### 6. Phản hồi theo timeline, trao đổi nếu có vấn đề phát sinh

- Sau khi được phê duyệt trích xuất dữ liệu, tiến hành phân tích và trích xuất dữ liệu theo đề xuất, đồng thời phản hồi lại timeline dự kiến tới stakeholder
- Trong quá trình xử lý dữ liệu, nếu có vấn đề phát sinh cần raise sớm và đưa ra các option xử lý.

---

## Kết quả cần nộp

1. **Bản ghi Ticket Odoo**
   - Classification: Fixed Deadline
   - Timeline + các mốc update
   - Scope đã chốt (MVP/nice-to-have)
2. **Email/Chat**
   - ACK + clarifying questions
   - Email chốt scope / đàm phán
   - Email bàn giao (kèm link/file)

---

## Checklist

- [ ] Đã hỏi đúng để chốt scope (không để mơ hồ)
- [ ] Có timeline cập nhật thông tin
- [ ] Có nhánh xử lý khi gặp vấn đề phát sinh
- [ ] Ticket Odoo được cập nhật tài liệu đầy đủ
