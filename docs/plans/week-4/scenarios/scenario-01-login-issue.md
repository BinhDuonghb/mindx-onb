# Scenario 1: Vấn đề đăng nhập (Standard)

**Class of Service:** Standard (< 5 người dùng)  
**Trọng tâm:** Xử lý ticket cơ bản, quy trình Odoo

> **📌 Lưu ý:** Đây là tình huống training giả định. Trong thực tế bạn sẽ check Base system, nhưng ở đây bạn sẽ giả định kết quả check và tập trung vào quy trình xử lý.

---

## Tình huống

Một giáo viên gửi email cho support về việc không thể đăng nhập vào hệ thống LMS của MindX. Vấn đề này chỉ ảnh hưởng đến một người dùng này.

**Email nhận được:**

```
From: nguyen.van.a@mindx.edu.vn
To: support@mindx.edu.vn
Subject: Không thể đăng nhập vào LMS

Chào Tech team,

Em đang cố đăng nhập vào LMS nhưng cứ bị lỗi "Invalid username or password".
Em chắc chắn mật khẩu của em đúng. Em cần truy cập tài liệu lớp học cho buổi học hôm nay.

Anh/chị có thể giúp em được không?

Cảm ơn,
Giáo viên Nguyễn Văn A
```

## Nhiệm vụ của bạn

### 1. Ghi nhận Ticket trong Odoo (Mục tiêu: < 15 phút)

Tạo ticket với:

- Tiêu đề: Rõ ràng và mô tả đầy đủ
- Danh mục: Hỗ trợ kỹ thuật
- Độ ưu tiên: Standard
- Class of Service: Standard (1 người dùng bị ảnh hưởng)
- Khách hàng: Tên và thông tin liên hệ của giáo viên
- Mô tả: Chi tiết đầy đủ
- Tags: login, LMS, teacher

### 2. Phản hồi ban đầu (Mục tiêu: < 30 phút từ khi nhận)

Viết email phản hồi chuyên nghiệp:

- Ghi nhận vấn đề
- Thể hiện sự đồng cảm về tính khẩn cấp (lớp học hôm nay)
- Giải thích những gì bạn sẽ kiểm tra
- Đặt timeline thực tế
- Cung cấp giải pháp tạm thời nếu có thể

### 3. Chẩn đoán

**Trong thực tế:** Bạn sẽ check Base system và application logs.  
**Trong training:** Giả định kết quả check và tập trung vào quy trình quyết định.

**Giả định kết quả check Base:**

- Account status: **Active** (hoặc Deactivated)
- Nhân sự status: **Đang làm việc**
- Email trong Base: Khớp với email ticket
- Lần cuối update: 2 tuần trước

**Quy trình điều tra (áp dụng logic thực tế):**

1. **Xác định nguyên nhân có thể:**
   - Password sai / quên password
   - Account bị deactivate (nhưng nhân sự vẫn làm việc)
   - Browser/cache issues
   - System-wide issue

2. **Chọn giải pháp dựa trên kết quả giả định:**
   - Nếu account Active → Reset password
   - Nếu account Deactivated + nhân sự đang làm việc → Reactivate + reset password
   - Nếu có system issue → Escalate

### 4. Giải quyết

**Các giải pháp phổ biến:**

**Option 1: Password Reset**

- Hướng dẫn người dùng reset password qua link
- Hoặc reset password cho người dùng trực tiếp
- Gửi thông tin đăng nhập mới qua email

**Option 2: Account Reactivation**

- Nếu account bị deactivate nhưng nhân sự đang làm việc
- Reactivate account trong Base
- Thông báo cho người dùng

**Option 3: Technical Issues**

- Check browser cache issues
- Verify correct login URL
- Clear cookies và thử lại

**Lưu ý:** Trong thực tế bạn sẽ thực hiện các bước check Base chi tiết.  
Ở đây bạn chỉ cần áp dụng logic quyết định dựa trên kết quả giả định.

### 5. Giao tiếp

Cập nhật ticket trong Odoo với:

- Kết quả điều tra
- Giải pháp đã áp dụng
- Phản hồi từ khách hàng

### 6. Theo dõi

Sau khi giải quyết:

- Xác nhận người dùng có thể đăng nhập thành công
- Hỏi xem có cần hỗ trợ thêm không
- Ghi lại giải pháp để tham khảo sau này

### 7. Tài liệu hóa

Trong Odoo:

- Ghi lại tất cả các hành động đã thực hiện
- Ghi lại thời gian đã sử dụng
- Tag các vấn đề tương tự
- Đóng ticket sau khi xác nhận

---

## Kết quả cần nộp

1. **Bản ghi Ticket Odoo**
   - Screenshot hoặc export cho thấy:
     - Phân loại đúng
     - Timeline đầy đủ
     - Tất cả giao tiếp đã được ghi lại
   - Link ticket trên Odoo

2. **Email phản hồi**
   - Email xác nhận ban đầu
   - Email giải quyết
   - Email xác nhận theo dõi

---

## Checklist đánh giá

### Quản lý Ticket

- [ ] Ticket được tạo trong Odoo
- [ ] Class of Service đúng (Standard)
- [ ] Tất cả các trường bắt buộc đã điền
- [ ] Tags phù hợp đã được áp dụng

### Giao tiếp

- [ ] Phản hồi ban đầu kịp thời
- [ ] Giọng điệu chuyên nghiệp và đồng cảm
- [ ] Giải thích rõ ràng các bước tiếp theo
- [ ] Kỳ vọng về thời gian được đưa ra và xử lý

### Quy trình kỹ thuật (gọn)

- [ ] Kiểm tra Base system (giả định): trạng thái account, trạng thái nhân sự, email khớp
- [ ] Branch xử lý (nộp bài bằng từng trường hợp):
  - Nếu **Active** → reset password hoặc hướng dẫn user tự reset
  - Nếu **Deactivated** → xác minh với HR/manager; nếu đang làm → reactivate + reset; nếu nghỉ việc → giải thích và đóng ticket
- [ ] Kiểm tra log đăng nhập (giả định) để tìm failed attempts hoặc pattern khác
- [ ] Chọn và thực hiện giải pháp phù hợp; xác minh kết quả với user (giả định)

### Tài liệu hóa (cốt lõi)

- [ ] Ghi mọi hành động **ngay khi thực hiện** trong Odoo (mỗi bước ngắn)
- [ ] Ghi rõ **quyết định** và lý do (ví dụ: account deactivated; HR xác nhận)
- [ ] Đính kèm bằng chứng liên quan (log / screenshot giả định)
- [ ] Đóng ticket chỉ khi có xác nhận vấn đề đã được giải quyết

---

## Những lỗi thường gặp cần tránh

❌ Quên ghi nhận ticket ngay lập tức  
❌ Không áp dụng logic check Base (dù là giả định)  
❌ Bật lại account deactivate mà không xem xét trạng thái nhân sự  
❌ Phản hồi quá kỹ thuật cho người dùng không phải kỹ thuật  
❌ Không đưa ra timeline dự kiến
❌ Đóng ticket trước khi có xác nhận (giả định)  
❌ Thiếu tài liệu trong Odoo

---

## Template Email phản hồi

```
Subject: RE: Không thể đăng nhập vào LMS - Ticket #[SỐ]

Chào Teacher Nguyễn Văn A,

Cảm ơn bạn đã liên hệ. Team đã ghi nhận vấn đề không thể đăng nhập vào hệ thống LMS.

Team sẽ thực hiện kiểm tra tài khoản của bạn trên hệ thống và dự kiến sẽ có phản hồi trong vòng 30 phút (09:30 AM hôm nay).

Trong lúc chờ, bạn vui lòng thử:
- Sử dụng chế độ ẩn danh (Incognito) để đăng nhập
- Đảm bảo đang dùng đúng địa chỉ: lms.mindx.edu.vn

Cảm ơn bạn đã hỗ trợ !

Trân trọng,
MindX Support Team
Ticket #[SỐ]
```

**Template cho trường hợp Account bị Deactivate (đã reactivate):**

```
Subject: RE: Không thể đăng nhập vào LMS - Đã xử lý - Ticket #[SỐ]

Chào Teacher Nguyễn Văn A,

Team đã kiểm tra và phát hiện tài khoản của bạn đã bị deactivate trong hệ thống.

Sau khi xác nhận với team HR và quản lý trực tiếp của bạn, team đã reactivate tài khoản.

Bạn vui lòng thử đăng nhập lại giúp team và phản hồi thêm nếu vấn đề đã được xử lý.

Trân trọng,
MindX Support Team
Ticket #[SỐ]
```
