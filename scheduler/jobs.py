import subprocess
import os
import sys
import pandas as pd
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

scheduler = BlockingScheduler()


def run_spider():
    print(f"\n🕷️  Running spider: "
          f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    project_root = os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )
    result = subprocess.run(
        ["scrapy", "crawl", "amazon_bearing"],
        cwd=project_root
    )
    if result.returncode == 0:
        print(f"✅ Spider done. Running alert checks...")
        run_alerts()
    else:
        print(f"❌ Spider failed: {result.returncode}")


def run_alerts():
    """Run alert checks after every spider run."""
    try:
        from db.models import engine
        from api.alerts import run_all_checks
        df = pd.read_sql(
            "SELECT * FROM price_snapshots ORDER BY scraped_at DESC",
            engine
        )
        df["price"] = pd.to_numeric(df["price"], errors="coerce")
        df = df[df["price"] > 0]
        run_all_checks(df)
    except Exception as e:
        print(f"❌ Alert check failed: {e}")


def start_scheduler(interval_minutes=60):
    print(f"\n{'='*55}")
    print(f"  Scheduler started — every {interval_minutes} min")
    print(f"  Alerts sent to all registered sellers")
    print(f"  Press Ctrl+C to stop")
    print(f"{'='*55}\n")

    scheduler.add_job(
        run_spider,
        trigger=IntervalTrigger(minutes=interval_minutes),
        id="amazon_spider",
        next_run_time=datetime.now(),
        max_instances=1,
    )

    try:
        scheduler.start()
    except KeyboardInterrupt:
        print("\n⛔ Scheduler stopped.")
        scheduler.shutdown()


if __name__ == "__main__":
    start_scheduler(interval_minutes=60)