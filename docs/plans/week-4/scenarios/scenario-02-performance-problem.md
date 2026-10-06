# Scenario 2: Vấn đề Performance (Priority)

**Class of Service:** Priority (5-25 người dùng)  
**Trọng tâm:** Điều tra, phân tích log, escalation

> **📌 Lưu ý:** Đây là tình huống training giả định. Bạn sẽ tập trung vào quy trình điều tra và quyết định escalation, không cần truy cập monitoring thật.

---

## Tình huống

Bạn nhận được một ticket từ CXO (Class Administrator) báo cáo rằng 15 học viên trong một lớp học trực tuyến đang gặp tình trạng tải trang cực kỳ chậm trong LMS. Lớp học đang diễn ra ngay bây giờ.

**Chi tiết ticket:**

```
From: coordinator.ha@mindx.edu.vn
Subject: Khẩn cấp - Lớp học đang gặp tình trạng chậm nghiêm trọng

Chào Tech team,

Chúng tôi có 15 học viên trong lớp Web Development (Lớp WEB101-HN-2024) đang gặp tình trạng tải trang rất chậm trong Denise.

Các trang đang mất hơn 1 phút để truy cập. Một số học viên không thể nộp bài tập.

Xin hãy giúp khẩn cấp.

Nguyễn Thị Hà
CXO
```

## Nhiệm vụ của bạn

### 1. Phân loại ngay lập tức (< 5 phút)

Đánh giá:

- Có bao nhiêu người dùng bị ảnh hưởng? (15 = Priority class)
- Có đang chặn công việc không? (Có = Độ ưu tiên cao hơn)
- Có giải pháp tạm thời không? (Cần điều tra)
- Thời gian tác động? (Đang xảy ra ngay = Khẩn cấp)

**Quyết định phân loại:**

- Class of Service: **Priority** (5-25 người dùng bị ảnh hưởng, chặn công việc)
- Không phải Expedite vì < 25 người dùng
- Không phải Standard vì nhiều người dùng + chặn công việc

### 2. Ghi nhận trong Odoo (< 10 phút)

Tạo ticket với:

- Tiêu đề: "LMS Performance Issue - Class WEB101-HN-2024 (15 users)"
- Độ ưu tiên: High
- Class of Service: Priority
- Người dùng bị ảnh hưởng: 15 học viên + 1 CXO
- Timeline: Sự cố đang diễn ra (lớp học đang tiến hành)
- Tags: performance, LMS, priority, web101

### 3. Phản hồi ban đầu (< 15 phút từ khi nhận)

Ghi nhận tính khẩn cấp và nêu các hành động ngay lập tức:

- Xác nhận đã nhận và độ ưu tiên
- Nêu rằng bạn đang điều tra ngay lập tức
- Đề cập việc kiểm tra với dev team nếu cần
- Cập nhật người dùng khi có tiến triển

### 4. Điều tra

**Trong thực tế:** Bạn sẽ check Azure App Insights, logs, system health.  
**Trong training:** Giả định kết quả và tập trung vào quy trình quyết định.

**Giả định kết quả điều tra:**

- Azure App Insights: Response time tăng đột biến từ 14:00 (từ 2s → 35s)
- Application logs: Nhiều timeout errors, slow queries
- System health: Database connection pool gần đầy
- Pattern: Chỉ ảnh hưởng lớp WEB101-HN-2024, các lớp khác bình thường

**Quy trình điều tra (áp dụng logic thực tế):**

1. **Xác định phạm vi:** Toàn hệ thống hay cục bộ?
2. **Xác định nguyên nhân có thể:** Database, cache, hoặc code issue?
3. **Quyết định:** Tự xử lý hay escalate dev team?

### 5. Quyết định Escalation

**Escalate cho Dev Team nếu:**

- Phát hiện suy giảm performance toàn hệ thống
- Xác định vấn đề database
- Cần code deployment hoặc thay đổi config
- Nguyên nhân gốc ngoài phạm vi support

**Tự xử lý nếu:**

- Vấn đề đã biết với giải pháp tạm thời được ghi lại
- Vấn đề phía người dùng (browser, network)

### 6. Phối hợp

**Nếu escalate:**

Tạo message Teams cho Dev Team / Engineer hỗ trợ:

```
@dev-team Vấn đề Performance Khẩn cấp

Lớp: WEB101-HN-2024
Người dùng bị ảnh hưởng: 15 học viên
Tác động: Tải trang 30+ giây, chặn lớp học
Thời gian: Lớp học đang diễn ra
Ticket: #[SỐ]

Kết quả điều tra:
- [Các phát hiện từ monitoring]
- [Logs/screenshots liên quan]

Cần: Phân tích nguyên nhân gốc và sửa

Nhạy cảm về thời gian: Lớp học đang diễn ra
```

### 7. Vòng lặp giao tiếp

- **Với người dùng (cập nhật khi có tiến triển):**

- Cập nhật tiến độ điều tra
- Các phát hiện cho đến nay
- Các bước tiếp theo
- Cập nhật thay đổi nếu cần

**Trong Odoo:**

- Ghi lại tất cả các bước điều tra
- Ghi lại phối hợp với dev team
- Tài liệu hóa các phát hiện

### 8. Giải pháp tạm thời (Nếu có)

Trong khi chờ sửa:

- Học viên có thể dùng browser khác không?
- Lớp học có thể chuyển sang hoạt động dự phòng không?
- Có thể nộp bài tập qua email tạm thời không?

### 9. Giải quyết & Theo dõi

- Xác minh sửa với người dùng bị ảnh hưởng
- Theo dõi tái phát
- Tài liệu hóa nguyên nhân gốc
- Tạo bài viết knowledge base

---

## Kết quả cần nộp

1. **Bản ghi Ticket Odoo**
   - Screenshot hoặc export cho thấy:
     - Phân loại đúng
     - Timeline đầy đủ
     - Tất cả giao tiếp đã được ghi lại
   - Link ticket trên Odoo (link trong bản ghi là đủ để mentor xem)

2. **Email phản hồi**
   - Email xác nhận ban đầu
   - Email cập nhật điều tra / escalation (nếu có)
   - Email xác nhận giải quyết / follow-up

---

## Checklist đánh giá

### Phân loại & Phân hạng

- [ ] Xác định đúng là Priority (không phải Standard hoặc Expedite)
- [ ] Đánh giá tác động và tính khẩn cấp chính xác
- [ ] Đặt mức độ ưu tiên phù hợp

### Điều tra

- [ ] Đã kiểm tra monitoring dashboards
- [ ] Đã xem lại logs liên quan
- [ ] Xác định patterns hoặc bất thường
- [ ] Tài liệu hóa phát hiện rõ ràng

### Escalation

- [ ] Ra quyết định escalation phù hợp
- [ ] Cung cấp đầy đủ ngữ cảnh cho dev team
- [ ] Bao gồm chi tiết kỹ thuật liên quan

### Giao tiếp

- [ ] Phản hồi ban đầu nhanh do tính khẩn cấp
- [ ] Cung cấp cập nhật thường xuyên
- [ ] Kỳ vọng về thời gian được đưa ra và xử lý

### Giải quyết

- [ ] Vấn đề được giải quyết hoặc cung cấp giải pháp tạm thời
- [ ] Giải pháp được xác minh lại với người dùng
- [ ] Theo dõi đã hoàn thành
- [ ] Tài liệu hóa đầy đủ

---

## Thách thức thường gặp

### Thách thức 1: Điều tra không đầy đủ

**Sai:** Escalate ngay lập tức mà không kiểm tra  
**Đúng:** Điều tra trước, escalate với dữ liệu

### Thách thức 2: Giao tiếp Dev Team kém

**Sai:** "LMS chậm, xin sửa"  
**Đúng:** Chi tiết cụ thể, logs, tác động, timeline

### Thách thức 3: Người dùng bị bỏ quên

**Sai:** Không cập nhật trong khi điều tra  
**Đúng:** Cập nhật thường xuyên ngay cả khi không có tiến triển

### Thách thức 4: Thiếu lý do ưu tiên

**Sai:** "Độ ưu tiên cao vì người dùng nói khẩn cấp"  
**Đúng:** "Priority: 15 người dùng bị chặn, lớp học đang diễn ra"

---

## Checklist điều tra (Tham khảo - áp dụng logic trong thực tế)

**Trong training:** Bạn sẽ giả định đã check các điểm này và tập trung vào quyết định.

- [ ] Xác định phạm vi ảnh hưởng (toàn hệ thống / cục bộ)
- [ ] Xác định nguyên nhân có thể (database / cache / code)
- [ ] Đánh giá mức độ nghiêm trọng
- [ ] Quyết định escalation hay tự xử lý

---

## Templates Email

### Phản hồi ban đầu

```
Subject: RE: Khẩn cấp - Lớp học đang gặp tình trạng chậm nghiêm trọng - PRIORITY Ticket #[SỐ]

Chào Coordinator Hà,

Team đã ghi nhận vấn đề và đang ưu tiên xử lý.

Hiện tại, team đang thực hiện ngay kiểm tra hệ thống, thông tin sẽ cập nhật cho chị trong vòng 15 phút tiếp theo.

Trong lúc chờ, chị vui lòng:
- Kiểm tra xem issue còn đang xảy ra không
- Ghi chú lại các trang cụ thể bị chậm và gửi cho team xin thêm thông tin
- Thử truy cập trình duyệt ẩn danh

Team sẽ cập nhật liên tục tình hình điều tra và ưu tiên xử lý case này.

Trân trọng,
[Tên của bạn]
Ticket #[SỐ]
```

### Escalation Dev Team

```
@dev-team 🔴 PRIORITY Vấn đề Performance

**Ticket:** #[SỐ]
**Tác động:** 15 học viên bị chặn, lớp học đang diễn ra

**Vấn đề gặp phải:**
- Thời gian tải trang 30+ giây
- Lỗi nộp bài tập
- Ảnh hưởng lớp cụ thể: WEB101-HN-2024

**Kết quả điều tra sơ bộ:**
- Tăng đột biến thời gian phản hồi từ 14:00 (đính kèm screenshot)
- [Lỗi cụ thể từ logs nếu tìm thấy]
- [Vấn đề Database/API nếu xác định]

**Monitoring:** [Link đến App Insights dashboard]
**Logs:** [Trích đoạn log liên quan]

**Yêu cầu:** Giải pháp tạm thời để xử lý

**Timeline:** Sẽ cập nhật user mỗi 15 phút
```
