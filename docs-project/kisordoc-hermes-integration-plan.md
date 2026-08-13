# Hermes Skill cho KisorDoc — Implementation Plan

> Ngày tạo: 2026-08-13

## Tổng quan

Tích hợp KisorDoc vào Hermes dưới dạng một **Skill** (`skills/productivity/kisordoc/`)
kết hợp với một **Hermes Plugin** (`plugins/kisordoc/`).

- **Skill** → dạy Hermes nghiệp vụ, cách parse lệnh, cách diễn giải kết quả
- **Plugin** → cung cấp các tool gọi trực tiếp KisorDoc FastAPI (`http://localhost:8000`)

Hai thành phần phối hợp: Skill gọi các tool do Plugin đăng ký, tool gọi API, trả JSON về cho Hermes tổng hợp trả lời.

---

## Kiến trúc

```
Người dùng (Zalo/CLI)
    │
    ▼
Hermes Agent
    │  đọc SKILL.md (khi user nói đến kisordoc/sinh văn bản/hồ sơ thầu)
    │
    ▼
Plugin tools (plugins/kisordoc/)
    ├── kisordoc_list_options   → GET  /options
    ├── kisordoc_list_packages  → GET  /packages?option=Opt1
    ├── kisordoc_list_templates → GET  /templates?option=Opt1
    ├── kisordoc_generate       → POST /generate  (tạo job, poll đến done/failed)
    └── kisordoc_job_status     → GET  /jobs/{job_id}  (poll thủ công nếu cần)
    │
    ▼
KisorDoc FastAPI  (localhost:8000 hoặc host.docker.internal:8000)
    │
    ▼
kisorlib  →  File DOCX output tại {ProjectPath}/3. Files/
```

---

## Cấu trúc file sẽ tạo

```
D:\Antigravity\Hermes\
├── skills/productivity/kisordoc/
│   ├── SKILL.md
│   └── scripts/
│       └── kisordoc_client.py
│
└── plugins/kisordoc/
    ├── plugin.yaml
    └── __init__.py
```

---

## 5 Plugin Tools

| Tool | Method | Endpoint | Mô tả |
|---|---|---|---|
| kisordoc_list_options | GET | /options | Liệt kê quy trình |
| kisordoc_list_packages | GET | /packages?option=X | Liệt kê gói thầu |
| kisordoc_list_templates | GET | /templates?option=X | Liệt kê template |
| kisordoc_generate | POST+poll | /generate + /jobs/{id} | Sinh văn bản, chờ xong |
| kisordoc_job_status | GET | /jobs/{job_id} | Kiểm tra trạng thái job |

## Biến môi trường

| Biến | Mặc định | Mô tả |
|---|---|---|
| KISORDOC_API_URL | http://localhost:8000 | Base URL KisorDoc API |
| KISORDOC_POLL_INTERVAL | 2 | Giây giữa các lần poll |
| KISORDOC_TIMEOUT | 300 | Timeout tổng (giây) |

## Các file sẽ tạo (không sửa KisorDoc)

- [NEW] plugins/kisordoc/plugin.yaml
- [NEW] plugins/kisordoc/__init__.py
- [NEW] skills/productivity/kisordoc/SKILL.md
- [NEW] skills/productivity/kisordoc/scripts/kisordoc_client.py
