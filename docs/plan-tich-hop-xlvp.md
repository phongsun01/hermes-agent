# Kế hoạch Tích hợp Bộ công cụ XLVP (OfficeCLI) vào Kỹ năng Dự thảo (congchuc skill)

Tài liệu này đánh giá tính khả thi, thiết kế kiến trúc tái sử dụng và lên kế hoạch tích hợp bộ công cụ xử lý văn phòng **xlvp** (dựa trên **OfficeCLI**) vào phần dự thảo văn bản (`congchuc_draft.py`) của skill **congchuc** trong Hermes Agent.

---

## 1. Đánh giá tính khả thi (Feasibility Assessment)

### Kỹ thuật & Môi trường
* **Lõi OfficeCLI**:
  * Được phát triển bằng **C# (.NET 10)** dưới dạng self-contained binary (nhúng sẵn runtime, dung lượng ~32MB trên Windows).
  * Do đặc thù khởi động (.NET cold-start) và tính chất tất định của luồng dự thảo cron, dự án sẽ sử dụng **Batch Mode** (`officecli batch --commands '[...]' --json`) cho luồng tự động ngầm. Quyết định này giúp loại bỏ hoàn toàn sự phụ thuộc vào Resident Mode (named pipe/socket), giảm thiểu rủi ro phân quyền thư mục và xung đột tiến trình chạy đồng thời.
  * Hiện tại có sẵn bản build cho **Linux** (dùng cho môi trường Docker của Hermes-agent) và bản build cho **Windows** (dùng cho môi trường máy chủ host).
* **Môi trường Docker (Linux) & Host (Windows)**:
  * Việc tích hợp được thực hiện bằng cách đóng gói (COPY) binary **OfficeCLI Linux** vào Docker image lúc build để tránh lỗi mất quyền thực thi (`Permission denied`) do NTFS bind-mount trên Docker Desktop gây ra.
  * Thư mục mã nguồn Python (`xlvp-py`) sẽ được mount để phục vụ quá trình phát triển nhanh.

### Lợi ích so với pipeline cũ
* **Tốc độ & Tính toàn vẹn**: Sử dụng Batch Mode giúp đóng gói tất cả thao tác chỉnh sửa (create, set, add) vào một phiên thực thi đơn lẻ, tối ưu hóa hiệu năng và đảm bảo tính toàn vẹn (nếu lỗi giữa chừng sẽ không ghi đè dở dang file cũ).
* **Độ chính xác**: Hỗ trợ đầy đủ tiêu chuẩn **NĐ 30** thông qua các lệnh thiết lập cấu trúc trực tiếp (`officecli set`).
* **Tính năng nâng cao**: Hỗ trợ Preview HTML real-time (`officecli watch`) giúp kiểm tra visual trước khi xuất bản bản thảo.

---

## 2. Thiết kế Kiến trúc Tái sử dụng (Design for Reusability)

Để bộ công cụ `xlvp` có thể được tái sử dụng nhanh chóng bởi các skill khác trong Hermes hoặc các dự án bên ngoài (không phải Hermes), chúng ta sẽ thiết kế một thư viện wrapper Python độc lập tên là `xlvp-py`.

### Sơ đồ Kiến trúc
```mermaid
graph TD
    subgraph External Projects / Other Skills
        A[Project X] -- Imports --> C[xlvp-py Wrapper]
        B[Skill Y in Hermes] -- Imports --> C
    end
    subgraph xlvp-py Library
        C --> D{OS Check}
        D -- Windows -- > E[Execute officecli.exe]
        D -- Linux (Docker) --> F[Execute officecli Linux]
    end
    E & F -- Batch JSON Commands --> G[DOCX/XLSX/PPTX Files]
```

### Thiết kế Thư viện Wrapper (`xlvp-py`)
Thư mục `D:\Antigravity\xlvp` sẽ đóng vai trò là một package Python độc lập.
Cấu trúc đề xuất:
```
xlvp/
├── xlvp/
│   ├── __init__.py
│   ├── client.py        # Lớp XLVPClient (chỉ tìm trong /usr/local/bin/officecli trên Linux, resources/bin/officecli.exe trên Windows)
│   └── utils.py         # Tiện ích chuyển đổi path, đọc file tiêu chuẩn
├── standards/
│   ├── nd30.md          # Quy chuẩn hành chính (bản đọc cho người)
│   └── nd30.json        # Quy chuẩn cấu trúc hóa (Single Source of Truth cho máy đọc)
├── resources/
│   └── bin/
│       └── officecli.exe # Chỉ giữ bản Windows ở repository (quản lý qua Git LFS)
├── pyproject.toml       # Quản lý dependency để pip install
├── NOTICE.txt           # Giấy phép & Tuyên bố bản quyền gốc của OfficeCLI (Apache 2.0)
└── README.md
```

#### Quản lý Tài nguyên & Bản quyền
* **Quản lý file lớn (Git LFS)**: Binary `officecli.exe` (~32MB) và các asset nhị phân khác sẽ được quản lý thông qua Git LFS (hoặc tải trực tiếp thông qua script cài đặt lúc build) thay vì commit thô vào git history để tránh phình dung lượng repository.
* **Bản quyền**: Thêm file `NOTICE.txt` và ghi rõ bản quyền thuộc về OfficeCLI (Giấy phép Apache License 2.0) khi đóng gói lại binary.

#### Sử dụng Nguồn Chuẩn NĐ 30 Cấu trúc hóa
Wrapper sẽ đọc trực tiếp các thông số định dạng (lề, font, spacing) từ file cấu trúc dữ liệu `standards/nd30.json` để làm Single Source of Truth, loại bỏ việc hardcode hoặc phân tích regex phức tạp từ văn bản xuôi `.md`.

* **Sử dụng trong Hermes Skill**: Cài đặt dạng chỉnh sửa: `pip install -e /opt/xlvp` trong môi trường ảo của Hermes.
* **Sử dụng trong dự án khác**: Cài đặt độc lập qua git: `pip install git+https://github.com/phongsun01/xlvp.git`.

---

## 3. Lưu ý về Docker, Font & Môi trường Hỗn hợp

### 1. Cài đặt Font chữ Times New Roman trên Linux (Quan trọng)
Quy chuẩn NĐ 30 yêu cầu font chữ **Times New Roman**. Do môi trường Docker Linux mặc định không có sẵn font thương mại này của Microsoft, chúng ta cần:
* Bổ sung bước cài đặt các font metric-compatible như `fonts-liberation` (hoặc font `Tinos` tương đương) hoặc cài đặt gói `ttf-mscorefonts-installer` vào `Dockerfile` trong quá trình build image.
* Việc này giúp tính năng preview HTML (`view html`) hoặc xuất screenshot (`view screenshot`) của OfficeCLI hiển thị chính xác layout văn bản không bị lỗi dòng/lệch lề.

### 2. Đóng gói Binary vào Docker Image (Tránh rủi ro Permission)
* Do rủi ro mất quyền thực thi (`chmod +x` bị mất do NTFS bind-mount trên Docker Windows), chúng ta sẽ không chạy trực tiếp binary từ thư mục mount.
* Thay vào đó, trong `Dockerfile`, chúng ta sẽ COPY file binary `officecli` Linux vào trong Container `/usr/local/bin/officecli` khi build image và set quyền execute cố định.
* Thư mục code Python `/opt/xlvp` vẫn được mount như bình thường để dev nhanh.

### 3. Tắt Tự động Cập nhật (Version Pinning)
Để đảm bảo các tác vụ chạy tự động qua cron của `/cc duthao` luôn hoạt động ổn định và nhất quán, chúng ta sẽ ghim cố định phiên bản OfficeCLI sử dụng và tắt tính năng tự động cập nhật ngầm. Setting này sẽ được tích hợp trực tiếp vào câu lệnh `RUN` trong `Dockerfile` hoặc cấu hình khởi tạo của container (`entrypoint.sh`) thay vì chạy thủ công:
```bash
# Thực hiện tự động trong Dockerfile/entrypoint
officecli config autoUpdate false
```

### 4. Ánh xạ Đường dẫn (Path Translation) giữa Docker và Host
Khi dự thảo được tạo trong Docker (Linux), đường dẫn lưu file sẽ dạng `/opt/data/cron/cong-van-den/drafts/...`.
* Khi gửi file đính kèm qua Zalo/Telegram chạy ở phía Host (Windows), Zalo Plugin đòi hỏi đường dẫn vật lý trên Host (ví dụ: `C:\Users\Desktop\.hermes\cron\cong-van-den\drafts\...`).
* **Giải pháp**: Bộ chuyển đổi `xlvp` hoặc script `congchuc_draft.py` sẽ sử dụng biến môi trường `ZALO_HOST_HERMES_HOME` để dịch đường dẫn tự động trước khi gửi API (đã có sẵn cơ chế replace trong `congchuc_draft.py` hiện tại).

---

## 4. Phân tách Kiến trúc: Thư viện lập trình vs. MCP Server

* **Thư viện Python (`xlvp-py`)**: Được sử dụng cho các script nội bộ hoặc tác vụ cron tự động (`congchuc_draft.py`) với luồng xử lý định trước (deterministic), gọi lệnh qua Batch Mode không trạng thái (stateless).
* **MCP Server (`officecli mcp`)**: Sẽ là cấu phần tùy chọn bổ sung trong tương lai. MCP sẽ được dùng khi người dùng muốn giao tiếp trực tiếp với Agent qua khung chat (ví dụ: *"Sửa giùm tôi bảng này sang cột mới"*) và LLM cần khả năng tự động gọi công cụ một cách linh hoạt để thao tác trên tài liệu. Việc tách bạch rõ 2 luồng này giúp giữ mã nguồn sạch và dễ bảo trì.

---

## 5. Kế hoạch Triển khai (Implementation Plan)

* **Tổng thời gian dự kiến**: 5 - 7 ngày (Sử dụng kiến trúc Batch Mode stateless giúp rút ngắn thời gian thiết lập named pipe và xử lý tranh chấp concurrency phức tạp).

### Bước 1: Chuẩn bị môi trường, Font & Binary (1-2 ngày)
1. Tải OfficeCLI phiên bản Linux (từ GitHub iOfficeAI/OfficeCLI).
2. Viết câu lệnh đóng gói binary Linux trực tiếp vào `Dockerfile` (đặt tại `/usr/local/bin/officecli`, cấp quyền `chmod +x`). Loại bỏ bản Linux khỏi thư mục mounted `resources/bin` để tránh xung đột phiên bản.
3. Cập nhật `Dockerfile` cài đặt font chữ `fonts-liberation` hoặc `ttf-mscorefonts-installer` để hỗ trợ render preview chính xác.
4. Cài đặt tự động `officecli config autoUpdate false` thông qua entrypoint/Dockerfile.
5. Cập nhật `docker-compose.yml` của Hermes để mount thư mục code Python `/opt/xlvp` và restart container.

### Bước 2: Xây dựng Thư viện Wrapper `xlvp` (2-3 ngày)
1. Tạo package cấu trúc `xlvp` trong thư mục `d:\Antigravity\xlvp` như thiết kế ở Mục 2.
2. Xây dựng file định nghĩa tiêu chuẩn `standards/nd30.json` dạng cấu trúc hóa.
3. Thiết lập cơ chế parse file tiêu chuẩn từ `standards/nd30.json` làm Single Source of Truth cho các margin/font.
4. Xây dựng phương thức chuyển đổi nâng cao `convert_markdown_to_docx` sử dụng **Batch Mode** (`officecli batch`) gửi danh sách các lệnh định dạng và thêm đoạn văn trong 1 lần gọi để tối ưu hiệu năng.
5. Kiểm tra unit test trên cả Windows (local) và Linux (trong Docker).

### Bước 3: Nâng cấp `congchuc_draft.py` & Tích hợp Cơ chế Fallback (1-2 ngày)
1. Cấu hình cài đặt wrapper `xlvp-py` vào môi trường ảo thông qua lệnh:
   ```bash
   pip install -e /opt/xlvp
   ```
2. Cập nhật mã nguồn `congchuc_draft.py` để import `xlvp` và sử dụng `XLVPClient` sinh văn bản chất lượng cao.
3. **Tích hợp Cơ chế Fallback & Watermark**:
   * Thiết lập khối `try-except` xung quanh tiến trình gọi `XLVPClient`.
   * Nếu có lỗi (thiếu binary, validation thất bại, hoặc crash), ghi log WARNING chi tiết lỗi vào `agent.log`/`errors.log`.
   * Tự động fallback về luồng chuyển đổi cũ (`convert_md_to_docx.py` dựa trên `python-docx`).
   * **Đóng dấu cảnh báo**: Thêm một dòng chữ nhỏ màu đỏ hoặc watermark ở phần đầu/cuối file Word fallback: *"Bản dịch thảo dự phòng - Cần soát lại định dạng do sự cố pipeline OfficeCLI"* để người dùng nhận biết chất lượng văn bản chưa được kiểm định chuẩn NĐ 30.
4. **Tích hợp QA Loop đầy đủ**:
   * Gọi lệnh `officecli validate` để kiểm tra tính hợp lệ cấu trúc OOXML.
   * Gọi `officecli view issues` để phát hiện các lỗi trình bày visual (tràn chữ, thiếu alt text).

### Bước 4: Kiểm thử và Bàn giao (1 ngày)
1. Kiểm tra luồng dự thảo tự động với các số văn bản thực tế qua lệnh `/cc duthao <số>`.
2. Kiểm tra chất lượng hiển thị của file Word kết quả trên các ứng dụng đọc tài liệu (MS Word, LibreOffice).
3. Biên soạn tài liệu hướng dẫn sử dụng wrapper cho các skill khác.
