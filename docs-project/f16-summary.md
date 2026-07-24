# F16 — Attachment Download: Implementation Summary

## Phát hiện từ exploration

### Trang chi tiết VB
- Click `lbSoDen` (số đến link) trong grid → navigate đến detail page
- URL: `Default.aspx?tabid=1126&ctl=VBDen_ThemMoi&mid=5725&ID=<base64>&parameters=<base64>`
- Grid file: `grdTepDinhKem` (RadGrid)
- Mỗi VB có thể có 0-4 file đính kèm

### Cấu trúc grdTepDinhKem (10 cột)
| Index | Ẩn/hiện | Nội dung |
|-------|----------|----------|
| td[0] | visible | Checkbox chọn |
| td[1] | hidden  | **FileID** (số nguyên, VD: 111738417) |
| td[2] | hidden  | ? (44152) |
| td[3] | hidden  | UnitID (2256) |
| td[4] | visible | **Tên file** (VD: 1444.KH_2026.pdf) |
| td[5] | hidden  | Phiên bản (1) |
| td[6] | hidden  | Xác thực chữ ký |
| td[7] | visible | Ký sao y (image button) |
| td[8] | visible | **Tải** — `input type="image" title="Tải file"` |
| td[9] | visible | Xóa (image button) |

### Download mechanism
- Button: `input[type="image"][title="Tải file"]` — ASP.NET postback button
- **Chỉ file đầu tiên trong 1 page load mới download được** — các file sau cần reload page
- Cần `page.expect_download()` để bắt sự kiện download
- Filename từ `download.suggested_filename`

### Login flow (giữ nguyên)
- urllib GET `/SSO/Login.aspx` → POST form fields + IDToken1/IDToken2
- Handle password warning page (TIẾP TỤC)
- Pass cookies to Playwright context
- Unit selection via tabid=56 → select `ddlChonDonVi`

## Kiến trúc tích hợp

### Option A: Inline vào congchuc_scrape.py (ưu tiên)
- Thêm function `download_attachments(page, doc_data)` gọi sau khi scrape xong
- Với mỗi VB mới, navigate detail page → download files → save to `attachments/<so_den>/`
- Update state với thông tin attachment

### Option B: Script riêng (cho cron)
- `congchuc_attachment.py` — chạy sau scrape, xử lý attachments cho VB chưa download
- Reuse login/unit selection từ congchuc_scrape.py

### State file changes (vbden_state.json)
```json
"so_den_1234": {
  ...,  // existing fields
  "attachments": [
    {
      "filename": "file.pdf",
      "size": 958531,
      "downloaded_at": "2026-06-19T10:30:00",
      "path": "attachments/1234/file.pdf"
    }
  ]
}
```

### Directory structure
```
~/.hermes/cron/cong-van-den/
├── vbden_state.json
└── attachments/
    └── 1234/
        ├── file1.pdf
        └── file2.docx
```
