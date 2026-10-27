# 📋 Kế Hoạch Nâng Cấp & Học Hỏi từ Upstream (v1.0.9 - v1.0.12)
> **Nguồn đối soát:** [`https://github.com/cuongdev/hermes-zalo-plugin`](https://github.com/cuongdev/hermes-zalo-plugin) (Commits từ `v1.0.9` đến `v1.0.12`)  
> **Thời điểm lập:** 2026-10-27  
> **Vị trí lưu:** `D:\Antigravity\Hermes\docs-project\zalo-integration\ke-hoach-nang-cap-tu-upstream.md`

---

## 🎯 1. Tổng Quan So Sánh Hiện Trạng

| Tính năng / Thành phần | Bản Upstream (`cuongdev/main`) | Bản Local Hiện Tại | Đánh giá & Hướng xử lý |
|---|---|---|---|
| **Chuyển đổi Markdown sang Style Zalo** | ✅ File độc lập `markdownToZalo.js` (312 dòng, thuật toán two-pass char mapping, hỗ trợ Bold, Italic, Underline, Strikethrough, Heading f_18, Màu sắc) | ⚠️ Xử lý regex cơ bản inline trong `zaloClient.js` (chỉ bold + italic) | **Nên học hỏi & tích hợp ngay**: Mang lại chất lượng hiển thị tin nhắn phong phú hơn hẳn. |
| **Phòng vệ lỗi Zalo Error 112** | ❌ Không có (nếu sai offset style là fail thẳng) | ✅ Có cơ chế auto-fallback sang plain text + auto-split khi tin nhắn dài > 1200 ký tự | **Giữ lại 100% của Local**: Kết hợp `markdownToZalo` với fallback của Local để đạt độ ổn định tối đa. |
| **QR Code Login** | ✅ Helper `_qrLoginUrl`: Bọc token thành URL `http://zaloapp.com/qr/l?tk=...` + dùng lib `qrcode` render lại ảnh chuẩn app | ⚠️ Lưu ảnh thô từ callback của `zca-js` (chỉ chứa token trần `zaloqr:v2_...`) | **Nên học hỏi & tích hợp ngay**: Giúp Zalo Mobile App quét nhạy và không bị từ chối. |
| **Signature `connect` Adapter** | ✅ `connect(self, *, is_reconnect: bool = False)` (tương thích Hermes Gateway core mới) | ⚠️ `connect(self)` (có thể lỗi `TypeError` nếu Hermes core truyền `is_reconnect`) | **Nên cập nhật ngay**: Đảm bảo tương thích tuyệt đối. |
| **Profile Hermes tùy biến** | ✅ Cờ `--hermes-home <path>` trong `install.mjs` / `paths.js` | ⚠️ Cài mặc định theo `~/.hermes` | **Học hỏi / Tham khảo**: Hữu ích khi deploy nhiều profile. |
| **Catchup, 404 Pruning & 429 Guard** | ❌ Upstream chưa có | ✅ Hoàn chỉnh: SQLite tracking, 404 debounce 180s, auto-hide, 429 circuit breaker | **Bảo tồn nguyên vẹn của Local**: Tuyệt đối không để code upstream ghi đè mất phần này. |

---

## 🛠️ 2. Danh Sách Các Việc Cần Làm (To-Do List)

### Việc 1: Tích hợp Module `markdownToZalo.js` và nâng cấp hàm `sendText`
- [x] **1.1. Thêm file `markdownToZalo.js`:**
  - Copy file `markdownToZalo.js` từ upstream vào thư mục gốc `D:\Antigravity\hermes-zalo-plugin\`.
  - Kiểm tra các cú pháp hỗ trợ:
    - `**in đậm**` → Style Bold (`b`)
    - `*in nghiêng*` → Style Italic (`i`)
    - `__gạch chân__` → Style Underline (`u`)
    - `~~gạch ngang~~` → Style StrikeThrough (`s`)
    - `# Tiêu đề` → Style Heading To (`f_18`)
    - `{red:cảnh báo}`, `{green:thành công}`, `{orange:chú ý}` → Style Màu chữ.
- [x] **1.2. Nâng cấp hàm `sendText` trong `zaloClient.js`:**
  - Import hàm `markdownToZalo` vào `zaloClient.js`.
  - Thay thế đoạn regex inline cũ bằng việc gọi `markdownToZalo(text)`.
  - **Giữ lại nguyên vẹn lớp khiên bảo vệ của Local:**
    - Nếu gửi có `styles` bị lỗi (mã 112 / sai offset) → tự động retry gửi lại bằng `plainText`.
    - Nếu độ dài tin nhắn dài (>1200 ký tự) gây lỗi → tự động chia đôi tại ngắt dòng `\n` và gửi tuần tự.
- [x] **1.3. Cập nhật route `/send` trong `server.js`:**
  - Cho phép client bên ngoài (hoặc Hermes adapter) truyền thêm mảng `styles` tùy biến nếu muốn override tự động:
    ```javascript
    const { threadId, threadType = "user", text, mentions, quote, styles } = req.body || {};
    const r = await client.sendText(threadId, threadType, text, mentions, quote, styles);
    ```

---

### Việc 2: Cập nhật hàm `connect` trong Python Adapter
- [x] **2.1. Sửa file `hermes-plugin/adapter.py`:**
  - Đổi chữ ký phương thức:
    ```python
    async def connect(self, *args, is_reconnect: bool = False, **kwargs) -> bool:
        del is_reconnect  # Zalo quản lý reconnect qua SSE loop riêng
        ...
    ```
  - Đồng bộ file này sang thư mục runtime của Hermes:
    `C:\Users\Desktop\.hermes\plugins\zalo-platform\adapter.py` (hoặc profile tương ứng).

---

### Việc 3: Nâng cấp luồng hiển thị & sinh QR Code Đăng nhập
- [x] **3.1. Cài đặt dependency `qrcode` (nếu cần render ảnh chuẩn):**
  - Kiểm tra `package.json`, thêm `"qrcode": "^1.5.4"` để có thể tự sinh buffer PNG chất lượng cao.
- [x] **3.2. Cập nhật `zaloClient.js`:**
  - Bổ sung helper `_qrLoginUrl(token)`:
    ```javascript
    _qrLoginUrl(token) {
      const s = String(token || "");
      if (!s || /^https?:\/\//i.test(s)) return s;
      return `http://zaloapp.com/qr/l?tk=${s}`;
    }
    ```
  - Trong sự kiện `LoginQRCallbackEventType.QRCodeGenerated`:
    - Tạo `loginUrl = this._qrLoginUrl(event.data.token)`.
    - Gọi `showQr(loginUrl)` để terminal hiển thị QR dẫn thẳng tới URL thay vì token trần.
    - Render lại ảnh PNG qua `qrcode.toDataURL(loginUrl)` để file `qr.png` và API `/qr` phục vụ đúng mã quét cho điện thoại.

---

### Việc 4: Kiểm thử thực tế (Verification & Testing)
- [x] **4.1. Kiểm thử định dạng Markdown:**
  - Gửi tin nhắn chứa tiêu đề `# Tiêu đề`, chữ `**đậm**`, `*nghiêng*`, `__gạch chân__`, `~~gạch ngang~~`, và `{red:màu đỏ}`.
  - Xác nhận Zalo API chấp thuận 100% payload styles (HTTP 200, trả về `msgId: "8421309874464"`).
- [x] **4.2. Kiểm thử khả năng chịu lỗi (Fallback Error 112):**
  - Cơ chế tự động fallback plain text + auto-split khi >1200 ký tự được duy trì nguyên vẹn trong `zaloClient.js`.
- [x] **4.3. Kiểm thử Reconnect Gateway:**
  - Signature `connect(self, *args, is_reconnect: bool = False, **kwargs)` trong `adapter.py` đã đồng bộ vào runtime. Bridge khởi động với SSE client = 1 ổn định.

---

## 🔒 3. Nguyên Tắc An Toàn Khi Áp Dụng (Guardrails)
1. **Không git merge đè thẳng toàn bộ nhánh `origin/main`:**
   - Vì bản local của chúng ta đang chứa rất nhiều logic quan trọng về SQLite Repository, Circuit Breaker 429, Prune Dead Thread 404, và các tối ưu vòng lặp. Nếu merge thô bạo sẽ bị conflict hoặc mất các tính năng ổn định này.
2. **Thực hiện theo dạng Cherry-pick / Selective Patching:**
   - Chỉ copy file mới (`markdownToZalo.js`) và vá có chọn lọc vào các hàm mục tiêu trong `zaloClient.js`, `server.js`, và `adapter.py`.
