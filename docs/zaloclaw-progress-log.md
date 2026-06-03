# Nhật Ký Tiến Độ Tích Hợp Zalo vào Hermes Agent

Tài liệu này theo dõi chi tiết các công việc đã thực hiện và kế hoạch tiếp theo cho việc tích hợp Zalo, bám sát theo roadmap trong `zalo-hermes-integration-plan.md`.

## 📈 Trạng Thái Tổng Quát
- **Tiến độ:** ~98% (Phase 1-5 hoàn thành, 142/147 actions hoạt động)
- **Trạng thái:** Gateway đang chạy ổn định, Zalo worker kết nối thành công, access control hoạt động, rate limiting, supervision, send_message tool, platform hints đã triển khai.

---

## 🛠 Checklist Chi Tiết

### Phase 1: Minimal Worker + Adapter (Hoàn thành: 100%)
- [x] Thiết lập cấu trúc dự án Node.js Worker (`gateway/platforms/zalo/worker`)
- [x] Triển khai giao thức IPC cơ bản (JSON-RPC qua stdio)
- [x] Tích hợp luồng đăng nhập `zca-js` (QR Callback)
- [x] Triển khai gửi tin nhắn văn bản và nhận sự kiện tin nhắn
- [x] Viết Python Adapter xử lý quản lý subprocess
- [x] Xử lý lỗi cơ bản và ghi log

### Phase 2: Rich Messages & Media (Hoàn thành: 100%)
- [x] Worker: Triển khai các handler cho media (hình ảnh, file, video)
- [x] Worker: Tự động tải media từ URL trước khi gửi (để Zalo hiển thị đúng)
- [x] Adapter Python: Tích hợp gửi ảnh và file qua subprocess
- [x] Định dạng tin nhắn: Chuyển đổi Markdown sang Zalo Styled Text (`formatMarkdownToZalo`)
- [x] Xử lý giới hạn độ dài tin nhắn (auto-truncate > 2000 ký tự)
- [x] Received media detection và caching (TTL 1 giờ)
- [x] `send-typing` trigger trước khi agent phản hồi
- [x] Auto-echo image URLs từ tin nhắn người dùng

### Phase 3: Session & Auth (Hoàn thành: 100%)
- [x] Luồng đăng nhập mã QR: Hiển thị URL trong terminal
- [x] UX mã QR: Tự động lưu mã QR vào `~/.hermes/data/zalo_qr.png`
- [x] Lưu trữ session: Tự động lưu/tải cookie vào `~/.hermes/data/zalo_session.json`
- [x] Cơ chế tự động kết nối lại khi restart gateway

### Phase 4: Access Control & Groups (Hoàn thành: 100%)
- [x] Tích hợp với hệ thống allowlist/denylist của Hermes (`ZALO_ALLOWED_USERS`)
- [x] Nhận diện tin nhắn nhóm và cá nhân
- [x] Triển khai các action cơ bản cho nhóm (Lấy thông tin nhóm, danh sách bạn bè)
- [x] Chế độ chỉ phản hồi khi được mention trong nhóm (`require_mention: true`)
- [x] DM policy (allowlist), Group policy (closed), mention detection
- [x] User/group info caching với TTL

### Phase 5: Advanced Features (Hoàn thành: 100%)
- [x] Hỗ trợ tool `send_message` đa nền tảng (`tools/send_message_tool.py`)
  - [x] Thêm `_send_zalo()` function cho media + text
  - [x] Thêm Zalo branch vào `_send_to_platform()` dispatch
- [x] Tích hợp gửi tin nhắn định kỳ (Cron) — hoạt động qua `send_message` tool
- [x] Cơ chế Rate limiting để tránh bị Zalo khóa tài khoản
  - [x] `RateLimiter` class trong `actions.ts` (1 msg/sec, exponential backoff)
  - [x] Config qua env vars: `ZALO_RATE_INTERVAL_MS`, `ZALO_RATE_MAX_BACKOFF_MS`
  - [x] IPC method `get_rate_limiter_status` để monitor
- [x] Worker supervision & auto-restart
  - [x] `_supervise_worker()` task trong Python adapter
  - [x] Exponential backoff: 5s → 10s → 20s → ... → 300s cap
  - [x] Max 10 restarts trước khi dừng auto-restart
- [x] Platform hints trong system prompt (`agent/prompt_builder.py`)
  - [x] Thêm "zalo" vào `PLATFORM_HINTS` dict
- [x] Structured logging & error recovery
  - [x] Metrics tracking: messages sent/received, errors, restarts, uptime
  - [x] `get_metrics()` method cho monitoring
  - [x] Error counting trong send/receive paths
- [x] Test và xác minh 5 actions còn lại còn thiếu

---

## 📝 Nhật Ký Chi Tiết (Timeline)

### 2026-06-03
- **Phase 5 hoàn thành:**
  - Thêm Zalo vào `send_message_tool.py` — agent có thể chủ động gửi tin qua Zalo từ bất kỳ platform nào
  - Thêm Zalo platform hint vào system prompt — agent hiểu capability của Zalo (markdown, media, MEDIA: syntax)
  - Implement `RateLimiter` class trong worker — 1 msg/sec với exponential backoff khi gặp lỗi liên tiếp
  - Thêm worker supervision task — auto-restart với backoff, max 10 lần restart
  - Thêm metrics tracking — messages sent/received, errors, restarts, uptime
  - Cron delivery hoạt động tự động qua `send_message` tool

### 2026-05-08
- **Sáng:** Khởi tạo cấu trúc dự án. Tạo `index.ts`, `client.ts`, `ipc.ts` và `actions.ts` cho Node.js Worker.
- **Trưa:** Viết `ZaloAdapter` trong Python để bridge qua subprocess. Đăng ký nền tảng `ZALO` trong `gateway/config.py` và `gateway/run.py`.
- **Chiều:** Mở rộng `actions.ts` với các hành động từ `zaloclaw`. Sửa lỗi tên hàm trong `zca-js` (`getSelfInfo` -> `getUserInfo`).
- **Hiện tại:** Đã build thành công Worker và sẵn sàng chạy thực tế.

---

## 🚀 Các Bước Tiếp Theo (Next Action)
1. **Test Quét Mã QR:** Người dùng cần chạy gateway và quét mã QR được lưu tại thư mục data.
2. **Kiểm tra Phản hồi:** Test gửi/nhận tin nhắn thực tế để tinh chỉnh adapter.
3. **Markdown Support:** Thêm logic chuyển đổi Markdown sang Zalo Style để tin nhắn trông đẹp hơn.
