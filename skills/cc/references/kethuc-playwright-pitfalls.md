# Kethuc Playwright Pitfalls

## 1. `HERMES_HOME=/tmp` → Login thất bại

**Vấn đề**: Script `congchuc_action.py` đọc `.env` từ `HERMES_HOME/.env`.
Nếu set `HERMES_HOME=/tmp`, nó tìm `/tmp/.env` — file không tồn tại → không có
CONGVAN_USER/CONGVAN_PASS → login thất bại.

**Fix**: KHÔNG ghi đè HERMES_HOME. Giá trị hiện tại là `/opt/data`
(từ biến môi trường, mặc định `HERMES_HOME=/opt/data`). File `.env` thực tế ở `/opt/data/.env`.

```bash
# ĐÚNG — không ghi đè HERMES_HOME
uv run python /opt/data/skills/cc/scripts/congchuc_action.py kethuc <số>

# SAI — /tmp/.env không tồn tại
HERMES_HOME=/tmp uv run python /opt/data/skills/cc/scripts/congchuc_action.py kethuc <số>
```

**Kiểm tra**: In thử `echo $HERMES_HOME` và `ls -la $HERMES_HOME/.env` để xác nhận.

## 1b. Password warning page không nhận diện được

**Vấn đề**: Sau login thành công, hệ thống hiển thị trang cảnh báo mật khẩu yếu
với nút "Tiếp tục" (`id=btnContinue`). Trang này vẫn ở URL `Login.aspx`
(không chứa "CanhBaoMatKhau" như script cũ kiểm tra).
Script cũ: `if "CanhBaoMatKhau" in page.url or "PasswordWarning" in page.url`
→ không match → rơi vào `if "Login.aspx" in page.url` → báo sai "login thất bại".

**Fix**: Script hiện tại đã được patch thêm check `page.query_selector("#btnContinue")`
song song với check URL, và sửa logic check login thành:
`still_on_login = "Login.aspx" in page.url and page.query_selector("#IDToken1") is not None`
(cả URL + form cùng xuất hiện mới là login thất bại thật).

## 2. Chạy song song → EPIPE / timeout / login failure

**Vấn đề**: Nhiều tiến trình `kethuc` cùng lúc tranh giành Playwright storage state
(cùng file `.playwright_storage.json`). Kết quả:
- `Error: write EPIPE` — Chromium pipe bị ngắt
- `Page.goto: Timeout 30000ms exceeded` — navigation treo
- Login fail hàng loạt vì storage state bị corrupt

**Fix**: Luôn chạy tuần tự, từng VB một. Dùng loop:

```bash
for vb in 2941 2933 2932; do
    uv run python /opt/data/skills/cc/scripts/congchuc_action.py kethuc $vb
done
```

## 3. Timeout 60s chưa đủ

**Vấn đề**: Skill cũ ghi "mất 10-15s" nhưng Chromium launch + navigation
+ grid scan (nhiều trang) có thể mất 30-60s, nhất là lần đầu fresh login.

**Fix**: Dùng timeout ≥ 120s cho terminal tool khi gọi kethuc.

## 4. "Không tìm thấy văn bản trên grid"

**Vấn đề**: Script báo không tìm thấy VB trên grid. Thường do VB đã được
xử lý trước đó (kethuc tay) hoặc nằm ở trang/danh sách khác.

**Xử lý**: Coi như đã xong. Vẫn chạy `congvan_status.py done <số_vb>`
để đồng bộ state.
