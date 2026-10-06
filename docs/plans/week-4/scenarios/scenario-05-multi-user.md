# Scenario 5: Sự cố nhiều người dùng - Video không xem được (Priority)

**Class of Service:** Priority (5-25 người dùng)  
**Trọng tâm:** Nhận diện pattern, gom ticket, điều tra theo dữ liệu, cập nhật đồng bộ

> **📌 Lưu ý (training):** Bạn không cần truy cập hệ thống thật. Hãy **giả định** kết quả check (monitoring/logs) nhưng vẫn phải trình bày **đúng quy trình** và **đủ dữ liệu cần hỏi/thu thập** như thực tế.

---

## Tình huống

Trong vòng 20 phút, bạn nhận 3 ticket cùng báo: **video bài học không chạy, loading mãi**.

**Dữ liệu mô phỏng:**

- Khoá học: `Advanced JavaScript`
- Lớp: `JS-ADV-HN-2412`
- Số người bị ảnh hưởng: **12 học viên** (Priority)
- Thời gian bắt đầu: khoảng **19:40**
- Thiết bị:
  - 8 học viên: web (Chrome 120+)
  - 4 học viên: mobile (iOS Safari / Android Chrome)
- Hiện tượng lỗi:
  - Video loading vô hạn, không phát
  - Một số user thấy lỗi “Cannot load media”
  - Một số user đổi mạng 4G vẫn lỗi

**1 trong 3 email/ticket (ví dụ):**

```
From: cxo@mindx.edu.vn
To: support@mindx.edu.vn
Subject: Không xem được video bài 3 - Advanced JS trên Denise

Dear Tech Team,

Học sinh lớp JS-ADV-HN-2412 phản ảnh vào bài 3 trên Denise thì video cứ loading mãi không chạy.

Em thử tắt/bật wifi rồi vẫn vậy.

Nhờ team hỗ trợ giúp em ạ.
CXO
```

---

## Nhiệm vụ của bạn

### 1. Triage & phân loại nhanh (< 5 phút)

- Xác định đây là **multi-user** (12 users) → **Priority**
- Xác định tính chất:
  - Chỉ 1 lớp/1 bài hay nhiều lớp?
  - Chỉ 1 video/1 lesson hay toàn bộ video?
  - Web-only hay cả mobile?

### 2. Ghi ticket + gom nhóm (Odoo) (< 10 phút)

- Tạo **1 ticket chính**: “Video playback issue - Lesson 3 (JS-ADV-HN-2412) - 12 users”
- Link/relate 2 ticket còn lại vào ticket chính (duplicate / related)
- Tag gợi ý: `lms`, `video`, `cdn`, `priority`, `js-adv`, `lesson-3`
- Ghi rõ:
  - Số users bị ảnh hưởng (12)
  - Thời điểm bắt đầu

### 3. Phản hồi ban đầu (ACK) (< 15 phút)

Mục tiêu: **nhận trách nhiệm điều phối**, không hứa ETA cố định.

- Xác nhận đã nhận và đang điều tra theo mức Priority
- Xin thêm 3 thông tin tối thiểu (để khỏi ping qua ping lại):
  - Link bài học / lesson ID
  - Ảnh/screenshot lỗi (nếu có)
  - Thiết bị + mạng (wifi/4G) + thời điểm gặp lỗi
- Đưa workaround nhanh:
  - Thử Incognito / tắt adblock / đổi browser
  - Nếu có link mirror (nếu nội bộ có) / hoặc “tạm dùng tài liệu PDF (nếu có)” để học tiếp

### 4. Thu thập dữ liệu điều tra (logic thực tế)

**Trong thực tế** bạn sẽ check:

- Monitoring: error rate video endpoint / CDN 4xx/5xx / response time
- Log/API gateway: correlationId / requestId / status code
- Storage (nếu có): asset tồn tại? permission? signed URL expiry?
- Phạm vi: lesson-specific hay system-wide?

**Trong training**: giả định kết quả theo 1 trong 3 branch dưới đây và trình bày quyết định.

---

## Branches & Required Responses (bắt buộc)

Yêu cầu: với mỗi branch, nộp:

- Step-by-step xử lý (theo 7-step)
- Email/Chat draft tiếng Việt (đúng audience)
- Nội dung update trong Odoo (ngắn, có timestamp)

### Branch A — Vấn đề “nội dung” (asset lỗi / sai permission / signed URL hết hạn)

**Dấu hiệu (giả định):**

- Chỉ lỗi ở `Lesson 3`, các lesson khác OK
- API trả `403` hoặc `404` cho file video của lesson
- Nhiều user, nhiều mạng đều lỗi (không phải user-side)

**Hướng xử lý:**

- Thu thập: lessonId, videoAssetId, thời điểm, 1-2 user sample
- Escalate dev/content ops với đầy đủ IDs
- Workaround: cung cấp bản video dự phòng (nếu có) / tạm chuyển sang bài khác

### Branch B — Vấn đề hệ thống/CDN (tăng lỗi 5xx hoặc timeout)

**Dấu hiệu (giả định):**

- Nhiều lesson/khoá khác cũng bắt đầu lỗi
- Monitoring: error rate tăng đột biến, response time tăng
- CDN/gateway: `502/504` spike

**Hướng xử lý:**

- Escalate DevOps/Infra ngay, cập nhật mỗi 15-30 phút
- Thông báo broadcast tới nhóm nội bộ (CXO/teacher) nếu ảnh hưởng rộng
- Theo dõi sau fix: error rate giảm? user xác nhận?

### Branch C — Nguyên nhân phía người dùng (adblock / DNS / browser cache)

**Dấu hiệu (giả định):**

- Chỉ một nhóm nhỏ user bị, cùng 1 nhà mạng / cùng extension
- Incognito phát bình thường
- Video phát OK trên mobile nhưng lỗi trên desktop (hoặc ngược lại)

**Hướng xử lý:**

- Gửi hướng dẫn user-side (check extension/adblock, clear cache, đổi DNS, thử 4G)
- Verify với 1-2 user mẫu
- Ghi rõ điều kiện đóng ticket: user xác nhận OK

---

## Kết quả cần nộp

1. **Bản ghi Ticket Odoo**
   - Screenshot/export thể hiện:
     - Ticket chính + relate tickets
     - Class of Service đúng (Priority)
     - Timeline update rõ
     - Communication log đầy đủ
2. **Email/Chat**
   - ACK ban đầu
   - Update điều tra / escalation (tuỳ branch)
   - Xác nhận giải quyết / follow-up

---

## Checklist

- [ ] Có ticket chính + relate/duplicate đúng các ticket liên quan
- [ ] Quyết định branch dựa trên “dấu hiệu” (không phỏng đoán)
- [ ] Có workaround tạm thời + verify với sample users (giả định)
- [ ] Odoo được cập nhật theo timeline (ngắn gọn, có timestamp)
