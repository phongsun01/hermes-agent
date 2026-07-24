# Zalo Bot — Chẩn đoán & Fix lỗi

> Ghi chép lại các lỗi Zalo gateway đã gặp, nguyên nhân gốc và cách khắc phục.
> Cập nhật lần cuối: **06/07/2026**

---

## Sự cố 1: Bot không phản hồi tin nhắn DM (06/07/2026)

### Triệu chứng

- Bot Zalo nhận được tin nhắn (log ghi nhận `inbound message`) và xử lý xong
- Nhưng **không gửi được phản hồi** — log báo liên tục:
  ```
  WARNING [Zalo] Send failed: Nhóm này không tồn tại. — trying plain-text fallback
  ERROR   [Zalo] Fallback send also failed: Nhóm này không tồn tại.
  ```
- Lỗi xảy ra với DM của sếp (`threadId=2825656851207986406`)

### Nguyên nhân gốc

**Bug trong `_thread_type_from_chat_id`** tại `~/.hermes/plugins/zalo/adapter.py`:

Hàm kiểm tra `_allowed_threads` **TRƯỚC** khi kiểm tra cache `_thread_types` từ inbound messages.
Vì `ZALO_ALLOWED_THREADS` chứa cả User ID của sếp (`2825656851207986406`), hàm trả về `"group"` dù đây là DM.
→ Bridge gửi Zalo API với `threadType=group` → Zalo báo `"Nhóm này không tồn tại"`.

### Cách fix

**Fix 1 — Sửa logic code** (`adapter.py` dòng 802–819):

Đổi thứ tự ưu tiên:
1. Cache `_thread_types` (ground truth từ tin nhắn thực tế) được kiểm tra TRƯỚC
2. Heuristic `_allowed_threads` chỉ dùng khi chưa có cache VÀ ID không nằm trong `_allowed_users`

**Fix 2 — Sửa cấu hình `.env`**:

```diff
- ZALO_ALLOWED_THREADS=2825656851207986406,3339712927031818889
+ ZALO_ALLOWED_THREADS=3339712927031818889
```

---

## Sự cố 2: Xung đột profile `family` (03/07/2026)

### Triệu chứng

- Bot Zalo không phản hồi hoặc phản hồi không ổn định
- Log container báo: `s6-log: unable to lock .../gateways/default/lock: Resource busy`
- Zalo bridge báo `sseClients: 2` (2 client SSE kết nối đồng thời)

### Nguyên nhân gốc

Profile `family` chạy song song với profile `default`, cả hai connect SSE tới cùng Zalo bridge
→ Bridge báo `409 Conflict` → vòng lặp reconnect → file lock bị tranh chấp.

### Cách fix

```powershell
# 1. Kill process đang giữ lock (dùng wmic khi taskkill bị Access Denied)
wmic process where processid=<PID> call terminate

# 2. Xóa profile family
Remove-Item -Recurse -Force "C:\Users\Desktop\.hermes\profiles\family"
Remove-Item -Recurse -Force "C:\Users\Desktop\.hermes\logs\gateways\family"

# 3. Restart sạch container
docker compose stop gateway
docker compose start gateway
```

---

## Sự cố 3: Lỗi timeout gửi Zalo từ cron/tool (03/07/2026)

### Triệu chứng

```
Adapter send failed: Timeout context manager should be used inside a task
```

### Nguyên nhân gốc

`aiohttp.ClientTimeout` (phiên bản mới) dùng `asyncio.timeout()` bên trong.
Khi gọi từ thread cron hoặc `run_coroutine_threadsafe` (không có asyncio Task context) → crash.

### Cách fix

Thay `aiohttp.ClientTimeout` bằng `asyncio.wait_for()`:

```python
# Trước (lỗi)
async with session.post(url, timeout=aiohttp.ClientTimeout(total=60)) as resp:
    ...

# Sau (đúng)
async def _do():
    async with session.post(url, timeout=None) as resp:
        return await resp.json()
return await asyncio.wait_for(_do(), timeout=60.0)
```

---

## Sự cố 4: SSE rejected (already have 1 client) — returning 409 (06/07/2026)

### Triệu chứng
- Bot không phản hồi trên Zalo dù bridge nhận được tin nhắn.
- Logs từ Zalo Bridge báo lỗi liên tục:
  ```
  [bridge] SSE rejected (already have 1 client) — returning 409
  ```

### Nguyên nhân gốc
- Cả hai container `hermes` (gateway) và `hermes-dashboard` (dashboard) đều sử dụng chung một thư mục volume mount `~/.hermes`.
- Khi container `hermes-dashboard` khởi động, cơ chế s6-supervise mặc định quét các profile đang ở trạng thái `running` (phát hiện trong `state.json`) và tự khởi động chúng dưới dạng service ngầm.
- Vì dùng Windows bind mount (`~/.hermes`), cơ chế lock file `gateway.lock` (`fcntl.flock`) **không đồng bộ độc quyền xuyên suốt giữa các container**. 
- Hệ quả là cả `hermes` và `hermes-dashboard` đều cho rằng mình giữ lock độc quyền, đồng thời khởi chạy Zalo gateway adapter và connect SSE tới bridge. Bridge từ chối kết nối thứ hai bằng mã lỗi 409.

### Cách fix
- Thêm cấu hình vô hiệu hóa s6 gateway service trên dashboard service trong `docker-compose.yml`:
  ```yaml
  dashboard:
    environment:
      - HERMES_GATEWAY_NO_SUPERVISE=1
      - S6_PROFILE_GATEWAY_SCANDIR=/tmp/dummy_scandir
  ```
- Khởi động lại docker-compose (`docker compose up -d`) để áp dụng thay đổi. Điều này đảm bảo chỉ duy nhất container `hermes` chạy gateway kết nối Zalo.

---

## Sự cố 5: Bot bỏ qua tin nhắn DM từ sếp do bộ lọc Thread Allowlist (06/07/2026)

### Triệu chứng
- Bridge nhận được tin nhắn DM từ sếp (`Xitrum`), log gateway ghi nhận tin nhắn đã nhận, nhưng Bot hoàn toàn im lặng và không phản hồi.

### Nguyên nhân gốc
- Trong cấu hình `.env`, biến `ZALO_ALLOWED_THREADS` được cấu hình để bot chỉ được phép hoạt động trong một số group chỉ định (ví dụ: nhóm "Bi bống house").
- Logic lọc tin nhắn trong `adapter.py` kiểm tra `ZALO_ALLOWED_THREADS` đầu tiên:
  ```python
  if self._allowed_threads and thread_id not in self._allowed_threads:
      logger.debug("Zalo: ignoring message in non-allowed thread %s", thread_id)
      return
  ```
- Khi sếp nhắn tin trực tiếp (DM), `thread_id` chính là User ID của sếp. ID này không thuộc danh sách group trong `ZALO_ALLOWED_THREADS` nên tin nhắn bị gateway silently drop ngay lập tức, bỏ qua cả kiểm tra User ID hợp lệ trong `ZALO_ALLOWED_USERS`.

### Cách fix
- Sửa lại logic trong `~/.hermes/plugins/zalo/adapter.py` để tin nhắn DM từ user được cho phép trong `ZALO_ALLOWED_USERS` có thể bỏ qua (bypass) lớp lọc `ZALO_ALLOWED_THREADS`:
  ```python
  # Bypass thread allowlist check if this is a DM and the sender is in the user allowlist.
  is_allowed_user_dm = (chat_type == "dm") and (not self._allowed_users or sender_id in self._allowed_users)
  if self._allowed_threads and thread_id not in self._allowed_threads and not is_allowed_user_dm:
      logger.debug("Zalo: ignoring message in non-allowed thread %s", thread_id)
      return
  ```
- Khởi động lại container `gateway` (`docker compose restart gateway`).

---

## Quy tắc cấu hình ZALO

| Biến | Mục đích | Loại ID được phép |
|------|----------|-------------------|
| `ZALO_ALLOWED_USERS` | Kiểm soát ai được nhắn DM với bot | **User ID** (uidFrom) |
| `ZALO_ALLOWED_THREADS` | Giới hạn bot chỉ hoạt động trong nhóm cụ thể | **Group ID** (threadId của nhóm) |
| `ZALO_HOME_CHANNEL` | Kênh mặc định gửi thông báo cron | User ID hoặc `group:<groupId>` |

> **KHÔNG trộn User ID vào `ZALO_ALLOWED_THREADS`!**
>
> `ZALO_ALLOWED_THREADS` dùng để whitelist nhóm. Nếu đặt User ID vào đây,
> adapter nhận nhầm DM là group → gửi với `threadType=group` → lỗi "Nhóm này không tồn tại".
>
> DM của user đã được kiểm soát qua `ZALO_ALLOWED_USERS`.
> Để `ZALO_ALLOWED_THREADS` trống nếu muốn bot hoạt động trong mọi nhóm.

### Cấu hình hiện tại (sau khi fix — 06/07/2026)

```env
# DM được phép: sếp (Nguyễn Huy Phong) và vợ (Hà Thị Huế)
ZALO_ALLOWED_USERS=2825656851207986406,3656141905842635373

# Bot chỉ hoạt động trong nhóm: "Bi bống house"
ZALO_ALLOWED_THREADS=3339712927031818889

# Kênh nhận thông báo cron mặc định: DM của sếp
ZALO_HOME_CHANNEL=2825656851207986406
```

---

## Lệnh chẩn đoán nhanh

```powershell
# Xem log gateway realtime
docker compose logs -f gateway

# Xem agent.log chi tiết bên trong container
docker exec hermes bash -c "tail -50 /opt/data/logs/agent.log"

# Kiểm tra Zalo bridge còn sống không
Invoke-RestMethod -Uri "http://localhost:8787/health"
# Kết quả mong đợi: sseClients: 1, loggedIn: true

# Kiểm tra biến env Zalo đang active
docker exec hermes bash -c "grep -i ZALO /opt/data/.env | grep -v TOKEN"

# Restart sạch gateway (tránh lock conflict)
docker compose stop gateway; docker compose start gateway
```

---

## Sự cố 6: Bot im lặng sau khi cấu hình DM bypass (21/07/2026)

### Triệu chứng
- Đã thêm code bypass `_allowed_threads` cho DM hợp lệ nhưng bot vẫn không phản hồi khi nhắn `ping`.
- Bridge log báo: `[bridge] SSE client connected, total: 1` và `RAW message: ... ping`.
- Nhưng `agent.log` hoàn toàn im lặng, không có dòng `Zalo inbound` nào.

### Nguyên nhân gốc
- Container `hermes` bị kẹt connection SSE cũ (hoặc tiến trình gateway trong container bị kẹt/treo loop SSE do chưa áp dụng triệt để file code mới).
- Mặc dù file `adapter.py` đã sửa trên host, nhưng tiến trình chạy ngầm trong container chưa được restart để nạp lại class adapter.

### Cách fix
- Bắt buộc phải restart lại container `hermes` (chứa Gateway) để nạp lại mã nguồn Python mới:
  ```powershell
  docker restart hermes
  ```
- Sau khi khởi động lại, bot lập tức ghi nhận `Zalo inbound` và xử lý tin nhắn bình thường.

---

## Sự cố 7: Bot Zalo báo lỗi API (Connection error) (21/07/2026)

### Triệu chứng
- Nhắn tin `ping`, bot Zalo trả lời bằng câu thông báo lỗi: `API call failed sau 3 retries. Connection error.`
- Kiểm tra `agent.log` thấy báo lỗi kết nối tới LLM:
  ```
  API call failed (attempt 3/3) error_type=APIConnectionError ... base_url=http://host.docker.internal:20128/v1
  ```

### Nguyên nhân gốc
- Pipeline kết nối Zalo ↔ Hermes đã hoạt động **hoàn hảo** (tin nhắn đi và về thành công).
- Nguyên nhân lỗi nằm ở backend AI (model provider). Gateway đang cố gọi API LLM tại `host.docker.internal:20128` (ví dụ: Local server hoặc container AI khác) nhưng endpoint này đang down hoặc không phản hồi.

### Cách fix
- Kiểm tra lại backend AI đang chạy (ví dụ: LM Studio, Ollama, vLLM hoặc container AI tương ứng) đang map port 20128.
- Chạy LLM server lên, bot Zalo sẽ phản hồi bình thường.

---

## Sự cố 8: ZaloAdapter.connect() got an unexpected keyword argument 'is_reconnect' (23/07/2026)

### Triệu chứng
- Gateway khởi động lên báo lỗi:
  ```
  ERROR gateway.run: ✗ zalo error: ZaloAdapter.connect() got an unexpected keyword argument 'is_reconnect'
  ```
- Kết nối tới Zalo bị dừng và liên tục thử lại (reconnect loop) nhưng thất bại.

### Nguyên nhân gốc
- Phiên bản core `hermes-agent` mới cập nhật truyền thêm đối số `is_reconnect` khi gọi hàm `connect()` trên các platform adapter.
- File plugin custom `ZaloAdapter` (`~/.hermes/plugins/zalo/adapter.py`) có hàm `connect()` với signature cũ `async def connect(self) -> bool:` không chấp nhận đối số này.

### Cách fix
- Sửa signature của hàm `connect` trong `~/.hermes/plugins/zalo/adapter.py` để chấp nhận mọi đối số động:
  ```python
  async def connect(self, *args, **kwargs) -> bool:
  ```
- Khởi động lại container `gateway`.

---

## Sự cố 9: Lỗi kết nối lặp lại 'listener disconnected 1000 NORMAL_CLOSURE' (23/07/2026)

### Triệu chứng
- Bridge Zalo và watchdog liên tục chuyển đổi trạng thái: `CONNECTED -> CATCHUP -> DISCONNECTED -> CONNECTED` chỉ trong vài giây.
- Log báo lỗi kết nối đóng sạch từ phía Zalo server: `listener disconnected 1000 NORMAL_CLOSURE`.
- Zalo bot không phản hồi tin nhắn `ping`.

### Nguyên nhân gốc
- Zalo giới hạn nghiêm ngặt chỉ cho phép một kết nối hoạt động tại một thời điểm cho một tài khoản.
- Trên máy host Windows đang chạy nhiều tiến trình Node.js ngầm của Zalo bridge cùng kết nối tới một tài khoản, dẫn đến việc các tiến trình tranh chấp và liên tục "đá" nhau ra.

### Cách fix
1. Tắt toàn bộ CMD/Terminal chạy Zalo bridge hoặc watchdog.
2. Dọn dẹp sạch các tiến trình Node chạy ngầm trên Windows Host qua PowerShell:
   ```powershell
   Stop-Process -Name node -Force
   ```
3. Khởi chạy lại duy nhất một tiến trình watchdog/bridge.
