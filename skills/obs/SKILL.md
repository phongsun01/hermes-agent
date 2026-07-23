---
name: obs
description: Quản lý ghi chú Obsidian bảo mật và an toàn. Hỗ trợ các lệnh slash /obs search <từ khóa>, /obs view <ghi chú>, /obs append <ghi chú> <nội dung>, /obs write <ghi chú> <nội dung>, và /obs check-expiry.
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [obsidian, obs, note-taking, personal]
    category: productivity
---

# Kỹ năng Quản lý Obsidian (/obs)

Kỹ năng này kết nối an toàn kho dữ liệu Obsidian (Second Brain) cục bộ với Hermes Agent, tích hợp các công cụ tìm kiếm, đọc, ghi đè an toàn, và tự động quét hạn dùng giấy tờ.

LƯU Ý BẢO MẬT: Mọi hoạt động truy xuất tệp tin chỉ được phép hoạt động trong thư mục chỉ định bởi biến môi trường `OBSIDIAN_VAULT_PATH`. Nếu biến này chưa được đặt, hãy tìm kiếm trong thư mục mặc định `~/Documents/Obsidian Vault` hoặc yêu cầu người dùng xác nhận đường dẫn.

## Danh sách Lệnh nhanh (Slash Commands)

| Lệnh | Hành động thực tế |
|---|---|
| `/obs search <từ khóa>` | Tìm kiếm các tệp `.md` chứa từ khóa trong Obsidian Vault sử dụng công cụ tìm kiếm hoặc tập lệnh Python. |
| `/obs view <tên ghi chú>` | Đọc và in ra nội dung tệp tin Markdown được chỉ định. |
| `/obs append <tên ghi chú> <nội dung>` | Thêm nội dung vào dòng cuối của tệp tin ghi chú kèm dấu mốc thời gian. |
| `/obs write <tên ghi chú> <nội dung>` | Ghi đè hoặc tạo mới ghi chú bằng tập lệnh an toàn `safe_write.py` để tránh mất mát dữ liệu. |
| `/obs check-expiry` | Chạy tập lệnh `check_expiry.py` để quét các ghi chú chứa thông tin giấy tờ và báo cáo ngày hết hạn. |

---

## Hướng dẫn Vận hành chi tiết cho Agent

### 1. Phân giải đường dẫn Vault
Trước khi thực hiện bất kỳ lệnh đọc ghi nào, Agent bắt buộc phải lấy đường dẫn tuyệt đối của Obsidian Vault từ biến môi trường `OBSIDIAN_VAULT_PATH`.
* Tuyệt đối không tự bịa ra đường dẫn.
* Nếu không tìm thấy biến môi trường, hãy tìm ở thư mục mặc định của Windows/macOS/Linux hoặc hỏi người dùng.

### 2. Sử dụng lệnh ghi đè an toàn `/obs write`
Để tránh làm mất dữ liệu ghi chú cũ của người dùng do LLM ảo tưởng:
* Không tự viết tệp tin trực tiếp bằng các công cụ shell nếu chưa chắc chắn.
* Thay vào đó, hãy luôn gọi tập lệnh an toàn:
  `python /opt/data/skills/obs/scripts/safe_write.py "<đường_dẫn_tuyệt_đối_file>" "<nội_dung_mới>"`
* Script này sẽ tự động backup tệp cũ và kiểm tra độ toàn vẹn của nội dung mới.

### 3. Quét hạn dùng giấy tờ `/obs check-expiry`
* Chạy lệnh: `python /opt/data/skills/obs/scripts/check_expiry.py "<thư_mục_vault>"`
* Kết quả trả về sẽ liệt kê danh sách các giấy tờ và trạng thái hết hạn của chúng.
* Bạn có thể khuyên người dùng đăng ký lịch chạy tự động hàng tuần hoặc hàng tháng cho tác vụ này thông qua lệnh `/schedule`.

