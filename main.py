from fastapi import FastAPI, HTTPException, Header, Depends
import httpx
import re
import os
from bs4 import BeautifulSoup

app = FastAPI(title="LeadRadar API")

# Security Gear
PROXY_SECRET = os.getenv("RAPIDAPI_PROXY_SECRET")

# Data Signatures
TECH_DB = {
    "E-commerce": {"Shopify": r"cdn\.shopify\.com", "WooCommerce": r"woocommerce"},
    "Stack": {"React": r"data-reactroot", "WordPress": r"wp-content"}
}

async def verify_request(x_rapidapi_proxy_secret: str = Header(None)):
    if x_rapidapi_proxy_secret != PROXY_SECRET:
        raise HTTPException(status_code=403, detail="Unauthorized")

@app.get("/analyze")
async def analyze_company(url: str, _ = Depends(verify_request)):
    target = url if url.startswith("http") else f"https://{url}"
    
    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        try:
            # 1. Tech Discovery (#8)
            res = await client.get(target)
            tech = [name for cat, techs in TECH_DB.items() 
                    for name, pat in techs.items() if re.search(pat, res.text)]
            
            # 2. Hiring Signals (#4)
            career_res = await client.get(f"{target}/careers")
            hiring = "hiring" in career_res.text.lower() if career_res.status_code == 200 else False
            
            # 3. StockWatch (#10) - Basic check for 'Out of Stock' text
            stockout = any(word in res.text.lower() for word in ["sold out", "out of stock"])

            return {
                "url": target,
                "tech_stack": tech,
                "is_hiring": hiring,
                "inventory_issue_detected": stockout,
                "lead_score": (len(tech) * 10) + (50 if hiring else 0) + (100 if stockout else 0)
            }
        except Exception as e:
            return {"error": "Scan failed", "msg": str(e)}
