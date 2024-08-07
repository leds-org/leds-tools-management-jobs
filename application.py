from job_daily_report import main as main_job_daily_report
from job_daily_clockify import main as main_job_daily_clockify
from job_resume_sprint import main as main_job_resume_sprint
from job_resume_project import main as main_job_resume_project
import schedule
import time

def main():
    main_job_daily_report()
    main_job_daily_clockify()
    main_job_resume_sprint()
    main_job_resume_project()

if __name__ == "__main__":
    
    schedule.every().monday.at("17:00").do(main)
    schedule.every().tuesday.at("17:00").do(main)
    schedule.every().wednesday.at("17:00").do(main)
    schedule.every().thursday.at("17:00").do(main)
    schedule.every().friday.at("17:00").do(main)

    while True:
        schedule.run_pending()
        time.sleep(1)