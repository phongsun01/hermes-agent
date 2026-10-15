# Kế hoạch triển khai: F9 — Dự thảo văn bản trả lời với LightRAG

Mục tiêu: Thay thế Onyx RAG bằng LightRAG để tăng chất lượng dự thảo văn bản trả lời tự động qua Zalo (chuẩn Nghị định 30).

## User Review Required

- **Xác nhận Model LLM**: Trong file `.env.lightrag`, LLM dùng cho entity extraction đang set là `gpt-4o-mini`. Để tiết kiệm chi phí, có thể cân nhắc dùng `gemini-2.5-flash` qua OpenAI-compatible endpoint. (Mặc định sẽ triển khai `gpt-4o-mini` theo tài liệu).
- **Zalo Trigger Regex**: Regex hiện tại là `^(dự thảo|du thao|draft)\s+(\d+)`, nếu có cần điều chỉnh gì vui lòng bổ sung.
- **Port LightRAG**: 9621, chạy qua Docker trên host hiện tại.

## Proposed Changes

### Docker & Config (Phase 0)

*Môi trường triển khai: Triển khai trực tiếp trên server hiện tại.*

#### [MODIFY] docker-compose.yml
- Bổ sung service `lightrag` sử dụng image `ghcr.io/hkuds/lightrag:latest`.
- Map port 9621, volume `lightrag_data`, và load env từ `.env.lightrag`.

#### [NEW] .env.lightrag
- Tạo file cấu hình chứa API key OpenAI, binding host, model (mặc định OpenAI + text-embedding-3-small).

#### [MODIFY] .env
- Thêm các biến môi trường cho việc drafting: `LIGHTRAG_API_URL`, `LIGHTRAG_API_KEY`, `CONGVAN_DRAFT_MODE`, `CONGVAN_ORG_NAME`, v.v.

---

### Scripts & Logic (Phase 1 & Phase 2)

#### [NEW] scripts/lightrag/ingest_corpus.py
- Script Python hỗ trợ đẩy hàng loạt files `.pdf, .docx, .md` vào LightRAG (Dùng để ingest templates, văn bản cũ).
- **Tích hợp `boc-tach-pdf-v1.0`:** Script `ingest_corpus.py` được thiết kế để tự động nhận dạng file Markdown sinh ra từ skill `bóc tách pdf`. Khi gặp file PDF mờ/scan, người dùng sử dụng skill `bóc tách pdf` để xuất ra file Markdown chuẩn layout NĐ 30. Sau đó, chạy `ingest_corpus.py` để nạp file Markdown này vào LightRAG nhằm đảm bảo nội dung và bảng biểu được LLM hiểu chính xác 100% thay vì dùng PDF OCR thông thường.

#### [MODIFY] scripts/congchuc/congchuc_scrape.py
- Cập nhật luồng tải attachment (F16a) để tự động gọi API `upload` của LightRAG ngay sau khi file được tải về.

#### [NEW] scripts/congchuc/congchuc_draft.py
- Script nhận `so_den` từ Zalo, tìm metadata, trích xuất text từ PDF/DOCX.
- Query LightRAG lấy context, gọi OpenAI tạo Markdown chuẩn.
- Gọi script `convert_md_to_docx.py` để ra file Word cuối cùng gửi người dùng.

#### [MODIFY] docs/xu-ly-van-phong-v1.0/scripts/convert/convert_md_to_docx.py
- **Hiện trạng:** Đã kiểm tra file này, script đang sử dụng thư viện `python-docx` để format cơ bản, nhưng chưa có logic chia 2 cột cho Header NĐ 30.
- **Giải pháp:** Bổ sung logic nhận diện Header chuẩn NĐ 30 và tạo bảng ẩn (table 2 cột, no border) bằng `python-docx` để phân bổ Quốc hiệu/Tiêu ngữ và Tên cơ quan đúng thể thức. Do đã dùng sẵn `python-docx`, công việc chỉ là bổ sung hàm xử lý, không phải đập đi viết lại từ đầu (không phải viết lại từ Pandoc wrapper thuần).

---

### Tích hợp Zalo & Cron (Phase 3)

#### [MODIFY] scripts/congchuc/update_cron_jobs.py
- Thêm job `f9-draft` dạng trigger `zalo_command` vào danh sách `new_jobs` để cập nhật file `/opt/data/cron/jobs.json`.

#### [UPDATE] Cơ chế gửi file qua Zalo (Thay cho Link tải)
- Quá trình kiểm tra mã nguồn `hermes-zalo-plugin` cho thấy plugin có hỗ trợ endpoint `POST /send-attachment`.
- Thay vì cấu hình web server (port 8642) và gửi link tải (không hoạt động với mobile do localhost), script `congchuc_draft.py` sẽ được cập nhật để lấy `chat_id` và trực tiếp gọi API `http://localhost:8787/send-attachment` của Zalo plugin để đẩy thẳng file DOCX vào cuộc trò chuyện.

## Verification Plan

### Automated Tests
- Chạy `python scripts/lightrag/ingest_corpus.py --help` để đảm bảo script import không lỗi.
- Kiểm tra trạng thái LightRAG bằng `curl http://localhost:9621/health` (sau khi start container).

### Manual Verification
- Chạy thử lệnh ingest một template NĐ 30 mẫu để xem LightRAG có nhận không.
- **Kiểm tra CLI độc lập:** Chạy lệnh `python scripts/congchuc/congchuc_draft.py --so-den 2348` để đảm bảo luồng script chạy đúng, gọi LightRAG/OpenAI và tạo ra file DOCX thành công, dễ khoanh vùng debug trước khi cắm vào Zalo.
- Thử gửi Zalo `dự thảo 2348` (với 1 số đến thực tế đã được cào) và kiểm tra file DOCX trả về xem format 2 cột đã xử lý tốt chưa.
