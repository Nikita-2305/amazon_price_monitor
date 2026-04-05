import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import sys
import os
import requests as http_requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.models import engine
from api.alerts import PRICE_FLOORS, check_price_floors, check_and_alert_price_drop
from api.ai_recommendations import (
    get_ai_recommendation,
    get_competitor_analysis,
    get_demand_prediction,
)

st.set_page_config(
    page_title="BearingWatch Dashboard",
    page_icon="🔩",
    layout="wide",
)

# ─────────────────────────────────────────────
# ✅ SAFE SELLER INFO
# ─────────────────────────────────────────────
def get_seller_info():
    params = st.query_params
    name = params.get("seller_name", "")
    email = params.get("seller_email", "")
    token = params.get("token", "")

    if not name and not email:
        token = st.session_state.get("session_token", "")
        if token:
            try:
                resp = http_requests.get(
                    f"http://localhost:8000/api/session?token={token}",
                    timeout=3
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("authenticated"):
                        name = data.get("name", "")
                        email = data.get("email", "")
            except Exception:
                pass

    if name:
        st.session_state["seller_name"] = name
    if email:
        st.session_state["seller_email"] = email
    if token:
        st.session_state["session_token"] = token

    return (
        st.session_state.get("seller_name", "Seller"),
        st.session_state.get("seller_email", ""),
    )


# ─────────────────────────────────────────────
# ✅ FIXED LOAD DATA (VERY IMPORTANT)
# ─────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_data():
    try:
        with engine.connect() as conn:
            df = pd.read_sql(
                "SELECT * FROM price_snapshots ORDER BY scraped_at DESC",
                conn
            )
        return df

    except Exception as e:
        st.error("⚠️ Database connection failed")
        st.text(str(e))
        return pd.DataFrame()


# ─────────────────────────────────────────────
# MAIN APP
# ─────────────────────────────────────────────
def main():
    seller_name, seller_email = get_seller_info()

    st.title("🔩 BearingWatch Dashboard")
    st.caption(f"Logged in as: {seller_name} ({seller_email})")

    df = load_data()

    # ✅ STOP CRASH IF NO DATA
    if df.empty:
        st.warning("⚠️ No data found OR database not connected.")
        st.info("👉 Check Supabase connection OR run scraper first.")
        return

    df["scraped_at"] = pd.to_datetime(df["scraped_at"])
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    df = df[df["price"] > 0]

    # ─────────────────────────
    # SIDEBAR
    # ─────────────────────────
    st.sidebar.title("Filters")

    models = ["All"] + sorted(df["model"].dropna().unique().tolist())
    selected_model = st.sidebar.selectbox("Model", models)

    sellers = ["All"] + sorted(df["seller_name"].dropna().unique().tolist())
    selected_seller = st.sidebar.selectbox("Seller", sellers)

    if st.sidebar.button("🔄 Refresh"):
        st.cache_data.clear()
        st.rerun()

    # ─────────────────────────
    # FILTER DATA
    # ─────────────────────────
    filtered = df.copy()

    if selected_model != "All":
        filtered = filtered[filtered["model"] == selected_model]

    if selected_seller != "All":
        filtered = filtered[filtered["seller_name"] == selected_seller]

    # ─────────────────────────
    # METRICS
    # ─────────────────────────
    st.subheader("📊 Overview")

    col1, col2, col3 = st.columns(3)

    col1.metric("Records", len(filtered))
    col2.metric("Avg Price", f"₹{filtered['price'].mean():.0f}")
    col3.metric("Sellers", filtered["seller_name"].nunique())

    # ─────────────────────────
    # PRICE TREND
    # ─────────────────────────
    st.subheader("📈 Price Trend")

    trend = filtered.groupby(
        [pd.Grouper(key="scraped_at", freq="30min"), "seller_name"]
    )["price"].mean().reset_index()

    if not trend.empty:
        fig = px.line(trend, x="scraped_at", y="price", color="seller_name")
        st.plotly_chart(fig, use_container_width=True)

    # ─────────────────────────
    # TABLE
    # ─────────────────────────
    st.subheader("📋 Latest Data")

    latest = filtered.sort_values("scraped_at", ascending=False).head(50)

    st.dataframe(latest, use_container_width=True)


if __name__ == "__main__":
    main()