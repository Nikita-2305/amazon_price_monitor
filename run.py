import subprocess
import os
from datetime import datetime

def run_spider():
    print(f"\n{'='*55}")
    print(f"  Amazon Bearing Price Monitor")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*55}\n")

    os.makedirs("data", exist_ok=True)
    os.makedirs("logs", exist_ok=True)

    subprocess.run(
        ["scrapy", "crawl", "amazon_bearing"],
        cwd=os.path.dirname(os.path.abspath(__file__))
    )

    print(f"\n{'='*55}")
    print(f"  Done! Check data/ folder for CSV output")
    print(f"  Check logs/scraper.log for details")
    print(f"{'='*55}\n")

if __name__ == "__main__":
    run_spider()