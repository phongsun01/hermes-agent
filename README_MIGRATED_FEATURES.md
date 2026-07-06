# Migrated & Deployed Features for Hermes Agent

This document summarizes the custom features deployed and integrated into this Hermes Agent repository.

## 1. Telegram `/cronmenu` Command
A Telegram UI wrapper around Hermes cron jobs allowing users to manage scheduled tasks directly from Telegram chat via an inline keyboard.
* **Command:** Send `/cronmenu` in Telegram to open the Cron Controls board.
* **Options:**
  * `📋 List cron`: Lists active cron jobs (top 10), including their schedule, enablement status, next run time, and last status.
  * `🔄 Refresh`: Refreshes the cron job list.
  * `🔙 Back`: Returns to the main menu.
  * Manually trigger any job via `hx:cron:run:<job_id>` callbacks.

## 2. Zalo Morning Briefing & Vietnamese Lunar Calendar
A scheduled cron job running daily at **06:10 AM VN Time** (`10 6 * * *`) that compiles a morning update and delivers it to the Zalo group **Bi bống house** (`zalo:3339712927031818889`).
* **Script:** [zalo_morning_brief.py](file:///D:/Antigravity/Hermes/scripts/zalo/zalo_morning_brief.py)
* **Features Included:**
  * Vietnam Lunar Calendar date conversion (via `lunar_convert.py`).
  * Check for local/national commemorative holidays.
  * Vietnam domestic news feeds (3 latest articles from VnExpress, Tuổi Trẻ, Thanh Niên, VietnamNet, Lao Động).
  * A deterministic daily quiz (puzzle rotation).
  * Excludes duplicate information (such as weather and gasoline prices).

## 3. Mua Sắm Công (MSC) Skill
A specialized Hermes productivity skill and `/msc` slash command to search and monitor public procurement and bidding information from the Vietnamese Procurement Portal (https://muasamcong.mpi.gov.vn).
* **Location:** `skills/productivity/msc/`
* **Features:**
  * Intent routing for bidding queries.
  * Deterministic canary deployment configuration.
  * SQLite database support (`msc.sqlite3`) for watchlist monitoring of up to 30 units.
  * Telegram callback hooks (`v1|msc|` callbacks) and `/mscmenu` command intercept.
  * Cross-platform optimization using `sys.executable` execution path for both Windows and WSL/Docker containers.
