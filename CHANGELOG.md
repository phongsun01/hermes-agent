# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased] - 2026-07-07

### Added
- **News Skill**: Implemented the unified `news` skill under `skills/news/` supporting `/news` and `/newsmenu` slash commands.
- **Tide Forecast Support**: Added `/news trieucuong` command with automated tide-forecast.com scraper for coastal provinces.
- **Wikipedia Historical Events Scraper**: Added `/news today` command scraping Vietnamese and World historical anniversaries dynamically from Wikipedia.

### Changed
- **Briefing Scripts Consolidation**: Grouped and cleaned up custom briefing scripts (`weather_quangninh.py`, `lunar_convert.py`, `gia_hang_hoa_sang.py`, `zalo_morning_brief.py`) into the unified `scripts/news/` directory.
- **CLI & Telegram Gateway Interception**: Registered `/news` and `/newsmenu` in `hermes_cli/commands.py`, `cli.py`, and `gateway/platforms/telegram.py` with inline keyboard buttons.
- **Windows Emoji Encoding Fix**: Reconfigured stdout to UTF-8 on Windows for `gia_hang_hoa_sang.py` and `weather_quangninh.py`.

## [Unreleased] - 2026-07-06


### Added
- **Zalo Morning Briefing Script**: Created [zalo_morning_brief.py](file:///D:/Antigravity/Hermes/scripts/zalo/zalo_morning_brief.py) to fetch Vietnamese lunar date, local commemorative holidays, domestic RSS feeds, and daily quiz.
- **Vietnamese Lunar Calendar Library**: Imported [lunar_convert.py](file:///D:/Antigravity/Hermes/scripts/lunar_convert.py) to compute Vietnamese lunar date.
- **MSC (Mua Sắm Công) Bidding Skill**: Integrated the MSC skill under `skills/productivity/msc/` to enable searching public procurement information and monitoring watchlists.
- **Docker wheels directory**: Created `docker/wheels` dummy directory to fix Docker compilation issue.
- **README for Migrated Features**: Added `README_MIGRATED_FEATURES.md` detailing the newly deployed features.

### Changed
- **Telegram Platform Adapter**: Patched [telegram.py](file:///D:/Antigravity/Hermes/gateway/platforms/telegram.py) to intercept `/cronmenu` and `/mscmenu` commands and handle `hx:cron:` and `v1|msc|` callbacks.
- **Cron Jobs Configuration**: Merged the preconfigured jobs for Zalo morning briefing and MSC watchlists into `jobs.json`.
- **Cross-Platform Compatibility**: Enhanced command execution to use `sys.executable` for python subprocesses instead of hardcoded `python3`, ensuring compatibility with both Windows and Linux/Docker/WSL.
- **Windows Console output fix**: Modified [msc_mvp_router.py](file:///D:/Antigravity/Hermes/skills/productivity/msc/lib/msc_mvp_router.py) to configure stdout with UTF-8 encoding on Windows to prevent `UnicodeEncodeError`.
