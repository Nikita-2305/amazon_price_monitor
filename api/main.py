from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy.orm import declarative_base
from passlib.context import CryptContext
from datetime import datetime
import secrets
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db.models import engine, SessionLocal

app = FastAPI()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

pwd_context = CryptContext(
    schemes=["pbkdf2_sha256"],
    deprecated="auto"
)

sessions = {}

# ── Seller DB model ───────────────────────────────────
Base = declarative_base()

class Seller(Base):
    __tablename__ = "sellers"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100))
    email = Column(String(100), unique=True, index=True)
    company = Column(String(100))
    hashed_password = Column(String(200))
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(engine)

# ── Helpers ───────────────────────────────────────────
def get_seller(email: str):
    db = SessionLocal()
    try:
        seller = db.query(Seller).filter(Seller.email == email).first()
        return seller
    finally:
        db.close()

# ── Routes ────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def landing(request: Request):
    return templates.TemplateResponse(
        request=request, name="landing.html", context={}
    )

@app.get("/login", response_class=HTMLResponse)
async def login_get(request: Request, registered: str = None):
    success = "Account created! Please log in." if registered else None
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"error": None, "success": success}
    )

@app.post("/login", response_class=HTMLResponse)
async def login_post(
    request: Request,
    email: str = Form(...),
    password: str = Form(...)
):
    try:
        email = email.strip().lower()
        password = password.strip()

        seller = get_seller(email)

        if not seller:
            return templates.TemplateResponse(
                request=request,
                name="login.html",
                context={"error": "User not found.", "success": None}
            )

        try:
            is_valid = pwd_context.verify(password, seller.hashed_password)
        except Exception as e:
            return templates.TemplateResponse(
                request=request,
                name="login.html",
                context={"error": f"Hash error: {str(e)}", "success": None}
            )

        if not is_valid:
            return templates.TemplateResponse(
                request=request,
                name="login.html",
                context={"error": "Wrong password.", "success": None}
            )

        token = secrets.token_hex(32)
        # ✅ FIX 2 & 3: Store name, email, and company in session
        sessions[token] = {
            "email": email,
            "name": seller.name,
            "company": seller.company or "",
        }

        response = RedirectResponse(url="/dashboard", status_code=302)
        response.set_cookie("session_token", token, httponly=True, max_age=86400)
        return response

    except Exception as e:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"error": f"Login error: {str(e)}", "success": None}
        )

@app.get("/register", response_class=HTMLResponse)
async def register_get(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="register.html",
        context={"error": None}
    )

@app.post("/register", response_class=HTMLResponse)
async def register_post(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    company: str = Form(...),
    password: str = Form(...)
):
    try:
        email = email.strip().lower()
        password = password.strip()

        existing = get_seller(email)
        if existing:
            return templates.TemplateResponse(
                request=request,
                name="register.html",
                context={"error": "Email already registered. Please login."}
            )

        db = SessionLocal()
        try:
            seller = Seller(
                name=name,
                email=email,
                company=company,
                hashed_password=pwd_context.hash(password),
                created_at=datetime.utcnow()
            )
            db.add(seller)
            db.commit()
        finally:
            db.close()

        return RedirectResponse(url="/login?registered=true", status_code=302)

    except Exception as e:
        return templates.TemplateResponse(
            request=request,
            name="register.html",
            context={"error": f"Registration error: {str(e)}"}
        )

@app.get("/dashboard")
async def dashboard(request: Request):
    token = request.cookies.get("session_token")
    if not token or token not in sessions:
        return RedirectResponse(url="/login")
    # ✅ FIX 2 & 3: Pass seller name and email to Streamlit via query params
    session = sessions[token]
    seller_name = session.get("name", "Seller")
    seller_email = session.get("email", "")
    redirect_url = (
        f"http://localhost:8501"
        f"?seller_name={seller_name}"
        f"&seller_email={seller_email}"
        f"&token={token}"
    )
    return RedirectResponse(url=redirect_url, status_code=302)

# ✅ FIX 2 & 3: New API endpoint — Streamlit calls this to get session info
@app.get("/api/session")
async def get_session_info(request: Request):
    token = request.query_params.get("token") or request.cookies.get("session_token")
    if not token or token not in sessions:
        return {"authenticated": False, "name": "", "email": "", "company": ""}
    session = sessions[token]
    return {
        "authenticated": True,
        "name": session.get("name", ""),
        "email": session.get("email", ""),
        "company": session.get("company", ""),
    }

@app.get("/logout")
async def logout(request: Request):
    token = request.cookies.get("session_token")
    if token and token in sessions:
        del sessions[token]
    response = RedirectResponse(url="/")
    response.delete_cookie("session_token")
    return response
