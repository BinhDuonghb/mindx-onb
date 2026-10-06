# Scenario 3: Lỗi nghiêm trọng (Expedite)

**Class of Service:** Expedite (> 25 người dùng)  
**Trọng tâm:** Phản ứng khẩn cấp, quản lý stakeholders

> **📌 Lưu ý:** Đây là tình huống training giả định. Bạn sẽ tập trung vào quy trình xử lý khẩn cấp, quản lý stakeholders và giao tiếp dưới áp lực.

---

## Context

Nhiều tickets đang tràn vào. Manager team vận hành ping bạn trên Teams. Đây là sự cố Expedite đầu tiên của bạn.

## Tình huống

Hệ thống nộp bài thi của học viên đã bị sập. 50+ học viên từ nhiều lớp không thể nộp bài thi cuối kỳ.

**Ticket ban đầu:**

```
From: cxo@mindx.edu.vn
Subject: KHẨN CẤP - Không nộp được bài trên hệ thống

KHẨN CẤP: Hệ thống nộp bài thi hoàn toàn không hoạt động!

Nhiều lớp học không thể nộp bài thi cuối kỳ.
Lỗi: "System error - please contact administrator"

Các lớp bị ảnh hưởng:
- WEB102-HN (20 học viên)
- DATA101-SG (18 học viên)
- MOBILE201-HN (15 học viên)

Lê Ngọc A
CXO Khối 18+ Cơ sở Nguyễn Chí Thanh
```

**Manager của team vận hành trên Teams:**

```
@your-name - Bên chị mới gửi ticket lỗi hệ thống LMS không nộp được bài ? Em check xem rồi xử lý cho chị !.
```

## Nhiệm vụ của bạn

### 1. Nhận diện ngay lập tức (< 2 phút)

**Tiêu chí phân loại Expedite đã đáp ứng:**

- ✅ > 25 người dùng bị ảnh hưởng (50+)
- ✅ Chức năng kinh doanh quan trọng (bài thi)
- ✅ Hệ thống hoàn toàn lỗi
- ✅ Nhiều stakeholders

**Hành động:** Đây là EXPEDITE class - giao thức khẩn cấp

### 2. Phản ứng khẩn cấp (< 5 phút)

**Các hành động ngay lập tức song song:**

A. **Ghi nhận với người dùng, stakeholder:**

- Xác nhận đã nhận
- Xác nhận xử lý như khẩn cấp
- Cam kết cập nhật liên tục
- Cập nhật người dùng, stakeholder khi có tiến triển

B. **Cảnh báo team:**

- Ping dev team, engineer hỗ trợ ngay lập tức

C. **Ghi nhận trong Odoo:**

- Đánh dấu là Expedite
- Độ ưu tiên cao nhất
- Liên kết các tickets liên quan

### 3. Thu thập thông tin (< 10 phút)

**Trong thực tế:** Bạn sẽ check monitoring và logs ngay lập tức cùng engineers kinh nghiệm khác (nếu có).  
**Trong training:** Giả định kết quả và tập trung vào quy trình xử lý khẩn cấp.

**Giả định thông tin đã thu thập:**

- Lỗi: "System error" (100% failure rate)
- Bắt đầu: 30 phút trước
- Azure App Insights: Exception spike, database connection errors
- Application logs: Database timeout, không thể lưu submissions

**Quy trình (áp dụng logic thực tế):**

1. Xác định đây là system-wide issue → Cần dev team ngay
2. Tìm xem có workaround nhanh → Revert code mới, release lại để database tự động reconnect lại

### 4. Escalation & Phối hợp (< 15 phút)

**Cảnh báo Dev Team (Khẩn cấp):**

```
🚨 EXPEDITE - Hệ thống nộp bài thi DOWN 🚨

TÁC ĐỘNG NGHIÊM TRỌNG:
- 50+ học viên không thể nộp bài thi cuối kỳ
- Tỷ lệ lỗi 100%
- Nhiều lớp bị ảnh hưởng

LỖI: "System error - please contact administrator"

PHÁT HIỆN BAN ĐẦU:
- [Lỗi từ logs]
- [Quan sát monitoring]
- [Bắt đầu vào thời điểm gần đúng]

YÊU CẦU: Điều tra ngay lập tức + sửa khẩn cấp

CẬP NHẬT TRẠNG THÁI: Cập nhật thường xuyên khi có tiến triển

TICKET: #[SỐ]

@senior-engineer @engineer-team @devops
```

### 5. Quản lý Stakeholders

**Nhiều đối tượng:**

**A. Quản lý team vận hành:**

- Chi tiết kỹ thuật tối thiểu
- Tập trung vào tác động kinh doanh
- Các lựa chọn với ưu/nhược điểm
- Ước tính tác động và phương án

**B. CXO (Đại diện cho người dùng bị ảnh hưởng):**

- Ghi nhận vấn đề
- Thông báo về phương án sửa / giải pháp tạm thời
- Giải pháp tạm thời nếu có

### 6. Giải quyết & Xác minh

**Khi dev team deploy fix:**

- Tự test nộp bài
- Xác minh qua các lớp khác nhau
- Theo dõi ngắn hạn sau khi fix

**Nếu thành công:**

- Thông báo giải quyết
- Theo dõi và kiểm tra hệ thống sau khi xử lý

### 7. Sau sự cố

- Tài liệu hóa lịch sử sự cố đầy đủ
- Thu thập dữ liệu cho post-mortem
- Tham gia review sự cố
- Tài liệu hóa cho các phản ứng expedite trong tương lai

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

### Phản ứng khẩn cấp

- [ ] Class Expedite được nhận diện ngay lập tức
- [ ] Nhiều stakeholders được cảnh báo nhanh chóng
- [ ] Manager được thông báo phù hợp
- [ ] Dev team được cung cấp đầy đủ ngữ cảnh

### Communicate

- [ ] Cập nhật thường xuyên được duy trì
- [ ] Các đối tượng khác nhau được xử lý phù hợp
- [ ] Giọng điệu giữ bình tĩnh và chuyên nghiệp
- [ ] Timeline dự kiến được cung cấp

### Phối hợp với team

- [ ] Thông tin chi tiết, rõ ràng cho dev team
- [ ] Có đưa ra giải pháp tạm thời (nếu có)
- [ ] Vấn đề sau khi được fixed đã được kiểm tra lại

---

## Lỗi thường gặp

### ❌ Lỗi 1: Chần chừ vì phân tích quá lâu

**Sai:** Dành 30 phút điều tra trước khi cảnh báo dev team  
**Đúng:** Cảnh báo dev team trong vòng 5 phút, điều tra song song

### ❌ Lỗi 2: Quên cập nhật

**Sai:** Chìm trong công việc, quên cập nhật stakeholders  
**Đúng:** Đặt timer, cập nhật mỗi 15 phút dù thế nào

### ❌ Lỗi 3: Giao tiếp quá nhiều thông tin kỹ thuật

**Sai:** Gửi Quản lý vận hành, CXO error logs chi tiết  
**Đúng:** Gửi lại tác động sự cố lên hệ thống + timeline + các lựa chọn

### ❌ Lỗi 4: Tự xử lý một mình

**Sai:** Xử lý mọi thứ một mình  
**Đúng:** Phối hợp team, mỗi người 1 vai trò khác nhau, engineer xử lý sự cố, vai trò giao tiếp. Escalate lên nhiều mức khi cần.

### ❌ Lỗi 5: Thông báo sớm

**Sai:** "Thông báo đã sửa" sau khi dev deploy  
**Đúng:** Tự check xác minh và theo dõi trước khi thông báo đã xử lý sự cố xong. Theo dõi một khoảng thời gian sau sự cố.
