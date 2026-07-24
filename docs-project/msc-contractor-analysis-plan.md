# 📝 Kế hoạch & Kết quả Nghiên cứu: Phân tích Nhà thầu (MSC Contractor Analysis)

## 1. Kết quả nghiên cứu hiện tại (Đã làm)

Chúng tôi đã thiết lập kết nối đến tab Chrome đang chạy qua CDP (Chrome DevTools Protocol - port `9222`) và thu thập các thông tin sau từ trang **Phân tích nhà thầu / Phân tích cơ hội**:

### A. Dữ liệu đã trích xuất từ Vue Component State
* Trích xuất thành công bảng dữ liệu **Tình hình tham dự thầu** của nhà thầu **VINMED (vn0108557117)** với:
  * Tổng số gói tham dự: **52**
  * Số gói trúng thầu: **21 (40,4%)**
  * Số gói trượt thầu: **30 (57,7%)**
  * Tổng giá trị trúng thầu: **9.364.870.000 VND**
  * Tỷ lệ tiết kiệm trung bình: **0,2%**
  * Các chỉ số chi tiết khác như số lượng gói thầu duy nhất tham dự, số gói đáp ứng kỹ thuật, số lần hủy thầu, v.v.

### B. Endpoint API đã capture từ Network Traffic
Trang web sử dụng Axios để gọi các API ẩn dưới portlet `/o/egp-portal-personal-page/services/`:
1. **`/static-overview-nt`**:
   * **Phương thức**: `POST`
   * **Tham số**: Truyền kèm `token` (Bearer token trong query string) và payload chứa thông tin tìm kiếm.
   * **Vai trò**: Trả về dữ liệu thống kê tổng quan (các chỉ số tiết kiệm, trúng/trượt, số lượng gói thầu theo lĩnh vực). Đây chính là API cung cấp dữ liệu cho bảng "Tình hình tham dự thầu".
2. **`/lcnt/bidding-data-statistic/save-percent-avg`**:
   * **Phương thức**: `POST`
   * **Vai trò**: Lưu trữ/tính toán thống kê tỷ lệ tiết kiệm trung bình.
3. Các endpoints bổ trợ khác:
   * `/get-org-info`: Lấy thông tin tổ chức/nhà thầu.
   * `/get-user-info`: Lấy thông tin tài khoản đăng nhập.

---

## 2. Kết quả triển khai tích hợp (Đã làm)

Chúng tôi đã hoàn thành tích hợp tính năng **Phân tích nhà thầu** vào MSC Skill:

### 🛠️ Script mới
*   **Đường dẫn**: [msc_contractor_analysis.py](file:///d:/Antigravity/Hermes/skills/productivity/msc/scripts/msc_contractor_analysis.py)
*   **Tính năng**: Gửi request đến `/o/egp-portal-personal-page/services/static-overview-nt?token=...`, bóc tách dữ liệu và sinh báo cáo Markdown chi tiết (bảng thống kê đầy đủ các cột: Tổng số, Hàng hóa, Xây lắp, Phi tư vấn, Tư vấn, Hỗn hợp).
*   **Xử lý mã hóa**: Tự động cấu hình `sys.stdout` UTF-8 trên Windows để in tiếng Việt và emoji không bị lỗi.

### 🔗 Đăng ký lệnh chat
*   Tích hợp lệnh `/msc ptnt <MST>` vào cả hai bộ định tuyến [lib/msc_mvp_router.py](file:///d:/Antigravity/Hermes/skills/productivity/msc/lib/msc_mvp_router.py) và [scripts/msc_mvp_router.py](file:///d:/Antigravity/Hermes/skills/productivity/msc/scripts/msc_mvp_router.py).
*   Ví dụ sử dụng: `/msc ptnt vn0108557117`

### 🔄 Đồng bộ Token tự động
*   Đăng nhập lại trên Chrome thành công, chạy script capture để cập nhật token mới lưu vào tệp [C:\Users\Desktop\.hermes\.env](file:///C:/Users/Desktop/.hermes/.env).

---

## 3. Các bước tiếp theo
*   Hỗ trợ hiển thị qua Telegram inline menu (`/mscmenu`) và liên kết báo cáo phân tích sâu các gói thầu chi tiết của nhà thầu.


** Bổ sung 17/07/2026
## Plan: Áp dụng persistent browser profile cho Mua Sắm Công

**Mục tiêu:** Loại bỏ phụ thuộc vào Chrome debug port chạy nền liên tục, thay bằng cơ chế login-once-reuse-profile.

### Phân tích Kiến trúc & Giải pháp cho rủi ro DPAPI Cookie Encryption
*   **Vấn đề:** Trình duyệt Chrome/Chromium mã hóa cookie ở mức độ hệ điều hành (OS-level encryption - `os_crypt`). Trên Windows, cookie được mã hóa bằng **DPAPI** (liên kết chặt chẽ với tài khoản Windows User hiện tại). Nếu tạo profile trên Windows rồi mang thư mục đó vào trong Linux Docker Container, thư viện của container **sẽ không thể giải mã được cookie** do không có khóa giải mã DPAPI của Windows Host.
*   **Giải pháp:** Chạy toàn bộ Playwright (cả luồng headful đăng nhập và luồng headless lấy token) trực tiếp trên Windows Host. Thiết lập một dịch vụ HTTP nhỏ (FastAPI/Flask) chạy ngầm ở cổng cụ thể trên Windows Host để expose endpoint trả về token. Docker Container chỉ cần gọi HTTP GET ra ngoài Host qua `http://host.docker.internal:PORT/msc/tokens` để lấy token.

### Sơ đồ kiến trúc mới
```
┌─────────────────────────┐        HTTP GET Request     ┌────────────────────────┐
│  Docker Container       │  ────────────────────────▶  │  Windows Host          │
│  (Hermes skill /msc)    │  http://host.docker.internal│  ┌──────────────────┐  │
│                         │  :PORT/msc/tokens           │  │ Local FastAPI    │  │
│  requests.get(...)      │  ◀────────────────────────  │  │ token service    │  │
└─────────────────────────┘      JSON: {bearer_token,   │  └────────┬─────────┘  │
                                        jsession_cookie,│           │ calls      │
                                        csrf_token}     │           ▼            │
                                                        │  Playwright headless   │
                                                        │  (using msc_profile)   │
                                                        └────────────────────────┘
```

---

### Giai đoạn 1 — Thiết lập profile trên Windows Host (một lần, thủ công)
1. Thư mục lưu profile: `C:\Users\Desktop\.hermes\msc_profile\` (Windows).
2. **Không dùng Playwright ở bước này** (để tránh bị Google reCAPTCHA phát hiện CDP session đang hoạt động và ẩn/chặn widget xác thực).
3. Người dùng mở Chrome chính thức bằng command line trực tiếp trỏ vào profile:
   ```cmd
   "C:\Program Files\Google\Chrome\Application\chrome.exe" --user-data-dir="C:\Users\Desktop\.hermes\msc_profile"
   ```
4. Tiến hành đăng nhập thủ công vào `muasamcong.mpi.gov.vn`, giải CAPTCHA v2/v3 bình thường.
5. Đăng nhập thành công xong, tắt hoàn toàn tất cả cửa sổ Chrome vừa mở (đảm bảo không còn tiến trình `chrome.exe` chạy ngầm để tránh khóa file profile). Profile lúc này đã có đủ session cookies của Liferay.

### Giai đoạn 2 — Thiết lập dịch vụ Token Bridge trên Windows Host
1. Viết script `msc_token_service.py` (FastAPI, chạy ngầm trên Windows Host):
   * Định nghĩa endpoint `GET /msc/tokens`.
   * Khi nhận request, khởi chạy Playwright **headless**, tái sử dụng profile `msc_profile`.
   * Điều hướng thẳng tới trang cá nhân: `https://muasamcong.mpi.gov.vn/web/guest/profile-info`.
   * Lắng nghe các request đi để bắt token.
     * Bắt Access Token Keycloak qua URL hint: `/auth/realms/`.
     * Bắt `JSESSIONID` qua `context.cookies()`.
     * Bắt CSRF token bằng cách đọc biến `window.Liferay.authToken` trên trang.
   * Trả về JSON chứa các token này và đóng browser lập tức để giải phóng RAM.

### Giai đoạn 3 — Xử lý hết hạn session (fallback)
1. Nếu Liferay session trong profile hết hạn (gọi API trả về 401/403):
   * Gửi cảnh báo qua Telegram/Zalo: "Phiên đăng nhập Mua Sắm Công hết hạn. Vui lòng chạy lại msc_login_setup.py trên máy chủ Windows để gia hạn."
   * Không tự động retry vô hạn để tránh khóa tài khoản.

### Giai đoạn 4 — Tích hợp vào Hermes skill trong Docker
1. Sửa code trong `msc_contractor_history.py` và `msc_contractor_analysis.py` (đang chạy trong Docker). Thay vì kết nối ra CDP debug port `9222`, chuyển sang gọi:
   `requests.get("http://host.docker.internal:PORT/msc/tokens")`
2. Sử dụng 3 token nhận được để thực hiện các API call procurement bình thường.

### Rủi ro cần lưu ý
- Nếu Keycloak/Liferay check IP/User-Agent bất nhất giữa lúc chạy headful (Windows) và headless (Windows - cùng máy chủ), có thể làm hỏng token. Do cả hai luồng đều chạy trên cùng một máy Windows Host nên rủi ro này cực kỳ thấp.
- Cloudflare/WAF chặn headless: Nếu headless bị chặn, ta có thể cấu hình Playwright giả lập User-Agent của trình duyệt thật hoặc cấu hình `headless=False` nhưng chạy ở dạng không hiển thị cửa sổ (hidden/minimized).

---