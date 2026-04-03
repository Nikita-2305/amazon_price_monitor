import pandas as pd
import numpy as np
from db.models import engine

def get_price_history():
    with engine.connect() as conn:
        df = pd.read_sql(
            "SELECT * FROM price_snapshots ORDER BY scraped_at ASC",
            conn
        )
    return df

def get_ai_recommendation(model: str, seller_name: str, cost_price: float):
    """
    AI-based price recommendation for a seller.
    Returns optimal price, expected profit, and strategy.
    """
    df = get_price_history()
    model_df = df[
        (df["model"] == model) &
        (df["price"] > 0)
    ].copy()

    if model_df.empty:
        return {
            "recommended_price": cost_price * 1.2,
            "min_price": cost_price * 1.05,
            "max_price": cost_price * 1.5,
            "strategy": "No history available. Using default 20% margin.",
            "confidence": "Low",
        }

    avg_price = model_df["price"].mean()
    min_price = model_df["price"].min()
    max_price = model_df["price"].max()

    buy_box_df = model_df[model_df["is_buy_box_winner"] == True]
    if not buy_box_df.empty:
        buy_box_avg = buy_box_df["price"].mean()
    else:
        buy_box_avg = avg_price

    # Strategy logic
    safe_min = max(cost_price * 1.05, min_price * 0.98)
    optimal = min(buy_box_avg * 0.99, avg_price * 0.97)
    optimal = max(optimal, safe_min)

    profit = optimal - cost_price
    margin = (profit / optimal) * 100

    # Determine strategy
    if optimal < avg_price * 0.95:
        strategy = "Aggressive — undercut market to win Buy Box"
        confidence = "High"
    elif optimal <= avg_price:
        strategy = "Competitive — match market rate for steady sales"
        confidence = "High"
    else:
        strategy = "Premium — slightly above market for higher margin"
        confidence = "Medium"

    return {
        "recommended_price": round(optimal, 2),
        "min_safe_price": round(safe_min, 2),
        "market_avg": round(avg_price, 2),
        "market_min": round(min_price, 2),
        "market_max": round(max_price, 2),
        "buy_box_avg": round(buy_box_avg, 2),
        "expected_profit": round(profit, 2),
        "margin_pct": round(margin, 1),
        "strategy": strategy,
        "confidence": confidence,
    }


def get_competitor_analysis(seller_name: str, model: str):
    """Identify real competitors for a seller based on price history."""
    df = get_price_history()
    model_df = df[
        (df["model"] == model) &
        (df["price"] > 0)
    ].copy()

    if model_df.empty:
        return []

    seller_df = model_df[model_df["seller_name"] == seller_name]
    if seller_df.empty:
        return []

    seller_avg = seller_df["price"].mean()
    competitors = []

    for other_seller in model_df["seller_name"].unique():
        if other_seller == seller_name:
            continue
        other_df = model_df[model_df["seller_name"] == other_seller]
        other_avg = other_df["price"].mean()
        price_diff = abs(seller_avg - other_avg)
        price_diff_pct = (price_diff / seller_avg) * 100

        if price_diff_pct <= 20:
            buy_box_wins = other_df[
                other_df["is_buy_box_winner"] == True
            ].shape[0]
            competitors.append({
                "seller": other_seller,
                "avg_price": round(other_avg, 2),
                "price_diff_pct": round(price_diff_pct, 1),
                "buy_box_wins": buy_box_wins,
                "threat_level": (
                    "High" if price_diff_pct < 5
                    else "Medium" if price_diff_pct < 10
                    else "Low"
                ),
            })

    return sorted(competitors, key=lambda x: x["price_diff_pct"])


def get_demand_prediction(model: str, stock_level: int):
    """
    Predict optimal price based on stock level.
    High stock → normal/lower price to move inventory
    Low stock → higher price to maximize revenue
    """
    df = get_price_history()
    model_df = df[
        (df["model"] == model) &
        (df["price"] > 0)
    ]

    if model_df.empty:
        avg = 500
    else:
        avg = model_df["price"].mean()

    if stock_level > 100:
        multiplier = 0.95
        advice = "High stock — price slightly below market to move inventory faster"
    elif stock_level > 50:
        multiplier = 1.0
        advice = "Normal stock — price at market rate"
    elif stock_level > 20:
        multiplier = 1.05
        advice = "Stock reducing — slight price increase recommended"
    elif stock_level > 5:
        multiplier = 1.12
        advice = "Low stock — increase price to maximize revenue"
    else:
        multiplier = 1.20
        advice = "Critical stock — high price, consider restocking urgently"

    return {
        "stock_level": stock_level,
        "market_avg": round(avg, 2),
        "recommended_price": round(avg * multiplier, 2),
        "price_multiplier": multiplier,
        "advice": advice,
    }