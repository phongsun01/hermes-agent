# HÆ°á»›ng dáº«n & Nháº­t kÃ½ Váº­n hÃ nh Hermes Desktop trÃªn Windows

> **TÃ i liá»‡u tá»•ng há»£p:** Ghi chÃ©p chi tiáº¿t toÃ n bá»™ quÃ¡ trÃ¬nh sao lÆ°u, cáº­p nháº­t upstream, cÃ i Ä‘áº·t á»©ng dá»¥ng Hermes Desktop tá»« source, káº¿t ná»‘i 9router, kháº¯c phá»¥c lá»—i xÃ¡c thá»±c 401 vÃ  Ä‘á»“ng bá»™ dá»¯ liá»‡u (Skills, Plugins) tá»« mÃ´i trÆ°á»ng Docker sang Desktop.

---

## ðŸ“Œ 1. Kiáº¿n trÃºc lÆ°u trá»¯: Docker vs Desktop

Hermes Agent trÃªn Windows quáº£n lÃ½ 2 phÃ¢n vÃ¹ng dá»¯ liá»‡u khÃ¡c nhau tÃ¹y theo mÃ´i trÆ°á»ng cháº¡y:

| MÃ´i trÆ°á»ng | ThÆ° má»¥c Home (`HERMES_HOME`) | Má»¥c Ä‘Ã­ch |
|---|---|---|
| **Hermes Docker** | `C:\Users\<User>\.hermes\` | Ãnh xáº¡ vÃ o volume `/opt/data` trong container. Chá»©a sessions, `.env`, config cá»§a Docker bot (Zalo, Telegram, Cron...). |
| **Hermes Desktop** | `C:\Users\<User>\AppData\Local\hermes\` | ThÆ° má»¥c chuáº©n cá»§a á»©ng dá»¥ng Desktop native vÃ  CLI host. LÆ°u trá»¯ sessions vÃ  cáº¥u hÃ¬nh cá»§a Desktop app. |
| **Source Code** | `D:\Antigravity\Hermes\` | MÃ£ nguá»“n git, repo Hermes Agent, client desktop Electron/React (`apps/desktop`). |
| **ThÆ° má»¥c Backup** | `D:\Antigravity\Hermes-backup\<YYYY-MM-DD>\` | NÆ¡i lÆ°u trá»¯ cÃ¡c báº£n snapshot dá»¯ liá»‡u trÆ°á»›c cÃ¡c Ä‘á»£t nÃ¢ng cáº¥p lá»›n. |

---

## ðŸ’¾ 2. Quy trÃ¬nh Backup & Update Hermes Agent

### BÆ°á»›c 2.1: Sao lÆ°u toÃ n diá»‡n (Full Backup)
TrÆ°á»›c khi nÃ¢ng cáº¥p, toÃ n bá»™ dá»¯ liá»‡u Ä‘Æ°á»£c Ä‘Ã³ng gÃ³i vÃ o `D:\Antigravity\Hermes-backup\2026-11-04\`:
* **`hermes-userdata.tar.gz` (~188 MB):** Chá»©a `.env`, `config.yaml`, cÆ¡ sá»Ÿ dá»¯ liá»‡u SQLite (`state.db`, `response_store.db`, `kanban.db`), custom skills, memories, plans (loáº¡i trá»« cÃ¡c thÆ° má»¥c cache, temp vÃ  socket lock).
* **`hermes-repo.bundle` (~1.01 GB):** ToÃ n bá»™ lá»‹ch sá»­ commit, táº¥t cáº£ cÃ¡c nhÃ¡nh vÃ  mÃ£ nguá»“n cá»§a repo Hermes dÆ°á»›i dáº¡ng git bundle hoÃ n chá»‰nh.

### BÆ°á»›c 2.2: Äá»“ng bá»™ báº£n cáº­p nháº­t má»›i nháº¥t tá»« Upstream
1. LÆ°u táº¡m cÃ¡c chá»‰nh sá»­a Ä‘ang dá»Ÿ dang báº±ng `git stash`.
2. KÃ©o code má»›i nháº¥t tá»« `upstream/main` (`NousResearch/hermes-agent`):
   ```bash
   git fetch upstream main
   git merge upstream/main
   ```
3. Xá»­ lÃ½ xung Ä‘á»™t táº¡i [Dockerfile](file:///d:/Antigravity/Hermes/Dockerfile): Giá»¯ nguyÃªn Ä‘Æ°á»ng dáº«n `/command` cáº§n thiáº¿t cho Docker trÃªn Windows song song vá»›i cÃ¡c biáº¿n mÃ´i trÆ°á»ng PATH má»›i cá»§a upstream.
4. KhÃ´i phá»¥c láº¡i cÃ¡c file Ä‘ang lÃ m viá»‡c dá»Ÿ dang báº±ng `git stash pop`.
5. Khá»Ÿi Ä‘á»™ng láº¡i há»‡ thá»‘ng Docker container:
   ```powershell
   docker compose up -d
   ```

---

## ðŸ–¥ï¸ 3. CÃ i Ä‘áº·t & Build Hermes Desktop tá»« Source

### 3.1. YÃªu cáº§u & Dá»± toÃ¡n dung lÆ°á»£ng
* **YÃªu cáº§u mÃ´i trÆ°á»ng:** Node.js (>= v24), npm, PowerShell.
* **Dung lÆ°á»£ng tiÃªu tá»‘n:**
  * Node modules & build cache: ~800 MB â€“ 1.2 GB.
  * Electron binary (v44.9.3): ~250 MB.
  * Báº£n build hoÃ n chá»‰nh: ~300 MB.
  * **Tá»•ng cá»™ng:** Khoáº£ng **1.5 GB â€“ 2 GB**.

### 3.2. QuÃ¡ trÃ¬nh CÃ i Ä‘áº·t & Build
1. **CÃ i Ä‘áº·t thÆ° viá»‡n á»Ÿ thÆ° má»¥c gá»‘c:**
   ```powershell
   cd D:\Antigravity\Hermes
   npm install --engine-strict=false
   ```
2. **BiÃªn dá»‹ch Desktop Renderer & Electron Main:**
   ```powershell
   cd D:\Antigravity\Hermes\apps\desktop
   npm run build
   node scripts/bundle-electron-main.mjs --dev
   ```
3. **Shortcut khá»Ÿi cháº¡y Desktop:**
   ÄÃ£ táº¡o shortcut **`Hermes Desktop`** ngoÃ i mÃ n hÃ¬nh mÃ¡y tÃ­nh (`Desktop`). Lá»‡nh cháº¡y ngáº§m chuáº©n xÃ¡c:
   ```cmd
   cmd.exe /c "start "" /d "D:\Antigravity\Hermes\apps\desktop" "D:\Antigravity\Hermes\node_modules\electron\dist\electron.exe" "D:\Antigravity\Hermes\apps\desktop""
   ```

---

## ðŸ”Œ 4. Cáº¥u hÃ¬nh Káº¿t ná»‘i 9router & Sá»­a lá»—i 401

### 4.1. ThÃ´ng sá»‘ káº¿t ná»‘i 9router trÃªn Host Windows
* **Port 9router:** `20128` (cháº¡y qua tiáº¿n trÃ¬nh Node.js trÃªn mÃ¡y).
* **API Key:** `sk-52322c0dd90d1c8a-2iry8g-ebb67c15` (Key `hermes-key` cáº¥u hÃ¬nh trong `AppData\Roaming\9router\db.json`).
* **Endpoint Base URL:** `http://127.0.0.1:20128/v1` *(LÆ°u Ã½: KhÃ´ng dÃ¹ng `host.docker.internal` vÃ¬ Desktop cháº¡y trá»±c tiáº¿p trÃªn Windows, khÃ´ng pháº£i bÃªn trong container)*.
* **Model khuyáº¿n nghá»‹:** `9router-combo`, `hermes-combo`, hoáº·c `claude-opus-4-6`.

### 4.2. Kháº¯c phá»¥c lá»—i "HTTP 401: Invalid API key"
* **NguyÃªn nhÃ¢n:** Trong file `C:\Users\Desktop\AppData\Local\hermes\config.yaml`, má»¥c `custom_providers` trÆ°á»›c Ä‘Ã³ bá»‹ cáº¥u hÃ¬nh nháº§m giÃ¡ trá»‹ cá»§a `api_key` thÃ nh chuá»—i URL (`api_key: http://localhost:20128/v1`), dáº«n Ä‘áº¿n header `Authorization` gá»­i sang 9router khÃ´ng há»£p lá»‡.
* **CÃ¡ch kháº¯c phá»¥c:**
  1. Cáº­p nháº­t láº¡i giÃ¡ trá»‹ key chÃ­nh xÃ¡c vÃ o `config.yaml`:
     ```yaml
     model:
       default: 9router-combo
       provider: custom
       base_url: http://127.0.0.1:20128/v1
       api_mode: chat_completions
       api_key: sk-52322c0dd90d1c8a-2iry8g-ebb67c15
     
     custom_providers:
       - name: Local (localhost:20128)
         base_url: http://127.0.0.1:20128/v1
         api_key: sk-52322c0dd90d1c8a-2iry8g-ebb67c15
         model: 9router-combo
     ```
  2. Bá»• sung `CUSTOM_API_KEY=sk-52322c0dd90d1c8a-2iry8g-ebb67c15` vÃ o `C:\Users\Desktop\AppData\Local\hermes\.env`.
  3. Khá»Ÿi Ä‘á»™ng láº¡i gateway:
     ```powershell
     hermes gateway restart
     ```

---

## ðŸ”„ 5. Äá»“ng bá»™ Skills & Plugins tá»« Docker sang Desktop

VÃ¬ Docker dÃ¹ng thÆ° má»¥c `C:\Users\Desktop\.hermes\` cÃ²n Desktop dÃ¹ng `C:\Users\Desktop\AppData\Local\hermes\`, cáº§n Ä‘á»“ng bá»™ cÃ¡c thÆ° má»¥c chá»©c nÄƒng:

### 5.1. Lá»‡nh Ä‘á»“ng bá»™ tá»± Ä‘á»™ng (PowerShell)
```powershell
# 1. Äá»“ng bá»™ Skills (cc, vietlott, news, xs, tvpl...)
robocopy "C:\Users\Desktop\.hermes\skills" "C:\Users\Desktop\AppData\Local\hermes\skills" /E /XC /XN /XO /NP /R:1 /W:1 /XD .git

# 2. Äá»“ng bá»™ Plugins (zalo-platform, xsmb, kanban, memory, 40+ model providers...)
robocopy "C:\Users\Desktop\.hermes\plugins" "C:\Users\Desktop\AppData\Local\hermes\plugins" /E /XC /XN /XO /NP /R:1 /W:1 /XD .git __pycache__
```

### 5.2. Káº¿t quáº£ kiá»ƒm tra
* Lá»‡nh `hermes skills list` trÃªn Desktop nháº­n diá»‡n Ä‘áº§y Ä‘á»§ **85 skills** á»Ÿ tráº¡ng thÃ¡i `enabled`.
* Lá»‡nh `hermes plugins list` nháº­n diá»‡n Ä‘áº§y Ä‘á»§ táº¥t cáº£ plugin tÃ­ch há»£p (`zalo-platform`, `xsmb`, `kanban`...).

---

## ðŸš€ 6. HÆ°á»›ng dáº«n khá»Ÿi Ä‘á»™ng hÃ ng ngÃ y

1. Äáº£m báº£o **9router** Ä‘ang cháº¡y táº¡i cá»•ng `20128`.
2. Má»Ÿ á»©ng dá»¥ng **Hermes Desktop** báº±ng cÃ¡ch nháº¥p Ä‘Ãºp vÃ o biá»ƒu tÆ°á»£ng trÃªn Desktop (hoáº·c cháº¡y tá»« PowerShell / CMD).
3. Chat bÃ¬nh thÆ°á»ng trá»±c tiáº¿p trÃªn giao diá»‡n cá»­a sá»• trá»±c quan. Má»i tin nháº¯n sáº½ Ä‘Æ°á»£c gateway local xá»­ lÃ½ vÃ  gá»­i sang 9router vá»›i Ä‘áº§y Ä‘á»§ reasoning stream.



---

## ⏰ 5.3. Đồng bộ toàn bộ Cron Jobs & Tác vụ Lịch trình

Ngoài Skills và Plugins, Hermes lưu trữ tác vụ lập lịch (cron) tại cron/jobs.json, các kịch bản chạy tại scripts/, file mẫu báo cáo và file đính kèm công văn tại cron/:

### Lệnh đồng bộ tự động sang Desktop:
`powershell
# 1. Đồng bộ kịch bản thực thi cron (scripts)
robocopy "C:\Users\Desktop\.hermes\scripts" "C:\Users\Desktop\AppData\Local\hermes\scripts" /E /XC /XN /XO /NP /R:1 /W:1 /XD .git __pycache__

# 2. Đồng bộ đính kèm công văn và thư mục output của cron
robocopy "C:\Users\Desktop\.hermes\cron\cong-van-den" "C:\Users\Desktop\AppData\Local\hermes\cron\cong-van-den" /E /XC /XN /XO /NP /R:1 /W:1
robocopy "C:\Users\Desktop\.hermes\cron\cong-van-di" "C:\Users\Desktop\AppData\Local\hermes\cron\cong-van-di" /E /XC /XN /XO /NP /R:1 /W:1
robocopy "C:\Users\Desktop\.hermes\cron\output" "C:\Users\Desktop\AppData\Local\hermes\cron\output" /E /XC /XN /XO /NP /R:1 /W:1

# 3. Đồng bộ template báo cáo
Copy-Item "C:\Users\Desktop\.hermes\cron\CRON_REPORT_TEMPLATE.md" "C:\Users\Desktop\AppData\Local\hermes\cron\CRON_REPORT_TEMPLATE.md" -Force
`

Sau khi đồng bộ, lệnh hermes cron list trên Desktop hiển thị đầy đủ tất cả các tác vụ:
* **Công văn:** Quét công văn đến/đi, Báo cáo tuần/tháng, Kiểm tra quá hạn, Dự thảo văn bản F9.
* **Đời sống & Tin tức:** Giá xăng vàng tỷ giá sáng, Thời khóa biểu sáng/tối (TKB), Postcard tối Bi Bống.
* **Xổ số:** XSMB hôm nay (kết quả & dự đoán LSTM/Pascal), KQ Vietlott Mega 6/45.
* **Bản tin AI:** Tin AI hot 7h/8h30 sáng, Bản tin sáng Zalo.
