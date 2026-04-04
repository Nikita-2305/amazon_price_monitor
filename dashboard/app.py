import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import sys
import os
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

# ── Teal theme matching login page ───────────────────
st.markdown("""
<style>
    /* Main background */
    .stApp {
        background: linear-gradient(135deg, #d6f0f0 0%, #e8f5f5 40%, #f5fbfb 100%);
    }
    /* Sidebar */
    [data-testid="stSidebar"] {
        background: #ffffff !important;
        border-right: 1px solid #d0e8e8;
    }
    /* Header */
    .bw-header {
        background: #1a8c8c;
        padding: 16px 24px;
        border-radius: 14px;
        margin-bottom: 24px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .bw-header h1 {
        color: white !important;
        font-size: 24px !important;
        font-weight: 700 !important;
        margin: 0 !important;
    }
    .bw-header p {
        color: rgba(255,255,255,0.8) !important;
        font-size: 13px !important;
        margin: 0 !important;
    }
    /* Metric cards */
    .metric-box {
        background: white;
        border-radius: 12px;
        padding: 18px 20px;
        border: 1px solid #d0e8e8;
        text-align: center;
    }
    .metric-box .label {
        font-size: 12px;
        color: #4a6a6a;
        margin-bottom: 6px;
    }
    .metric-box .value {
        font-size: 28px;
        font-weight: 700;
        color: #1a8c8c;
    }
    /* Section headers */
    .section-head {
        font-size: 16px;
        font-weight: 700;
        color: #1a3a3a;
        border-left: 4px solid #1a8c8c;
        padding-left: 10px;
        margin: 20px 0 12px 0;
    }
    /* Alert boxes */
    .alert-critical {
        background: #fff0f0;
        border: 1px solid #ffcccc;
        border-radius: 10px;
        padding: 12px 16px;
        margin: 6px 0;
        color: #cc3333;
        font-size: 14px;
    }
    .alert-warning {
        background: #fffbf0;
        border: 1px solid #ffe0a0;
        border-radius: 10px;
        padding: 12px 16px;
        margin: 6px 0;
        color: #9a6600;
        font-size: 14px;
    }
    .alert-ok {
        background: #f0fff4;
        border: 1px solid #b3f5cc;
        border-radius: 10px;
        padding: 12px 16px;
        margin: 6px 0;
        color: #1a7a40;
        font-size: 14px;
    }
    /* Recommendation card */
    .rec-card {
        background: white;
        border-radius: 12px;
        padding: 20px;
        border: 1px solid #d0e8e8;
        margin-top: 12px;
    }
    .rec-price {
        font-size: 36px;
        font-weight: 800;
        color: #1a8c8c;
    }
    /* Dataframe */
    .stDataFrame { border-radius: 10px !important; }
    /* Buttons */
    .stButton > button {
        background: #1a8c8c !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
    }
    .stButton > button:hover {
        background: #157070 !important;
    }
    /* Tabs */
    .stTabs [data-baseweb="tab"] {
        color: #4a6a6a !important;
        font-weight: 500 !important;
    }
    .stTabs [aria-selected="true"] {
        color: #1a8c8c !important;
        border-bottom-color: #1a8c8c !important;
    }
</style>
""", unsafe_allow_html=True)


# ── Load data ─────────────────────────────────────────
@st.cache_data(ttl=300)
def load_data():
    with engine.connect() as conn:
        df = pd.read_sql(
            "SELECT * FROM price_snapshots ORDER BY scraped_at DESC",
            conn
        )
    return df


def main():
    # Header
    st.markdown("""
    <div class="bw-header">
        <div>
            <h1>🔩 BearingWatch</h1>
            <p>Amazon.in · Karnataka (Bengaluru, Mysuru, Hubli, Dharwad, Belagavi) · Real-time monitoring</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    df = load_data()
    if df.empty:
        st.warning("No data found. Run the spider first: `py run.py`")
        return

    df["scraped_at"] = pd.to_datetime(df["scraped_at"])
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    df = df[df["price"] > 0]

    # ── Sidebar ───────────────────────────────────────
    st.sidebar.image("https://via.placeholder.com/200x60/1a8c8c/ffffff?text=BearingWatch",
                     use_column_width=True)
    st.sidebar.markdown("---")

    models = ["All"] + sorted(df["model"].dropna().unique().tolist())
    selected_model = st.sidebar.selectbox("Bearing Model", models)

    sellers = ["All"] + sorted(df["seller_name"].dropna().unique().tolist())
    selected_seller = st.sidebar.selectbox("Seller", sellers)

    locations = ["All"] + ["Bengaluru (560001)", "Mysuru (570001)",
                           "Hubli (580020)", "Dharwad (580001)",
                           "Belagavi (590001)"]
    selected_location = st.sidebar.selectbox("Location", locations)

    if st.sidebar.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.markdown("**Price Floor Settings**")
    for model, floor in PRICE_FLOORS.items():
        st.sidebar.text(f"SKF {model}: ₹{floor} min")

    # Apply filters
    filtered = df.copy()
    if selected_model != "All":
        filtered = filtered[filtered["model"] == selected_model]
    if selected_seller != "All":
        filtered = filtered[filtered["seller_name"] == selected_seller]

    # ── Metrics ───────────────────────────────────────
    c1, c2, c3, c4, c5 = st.columns(5)
    metrics = [
        (c1, "Total Records", len(filtered)),
        (c2, "Unique ASINs", filtered["asin"].nunique()),
        (c3, "Active Sellers", filtered["seller_name"].nunique()),
        (c4, "Avg Price", f"₹{filtered['price'].mean():.0f}"),
        (c5, "Models Tracked", filtered["model"].nunique()),
    ]
    for col, label, value in metrics:
        with col:
            st.markdown(f"""
            <div class="metric-box">
                <div class="label">{label}</div>
                <div class="value">{value}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")

    # ── Tabs ──────────────────────────────────────────
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Price Monitor",
        "🔔 Alerts & Floors",
        "🤖 AI Recommendations",
        "💰 Profit Calculator",
        "👥 Seller Behaviour",
    ])

    # ═══════════════════════════════════════════════
    # TAB 1: Price Monitor
    # ═══════════════════════════════════════════════
    with tab1:
        col1, col2 = st.columns(2)

        with col1:
            st.markdown('<div class="section-head">Price Trend Over Time</div>',
                        unsafe_allow_html=True)
            trend = filtered.groupby(
                [pd.Grouper(key="scraped_at", freq="30min"), "seller_name"]
            )["price"].mean().reset_index()
            if not trend.empty:
                fig = px.line(
                    trend, x="scraped_at", y="price",
                    color="seller_name",
                    color_discrete_sequence=px.colors.qualitative.Set2,
                )
                fig.update_layout(
                    height=320, paper_bgcolor="white",
                    plot_bgcolor="white",
                    font=dict(family="Arial", color="#1a3a3a"),
                    legend=dict(orientation="h", y=-0.3),
                    margin=dict(l=10, r=10, t=10, b=10),
                )
                fig.update_xaxes(showgrid=True, gridcolor="#e8f5f5")
                fig.update_yaxes(showgrid=True, gridcolor="#e8f5f5",
                                 tickprefix="₹")
                st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown('<div class="section-head">Seller Price Comparison</div>',
                        unsafe_allow_html=True)
            latest = filtered.sort_values("scraped_at").groupby(
                "seller_name"
            ).last().reset_index()
            if not latest.empty:
                fig2 = px.bar(
                    latest.sort_values("price"),
                    x="seller_name", y="price",
                    color="price",
                    color_continuous_scale=[[0, "#1a8c8c"],
                                            [0.5, "#5dcaa5"],
                                            [1, "#e8593c"]],
                )
                fig2.update_layout(
                    height=320, paper_bgcolor="white",
                    plot_bgcolor="white",
                    font=dict(family="Arial", color="#1a3a3a"),
                    showlegend=False,
                    margin=dict(l=10, r=10, t=10, b=10),
                )
                fig2.update_xaxes(tickangle=30, showgrid=False)
                fig2.update_yaxes(showgrid=True, gridcolor="#e8f5f5",
                                  tickprefix="₹")
                st.plotly_chart(fig2, use_container_width=True)

        col3, col4 = st.columns(2)

        with col3:
            st.markdown('<div class="section-head">Buy Box Winners</div>',
                        unsafe_allow_html=True)
            bb = filtered[filtered["is_buy_box_winner"] == True]
            if not bb.empty:
                bb_count = bb["seller_name"].value_counts().reset_index()
                bb_count.columns = ["seller", "wins"]
                fig3 = px.pie(
                    bb_count, names="seller", values="wins",
                    hole=0.5,
                    color_discrete_sequence=["#1a8c8c", "#5dcaa5",
                                             "#9fe1cb", "#d6f0f0",
                                             "#085041"],
                )
                fig3.update_layout(
                    height=300, paper_bgcolor="white",
                    margin=dict(l=10, r=10, t=10, b=10),
                    legend=dict(orientation="h", y=-0.2),
                )
                st.plotly_chart(fig3, use_container_width=True)

        with col4:
            st.markdown('<div class="section-head">Price Distribution</div>',
                        unsafe_allow_html=True)
            fig4 = px.histogram(
                filtered, x="price", nbins=25, color="model",
                color_discrete_sequence=["#1a8c8c", "#e8593c",
                                         "#5dcaa5", "#f0997b"],
            )
            fig4.update_layout(
                height=300, paper_bgcolor="white",
                plot_bgcolor="white",
                margin=dict(l=10, r=10, t=10, b=10),
            )
            fig4.update_xaxes(tickprefix="₹")
            st.plotly_chart(fig4, use_container_width=True)

        st.markdown('<div class="section-head">All Sellers — Latest Prices</div>',
                    unsafe_allow_html=True)
        table = filtered.sort_values(
            "scraped_at", ascending=False
        ).groupby(["asin", "seller_name"]).first().reset_index()
        display = table[[
            "asin", "model", "seller_name", "price",
            "mrp", "is_buy_box_winner", "fba_status",
            "availability", "pincode", "scraped_at"
        ]].copy()
        display["price"] = display["price"].apply(lambda x: f"₹{x:.0f}")
        display["is_buy_box_winner"] = display["is_buy_box_winner"].apply(
            lambda x: "✅ Yes" if x else "No"
        )
        display.columns = ["ASIN", "Model", "Seller", "Price", "MRP",
                           "Buy Box", "Fulfillment", "Availability",
                           "PIN", "Last Seen"]
        st.dataframe(display, use_container_width=True, height=350)

    # ═══════════════════════════════════════════════
    # TAB 2: Alerts & Price Floors
    # ═══════════════════════════════════════════════
    with tab2:
        st.markdown('<div class="section-head">Price Floor Monitor</div>',
                    unsafe_allow_html=True)
        st.info("Minimum prices are set to protect all sellers from losses. "
                "Any seller going below these prices triggers an email alert.")

        col1, col2 = st.columns(2)
        with col1:
            floor_data = pd.DataFrame([
                {"Model": f"SKF {m}", "Floor Price": f"₹{p}",
                 "Status": "Active"}
                for m, p in PRICE_FLOORS.items()
            ])
            st.dataframe(floor_data, use_container_width=True, height=280)

        with col2:
            violations = check_price_floors(filtered)
            if violations:
                st.error(f"🚨 {len(violations)} price floor violations detected!")
                for v in violations:
                    st.markdown(f"""
                    <div class="alert-critical">
                    🚨 <b>{v['seller']}</b> selling SKF {v['model']}
                    at <b>₹{v['price']}</b> — below floor ₹{v['floor']}
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div class="alert-ok">
                ✅ All sellers are above minimum price floors. Market is healthy!
                </div>
                """, unsafe_allow_html=True)

        st.markdown('<div class="section-head">Price Drop Alerts</div>',
                    unsafe_allow_html=True)
        drops = []

        sellers = filtered["seller_name"].dropna().unique()

        for seller in sellers:
            seller_email = "test@example.com"  # temporary (or fetch from DB)
            alerts = check_and_alert_price_drop(filtered, seller_email, seller)
            drops.extend(alerts)
        if drops:
            for d in drops[:5]:
                pct = d.get("drop_pct", 0)
                if pct > 15:
                    st.markdown(f"""
                    <div class="alert-critical">
                    🚨 <b>{d['competitor']}</b> — SKF {d['model']}
                    at ₹{d['competitor_price']:.0f} is {pct:.1f}% below market avg
                    ₹{d['my_price']:.0f}
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class="alert-warning">
                    ⚠️ <b>{d['competitor']}</b> — SKF {d['model']}
                    at ₹{d['competitor_price']:.0f} is {pct:.1f}% below market avg
                    ₹{d['my_price']:.0f}
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="alert-ok">
            ✅ No significant price drops detected.
            </div>
            """, unsafe_allow_html=True)

        st.markdown('<div class="section-head">Send Manual Alert Email</div>',
                    unsafe_allow_html=True)
        with st.form("email_form"):
            email_to = st.text_input("Recipient email")
            email_subject = st.text_input("Subject",
                                          value="BearingWatch Price Alert")
            email_body = st.text_area("Message")
            if st.form_submit_button("Send Email Alert"):
                from api.alerts import send_alert_email
                if send_alert_email(email_subject, email_body, email_to):
                    st.success("✅ Email sent successfully!")
                else:
                    st.error("❌ Email failed. Check .env settings.")

    # ═══════════════════════════════════════════════
    # TAB 3: AI Recommendations
    # ═══════════════════════════════════════════════
    with tab3:
        st.markdown('<div class="section-head">AI Price Recommendation</div>',
                    unsafe_allow_html=True)
        st.info("Enter your details to get an AI-powered optimal price "
                "recommendation based on competitor history.")

        col1, col2 = st.columns(2)
        with col1:
            ai_model = st.selectbox(
                "Select bearing model",
                options=sorted(df["model"].dropna().unique().tolist())
            )
            ai_seller = st.text_input("Your seller name (optional)",
                                      value="My Store")
            ai_cost = st.number_input("Your cost price (₹)", min_value=50,
                                      max_value=5000, value=300, step=10)

            if st.button("Get AI Recommendation"):
                rec = get_ai_recommendation(ai_model, ai_seller, ai_cost)
                with col2:
                    st.markdown(f"""
                    <div class="rec-card">
                        <div style="color:#4a6a6a;font-size:13px;
                        margin-bottom:4px;">Recommended price</div>
                        <div class="rec-price">₹{rec['recommended_price']}</div>
                        <div style="color:#1a7a40;font-size:14px;
                        margin:8px 0;">
                        Profit: ₹{rec['expected_profit']} |
                        Margin: {rec['margin_pct']}%
                        </div>
                        <hr style="border:1px solid #d0e8e8;margin:12px 0">
                        <div style="font-size:13px;color:#1a3a3a;">
                        <b>Strategy:</b> {rec['strategy']}
                        </div>
                        <div style="font-size:13px;color:#4a6a6a;
                        margin-top:8px;">
                        Market avg: ₹{rec['market_avg']} |
                        Buy Box avg: ₹{rec['buy_box_avg']}
                        </div>
                        <div style="font-size:13px;color:#4a6a6a;">
                        Safe min: ₹{rec['min_safe_price']} |
                        Confidence: {rec['confidence']}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

        st.markdown('<div class="section-head">Demand-Based Pricing</div>',
                    unsafe_allow_html=True)
        col3, col4 = st.columns(2)
        with col3:
            d_model = st.selectbox(
                "Model for demand pricing",
                options=sorted(df["model"].dropna().unique().tolist()),
                key="demand_model"
            )
            stock = st.slider("Your current stock level (units)",
                              min_value=1, max_value=200, value=50)
            if st.button("Get Demand Price"):
                demand = get_demand_prediction(d_model, stock)
                with col4:
                    color = ("#cc3333" if stock < 10 else
                             "#9a6600" if stock < 30 else "#1a7a40")
                    st.markdown(f"""
                    <div class="rec-card">
                        <div style="color:#4a6a6a;font-size:13px;">
                        Recommended price for {stock} units stock</div>
                        <div class="rec-price"
                        style="color:{color};">
                        ₹{demand['recommended_price']}</div>
                        <div style="font-size:13px;color:#4a6a6a;
                        margin-top:8px;">
                        Market avg: ₹{demand['market_avg']}
                        </div>
                        <hr style="border:1px solid #d0e8e8;margin:10px 0">
                        <div style="font-size:13px;color:#1a3a3a;">
                        {demand['advice']}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

    # ═══════════════════════════════════════════════
    # TAB 4: Profit Calculator
    # ═══════════════════════════════════════════════
    with tab4:
        st.markdown('<div class="section-head">Profit Optimization Calculator</div>',
                    unsafe_allow_html=True)
        col1, col2 = st.columns([1, 2])
        with col1:
            cost = st.number_input("Cost price (₹)", min_value=10,
                                   max_value=10000, value=400, step=10)
            overhead = st.number_input("Overhead per unit (₹)",
                                       min_value=0, max_value=500,
                                       value=20, step=5)
            total_cost = cost + overhead
            st.markdown(f"""
            <div class="metric-box" style="margin-top:12px;">
                <div class="label">Total cost per unit</div>
                <div class="value">₹{total_cost}</div>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            prices = list(range(
                int(total_cost * 1.01),
                int(total_cost * 2.0),
                max(1, int(total_cost * 0.05))
            ))
            profits = [p - total_cost for p in prices]
            margins = [(p / sp * 100) for p, sp in zip(profits, prices)]

            fig5 = go.Figure()
            fig5.add_trace(go.Scatter(
                x=prices, y=profits,
                mode="lines", name="Profit (₹)",
                line=dict(color="#1a8c8c", width=3),
                fill="tozeroy",
                fillcolor="rgba(26,140,140,0.1)",
            ))
            fig5.add_trace(go.Scatter(
                x=prices, y=margins,
                mode="lines", name="Margin (%)",
                line=dict(color="#e8593c", width=2, dash="dash"),
                yaxis="y2",
            ))
            fig5.add_vline(
                x=total_cost * 1.15,
                line_dash="dot", line_color="#1a7a40",
                annotation_text="15% margin",
            )
            fig5.add_vline(
                x=total_cost * 1.25,
                line_dash="dot", line_color="#9a6600",
                annotation_text="25% margin",
            )
            fig5.update_layout(
                height=350,
                paper_bgcolor="white",
                plot_bgcolor="white",
                yaxis=dict(title="Profit (₹)", tickprefix="₹",
                           gridcolor="#e8f5f5"),
                yaxis2=dict(title="Margin (%)", overlaying="y",
                            side="right", ticksuffix="%"),
                xaxis=dict(title="Selling price (₹)", tickprefix="₹",
                           gridcolor="#e8f5f5"),
                legend=dict(orientation="h", y=-0.25),
                margin=dict(l=10, r=10, t=30, b=10),
            )
            st.plotly_chart(fig5, use_container_width=True)

        # Profit table
        st.markdown('<div class="section-head">Profit at Different Prices</div>',
                    unsafe_allow_html=True)
        table_prices = [
            int(total_cost * m) for m in
            [1.05, 1.10, 1.15, 1.20, 1.25, 1.30, 1.40, 1.50]
        ]
        profit_table = pd.DataFrame({
            "Selling Price": [f"₹{p}" for p in table_prices],
            "Profit": [f"₹{p - total_cost:.0f}" for p in table_prices],
            "Margin %": [f"{((p-total_cost)/p*100):.1f}%" for p in table_prices],
            "Recommendation": [
                "Too low — risky" if p < total_cost * 1.10
                else "Minimum viable" if p < total_cost * 1.15
                else "Good margin" if p < total_cost * 1.25
                else "Excellent margin" if p < total_cost * 1.40
                else "Premium pricing"
                for p in table_prices
            ]
        })
        st.dataframe(profit_table, use_container_width=True, height=300)

    # ═══════════════════════════════════════════════
    # TAB 5: Seller Behaviour
    # ═══════════════════════════════════════════════
    with tab5:
        st.markdown('<div class="section-head">Seller Behaviour Analysis</div>',
                    unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            sel_model = st.selectbox(
                "Select model",
                options=sorted(df["model"].dropna().unique().tolist()),
                key="sel_model"
            )
            sellers_list = df[df["model"] == sel_model][
                "seller_name"
            ].dropna().unique().tolist()
            sel_name = st.selectbox("Select your seller", sellers_list)

            if st.button("Analyse Competitors"):
                competitors = get_competitor_analysis(sel_name, sel_model)
                with col2:
                    if competitors:
                        st.markdown(
                            f"**{len(competitors)} real competitors "
                            f"found for {sel_name}**"
                        )
                        for c in competitors[:5]:
                            color = (
                                "#cc3333" if c["threat_level"] == "High"
                                else "#9a6600" if c["threat_level"] == "Medium"
                                else "#1a7a40"
                            )
                            st.markdown(f"""
                            <div class="rec-card"
                            style="margin-bottom:8px;">
                                <div style="display:flex;
                                justify-content:space-between;">
                                    <b>{c['seller']}</b>
                                    <span style="color:{color};
                                    font-weight:600;">
                                    {c['threat_level']} threat</span>
                                </div>
                                <div style="font-size:13px;
                                color:#4a6a6a;margin-top:4px;">
                                Avg price: ₹{c['avg_price']} |
                                Diff: {c['price_diff_pct']}% |
                                Buy Box wins: {c['buy_box_wins']}
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.info("No close competitors found for this seller.")

        st.markdown('<div class="section-head">Seller Price History</div>',
                    unsafe_allow_html=True)
        seller_history = df[
            (df["model"] == sel_model) &
            (df["seller_name"].isin(sellers_list[:5]))
        ].copy()
        if not seller_history.empty:
            fig6 = px.line(
                seller_history,
                x="scraped_at", y="price",
                color="seller_name",
                color_discrete_sequence=["#1a8c8c", "#e8593c",
                                         "#5dcaa5", "#f0997b", "#085041"],
                markers=True,
            )
            fig6.update_layout(
                height=350, paper_bgcolor="white",
                plot_bgcolor="white",
                legend=dict(orientation="h", y=-0.3),
                margin=dict(l=10, r=10, t=10, b=10),
            )
            fig6.update_yaxes(tickprefix="₹", gridcolor="#e8f5f5")
            fig6.update_xaxes(showgrid=False)
            st.plotly_chart(fig6, use_container_width=True)

    st.markdown("---")
    st.caption(
        f"Last updated: {df['scraped_at'].max()} · "
        f"Total records: {len(df)} · "
        f"BearingWatch © 2026"
    )


if __name__ == "__main__":
    main()