# Kế hoạch Tích hợp nd30-document-drafter & nd30-sualoi vào Kỹ năng Xử lý văn phòng (cc)

Tài liệu này lên kế hoạch tích hợp hai bộ kỹ năng chuyên sâu về văn bản hành chính Việt Nam là **nd30-document-drafter** (soạn thảo chuẩn Nghị định 30/2020/NĐ-CP) và **nd30-sualoi** (hiệu đính, trích xuất ngược và soát lỗi văn bản) vào hệ thống xử lý công văn (`skills/cc`) hiện tại của Hermes.

---

## 1. Mục tiêu tích hợp

1. **Nâng cấp tính năng Dự thảo (`/cc duthao <số>`)**:
   - Thay đổi cơ chế sinh file Word cũ (layout tự do) sang xuất dữ liệu có cấu trúc (JSON Schema chuẩn NĐ 30).
   - Sử dụng script Node.js từ `nd30-document-drafter` để tạo file Word chuẩn chỉ 100% về căn lề, font chữ, bảng chữ ký ẩn, tiêu ngữ theo quy chuẩn của Chính phủ.
2. **Bổ sung tính năng Hiệu đính & Soát lỗi (`/cc hieudinh <số>` hoặc `/cc sualoi <đường_dẫn_file>`)**:
   - Sử dụng script Node.js từ `nd30-sualoi` để trích xuất ngược nội dung từ file `.docx` sang dữ liệu JSON.
   - LLM soát lỗi chính tả, nâng cấp hành văn từ ngôn ngữ nói sang ngôn ngữ hành chính pháp lý.
   - Xuất bản ra **02 phiên bản Word** để người dùng đối chiếu:
     * **Bản Chuẩn hóa (Standard)**: Chỉ sửa lỗi chính tả/máy đánh, giữ nguyên cấu trúc và ý văn (tô đỏ chỗ sửa).
     * **Bản Tối ưu (Optimized)**: Sửa chính tả + viết lại câu từ theo văn phong hành chính cao cấp (tô đỏ các câu/đoạn tối ưu).

---

## 2. Kiến trúc & Phân mảnh Công cụ

```mermaid
graph TD
    subgraph User Interaction (Zalo/Telegram)
        U[User Request] -->|"/cc duthao"| A[Hermes CC Skill]
        U -->|"/cc hieudinh"| A
    end

    subgraph Hermes Container
        A -->|1. Generate JSON Schema| B[congchuc_draft.py / congchuc_editor.py]
        B -->|2. Run Node.js scripts| C[nd30 Core Scripts]
        C -->|3. Compile/Render| D[Microsoft Word File .docx]
    end

    subgraph nd30 Core Scripts
        C1[generate_nd30_docx.js] -->|Drafter| C
        C2[extract_docx.js] -->|Extractor| C
        C3[generate_nd30_editor.js] -->|Editor & Colorizer| C
    end
```

---

## 3. Kế hoạch triển khai chi tiết

### Bước 1: Đồng bộ mã nguồn & Môi trường chạy (Docker)
1. Tận dụng volume mount có sẵn của `d:/Antigravity/xlvp:/opt/xlvp` trong `docker-compose.yml`.
2. Copy 2 thư mục kỹ năng từ `D:\Antigravity\Skill\` vào trong `D:\Antigravity\xlvp\`:
   - `D:\Antigravity\xlvp\nd30-document-drafter`
   - `D:\Antigravity\xlvp\nd30-sualoi`
3. Như vậy, trong container chúng sẽ được truy cập trực tiếp tại `/opt/xlvp/nd30-document-drafter` và `/opt/xlvp/nd30-sualoi` mà không cần thêm bất kỳ cấu hình volume mount mới nào.
4. Chạy `npm install` tại các thư mục này bên trong container để cài đặt đầy đủ các thư viện Node.js phụ thuộc.

### Bước 2: Tích hợp vào tính năng Dự thảo (`congchuc_draft.py`)
1. Cập nhật script `congchuc_draft.py`:
   - Khi nhận dữ liệu text/markdown từ LLM, chuyển đổi nó sang JSON Schema có các trường: `co_quan_chu_quan`, `co_quan_ban_hanh`, `so_ky_hieu`, `can_cu`, `noi_dung`, `noi_nhan`, `chuc_danh_nguoi_ky`, `ten_nguoi_ky`.
    - Ghi dữ liệu ra file tạm `/tmp/nd30_draft_data.json`.
    - Thực thi lệnh sinh Word qua Node.js:
      ```bash
      node /opt/xlvp/nd30-document-drafter/scripts/generate_nd30_docx.js /tmp/nd30_draft_data.json /tmp/Draft_VB_#<so_den>.docx
      ```
    - Tự động đồng bộ và gửi file `.docx` kết quả về Zalo cho sếp.
    - *Lưu ý*: Script đã được tích hợp sẵn cấu hình `footers` tự động đánh số trang (field `PAGE` 13pt) căn giữa ở chân trang cho văn bản nhiều trang, và bắt lỗi rõ ràng (ENOENT, SyntaxError, MODULE_NOT_FOUND).

### Bước 3: Phát triển mới Script Hiệu đính (`congchuc_editor.py`)
1. Tạo script Python mới `skills/cc/scripts/congchuc_editor.py` để điều phối luồng hiệu đính:
   - **Đọc & Trích xuất**: Chạy script Node.js của `nd30-sualoi` để trích xuất file Word gốc:
     ```bash
     node /opt/xlvp/nd30-sualoi/scripts/extract_docx.js <file_input> /tmp/temp_extracted.json
     ```
     (Script đã có thông báo báo lỗi trực quan nếu thiếu package `jszip`, `xml-js` hoặc sai đường dẫn).
   - **Hiệu đính (LLM)**: Đọc file `/tmp/temp_extracted.json`, đưa cho LLM xử lý 2 phiên bản (Standard và Optimized) dựa trên hướng dẫn soát lỗi và nâng cấp câu chữ.
   - **Tạo 2 File Word đối chiếu**: 
     - Ghi dữ liệu hiệu đính ra `data_standard.json` và `data_optimized.json` (set `is_edited: true` ở các mục thay đổi để tô đỏ chữ).
     - Chạy script Node.js sinh Word:
       ```bash
       node /opt/xlvp/nd30-sualoi/scripts/generate_nd30_editor.js /tmp/data_standard.json <File>_Ban_Chuuan_Hoa.docx
       node /opt/xlvp/nd30-sualoi/scripts/generate_nd30_editor.js /tmp/data_optimized.json <File>_Ban_Toi_Uu.docx
       ```
       (Đã đồng bộ bổ sung đánh số trang tự động `PAGE` và các bộ xử lý lỗi).
2. Gửi trả cả 2 file đính kèm này qua Zalo để sếp duyệt.

### Bước 4: Cập nhật hướng dẫn hệ thống (`SKILL.md`)
1. Cập nhật file `skills/cc/SKILL.md` để khai báo thêm lệnh mới:
   - `/cc hieudinh <số_vb>` hoặc `/cc sualoi <đường_dẫn_file>` kèm theo mô tả hành động chi tiết để LLM biết cách gọi `congchuc_editor.py`.

---

## 4. Kế hoạch kiểm thử (Verification Plan)
- **Kiểm thử Soạn thảo**: Chạy thử `/cc duthao 2723` và kiểm tra file Word kết quả. File Word phải có layout chuẩn NĐ 30, căn lề chuẩn, quốc hiệu kẻ bảng ẩn chính xác.
- **Kiểm thử Soát lỗi**: Chọn 1 văn bản nháp có sẵn lỗi chính tả/hành văn thô, chạy thử `/cc sualoi` và kiểm tra 2 file đầu ra xem các chỗ chỉnh sửa đã được tô đỏ nổi bật chính xác hay chưa.
