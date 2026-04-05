from sqlalchemy import (
    create_engine, Column, String, Float,
    Boolean, DateTime, Integer, Text
)
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

# ✅ NEW: Use DATABASE_URL directly (from Streamlit secrets or .env)
DATABASE_URL = os.getenv("DATABASE_URL")

# ❗ Safety check
if not DATABASE_URL:
    raise ValueError("❌ DATABASE_URL is not set. Please check your environment variables.")

# ✅ Create engine (Supabase requires SSL)
engine = create_engine(DATABASE_URL, echo=False)

SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


# ─────────────────────────────────────────────
# TABLE MODEL
# ─────────────────────────────────────────────
class PriceSnapshot(Base):
    __tablename__ = "price_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    asin = Column(String(20), nullable=False, index=True)
    product_title = Column(Text)
    model = Column(String(20), index=True)
    seller_name = Column(String(200))
    price = Column(Float)
    mrp = Column(String(20))
    is_buy_box_winner = Column(Boolean, default=False)
    fba_status = Column(String(10))
    availability = Column(String(100))
    pincode = Column(String(10))
    scraped_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return (
            f"<PriceSnapshot asin={self.asin} "
            f"seller={self.seller_name} price={self.price}>"
        )


# ─────────────────────────────────────────────
# CREATE TABLES
# ─────────────────────────────────────────────
def create_tables():
    Base.metadata.create_all(bind=engine)
    print("✅ Tables created successfully!")


def get_session():
    return SessionLocal()


# ─────────────────────────────────────────────
# RUN DIRECTLY
# ─────────────────────────────────────────────
if __name__ == "__main__":
    create_tables()