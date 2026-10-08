import json
import os

path = os.environ.get("CRON_JOBS_FILE", os.path.expanduser("~/.hermes/cron/jobs.json"))
with open(path, "r", encoding="utf-8") as f:
    data = json.load(f)

origin = {"platform": "zalo", "chat_id": "2825656851207986406", "chat_name": "Xitrum"}

new_jobs = [
    {
        "id": "c3d4e5f6a7b8",
        "name": "Bao cao thang cong van den",
        "schedule": {"kind": "cron", "expr": "1 1 1 * *", "display": "1 1 1 * *"},
        "schedule_display": "1 1 1 * * (08h01 VN ngay 1 hang thang)",
        "script": "congchuc/congchuc_report_monthly.sh",
        "no_agent": True,
        "deliver": "zalo",
        "origin": origin,
        "enabled": True,
        "state": "scheduled",
        "skills": [],
        "skill": None,
    },
    {
        "id": "d4e5f6a7b8c9",
        "name": "Kiem tra qua han cong van",
        "schedule": {"kind": "cron", "expr": "0 1 * * 1-5", "display": "0 1 * * 1-5"},
        "schedule_display": "0 1 * * 1-5 (08h00 VN T2-T6)",
        "script": "congchuc/congchuc_check_overdue.sh",
        "no_agent": True,
        "deliver": "zalo",
        "origin": origin,
        "enabled": True,
        "state": "scheduled",
        "skills": [],
        "skill": None,
    },
    {
        "id": "202d81764afb",
        "name": "Quet cong van den",
        "schedule": {"kind": "cron", "expr": "0 8-17 * * 1-5", "display": "0 8-17 * * 1-5"},
        "schedule_display": "0 8-17 * * 1-5 (08h-17h VN T2-T6)",
        "script": "congchuc/congchuc_scrape.py",
        "no_agent": True,
        "deliver": "zalo",
        "origin": origin,
        "enabled": True,
        "state": "scheduled",
        "skills": [],
        "skill": None,
    },
    {
        "id": "d7f9e2c1a4b6",
        "name": "Quet cong van di",
        "schedule": {"kind": "cron", "expr": "0 8,15 * * 1-5", "display": "0 8,15 * * 1-5"},
        "schedule_display": "0 8,15 * * 1-5 (08h, 15h VN T2-T6)",
        "script": "congchuc/congchuc_vbdi_scrape.py",
        "no_agent": True,
        "deliver": "zalo",
        "origin": origin,
        "enabled": True,
        "state": "scheduled",
        "skills": [],
        "skill": None,
    },
    {
        "id": "a1b2c3d4e5f6",
        "name": "Bao cao tuan cong van den",
        "schedule": {"kind": "cron", "expr": "0 10 * * 5", "display": "0 10 * * 5"},
        "schedule_display": "0 10 * * 5 (17h00 VN thu 6)",
        "script": "congchuc/congchuc_report_weekly.sh",
        "no_agent": True,
        "deliver": "zalo",
        "origin": origin,
        "enabled": True,
        "state": "scheduled",
        "skills": [],
        "skill": None,
    },
    {
        "id": "b2c3d4e5f6a7",
        "name": "Export Excel CV den",
        "schedule": {"kind": "cron", "expr": "5 10 * * 5", "display": "5 10 * * 5"},
        "schedule_display": "5 10 * * 5 (17h05 VN thu 6)",
        "script": "congchuc/congchuc_report_excel.sh",
        "no_agent": True,
        "deliver": "zalo",
        "origin": origin,
        "enabled": True,
        "state": "scheduled",
        "skills": [],
        "skill": None,
    },
    {
        "id": "f9a8b7c6d5e4",
        "name": "Du thao van ban F9",
        "schedule": {"kind": "zalo_command", "expr": "^(dự thảo|du thao|draft)\\s+(\\d+)", "display": "Lệnh Zalo: dự thảo <số_đến>"},
        "schedule_display": "Zalo Command: dự thảo <số_đến>",
        "script": "congchuc/congchuc_draft.py --so-den {2}",
        "no_agent": True,
        "deliver": "zalo",
        "origin": origin,
        "enabled": True,
        "state": "scheduled",
        "skills": [],
        "skill": None,
    },
]

existing_ids = {j["id"] for j in data["jobs"]}
for nj in new_jobs:
    if nj["id"] not in existing_ids:
        data["jobs"].append(nj)
        print("Added: " + nj["name"])
    else:
        for i, j in enumerate(data["jobs"]):
            if j["id"] == nj["id"]:
                data["jobs"][i] = nj
                print("Updated: " + nj["name"])
                break

data["updated_at"] = "2026-06-22T16:00:00+07:00"
with open(path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
print("Done")
