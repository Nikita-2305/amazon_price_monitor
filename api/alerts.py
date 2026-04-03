import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")

PRICE_FLOORS = {
    "6205": 150, "6206": 140, "6207": 160,
    "6208": 180, "6305": 200, "6306": 220,
    "6005": 120, "6006": 130,
}

# Track last alerted prices to avoid repeated emails
_last_alerted = {}


def get_all_registered_emails():
    """Fetch all registered seller emails from DB."""
    from db.models import SessionLocal
    from api.main import Seller
    db = SessionLocal()
    try:
        sellers = db.query(Seller).all()
        return [
            {"email": s.email, "name": s.name, "company": s.company}
            for s in sellers
        ]
    except Exception as e:
        print(f"Error fetching emails: {e}")
        return []
    finally:
        db.close()


def send_alert_email(subject: str, body_html: str, to_email: str):
    """Send a single alert email."""
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"BearingWatch <{GMAIL_USER}>"
        msg["To"] = to_email

        html = f"""
        <!DOCTYPE html>
        <html>
        <body style="margin:0;padding:0;background:#f0f7f7;
        font-family:Arial,sans-serif;">
        <div style="max-width:600px;margin:30px auto;
        background:white;border-radius:16px;overflow:hidden;
        box-shadow:0 4px 20px rgba(0,0,0,0.08);">

          <div style="background:#1a8c8c;padding:24px 32px;">
            <h2 style="color:white;margin:0;font-size:22px;">
              🔩 BearingWatch Alert
            </h2>
            <p style="color:rgba(255,255,255,0.8);margin:4px 0 0;
            font-size:13px;">
              Real-time price intelligence · Amazon India
            </p>
          </div>

          <div style="padding:28px 32px;">
            {body_html}
          </div>

          <div style="background:#f0f7f7;padding:16px 32px;
          border-top:1px solid #d0e8e8;">
            <p style="font-size:12px;color:#4a6a6a;margin:0;">
              You received this because you registered on BearingWatch.
              <a href="http://localhost:8000" style="color:#1a8c8c;">
              View Dashboard</a>
            </p>
          </div>
        </div>
        </body>
        </html>
        """
        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_USER, to_email, msg.as_string())

        print(f"✅ Alert sent to {to_email}")
        return True
    except Exception as e:
        print(f"❌ Email failed to {to_email}: {e}")
        return False


def send_to_all_sellers(subject: str, body_html: str):
    """Send alert email to ALL registered sellers."""
    sellers = get_all_registered_emails()
    if not sellers:
        print("No registered sellers found.")
        return

    for seller in sellers:
        personalized = body_html.replace(
            "{{name}}", seller["name"]
        ).replace(
            "{{company}}", seller.get("company", "")
        )
        send_alert_email(subject, personalized, seller["email"])


def check_price_floors(df):
    """
    Check price floor violations.
    Only alert if this seller+model combo hasn't been alerted before
    OR price has changed since last alert.
    """
    alerts = []
    for model, floor_price in PRICE_FLOORS.items():
        model_df = df[df["model"] == model]
        if model_df.empty:
            continue

        violations = model_df[
            (model_df["price"] > 0) &
            (model_df["price"] < floor_price)
        ]

        for _, row in violations.iterrows():
            key = f"{row['seller_name']}_{model}"
            current_price = row["price"]

            # Only send if not alerted before or price changed
            if key in _last_alerted:
                if abs(_last_alerted[key] - current_price) < 5:
                    continue

            _last_alerted[key] = current_price
            alerts.append({
                "model": model,
                "seller": row["seller_name"],
                "price": current_price,
                "floor": floor_price,
                "asin": row["asin"],
            })

            body = f"""
            <p style="color:#1a3a3a;font-size:16px;">
            Dear {{{{name}}}},</p>

            <div style="background:#fff0f0;border-left:4px solid #cc3333;
            padding:16px 20px;border-radius:8px;margin:16px 0;">
                <h3 style="color:#cc3333;margin:0 0 8px;">
                🚨 Price Floor Violation Detected</h3>
                <p style="margin:4px 0;color:#1a3a3a;">
                <b>Seller:</b> {row['seller_name']}</p>
                <p style="margin:4px 0;color:#1a3a3a;">
                <b>Product:</b> SKF Bearing {model}</p>
                <p style="margin:4px 0;color:#cc3333;">
                <b>Current Price: ₹{current_price:.0f}</b>
                (below floor ₹{floor_price})</p>
                <p style="margin:4px 0;color:#1a3a3a;">
                <b>ASIN:</b> {row['asin']}</p>
            </div>

            <p style="color:#4a6a6a;font-size:14px;">
            This seller is pricing below the minimum floor price.
            This may cause losses for all sellers in this category.
            Please review your pricing strategy.</p>

            <a href="http://localhost:8501"
            style="display:inline-block;background:#1a8c8c;color:white;
            padding:12px 24px;border-radius:8px;text-decoration:none;
            font-weight:600;margin-top:12px;">
            View Dashboard</a>
            """

            send_to_all_sellers(
                f"🚨 Price Floor Violation — SKF {model}",
                body
            )

    return alerts


def check_and_alert_price_drop(df, seller_email: str,
                                seller_name: str):
    """
    Check if any competitor dropped price BELOW this seller's price.
    Only send alert when it actually changes — not every time.
    """
    alerts = []

    for model in df["model"].unique():
        model_df = df[df["model"] == model]
        if model_df.empty:
            continue

        seller_df = model_df[
            model_df["seller_name"] == seller_name
        ]
        if seller_df.empty:
            continue

        my_price = seller_df["price"].min()

        # Find competitors cheaper than me
        cheaper = model_df[
            (model_df["seller_name"] != seller_name) &
            (model_df["price"] > 0) &
            (model_df["price"] < my_price)
        ]

        if cheaper.empty:
            continue

        cheapest = cheaper.sort_values("price").iloc[0]
        key = f"{seller_email}_{model}_competitor"
        current_low = cheapest["price"]

        # Only alert if price changed by more than ₹5
        if key in _last_alerted:
            if abs(_last_alerted[key] - current_low) < 5:
                continue

        _last_alerted[key] = current_low
        drop_pct = ((my_price - current_low) / my_price) * 100

        alerts.append({
            "model": model,
            "competitor": cheapest["seller_name"],
            "competitor_price": current_low,
            "my_price": my_price,
            "drop_pct": drop_pct,
        })

        body = f"""
        <p style="color:#1a3a3a;font-size:16px;">
        Dear {seller_name},</p>

        <div style="background:#fffbf0;border-left:4px solid #e8a020;
        padding:16px 20px;border-radius:8px;margin:16px 0;">
            <h3 style="color:#9a6600;margin:0 0 8px;">
            ⚠️ Competitor Price Drop Alert</h3>
            <p style="margin:4px 0;color:#1a3a3a;">
            <b>Model:</b> SKF {model}</p>
            <p style="margin:4px 0;color:#1a3a3a;">
            <b>Your price:</b> ₹{my_price:.0f}</p>
            <p style="margin:4px 0;color:#9a6600;">
            <b>Competitor ({cheapest['seller_name']}):</b>
            ₹{current_low:.0f}
            ({drop_pct:.1f}% cheaper)</p>
        </div>

        <p style="color:#4a6a6a;font-size:14px;">
        A competitor is now selling cheaper than you.
        Consider adjusting your price to stay competitive
        or maintain your margin.</p>

        <div style="background:#f0f7f7;padding:16px;
        border-radius:8px;margin:16px 0;">
            <p style="margin:0;font-size:14px;color:#1a3a3a;">
            <b>Suggested action:</b> Check your dashboard
            for AI price recommendations to find the optimal
            price point.</p>
        </div>

        <a href="http://localhost:8501"
        style="display:inline-block;background:#1a8c8c;color:white;
        padding:12px 24px;border-radius:8px;text-decoration:none;
        font-weight:600;margin-top:12px;">
        View Dashboard & Adjust Price</a>
        """

        send_alert_email(
            f"⚠️ Competitor dropped price on SKF {model}",
            body,
            seller_email
        )

    return alerts


def run_all_checks(df):
    """
    Run all alert checks at once.
    Called by the scheduler every hour.
    """
    print("\n🔍 Running alert checks...")
    floor_alerts = check_price_floors(df)
    print(f"   Floor violations: {len(floor_alerts)}")

    sellers = get_all_registered_emails()
    competitor_alerts = []
    for seller in sellers:
        alerts = check_and_alert_price_drop(
            df, seller["email"], seller["name"]
        )
        competitor_alerts.extend(alerts)

    print(f"   Competitor alerts: {len(competitor_alerts)}")
    print("✅ Alert checks complete\n")
    return floor_alerts, competitor_alerts