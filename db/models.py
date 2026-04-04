from sqlalchemy import (
    create_engine, Column, String, Float,
    Boolean, DateTime, Integer, Text
)
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
import os
from dotenv import load_dotenv
from urllib.parse import quote_plus

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "bearing_monitor")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "Madhura@1105")

DATABASE_URL = (
    f"postgresql://{DB_USER}:{quote_plus(DB_PASSWORD)}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


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


def create_tables():
    Base.metadata.create_all(engine)
    print("✅ Tables created successfully!")


def get_session():
    return SessionLocal()


if __name__ == "__main__":
    create_tables()
