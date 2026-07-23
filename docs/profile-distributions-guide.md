# Profile Distributions — Hướng dẫn

Nguồn: https://hermes-agent.nousresearch.com/docs/user-guide/profile-distributions

## Giải thích

**Profile Distribution** đóng gói toàn bộ Hermes agent (personality, skills, cron jobs, MCP connections, config) thành một git repository. Người khác cài đặt chỉ với **một lệnh**, cập nhật khi bạn push phiên bản mới. Memories, sessions, API keys của họ không bị ảnh hưởng.

Trước đây: gửi SOUL.md + danh sách skills + config.yaml + MCP servers + cron jobs + hướng dẫn env vars — thủ công, dễ sai.

Với distributions: tất cả trong một git repo.

## Dành cho tác giả (Author) — Đóng gói agent

### Bước 1: Tạo và hoàn thiện profile
```bash
hermes profile create research-bot
research-bot setup
# Chỉnh sửa SOUL.md ~/.hermes/profiles/research-bot/SOUL.md
# Cài skills, kết nối MCP, schedule cron jobs...
research-bot chat  # test cho đến khi ưng ý
```

### Bước 2: Thêm distribution.yaml
Tạo `~/.hermes/profiles/research-bot/distribution.yaml`:
```yaml
name: research-bot
version: 1.0.0
description: "Autonomous research assistant with arXiv and web tools"
hermes_requires: ">=0.12.0"
author: "Your Name"
license: "MIT"
env_requires:
  - name: OPENAI_API_KEY
    description: "OpenAI API key (for model access)"
    required: true
  - name: SERPAPI_KEY
    description: "SerpAPI key for web search"
    required: false
    default: ""
```

### Bước 3: Push lên git repo
```bash
cd ~/.hermes/profiles/research-bot
git init
git add .
git commit -m "v1.0.0"
git remote add origin git@github.com:you/research-bot.git
git tag v1.0.0
git push -u origin main --tags
```

### Bước 4: Tag version mới
Mỗi lần cập nhật, bump version trong `distribution.yaml`, commit & tag:
```bash
# Sửa distribution.yaml: version: 1.1.0
git add distribution.yaml SOUL.md skills/
git commit -m "v1.1.0: tighter SOUL, add arxiv skill"
git tag v1.1.0
git push --tags
```

### Cấu trúc repo distribution
```
research-bot/
├── distribution.yaml            # bắt buộc
├── SOUL.md                      # khuyến nghị
├── config.yaml                  # model, provider, tool defaults
├── mcp.json                     # MCP server connections
├── skills/
│   ├── arxiv-search/SKILL.md
│   └── ...
├── cron/
│   └── weekly-digest.json
└── README.md                    # tuỳ chọn
```

### Distribution-owned vs User-owned
| Category | Paths | Khi update |
|---|---|---|
| **Distribution-owned** | SOUL.md, config.yaml, mcp.json, skills/, cron/, distribution.yaml | Được ghi đè từ bản clone mới |
| **Config override** | config.yaml | Được giữ nguyên (trừ khi dùng `--force-config`) |
| **User-owned** | memories/, sessions/, state.db\*, auth.json, .env, logs/, workspace/, plans/, home/, \*\_cache/, local/ | Không bao giờ động đến |

Có thể ghi đè danh sách distribution-owned trong manifest:
```yaml
distribution_owned:
  - SOUL.md
  - skills/research/
  - cron/digest.json
```

## Dành cho người cài đặt (Installer)

### Cài đặt
```bash
hermes profile install github.com/you/research-bot --alias
```
Quy trình:
1. Clone repo vào thư mục tạm
2. Đọc distribution.yaml, hiển thị manifest
3. Kiểm tra env vars đã có chưa (hiển thị `✓ set` hoặc `needs setting`)
4. Hỏi xác nhận (hoặc dùng `-y` để bỏ qua)
5. Copy distribution-owned files vào `~/.hermes/profiles/research-bot/`
6. Tạo `.env.EXAMPLE` với các keys cần thiết
7. Với `--alias`, tạo wrapper để chạy `research-bot chat` trực tiếp

### Điền API keys
```bash
cp ~/.hermes/profiles/research-bot/.env.EXAMPLE ~/.hermes/profiles/research-bot/.env
# Sửa .env, điền keys thật của bạn
```

### Các nguồn git được hỗ trợ
```bash
# GitHub shorthand
hermes profile install github.com/you/research-bot

# HTTPS
hermes profile install https://github.com/you/research-bot.git

# SSH
hermes profile install git@github.com:you/research-bot.git

# Self-hosted (GitLab, Gitea, Forgejo...)
hermes profile install https://git.example.com/team/research-bot.git

# Private repo (dùng git auth hiện tại)
hermes profile install git@github.com:your-org/internal-bot.git

# Local directory (test trước khi push)
hermes profile install ~/my-profile-in-progress/
```

### Override tên profile
```bash
hermes profile install github.com/acme/support-bot --name support-us --alias
```

### Kiểm tra thông tin
```bash
hermes profile info research-bot
# Hiển thị: version, description, author, source, env vars...
```

### Cập nhật
```bash
hermes profile update research-bot
# Ghi đè distribution-owned files
# Giữ nguyên config.yaml (trừ --force-config)
# Không động đến memories, sessions, auth, .env, logs, state
```

### Gỡ bỏ
```bash
hermes profile delete research-bot
# Hiển thị thông tin distribution trước khi xác nhận
```

## Use cases

### Cá nhân: đồng bộ agent giữa các máy
```bash
# Laptop
cd ~/.hermes/profiles/research-bot
git init && git add . && git commit -m "initial"
git remote add origin git@github.com:you/research-bot.git
git push -u origin main

# Workstation
hermes profile install github.com/you/research-bot --alias
cp .../.env.EXAMPLE .../.env  # điền keys
```
Memories riêng biệt mỗi máy — không va chạm.

### Team: agent nội bộ
```bash
# Lead tạo và push lên GitLab nội bộ
hermes profile install git@gitlab.internal:team/pr-reviewer.git --alias
# Mỗi engineer điền API key riêng, update khi lead tag bản mới
```

### Cộng đồng: publish public agent
```bash
hermes profile install github.com/you/hermes-polymarket-trader --alias
```
Tweet lệnh cài đặt. Ai muốn custom thì fork repo.

## An toàn
- **auth.json, .env, memories/, sessions/, logs/, workspace/** — KHÔNG BAO GIỜ được đóng gói, kể cả khi author vô tình ship chúng
- Cron jobs từ distribution **không tự động chạy** — installer phải enable thủ công
- Distributions không có chữ ký số (mặc định). Đọc SOUL.md và skills trước khi chạy nếu cài từ nguồn không quen.
