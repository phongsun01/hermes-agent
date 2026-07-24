# Hướng dẫn Đăng ký Slash Command cho Hermes Gateway (Zalo & Telegram)

Tài liệu này hướng dẫn chi tiết cách tạo, cấu hình và phân quyền một Slash Command tùy chỉnh trong hệ thống Hermes Agent.

---

## 🛠️ Quy trình triển khai

### Bước 1: Đăng ký Command trong Registry trung tâm

Mọi Slash Command trong Hermes phải được khai báo tập trung tại file:
[hermes_cli/commands.py](file:///d:/Antigravity/Hermes/hermes_cli/commands.py)

Thêm một phần tử `CommandDef` vào danh sách `COMMAND_REGISTRY`. 

**Ví dụ khai báo lệnh `/cronmenu`:**
```python
    CommandDef("cronmenu", "Hiển thị danh sách các tác vụ cron đang chạy", "Tools & Skills",
               gateway_only=True, args_hint="[list|subcommand]",
               subcommands=("list",)),
```

*Các tham số chính:*
- `name`: Tên lệnh (không bao gồm ký tự `/`).
- `description`: Mô tả hiển thị cho người dùng.
- `category`: Nhóm lệnh (ví dụ: `"Tools & Skills"`, `"Session"`, `"Info"`).
- `gateway_only`: Set `True` nếu lệnh chỉ khả dụng qua các bot chat (Telegram, Zalo...) mà không hiển thị ở terminal CLI.
- `args_hint`: Hướng dẫn đối số hiển thị khi gõ lệnh.
- `subcommands`: Bộ các lệnh con để hỗ trợ tự động hoàn thành (autocomplete).

---

### Bước 2: Triển khai Logic xử lý lệnh trên Gateway

Gateway điều phối và xử lý tin nhắn từ Zalo/Telegram tại file:
[gateway/run.py](file:///d:/Antigravity/Hermes/gateway/run.py)

Tìm đến hàm dispatch lệnh chính và chèn block xử lý dựa trên giá trị `canonical` (tên lệnh sau khi đã phân giải alias).

**Ví dụ triển khai `/cronmenu list`:**
```python
        if canonical == "cronmenu":
            sub_arg = event.get_command_args().strip().lower()
            
            if sub_arg == "list" or not sub_arg:
                try:
                    from cron.jobs import load_jobs
                    jobs = load_jobs()
                    
                    if not jobs:
                        return "Hiện tại không có cron job nào đang hoạt động."
                        
                    lines = ["⏰ **Danh sách các cron job:**"]
                    for job in jobs:
                        state = job.get("state", "unknown")
                        schedule = job.get("schedule_display", "?")
                        name = job.get("name", "Unnamed Job")
                        lines.append(f"• **{name}**: `{schedule}` (Trạng thái: `{state}`)")
                    return "\n".join(lines)
                except Exception as e:
                    logger.error(f"Lỗi khi lấy danh sách cron: {e}", exc_info=True)
                    return f"⚠️ Có lỗi xảy ra khi lấy danh sách cron: {e}"
            else:
                return "Cú pháp không hợp lệ. Sử dụng: `/cronmenu list`"
```

---

### Bước 3: Phân quyền Admin-only (Chỉ Admin mới được dùng)

Hermes hỗ trợ phân quyền kiểm soát truy cập slash command thông qua file cấu hình người dùng `~/.hermes/config.yaml`.

#### 1. Cấu hình Admin trong `config.yaml`
Để giới hạn lệnh chỉ dành cho bạn (Admin), hãy chỉnh sửa tệp tin cấu hình và khai báo `allow_admin_from` (chứa User ID của bạn trên Telegram hoặc Zalo):

```yaml
platforms:
  telegram:
    enabled: true
    extra:
      # Danh sách User ID của Admin được quyền chạy mọi lệnh
      allow_admin_from: ["YOUR_TELEGRAM_USER_ID"]
      # Các lệnh mà người dùng thông thường ĐƯỢC PHÉP dùng (nếu không có trong đây, mặc định bị chặn)
      user_allowed_commands: ["help", "whoami", "status"]
      
  zalo:
    enabled: true
    extra:
      allow_admin_from: ["YOUR_ZALO_USER_ID"]
      user_allowed_commands: ["help", "whoami", "status"]
```

> [!IMPORTANT]
> - Nếu `allow_admin_from` **không** được cấu hình, hệ thống sẽ chạy ở chế độ tương thích ngược (mọi người dùng đều có quyền chạy tất cả các lệnh).
> - Khi bạn đã khai báo ít nhất 1 Admin trong `allow_admin_from`, hệ thống phân quyền sẽ kích hoạt. Mọi user không nằm trong list admin sẽ bị chặn không cho chạy lệnh `/cronmenu` và nhận được thông báo: `⛔ /cronmenu is admin-only here.`

#### 2. Lấy User ID của bạn
Gõ lệnh `/whoami` trên bot Telegram hoặc Zalo của bạn. Bot sẽ trả về thông tin User ID hiện tại của bạn:
```
**You** — telegram (DM)
User ID: `123456789`
Tier: unrestricted
```
Hãy copy ID này và điền vào trường `allow_admin_from` tương ứng.
