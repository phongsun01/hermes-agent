# Hướng Dẫn Kỹ Thuật: Token & Cookie Hệ Thống Mua Sắm Công (MSC)

Tài liệu này ghi chép chi tiết về cơ chế xác thực, cách trích xuất token/cookie, cấu hình biến môi trường và nguyên lý hoạt động của API Mua Sắm Công trong hệ thống.

---

## 📌 1. Tổng quan về Token & Cookie trên MSC

Hệ thống Mua Sắm Công Quốc gia hoạt động tại cổng chính thức:
👉 **`https://muasamcong.mof.gov.vn`** *(Bộ Tài chính quản lý, chuyển đổi từ domain cũ `muasamcong.mpi.gov.vn`)*.

Hệ thống bảo vệ các API tra cứu dữ liệu (KHLCNT, TBMT, kết quả mở thầu, thông tin giá dự thầu) bằng 2 lớp bảo mật:

| Thành phần | Tên tham số / Header | Bản chất & Vai trò | Thời gian sống |
|---|---|---|---|
| **Token** | Query string `?token=...` | **reCAPTCHA Enterprise / Session Token** được trình duyệt client sinh ra sau khi hoàn thành challenge hoặc đánh giá điểm số bot ngầm. Bắt buộc cho hầu hết endpoint tra cứu smart search và chi tiết gói thầu. | Khoảng **30 phút – 2 giờ** (hết hạn sẽ bị WAF chặn hoặc trả về mã guard). |
| **Cookie** | Header `Cookie: ...` | **Session Cookie** do máy chủ MSC cấp (`JSESSIONID`, `COOKIE_SUPPORT`, `GUEST_LANGUAGE_ID`, v.v.). Dùng để duy trì session của cổng Liferay/WAF, bắt buộc đối với API giá dự thầu, tải biên bản mở thầu, hoặc tải file đính kèm. | Thường duy trì theo phiên trình duyệt (vài giờ đến 1 ngày). |

---

## 🔍 2. Cách Lấy Token & Cookie từ Trình Duyệt

### Cách 1: Sử dụng DevTools Network (Khuyến nghị cho mọi người dùng)

1. Mở trình duyệt (Chrome, Edge, Brave...) truy cập vào: [https://muasamcong.mof.gov.vn](https://muasamcong.mof.gov.vn).
2. Nhấn phím **`F12`** (hoặc chuột phải chọn **Inspect / Kiểm tra**) ➔ chọn tab **Network** (Mạng).
3. Trong ô tìm kiếm / filter của tab Network, gõ: `search`.
4. Trên giao diện trang web Mua Sắm Công:
   - Vào mục **Tìm kiếm thông báo mời thầu** hoặc **Kế hoạch lựa chọn nhà thầu**.
   - Bấm nút **Tìm kiếm** (hoặc nhập từ khóa bất kỳ).
5. Trong danh sách request ở tab Network, tìm request gửi tới:
   ```text
   /services/smart/search?token=03AFcWeA...
   ```
6. Nhấp vào request đó để lấy thông tin:
   - **Lấy Token:** Nhìn vào dòng URL đầu tiên hoặc tab **Payload** ➔ copy toàn bộ chuỗi ký tự sau `token=` (bắt đầu bằng `03A...`).
   - **Lấy Cookie:** Chọn tab **Headers** ➔ cuộn xuống mục **Request Headers** ➔ tìm dòng `Cookie:` ➔ copy toàn bộ giá trị (dạng `JSESSIONID=...; COOKIE_SUPPORT=true`).

---

### Cách 2: Bắt tự động bằng Console Script (Tiện lợi & Nhanh chóng)

1. Mở trang [https://muasamcong.mof.gov.vn](https://muasamcong.mof.gov.vn).
2. Nhấn **`F12`** ➔ chọn tab **Console**.
3. Dán đoạn mã sau vào Console rồi nhấn **Enter**:

```javascript
(function() {
  const origFetch = window.fetch;
  window.fetch = async function(...args) {
    const url = args[0] || '';
    if (typeof url === 'string' && url.includes('token=')) {
      const match = url.match(/[?&]token=([^&]+)/);
      if (match) {
        const token = match[1];
        console.log("%c[MSC TOKEN THÀNH CÔNG]:", "color: #00ff00; font-weight: bold; font-size: 14px;");
        console.log(token);
        navigator.clipboard.writeText(token).then(() => {
          console.log("%c--> Đã tự động copy Token vào Clipboard!", "color: #00bcff;");
        });
      }
    }
    return origFetch.apply(this, args);
  };
  console.log("--> Hook sẵn sàng. Hãy bấm Tìm kiếm trên web để tự động lấy token!");
})();
```

4. Bấm nút **Tìm kiếm** trên web. Token sẽ tự động xuất hiện và được copy thẳng vào bộ nhớ tạm (Clipboard) của bạn.

---

## ⚙️ 3. Cấu Hình Biến Môi Trường

Skill MSC hỗ trợ nạp cấu hình tự động từ môi trường hệ điều hành hoặc file `.env`.

### 3.1 Thứ tự ưu tiên nạp biến
Hệ thống ưu tiên tên biến theo chuẩn mới nhất:

* **Token:**
  1. `MSC_SESSION_TOKEN` *(Chuẩn chính thức)*
  2. `MSC_TOKEN`
  3. `BOT2_MSC_TOKEN`
  4. `MUASAMCONG_TOKEN`

* **Cookie:**
  1. `MSC_COOKIE` *(Chuẩn chính thức)*
  2. `BOT2_MSC_COOKIE`
  3. `MUASAMCONG_COOKIE`

### 3.2 Vị trí file cấu hình `.env`
Router tự động quét tìm file `.env` theo thứ tự các thư mục:
1. `D:\Antigravity\Skill\msc\.env` (hoặc trong thư mục skill `skills/productivity/msc/.env`)
2. `D:\Antigravity\Skill\.env`
3. `~/.hermes/.env` (hoặc `C:\Users\<User>\.hermes\.env`)

**Cú pháp trong file `.env`:**
```env
MSC_SESSION_TOKEN=03AFcWeA...
MSC_COOKIE=JSESSIONID=...; COOKIE_SUPPORT=true; GUEST_LANGUAGE_ID=vi_VN
```

---

## 🛡️ 4. Cơ Chế Bảo Mật & Truyền Dữ Liệu Trong Mã Nguồn

1. **Không truyền qua CLI Flag (Chống rò rỉ tiến trình):**
   - Toàn bộ các script con (`msc_pl_lookup.py`, `msc_ib_lookup.py`, `msc_tbmt_detail.py`, `msc_khlcnt_detail.py`, `msc_exp_unified.py`, v.v.) **không nhận token/cookie qua cờ dòng lệnh `--token` hoặc `--cookie`**.
   - Secret chỉ được đọc thông qua `os.environ` của tiến trình con. Khi router hoặc script cha gọi script con, secret được truyền qua tham số `env=...` của `subprocess.run()`, giúp bảng tiến trình của hệ điều hành (`ps aux`, `Process Explorer`, `/proc/<pid>/cmdline`) hoàn toàn sạch và không bị lộ credential.

2. **Domain chính thức & WAF:**
   - Tất cả request gọi tới `https://muasamcong.mof.gov.vn`.
   - Header `Origin` và `Referer` được thiết lập đúng domain `mof.gov.vn` để tránh bị WAF từ chối hoặc chặn phiên.

---

## 🧪 5. Kiểm Tra Trạng Thái Token

Sau khi cấu hình token, có thể kiểm tra xem token còn hoạt động hay không bằng lệnh:

```bash
# Chạy từ repo
python skills/productivity/msc/lib/msc_mvp_router.py "msc status"

# Hoặc chạy từ thư mục trích xuất độc lập
python D:\Antigravity\Skill\msc\lib\msc_mvp_router.py "msc status"
```

**Kết quả mẫu khi thành công:**
```json
{
  "status": "ok",
  "command": "msc_status",
  "result": {
    "token_present": true,
    "cookie_present": true,
    "login_ok": true,
    "probe": "tbmt_today_count",
    "total": 450
  }
}
```

* Nếu `login_ok: false` hoặc trả về mã lỗi `guard`: Token đã hết hạn, cần thực hiện lại bước ở **Mục 2** để lấy token mới.
