import cron.scheduler
import cron.jobs

print("All jobs:")
for j in cron.jobs.list_jobs():
    print(f"ID: {j['id']} | Enabled: {j.get('enabled')} | Next run: {j.get('next_run_at')}")
    
due = cron.scheduler.get_due_jobs()
print("Due jobs:", [j['id'] for j in due])
