# Reference: congchuc_scrape.py

## Vị trí
`/opt/data/home/.hermes/scripts/congchuc_scrape.py`

## Chức năng
Script tự động đăng nhập SSO vào congchuc.quangninh.gov.vn, scrape danh sách văn bản đến, so sánh với state cũ để phát hiện văn bản mới.

## Luồng xử lý
1. Login vào `https://congchuc.quangninh.gov.vn/SSO/Login.aspx`
2. POST credentials (có thể gặp trang cảnh báo mật khẩu -> bấm "Tiếp tục")
3. GET `Default.aspx?tabid=1126` (trang văn bản đến)
4. Parse HTML table với class `rgRow` / `rgAltRow` (Telerik RadGrid)
5. So sánh với state file `~/.cron/vbden_state.json`
6. In ra văn bản mới (hoặc silent nếu không có mới)

## Credentials (hardcode)
- USERNAME = "nguyenhuyphong"
- PASSWORD = "comeon12"
- Login tại https://congchuc.quangninh.gov.vn

## State file
- `~/.cron/vbden_state.json` (`/opt/data/home/.cron/vbden_state.json`)
- Format: `{"seen_ids": [...], "last_check": "...", "last_count": N}`
- `seen_ids` = mảng các `so_den` đã xử lý

## HTML parsing
- Dùng regex, không dùng BeautifulSoup (tránh dependency)
- Các trường lấy từ `<td>`:
  - `stt` (index)
  - `so_den` (số đến)
  - `ngay_den` (ngày đến)
  - `ngay_vb` (ngày văn bản)
  - `han_xl` (hạn xử lý)
  - `so_ky_hieu` (số ký hiệu)
  - `tac_gia` (tác giả / cơ quan gửi)
  - `trich_yeu` (trích yếu nội dung)

## Output format
```
📋 CÓ VĂN BẢN MỚI - 2026-06-25 10:00:00
Phát hiện 1 văn bản đến ngày 25/06/2026:

1. Số đến: 123 | Số: 456/QĐ-UBND
   Tác giả: Sở Y tế Quảng Ninh
   Trích yếu: V/v triển khai công tác...
```

Nếu không có văn bản mới: script silent (không in gì, không output).

## Hạn chế
- Không nhận subcommand (luôn chạy full flow login + scrape)
- Không có cơ chế mark done / tracking trạng thái
- Không tải attachments
- Không tạo dự thảo Word
- Không retry logic nếu login fail
- Hardcode credentials (không dùng env var)
- SSL context dùng cipher list cụ thể (có thể fail nếu server thay đổi)
