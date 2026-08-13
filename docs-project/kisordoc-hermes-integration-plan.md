# Hermes Skill cho KisorDoc — Implementation Plan (v2)

> Ngày tạo: 2026-08-13

## Tổng quan

Tích hợp KisorDoc vào Hermes dưới dạng một **Skill thuần** (`skills/productivity/kisordoc/`). 
Loại bỏ hoàn toàn tầng **Plugin**, chuyển toàn bộ logic tương tác HTTP, polling, và parsing kết quả vào script client chạy độc lập.

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
Subprocess/Python Script: python skills/productivity/kisordoc/scripts/kisordoc_client.py <action>
    │
    ▼
KisorDoc FastAPI (mặc định http://host.docker.internal:8000 trong Docker hoặc http://localhost:8000)
    │
    ▼
kisorlib  →  File DOCX output tại {ProjectPath}/3. Files/
```

---

## Cấu trúc file

```
D:\Antigravity\Hermes\
└── skills/productivity/kisordoc/
    ├── SKILL.md
    └── scripts/
        └── kisordoc_client.py
```

---

## Danh sách các Action của `kisordoc_client.py`

| Action | HTTP Method | Endpoint | Ghi chú |
|---|---|---|---|
| list-options | GET | /options | Liệt kê các quy trình |
| list-packages | GET | /packages?option=X | Trả về danh sách gói thầu (chỉ có ID) |
| list-templates | GET | /templates?option=X | Liệt kê các template Word |
| generate | POST+poll | /generate + /jobs/{id} | Tạo job, tự động poll và trả kết quả |
| list-jobs | GET | /jobs | Liệt kê các job gần đây |

## Biến môi trường

| Biến | Mặc định | Mô tả |
|---|---|---|
| KISORDOC_API_URL | http://host.docker.internal:8000 | URL của KisorDoc FastAPI |
| KISORDOC_POLL_INTERVAL | 2 | Thời gian chờ giữa các lần poll (giây) |
| KISORDOC_TIMEOUT | 300 | Thời gian timeout tối đa của job (giây) |
