# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased] - 2026-07-24

### Security
- **MSC Subprocess Security Hardening**: Removed `--token` and `--cookie` flags from subprocess command-line arguments in all remaining scripts (`msc_exp_khlcnt.py`, `msc_expt_tbmt.py`, `msc_exp_unified.py`, `msc_hidden_api_counts.py`, `msc_hidden_api_daily_report.py`, `msc_khlcnt_detail.py`, `msc_tbmt_detail.py`, `msc_watchlist_latest_tbmt.py`), fully migrating them to environment variables.
- **Secure curl Invocations**: Reconfigured `msc_hidden_api_counts.py` to use secure stdin config via `curl --config -`.

### Changed
- **Script Path Resolution**: Dynamically resolved LOOKUP_SCRIPT and DETAIL_SCRIPT script paths relative to their parent directories instead of using hardcoded relative paths.

## [Unreleased] - 2026-07-21

### Added
- **Outgoing Dispatch Tracking**: Added `/cc theodoi <số>` (or `/cc watch <số>`) command to register dispatches for real-time monitoring. Integrated a `🔔 Theo dõi VB đi` button into the root `/ccmenu` layout.

### Security
- **MSC Skill Security Hardening**: Secured Mua Sam Cong (MSC) credentials by removing `--token` and `--cookie` flags from command-line arguments (argv) across all subprocesses (`msc_mvp_router.py`) and migrating them to secure environment variables (`os.environ`).
- **Secure curl Invocations**: Reconfigured 8 lookup and detail sub-scripts (`msc_pl_lookup.py`, `msc_ib_lookup.py`, `msc_tbmt_precise.py`, `msc_kh_precise.py`, `msc_tbmt_detail.py`, `msc_khlcnt_detail.py`, `msc_bid_pricing_search.py`, `msc_hidden_api_list.py`) to read sensitive `url` and `Cookie`/`Authorization` parameters via stdin using `curl --config -`.
- **FastAPI Token Service Auth**: Implemented loopback-binding requirement checks and `secrets.compare_digest` for secure service key verification in `msc_token_service.py`.

### Changed
- **CC Skill Remote Actions Verify**: Sửa lỗi false-positive Kết thúc/Chuyển thông qua việc re-navigate lại grid bằng hàm dùng chung `find_row` (whitespace-insensitive matching) và kiểm chứng VB thực sự biến mất khỏi grid.
- **Safe Subprocess Cleanups**: Bọc khối rename screenshot và update_status cục bộ trong try/except nội bộ để tránh lỗi đĩa/phân quyền lật ngược kết quả portal đã thành công thành báo lỗi giả.
- **File Locking State Management**: Giải quyết race condition ghi đè tệp state `vbden_state.json` bằng cơ chế khóa tệp tin `fcntl.flock` bao quanh chu kỳ load-modify-save, tự động tạo thư mục cha chứa tệp lock để tránh FileNotFoundError.
- **Update status API**: Tinh giản API `update_status` loại bỏ đối số `state` thừa, tự động khóa và load lại tệp state, bổ sung tích lũy note có giới hạn độ dài tối đa 500 ký tự.
- **Playwright Robustness**: Dời check login lỗi xuống sau trang cảnh báo mật khẩu để bắt được lỗi redirect xác thực.
- **Router wrapper**: Replaced duplicate script `scripts/msc_mvp_router.py` with a forwarding wrapper to prevent code drift.
- **Dynamic Path Resolution**: Configured `telegram_menu_bridge.py` to resolve `ROUTER` path dynamically based on `SKILL_ROOT`.
- **Timeout Translation**: Integrated subprocess timeout catches inside `dispatcher.py` to raise standard `TimeoutError`.

## [Unreleased] - 2026-07-08

### Added
- **MSC Bidding History**: Added contractor bidding history query command (`msc ls <MST>` or `/msc ls <MST>`) fetching detailed list of past bidding participations (notify number, bid price, win price, results) via Chrome CDP.
- **Contractor Bidding History script**: Created [msc_contractor_history.py](file:///d:/Antigravity/Hermes/skills/productivity/msc/scripts/msc_contractor_history.py) to execute authenticated browser-context fetches.
- **Developer Guide**: Added [docs/skill-inline-menu-guide.md](file:///d:/Antigravity/Hermes/docs/skill-inline-menu-guide.md) to document the end-to-end design and implementation workflow for skill-based inline button menus on Telegram/Zalo.
- **MSC Contractor Analysis**: Integrated contractor opportunity analysis (`msc ptnt <MST>` or `/msc ptnt <MST>`) fetching and rendering detailed bidding statistics (win/loss rate, savings, mixed bids) from the private MSC API.
- **Contractor Analysis script**: Created [msc_contractor_analysis.py](file:///d:/Antigravity/Hermes/skills/productivity/msc/scripts/msc_contractor_analysis.py) for opportunity analysis queries.

### Changed
- **MSC Inline Menu (`/mscmenu`)**: Added "📜 Lịch sử NT" and "📊 Phân tích NT" buttons on root menu and designed their respective submenus.
- **Router level mapping**: Integrated `'msc_ptnt'` and `'msc_hisbid'`/`'msc_ls'` callbacks in level mapping on both [lib/msc_mvp_router.py](file:///d:/Antigravity/Hermes/skills/productivity/msc/lib/msc_mvp_router.py) and [scripts/msc_mvp_router.py](file:///d:/Antigravity/Hermes/skills/productivity/msc/scripts/msc_mvp_router.py).
- **Dotenv encoding fix**: Specified UTF-8 encoding when reading `.env` configuration files inside `_load_dotenv` to avoid UnicodeDecodeError on Windows systems.

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
