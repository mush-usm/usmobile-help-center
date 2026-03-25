import re
import time
import html as html_lib
from datetime import datetime
from pathlib import Path

import requests
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader

# ── Config ────────────────────────────────────────────────────────────────────
ZENDESK_SUBDOMAIN = "help-usm"
ZENDESK_BASE = f"https://{ZENDESK_SUBDOMAIN}.zendesk.com/api/v2/help_center"
LOCALE = "en-us"
CANONICAL_BASE = "https://www.usmobile.com/help"
CACHE_TTL = 300  # 5 minutes

app = FastAPI()
jinja_env = Environment(
    loader=FileSystemLoader(str(Path(__file__).parent / "templates")),
    autoescape=True,
)


def render(template_name: str, **context) -> HTMLResponse:
    tpl = jinja_env.get_template(template_name)
    return HTMLResponse(tpl.render(**context))


# ── Cache ─────────────────────────────────────────────────────────────────────
_cache = {}

def cached_get(key, fetcher):
    """Simple TTL cache wrapper."""
    now = time.time()
    if key in _cache and now - _cache[key]["ts"] < CACHE_TTL:
        return _cache[key]["data"]
    data = fetcher()
    _cache[key] = {"data": data, "ts": now}
    return data


# ── Zendesk API ───────────────────────────────────────────────────────────────
def _fetch_sections():
    try:
        r = requests.get(f"{ZENDESK_BASE}/{LOCALE}/sections.json?per_page=100", timeout=10)
        r.raise_for_status()
        return r.json().get("sections", [])
    except Exception:
        return []

def _fetch_all_articles():
    articles = []
    url = f"{ZENDESK_BASE}/{LOCALE}/articles.json"
    params = {"per_page": 100, "sort_by": "position", "sort_order": "asc"}
    try:
        while url:
            r = requests.get(url, params=params, timeout=15)
            r.raise_for_status()
            data = r.json()
            articles.extend(data.get("articles", []))
            url = data.get("next_page")
            params = {}
        return articles
    except Exception:
        return []

def _search_articles(query):
    try:
        r = requests.get(
            f"{ZENDESK_BASE}/articles/search.json",
            params={"query": query, "per_page": 25}, timeout=10,
        )
        r.raise_for_status()
        return r.json().get("results", [])
    except Exception:
        return []

def get_sections():
    return cached_get("sections", _fetch_sections)

def get_articles():
    return cached_get("articles", _fetch_all_articles)


# ── Helpers ───────────────────────────────────────────────────────────────────
def slugify(text):
    if not text:
        return ""
    slug = text.lower().strip()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    return re.sub(r'-+', '-', slug).strip('-')

def article_slug(article):
    html_url = article.get("html_url", "")
    match = re.search(r'/articles/\d+-(.+)$', html_url)
    if match:
        return match.group(1)
    return slugify(article.get("title", str(article.get("id", ""))))

def section_slug(section):
    return slugify(section.get("name", str(section.get("id", ""))))

def strip_html(text, max_len=150):
    if not text:
        return ""
    clean = re.sub(r'<[^>]+>', ' ', text)
    clean = html_lib.unescape(clean)
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean[:max_len] + "..." if len(clean) > max_len else clean

def format_date(date_str):
    if not date_str:
        return ""
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return dt.strftime("%b %d, %Y")
    except Exception:
        return date_str[:10]

def enrich_article(art, sections):
    """Add computed fields to article dict."""
    art["_slug"] = article_slug(art)
    art["_excerpt"] = strip_html(art.get("body", ""), 150)
    art["_excerpt_short"] = strip_html(art.get("body", ""), 100)
    art["_date"] = format_date(art.get("updated_at", ""))
    art["_updated"] = format_date(art.get("updated_at", ""))
    art["_created"] = format_date(art.get("created_at", ""))
    sec = next((s for s in sections if s["id"] == art.get("section_id")), None)
    art["_section_name"] = sec["name"] if sec else ""
    return art

def enrich_section(sec, articles):
    """Add computed fields to section dict."""
    sec["_slug"] = section_slug(sec)
    sec_articles = [a for a in articles if a.get("section_id") == sec["id"]]
    sec["_article_count"] = len(sec_articles)
    sec["_preview"] = sec_articles[:4]
    return sec


# ── Routes ────────────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    sections = get_sections()
    articles = get_articles()

    # Enrich all
    for a in articles:
        enrich_article(a, sections)
    for s in sections:
        enrich_section(s, articles)

    recent = sorted(articles, key=lambda a: a.get("updated_at", ""), reverse=True)[:6]
    popular = sorted(articles, key=lambda a: a.get("vote_sum", 0), reverse=True)[:6]
    if popular and popular[0].get("vote_sum", 0) == 0:
        popular = []

    return render("home.html",
        sections=sections, recent=recent, popular=popular,
        canonical_base=CANONICAL_BASE,
    )


@app.get("/article/{slug}", response_class=HTMLResponse)
async def article_page(request: Request, slug: str):
    sections = get_sections()
    articles = get_articles()
    for a in articles:
        enrich_article(a, sections)

    article = next((a for a in articles if a["_slug"] == slug), None)
    if not article:
        return HTMLResponse("<h1>Article not found</h1><a href='/'>Go home</a>", status_code=404)

    section = next((s for s in sections if s["id"] == article.get("section_id")), None)
    if section:
        section["_slug"] = section_slug(section)

    related = [a for a in articles if a.get("section_id") == article.get("section_id") and a["id"] != article["id"]][:4]

    return render("article.html",
        article=article, section=section, related=related,
        canonical_base=CANONICAL_BASE,
    )


@app.get("/section/{slug}", response_class=HTMLResponse)
async def section_page(request: Request, slug: str):
    sections = get_sections()
    articles = get_articles()
    for a in articles:
        enrich_article(a, sections)

    section = next((s for s in sections if section_slug(s) == slug), None)
    if not section:
        return HTMLResponse("<h1>Section not found</h1><a href='/'>Go home</a>", status_code=404)

    section["_slug"] = section_slug(section)
    sec_articles = [a for a in articles if a.get("section_id") == section["id"]]

    return render("section.html",
        section=section, articles=sec_articles,
        canonical_base=CANONICAL_BASE,
    )


@app.get("/search", response_class=HTMLResponse)
async def search_page(request: Request, q: str = ""):
    sections = get_sections()
    results = []
    if q:
        results = _search_articles(q)
        for a in results:
            enrich_article(a, sections)

    return render("search.html",
        query=q, results=results,
        canonical_base=CANONICAL_BASE,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8502)
