# Hướng dẫn Tích hợp Onyx với Hermes Agent (v3.1)

**Nguồn tham khảo:**
1. Onyx MCP Server: https://docs.onyx.app/overview/onyx_anywhere/mcp_server
2. Hermes-agent: https://github.com/nousresearch/hermes-agent

> [!IMPORTANT]
> Kể từ v3.1, chúng ta sử dụng **Native MCP Server** của Onyx chạy trên port **8090**. 
> Việc này giúp Hermes truy cập thẳng vào "bộ não" của Onyx mà không cần qua Nginx hay Bridge trung gian.

---

## 1. Cấu hình phía Onyx (Dưới máy chủ Onyx)

Bạn cần kích hoạt MCP Server vì mặc định Onyx tắt tính năng này để tiết kiệm tài nguyên.

### Bước 1.1: Sửa file `.env` của Onyx
Tìm file `.env` trong thư mục deployment của Onyx (thường là `onyx/deployment/docker_compose/.env`):
```env
# Tìm và sửa dòng này thành true
MCP_SERVER_ENABLED=true
```

### Bước 1.2: Sửa file `docker-compose.yml` của Onyx
Tìm block `mcp_server:` (mặc định bị comment bằng dấu `#`) và bỏ comment để kích hoạt service này.

### Bước 1.3: Khởi động lại Onyx
Chạy lệnh sau để áp dụng cấu hình:
```bash
docker compose up -d mcp_server
```

---

## 2. Cấu hình phía Hermes

### Bước 2.1: Thiết lập Token trong `~/.hermes/.env`
Lấy **Personal Access Token** từ giao diện Onyx (Settings -> Profile) và dán vào:
```env
ONYX_API_TOKEN=on_KuYVQ95... (token của bạn)
```

### Bước 2.2: Cấu hình Server trong `~/.hermes/config.yaml`
Sử dụng địa chỉ container name và port 8090:
```yaml
mcp_servers:
  onyx:
    url: "http://onyx-mcp_server-1:8090/"
    headers:
      Authorization: "Bearer ${ONYX_API_TOKEN}"
    timeout: 60
```

---

## 3. Kết nối Docker Network
Để container `hermes` có thể gọi được `onyx-mcp_server-1`, chúng phải chung network:
```powershell
docker network connect onyx_default hermes
```

---

## 4. Kiểm tra
Chạy lệnh sau trong container Hermes để kiểm tra danh sách tool:
```bash
hermes mcp list
```
Nếu hiện `onyx` trạng thái `✓ enabled` là thành công.

---

## Giải đáp về việc Build chậm
- **Tại sao chậm?**: Image `hermes-agent` chứa toàn bộ môi trường Python 3.13, các thư viện AI, và các SDK MCP. Kích thước có thể lên đến vài GB.
- **Do mạng?**: Đúng một phần. Docker sẽ tải các layer từ internet. Nếu mạng chậm hoặc Docker Hub bị bóp băng thông, việc này sẽ mất rất nhiều thời gian.
- **Đổi network?**: Bạn hoàn toàn có thể đổi sang mạng mạnh hơn. Docker hỗ trợ resume download nên không lo bị mất tiến trình.
- **Giải pháp nhanh**: Thay vì chờ build lại toàn bộ, tôi đang cố gắng sửa trực tiếp file bị lỗi trong container hiện tại của bạn để bạn dùng được ngay.
```

Onyx cung cấp **3 Tools** qua MCP:
- `search` — Tìm kiếm trong knowledge base (Confluence, Drive, Slack, GitHub, Jira, và 40+ nguồn khác)
- `web_search` — Tìm kiếm thông tin công khai trên web
- `fetch_page` — Lấy nội dung đầy đủ từ một URL bất kỳ

---

## 2. Điều kiện tiên quyết

- Onyx đang chạy và có thể truy cập (mặc định: `http://localhost:3000`)
- Bạn có **Personal Access Token (PAT)** hoặc **API Key** của Onyx

### Tạo Personal Access Token (PAT)

1. Đăng nhập vào Onyx tại `http://localhost:3000`
2. Vào **Settings → Profile → Personal Access Tokens**
3. Tạo token mới — token sẽ có dạng `onyx_pat_...`
4. Lưu token lại (chỉ hiện một lần)

> [!NOTE]
> **PAT** (Personal Access Token) dùng cho cá nhân, kế thừa quyền của tài khoản bạn.
> **API Key** (Admin) do Admin cấp, dùng cho service accounts hoặc tích hợp toàn hệ thống.
> Với Hermes, PAT là lựa chọn đơn giản và đủ dùng nhất.

---

## 3. Cấu hình Hermes Agent

Mở file `~/.hermes/config.yaml` và thêm đoạn sau:

```yaml
mcp_servers:
  onyx:
    url: "http://localhost:3000/mcp"   # Self-hosted Onyx (mặc định)
    # url: "https://cloud.onyx.app/mcp" # Hoặc dùng Onyx Cloud
    headers:
      Authorization: "Bearer onyx_pat_YOUR_TOKEN_HERE"
    timeout: 60           # Timeout cho mỗi tool call (giây)
    connect_timeout: 30   # Timeout kết nối ban đầu (giây)
```

> [!CAUTION]
> **Bảo mật Token:** Không commit token vào git. Nên lưu token trong `.env` và tham chiếu qua biến môi trường, hoặc giữ `config.yaml` trong `.gitignore`.

### Cấu hình qua CLI

```bash
hermes mcp add onyx http://localhost:3000/mcp
```

---

## 4. Kiểm tra Kết nối

Sau khi cấu hình, khởi động Hermes và kiểm tra:

```bash
# Liệt kê tất cả tools từ MCP servers đã đăng ký
hermes chat --list-tools

# Test trực tiếp bằng lệnh chat
hermes chat "Tìm kiếm tài liệu về quy trình onboarding"
```

Hermes sẽ tự động gọi tool `search` của Onyx khi cần tra cứu kiến thức nội bộ.

---

## 5. Cấu hình Nâng cao

### Dùng với Docker Network

Nếu cả Hermes và Onyx cùng chạy trong Docker (cùng network):

```yaml
mcp_servers:
  onyx:
    url: "http://onyx-nginx-1:80/mcp"   # Container name của Onyx nginx
    headers:
      Authorization: "Bearer onyx_pat_YOUR_TOKEN_HERE"
```

Hoặc nếu truy cập Onyx từ container Hermes ra ngoài host:

```yaml
mcp_servers:
  onyx:
    url: "http://host.docker.internal:3000/mcp"
    headers:
      Authorization: "Bearer onyx_pat_YOUR_TOKEN_HERE"
```

### Tích hợp nhiều Persona / Knowledge Base

Onyx cho phép dùng nhiều Persona khác nhau. Bạn có thể cấu hình nhiều MCP server entries trỏ đến cùng Onyx nhưng với token khác nhau (mỗi token tương ứng một user/quyền khác nhau):

```yaml
mcp_servers:
  onyx-engineering:
    url: "http://localhost:3000/mcp"
    headers:
      Authorization: "Bearer onyx_pat_ENGINEERING_TOKEN"
  onyx-hr:
    url: "http://localhost:3000/mcp"
    headers:
      Authorization: "Bearer onyx_pat_HR_TOKEN"
```

---

## 5. Hướng dẫn sử dụng (Usage)

### Cách Chat để Bot tự kích hoạt Onyx

Hermes được thiết kế để tự động nhận diện ý định. Tuy nhiên, để đảm bảo Bot luôn gọi đúng dữ liệu từ Onyx, bạn nên sử dụng các "từ khóa gợi ý" trong câu lệnh:

*   **Tra cứu tài liệu nội bộ:**
    *   *Câu lệnh:* "Kiểm tra trong **Onyx** về chính sách bảo hiểm của công ty."
    *   *Tại sao:* Từ khóa "Onyx" giúp AI ưu tiên chọn MCP Server này.
*   **Yêu cầu tìm kiếm có phạm vi:**
    *   *Câu lệnh:* "Dựa trên **kiến thức nội bộ**, dự án X đang ở giai đoạn nào?"
    *   *Tại sao:* Cụm từ "kiến thức nội bộ" thường kích hoạt tool `search_indexed_documents`.
*   **Tìm kiếm Web qua Onyx:**
    *   *Câu lệnh:* "Dùng **Onyx Search Web** tìm thông tin mới nhất về giá card đồ họa."
    *   *Tại sao:* Chỉ định rõ hành động giúp AI không nhầm lẫn với các tool tìm kiếm khác (như Google/DuckDuckGo nếu có).

> [!TIP]
> Nếu Bot không tự gọi Onyx, hãy ra lệnh cưỡng ép: *"Hãy dùng tool mcp_onyx_search_indexed_documents để tìm thông tin về..."*

---

## 6. Thay đổi Persona cho Telegram Bot (Hermes)

Persona (tính cách) quyết định cách Bot xưng hô, giọng điệu và mức độ chi tiết khi trả lời.

### Cách 1: Đổi trực tiếp qua Chat (Nếu Agent hỗ trợ)
Gửi lệnh sau trực tiếp cho Bot trên Telegram:
```text
/persona <tên_persona>
```
*(Ví dụ: `/persona ares` hoặc `/persona default`)*

### Cách 2: Cấu hình trong `config.yaml` (Ưu tiên)
Mở file `~/.hermes/config.yaml` và tìm mục `display.skin` hoặc cấu hình `prompt`:

1.  **Đổi Skin (Giao diện & Giọng điệu mặc định):**
    ```yaml
    display:
      skin: "ares"  # Các skin có sẵn: default, ares, mono, slate, cyberpunk
    ```
2.  **Đổi System Prompt (Cốt lõi tính cách):**
    Bạn có thể định nghĩa persona trong mục `agent`:
    ```yaml
    agent:
      model: "..."
      system_prompt: "Bạn là một chuyên gia hỗ trợ kỹ thuật chuyên nghiệp, luôn trả lời ngắn gọn và tập trung vào dữ liệu từ Onyx."
    ```

Sau khi sửa file, hãy khởi động lại container Hermes: `docker restart hermes`.

---

## 7. Các Lớp Bảo Vệ Tích hợp của Onyx

Onyx MCP Server tích hợp sẵn các cơ chế bảo vệ:

1. **Rate Limiting** — Onyx tự quản lý giới hạn request.
2. **Permission Scoping** — Kết quả tìm kiếm được lọc theo quyền của token (bạn chỉ thấy tài liệu bạn được phép xem).
3. **Audit Logging** — Mọi query đều được ghi log trong Onyx Admin Dashboard → Query History.

---

## 8. Xử lý Lỗi Thường Gặp

| Lỗi | Nguyên nhân | Giải pháp |
|---|---|---|
| `401 Unauthorized` | Token sai hoặc hết hạn | Tạo lại PAT trong Onyx Settings |
| `Connection refused` | Onyx chưa chạy | Kiểm tra `docker ps` và `http://localhost:3000` |
| `404 Not Found` | URL endpoint sai | Thử `/mcp` thay vì `/sse` (hoặc ngược lại) |
| `timeout` | Onyx quá tải hoặc index đang rebuild | Tăng `timeout` trong config, thử lại sau |
| `onyx [http]: failed` (TUI) | Handshake thất bại lúc khởi động | Gõ `/mcp refresh` để kết nối lại |
| `streamable_http not available` | Thư viện `mcp` trên host bị cũ | Chạy `pip install --upgrade mcp` trong `.venv` |
| `getaddrinfo failed` (Host) | Máy host không hiểu tên container | Dùng lệnh `docker exec` để test chuẩn (xem bên dưới) |

### Lệnh Kiểm tra "Nguồn sự thật" (Source of Truth)

Khi gặp bất kỳ thông báo lỗi nào trên giao diện TUI hoặc PowerShell máy host, hãy luôn dùng lệnh này bên trong Docker để xác định trạng thái kết nối thực tế:

```powershell
docker exec hermes /opt/hermes/.venv/bin/hermes mcp list
```

Nếu kết quả hiện **`onyx ✓ enabled`**, nghĩa là hệ thống **đang hoạt động hoàn hảo**, các lỗi khác chỉ là vấn đề hiển thị trên máy host.

### Lưu ý về Môi trường Local (Máy host)

Nếu bạn chạy Hermes TUI trực tiếp trên Windows (ngoài Docker), hãy đảm bảo môi trường Python local của bạn luôn được cập nhật để hỗ trợ giao thức HTTP của MCP:

```powershell
cd D:\Antigravity\Hermes
.\.venv\Scripts\activate
pip install --upgrade mcp
```

---

## 9. Tham khảo

- [Onyx MCP Server Docs](https://docs.onyx.app/overview/onyx_anywhere/mcp_server)
- [Onyx API Authentication](https://docs.onyx.app/developers/overview#personal-access-tokens)
- [Onyx Admin — MCP Actions](https://docs.onyx.app/admins/actions/mcp)
- [Hermes MCP Configuration](https://github.com/nousresearch/hermes-agent) — xem `docs/mcp.md`