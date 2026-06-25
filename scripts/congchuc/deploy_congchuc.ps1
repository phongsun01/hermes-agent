# Deploy congchuc scripts to container (subdirectory)
docker exec hermes mkdir -p /opt/data/scripts/congchuc
docker cp D:\Antigravity\Hermes\scripts\congchuc\congchuc_scrape.py hermes:/opt/data/scripts/congchuc/congchuc_scrape.py
docker cp D:\Antigravity\Hermes\scripts\congchuc\congchuc_vbdi_scrape.py hermes:/opt/data/scripts/congchuc/congchuc_vbdi_scrape.py
docker cp D:\Antigravity\Hermes\scripts\congchuc\congvan_status.py hermes:/opt/data/scripts/congchuc/congvan_status.py
docker cp D:\Antigravity\Hermes\scripts\congchuc\congchuc_action.py hermes:/opt/data/scripts/congchuc/congchuc_action.py
docker cp D:\Antigravity\Hermes\scripts\congchuc\congchuc_report.py hermes:/opt/data/scripts/congchuc/congchuc_report.py
docker cp D:\Antigravity\Hermes\scripts\congchuc\congchuc_report_weekly.sh hermes:/opt/data/scripts/congchuc/congchuc_report_weekly.sh
docker cp D:\Antigravity\Hermes\scripts\congchuc\congchuc_report_excel.sh hermes:/opt/data/scripts/congchuc/congchuc_report_excel.sh
docker cp D:\Antigravity\Hermes\scripts\congchuc\congchuc_report_monthly.sh hermes:/opt/data/scripts/congchuc/congchuc_report_monthly.sh
docker cp D:\Antigravity\Hermes\scripts\congchuc\congchuc_check_overdue.sh hermes:/opt/data/scripts/congchuc/congchuc_check_overdue.sh
docker exec hermes chmod +x /opt/data/scripts/congchuc/congchuc_report_weekly.sh /opt/data/scripts/congchuc/congchuc_report_excel.sh /opt/data/scripts/congchuc/congchuc_report_monthly.sh /opt/data/scripts/congchuc/congchuc_check_overdue.sh
docker cp D:\Antigravity\Hermes\scripts\congchuc\deploy_congchuc.ps1 hermes:/opt/data/scripts/congchuc/deploy_congchuc.ps1
docker cp D:\Antigravity\Hermes\scripts\congchuc\update_cron_jobs.py hermes:/opt/data/scripts/congchuc/update_cron_jobs.py
Write-Host "Deployed to /opt/data/scripts/congchuc/"
