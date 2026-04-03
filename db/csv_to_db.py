import csv
import os
from datetime import datetime
from models import get_session, PriceSnapshot, create_tables

def import_csv_to_db(csv_path):
    print(f"Importing {csv_path} to PostgreSQL...")
    create_tables()
    session = get_session()
    count = 0

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        batch = []
        for row in reader:
            try:
                scraped_at = row.get("scraped_at", "")
                if scraped_at:
                    scraped_at = datetime.fromisoformat(scraped_at)
                else:
                    scraped_at = datetime.utcnow()

                record = PriceSnapshot(
                    asin=row.get("asin", ""),
                    product_title=row.get("product_title", "")[:500],
                    model=row.get("model", ""),
                    seller_name=row.get("seller_name", ""),
                    price=float(row.get("price", 0) or 0),
                    mrp=str(row.get("mrp", "")),
                    is_buy_box_winner=row.get(
                        "is_buy_box_winner", "False"
                    ) == "True",
                    fba_status=row.get("fba_status", "FBM"),
                    availability=row.get("availability", "Unknown"),
                    pincode=str(row.get("pincode", "")),
                    scraped_at=scraped_at,
                )
                batch.append(record)
                count += 1

                if len(batch) >= 50:
                    session.bulk_save_objects(batch)
                    session.commit()
                    batch = []
                    print(f"  Saved {count} records...")

            except Exception as e:
                print(f"  Row error: {e}")
                continue

        if batch:
            session.bulk_save_objects(batch)
            session.commit()

    session.close()
    print(f"✅ Import complete! {count} records saved to PostgreSQL.")

if __name__ == "__main__":
    data_folder = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data"
    )
    csv_files = [f for f in os.listdir(data_folder) if f.endswith(".csv")]

    if not csv_files:
        print("No CSV files found in data/ folder")
    else:
        latest = sorted(csv_files)[-1]
        csv_path = os.path.join(data_folder, latest)
        import_csv_to_db(csv_path)