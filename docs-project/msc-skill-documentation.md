# Hướng dẫn sử dụng & Tài liệu kỹ thuật Skill Mua Sắm Công (MSC)

Tài liệu này ghi lại các chức năng, hướng dẫn sử dụng, cấu hình và danh sách các file liên quan đến Skill **Mua Sắm Công (MSC) - Thông tin Đấu thầu Việt Nam** trong hệ thống Hermes Agent.

---

## 🏛️ 1. Giới thiệu chức năng

Hệ thống MSC cho phép Hermes kết nối và tra cứu dữ liệu từ Hệ thống mạng đấu thầu quốc gia Việt Nam (Mua Sắm Công - muasamcong.mpi.gov.vn):
- **Tra cứu Thông báo mời thầu (TBMT)**: Tìm kiếm các thông báo mời thầu mới nhất theo từ khóa hoặc tên đơn vị.
- **Tra cứu Kế hoạch lựa chọn nhà thầu (KHLCNT)**: Tra cứu danh sách kế hoạch lựa chọn nhà thầu của các đơn vị.
- **Watchlist (Theo dõi đơn vị)**: Đăng ký danh sách các đơn vị cần theo dõi (tối đa 30 đơn vị) để tự động giám sát các thông báo thầu mới.
- **Báo cáo định kỳ (Cron)**: Tích hợp gửi báo cáo tự động hàng ngày lúc 18:00 về các thông tin thầu mới nhất từ watchlist lên Telegram.
- **Giao diện Menu trực quan**: Hỗ trợ giao diện Menu tương tác thông qua các Inline Button trên Telegram (`/mscmenu`) giúp người dùng điều hướng nhanh chóng mà không cần nhớ cú pháp lệnh.
- **Export báo cáo**: Hỗ trợ trích xuất báo cáo chi tiết về thông báo mời thầu (TBMT) hoặc kế hoạch lựa chọn nhà thầu (KHLCNT) ra định dạng Markdown lưu trữ cục bộ.

---

## 🛠️ 2. Các file liên quan trong Source Code

Hệ thống được phát triển dưới dạng một Skill độc lập nằm trong thư mục:
`skills/productivity/msc/`

Các file cốt lõi bao gồm:

1. **Tài liệu hướng dẫn cho AI**:
   - [skills/productivity/msc/SKILL.md](file:///d:/Antigravity/Hermes/skills/productivity/msc/SKILL.md): Định nghĩa metadata của skill (version, prerequisites, author), mô tả hành vi của AI và các slash command được hỗ trợ.
2. **Bộ điều phối & Xử lý lệnh (Router & Dispatcher)**:
   - [skills/productivity/msc/lib/msc_mvp_router.py](file:///d:/Antigravity/Hermes/skills/productivity/msc/lib/msc_mvp_router.py): Entrypoint chính nhận lệnh từ Agent hoặc Gateway, thực hiện phân tích cú pháp và điều hướng.
   - [skills/productivity/msc/lib/msc_tool/router.py](file:///d:/Antigravity/Hermes/skills/productivity/msc/lib/msc_tool/router.py): Phân tích ý định người dùng (Intent) từ câu lệnh tự nhiên (ví dụ: `tbmt`, `kh`, `fl`, `exp`).
   - [skills/productivity/msc/lib/msc_tool/dispatcher.py](file:///d:/Antigravity/Hermes/skills/productivity/msc/lib/msc_tool/dispatcher.py): Điều phối thực thi script Python tương ứng tùy theo Intent.
   - [skills/productivity/msc/lib/msc_tool/renderer.py](file:///d:/Antigravity/Hermes/skills/productivity/msc/lib/msc_tool/renderer.py): Định dạng dữ liệu thô nhận được từ API thành văn bản Markdown thân thiện với người dùng.
   - [skills/productivity/msc/lib/msc_tool/schema.py](file:///d:/Antigravity/Hermes/skills/productivity/msc/lib/msc_tool/schema.py): Định nghĩa cấu trúc dữ liệu JSON Schema chuẩn hóa cho các phản hồi.
3. **Các Script Crawl & Tương tác API**:
   - `skills/productivity/msc/scripts/msc_tbmt_precise.py`: Tra cứu thông báo mời thầu.
   - `skills/productivity/msc/scripts/msc_kh_precise.py`: Tra cứu kế hoạch lựa chọn nhà thầu.
   - `skills/productivity/msc/scripts/msc_ib_lookup.py`: Tra cứu chi tiết một TBMT cụ thể qua mã số thầu (IB...).
   - `skills/productivity/msc/scripts/msc_pl_lookup.py`: Tra cứu chi tiết một KHLCNT cụ thể qua mã kế hoạch (PL...).
4. **Hệ thống Watchlist & Cơ sở dữ liệu**:
   - `skills/productivity/msc/scripts/watchlist/msc_watchlist_publish_telegram.py`: Script quét và gửi cập nhật thông tin thầu từ danh sách theo dõi lên Telegram.
   - [skills/productivity/msc/data/msc.sqlite3](file:///d:/Antigravity/Hermes/skills/productivity/msc/data/msc.sqlite3): Cơ sở dữ liệu SQLite lưu giữ danh sách đơn vị theo dõi (watchlist) và lịch sử gửi tin.
5. **Giao diện Menu & Tích hợp Telegram**:
   - [skills/productivity/msc/lib/inline_menu_payload.py](file:///d:/Antigravity/Hermes/skills/productivity/msc/lib/inline_menu_payload.py): Khai báo cấu trúc các menu phân tầng và callback token của nút bấm.
   - Tích hợp trực tiếp tại `gateway/platforms/telegram.py` để xử lý command `/mscmenu` và các callback `v1|msc|...`.
6. **Tài liệu Triển khai**:
   - [docs/migrate/MSC_SKILL_PORTABLE_DEPLOYMENT.md](file:///d:/Antigravity/Hermes/docs/migrate/MSC_SKILL_PORTABLE_DEPLOYMENT.md): Hướng dẫn chi tiết cách đóng gói, di chuyển và cài đặt skill này sang một máy chủ Hermes độc lập khác.

---

## ⚙️ 3. Cấu hình & Sử dụng

### Cấu hình Token Mua Sắm Công (Tự động)
Do Hệ thống mạng đấu thầu quốc gia sử dụng token xác thực động và IP blocking gắt gao, hệ thống hiện tại sử dụng kiến trúc **FastAPI Token Service** chạy trực tiếp trên máy host Windows để tự động lấy token thay vì copy thủ công.

**Cách thiết lập:**
1. Đăng nhập vào [muasamcong.mpi.gov.vn](https://muasamcong.mpi.gov.vn) bằng trình duyệt Chrome thông thường (chỉ cần làm 1 lần để lưu profile).
2. Chạy dịch vụ Token Service trên máy host Windows (chạy ngầm, port 8789):
   ```bash
   py -m uvicorn msc_token_service:app --host 0.0.0.0 --port 8789
   ```
3. Các lệnh `/msc` chạy trong Docker (Hermes Agent) sẽ tự động gọi tới `http://host.docker.internal:8789/msc/tokens` để lấy đủ bộ 3 token (`bearer_token`, `jsessionid`, `csrf_token`) cần thiết cho các API gọi thẳng (REST).

### Các câu lệnh tương tác qua chat (Slash Commands)

Dưới đây là danh sách các lệnh bạn có thể nhập trực tiếp khi chat với Hermes:

| Nhóm chức năng | Cú pháp câu lệnh | Ý nghĩa / Tác dụng |
| :--- | :--- | :--- |
| **Hệ thống** | `/msc status` | Kiểm tra trạng thái kết nối Token Service và hiệu lực của token. |
| | `/mscmenu` | Mở menu tương tác trực quan (chỉ khả dụng trên Telegram). |
| **Tra cứu** | `/msc tbmt <số lượng> <tên đơn vị hoặc mã số thầu>` | Tra cứu thông báo mời thầu mới nhất (Ví dụ: `msc tbmt 5 bệnh viện bạch mai`). |
| | `/msc kh <số lượng> <tên đơn vị hoặc mã kế hoạch>` | Tra cứu kế hoạch lựa chọn nhà thầu mới nhất. |
| **Nhà thầu** | `/msc ls <mã tổ chức>` | Phân tích nhà thầu và lịch sử tham dự thầu của nhà thầu. |
| **Watchlist** | `/msc fl list` | Hiển thị danh sách 30 đơn vị đang được theo dõi. |
| | `/msc fl add <tên đơn vị hoặc mã>` | Thêm một đơn vị vào danh sách theo dõi. |
| | `/msc fl remove <mã đơn vị>` | Xóa đơn vị khỏi danh sách theo dõi. |
| | `/msc fl latest [n]` | Xem nhanh `n` thông báo mời thầu mới nhất từ các đơn vị trong watchlist. |
| **Xuất báo cáo** | `/msc exp <Mã PL... hoặc Mã IB...>` | Xuất báo cáo chi tiết của TBMT/KHLCNT ra file Markdown cục bộ. |

---

## 🛠️ 4. Hướng dẫn Tích hợp Cổng Telegram (Telegram Gateway Integration)

Để menu tương tác `/mscmenu` và các nút bấm hoạt động mượt mà trên Telegram, tệp tin `gateway/platforms/telegram.py` được tích hợp hai đoạn xử lý sau:

1. **Xử lý lệnh `/mscmenu`:**
   Khi nhận tin nhắn bắt đầu bằng `/mscmenu`, gateway sẽ gọi trực tiếp router với đối số `/menu` để nhận cấu trúc nút bấm và trả về cho Telegram client dưới dạng inline keyboard.
2. **Xử lý Callback Query (`v1|msc|...`):**
   Khi người dùng click vào các nút bấm, Telegram gửi về callback query data có prefix `v1|msc|`. Gateway sẽ đánh chặn callback này, chạy router MSC cục bộ, sau đó chỉnh sửa (edit) nội dung tin nhắn hiện tại kèm theo menu con tiếp theo. Việc này giúp ẩn hoàn toàn các chuỗi lệnh thô kỹ thuật khỏi người dùng.

---

## 📈 5. Quản lý Tác vụ Định kỳ (Watchlist Cron Job)

Hệ thống cung cấp một script gửi tin định kỳ hàng ngày lúc **18:00** để thông báo toàn bộ thông tin đấu thầu mới phát sinh của 30 đơn vị trọng điểm về nhóm Telegram:

### Đăng ký Cron Job thông qua Hermes CLI:
```bash
hermes cron create "0 18 * * *" \
  "MSC watchlist daily report" \
  --command "cd ~/.hermes/skills/productivity/msc && python3 scripts/watchlist/msc_watchlist_publish_telegram.py --n 999 --artifact-ts \$(date +%Y-%m-%d_%H-00) --send"
```

Bạn có thể kiểm tra danh sách cron job đang chạy bằng lệnh:
```bash
hermes cron list | grep -i msc
```
