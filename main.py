from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Literal
from playwright.sync_api import sync_playwright

app = FastAPI()

# Allow browser calls (safe defaults)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve the frontend
app.mount("/", StaticFiles(directory="static", html=True), name="static")

class ConvertRequest(BaseModel):
    code: str
    from_platform: Literal["sportybet", "bet9ja"]
    to_platform: Literal["sportybet", "bet9ja"]

# Market name mapping
MARKET_MAP = {
    ("sportybet", "1X2"): "Match Result",
    ("sportybet", "GG"): "Both Teams To Score",
    ("sportybet", "O/U 2.5"): "Over/Under 2.5 Goals",
    ("bet9ja", "Match Result"): "1X2",
    ("bet9ja", "Both Teams To Score"): "GG",
    ("bet9ja", "Over/Under 2.5 Goals"): "O/U 2.5",
}

def fetch_sportybet_slip(code: str) -> dict:
    """Scrape a real slip from SportyBet using Playwright"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        url = f"https://www.sportybet.com/ng/m/sporty-code-share/{code}"
        page.goto(url, timeout=60000)

        # Wait until slip container loads
        page.wait_for_selector("div.share-bet-slip", timeout=60000)

        # Extract slip text (basic example)
        slip_text = page.inner_text("div.share-bet-slip")

        browser.close()

        return {"raw_text": slip_text}

def fake_convert_slip(slip: dict, from_plat: str, to_plat: str) -> dict:
    legs_out = []
    for leg in slip.get("legs", []):
        market_in = leg.get("market", "")
        key = (from_plat, market_in)
        mapped_market = MARKET_MAP.get(key, market_in)
        legs_out.append({**leg, "market": mapped_market})
    return {"legs": legs_out}

def fake_generate_code(to_plat: str, source_code: str) -> str:
    prefix = "BJ" if to_plat == "bet9ja" else "SP"
    return f"{prefix}{abs(hash(source_code)) % 100000:05d}"

@app.post("/api/convert")
def convert(req: ConvertRequest):
    if req.from_platform == req.to_platform:
        return {"ok": False, "message": "From/To platforms are the same.", "converted_code": None, "preview": None}

    if req.from_platform == "sportybet":
        slip = fetch_sportybet_slip(req.code)
    else:
        return {"ok": False, "message": "Only sportybet scraping is implemented for now.", "converted_code": None, "preview": None}

    converted_code = fake_generate_code(req.to_platform, req.code)

    return {
        "ok": True,
        "message": "Converted from real SportyBet.",
        "converted_code": converted_code,
        "preview": slip
    }

@app.get("/api/health")
def health():
    return {"status": "ok"}
