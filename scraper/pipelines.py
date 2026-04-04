import csv
import os
from datetime import datetime


class CSVPipeline:
    def open_spider(self, spider):
        os.makedirs("data", exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.filename = f"data/prices_{timestamp}.csv"
        self.file = open(self.filename, "w", newline="", encoding="utf-8")
        self.writer = csv.DictWriter(self.file, fieldnames=[
            "asin", "product_title", "model", "seller_name",
            "price", "mrp", "is_buy_box_winner", "fba_status",
            "availability", "pincode", "scraped_at"
        ])
        self.writer.writeheader()
        spider.logger.info(f"CSV: saving to {self.filename}")

    def close_spider(self, spider):
        self.file.close()
        spider.logger.info(f"CSV: saved to {self.filename}")

    def process_item(self, item, spider):
        self.writer.writerow(dict(item))
        return item


class PostgreSQLPipeline:
    def open_spider(self, spider):
        import sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from db.models import SessionLocal, PriceSnapshot
        self.SessionLocal = SessionLocal
        self.PriceSnapshot = PriceSnapshot
        self.batch = []
        self.batch_size = 20
        spider.logger.info("PostgreSQL pipeline opened")

    def close_spider(self, spider):
        if self.batch:
            self._flush_batch()
        spider.logger.info("PostgreSQL pipeline closed")

    def process_item(self, item, spider):
        try:
            scraped_at = item.get("scraped_at")
            if isinstance(scraped_at, str):
                scraped_at = datetime.fromisoformat(scraped_at)

            record = self.PriceSnapshot(
                asin=item.get("asin", ""),
                product_title=item.get("product_title", "")[:500],
                model=item.get("model", ""),
                seller_name=item.get("seller_name", ""),
                price=float(item.get("price", 0) or 0),
                mrp=str(item.get("mrp", "")),
                is_buy_box_winner=bool(item.get("is_buy_box_winner", False)),
                fba_status=item.get("fba_status", "FBM"),
                availability=item.get("availability", "Unknown"),
                pincode=str(item.get("pincode", "")),
                scraped_at=scraped_at or datetime.utcnow(),
            )
            self.batch.append(record)

            if len(self.batch) >= self.batch_size:
                self._flush_batch()

        except Exception as e:
            spider.logger.error(f"DB error: {e}")

        return item

    def _flush_batch(self):
        db = self.SessionLocal()
        try:
            db.bulk_save_objects(self.batch)
            db.commit()
            print(f"✅ Saved {len(self.batch)} records to PostgreSQL")
            self.batch = []
        except Exception as e:
            db.rollback()
            print(f"❌ Batch save failed: {e}")
            self.batch = []
        finally:
            db.close()