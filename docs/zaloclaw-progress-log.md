# Nhật Ký Tiến Độ Tích Hợp Zalo vào Hermes Agent

Tài liệu này theo dõi chi tiết các công việc đã thực hiện và kế hoạch tiếp theo cho việc tích hợp Zalo, bám sát theo roadmap trong `zalo-hermes-integration-plan.md`.

## 📈 Trạng Thái Tổng Quát
- **Tiến độ:** ~85% (Phase 1-4 cơ bản đã xong)
- **Trạng thái:** Đã build thành công Worker và đăng ký Adapter vào lõi Hermes. Sẵn sàng cho việc quét mã QR và test thực tế.

---

## 🛠 Checklist Chi Tiết

### Phase 1: Minimal Worker + Adapter (Hoàn thành: 100%)
- [x] Thiết lập cấu trúc dự án Node.js Worker (`gateway/platforms/zalo/worker`)
- [x] Triển khai giao thức IPC cơ bản (JSON-RPC qua stdio)
- [x] Tích hợp luồng đăng nhập `zca-js` (QR Callback)
- [x] Triển khai gửi tin nhắn văn bản và nhận sự kiện tin nhắn
- [x] Viết Python Adapter xử lý quản lý subprocess
- [x] Xử lý lỗi cơ bản và ghi log

### Phase 2: Rich Messages & Media (Hoàn thành: 90%)
- [x] Worker: Triển khai các handler cho media (hình ảnh, file)
- [x] Worker: Tự động tải media từ URL trước khi gửi (để Zalo hiển thị đúng)
- [x] Adapter Python: Tích hợp gửi ảnh và file qua subprocess
- [ ] Định dạng tin nhắn: Chuyển đổi Markdown sang Zalo Styled Text (Đang dùng text thuần)
- [x] Xử lý giới hạn độ dài tin nhắn (thông qua zca-js)

### Phase 3: Session & Auth (Hoàn thành: 100%)
- [x] Luồng đăng nhập mã QR: Hiển thị URL trong terminal
- [x] UX mã QR: Tự động lưu mã QR vào `~/.hermes/data/zalo_qr.png`
- [x] Lưu trữ session: Tự động lưu/tải cookie vào `~/.hermes/data/zalo_session.json`
- [x] Cơ chế tự động kết nối lại khi restart gateway

### Phase 4: Access Control & Groups (Hoàn thành: 80%)
- [x] Tích hợp với hệ thống allowlist/denylist của Hermes (`ZALO_ALLOWED_USERS`)
- [x] Nhận diện tin nhắn nhóm và cá nhân
- [x] Triển khai các action cơ bản cho nhóm (Lấy thông tin nhóm, danh sách bạn bè)
- [ ] Chế độ chỉ phản hồi khi được mention trong nhóm (`requireMention`)

### Phase 5: Advanced Features & Finalization (Tiếp theo)
- [ ] Hỗ trợ tool `send_message` đa nền tảng
- [ ] Tích hợp gửi tin nhắn định kỳ (Cron)
- [ ] Cơ chế Rate limiting để tránh bị Zalo khóa tài khoản
- [ ] Hoàn thiện các hành động nâng cao từ zaloclaw (147 actions)
- [ ] Tài liệu hướng dẫn sử dụng cho người dùng cuối

---

## 📝 Nhật Ký Chi Tiết (Timeline)

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
