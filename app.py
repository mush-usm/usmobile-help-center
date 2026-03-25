import streamlit as st
import requests
import html
import re
from datetime import datetime

# ── Config ────────────────────────────────────────────────────────────────────
ZENDESK_SUBDOMAIN = "help-usm"
ZENDESK_BASE = f"https://{ZENDESK_SUBDOMAIN}.zendesk.com/api/v2/help_center"
LOCALE = "en-us"
CACHE_TTL = 300  # 5 min — keeps content fresh from Zendesk

st.set_page_config(
    page_title="US Mobile Help Center",
    page_icon="https://www.usmobile.com/favicon.ico",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Section icons mapping ─────────────────────────────────────────────────────
SECTION_ICONS = {
    "Getting Started": "rocket",
    "Managing Lines": "sliders",
    "Device Setup": "smartphone",
    "Billing and Payments": "credit-card",
    "International Travel": "globe",
    "Troubleshooting": "tool",
}

def get_icon(section_name):
    icon = SECTION_ICONS.get(section_name, "file-text")
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><use href="#{icon}"/></svg>'

# ── Styles ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

.stApp { background: #f7f8fc; }
[data-testid="stSidebar"] { display: none; }
header[data-testid="stHeader"] { display: none; }
.block-container { padding-top: 0 !important; max-width: 1200px; }

/* Top bar */
.topbar {
    background: linear-gradient(135deg, #0a0a23 0%, #161638 100%);
    padding: 14px 40px;
    display: flex; align-items: center; justify-content: space-between;
    margin: -1rem -4rem 0 -4rem;
    border-bottom: 3px solid #4f6ef7;
    position: sticky; top: 0; z-index: 999;
}
.topbar-logo {
    color: white; font-family: 'Inter', sans-serif;
    font-weight: 800; font-size: 20px; letter-spacing: -0.5px;
}
.topbar-logo span { color: #4f6ef7; }
.topbar-links { display: flex; gap: 20px; }
.topbar-links a {
    color: rgba(255,255,255,0.65); text-decoration: none;
    font-family: 'Inter', sans-serif; font-size: 13px; font-weight: 500;
    transition: color 0.2s;
}
.topbar-links a:hover { color: white; }

/* Hero */
.hero {
    background: linear-gradient(135deg, #0a0a23 0%, #1a1a3e 50%, #2d1b69 100%);
    padding: 56px 40px 44px; margin: 0 -4rem; text-align: center;
    position: relative; overflow: hidden;
}
.hero::before {
    content: ''; position: absolute; top: -50%; left: -50%; width: 200%; height: 200%;
    background: radial-gradient(circle at 30% 50%, rgba(79,110,247,0.12) 0%, transparent 50%),
                radial-gradient(circle at 70% 50%, rgba(139,92,246,0.08) 0%, transparent 50%);
}
.hero h1 {
    color: white; font-family: 'Inter', sans-serif; font-weight: 800;
    font-size: 38px; margin: 0 0 10px 0; position: relative; letter-spacing: -1px;
}
.hero p {
    color: rgba(255,255,255,0.55); font-family: 'Inter', sans-serif;
    font-size: 17px; margin: 0; position: relative;
}

/* Section pills */
.pill-grid {
    display: flex; flex-wrap: wrap; gap: 10px; justify-content: center;
    margin: 28px auto 0; max-width: 780px; position: relative;
}
.pill {
    background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.12);
    color: white; padding: 9px 20px; border-radius: 50px;
    font-family: 'Inter', sans-serif; font-size: 13px; font-weight: 500;
    transition: all 0.2s; display: inline-flex; align-items: center; gap: 7px;
}
.pill:hover {
    background: rgba(79,110,247,0.3); border-color: rgba(79,110,247,0.5);
    transform: translateY(-1px);
}

/* Section heading */
.section-heading {
    font-family: 'Inter', sans-serif; font-weight: 700; font-size: 22px;
    color: #1a1a2e; margin: 36px 0 18px 0;
    padding-bottom: 10px; border-bottom: 2px solid #e8eaf0;
    display: flex; align-items: center; gap: 10px;
}
.section-heading .count {
    background: #eef2ff; color: #4f6ef7; padding: 2px 10px;
    border-radius: 20px; font-size: 13px; font-weight: 600;
}

/* Article cards */
.article-card {
    background: white; border-radius: 14px; padding: 24px 26px;
    border: 1px solid #e8eaf0; transition: all 0.22s ease;
    cursor: pointer; height: 100%; display: flex; flex-direction: column;
}
.article-card:hover {
    border-color: #4f6ef7;
    box-shadow: 0 8px 28px rgba(79,110,247,0.10);
    transform: translateY(-2px);
}
.article-card h3 {
    font-family: 'Inter', sans-serif; font-weight: 600; font-size: 16px;
    color: #1a1a2e; margin: 0 0 8px 0; line-height: 1.4;
}
.article-card .excerpt {
    font-family: 'Inter', sans-serif; font-size: 13.5px; color: #6b7280;
    line-height: 1.6; flex: 1; margin: 0 0 14px 0;
}
.article-card .meta {
    display: flex; align-items: center; gap: 12px;
    font-family: 'Inter', sans-serif; font-size: 11.5px; color: #9ca3af;
}
.article-card .badge {
    background: #eef2ff; color: #4f6ef7; padding: 3px 10px;
    border-radius: 20px; font-size: 11px; font-weight: 600;
}

/* Article detail */
.article-detail {
    background: white; border-radius: 18px; padding: 44px 52px;
    border: 1px solid #e8eaf0; margin: 28px auto;
    max-width: 820px; box-shadow: 0 4px 20px rgba(0,0,0,0.03);
}
.article-detail h1 {
    font-family: 'Inter', sans-serif; font-weight: 800; font-size: 30px;
    color: #1a1a2e; margin: 0 0 14px 0; letter-spacing: -0.5px; line-height: 1.3;
}
.article-detail .article-meta {
    display: flex; gap: 16px; color: #9ca3af;
    font-family: 'Inter', sans-serif; font-size: 13px;
    margin-bottom: 28px; padding-bottom: 20px; border-bottom: 1px solid #f0f0f5;
}
.article-detail .article-body {
    font-family: 'Inter', sans-serif; font-size: 15.5px; line-height: 1.8; color: #374151;
}
.article-detail .article-body h2 {
    font-size: 21px; color: #1a1a2e; margin: 28px 0 14px; font-weight: 700;
}
.article-detail .article-body h3 {
    font-size: 17px; color: #1a1a2e; margin: 22px 0 10px; font-weight: 600;
}
.article-detail .article-body a { color: #4f6ef7; }
.article-detail .article-body img { max-width: 100%; border-radius: 10px; margin: 14px 0; }
.article-detail .article-body ul, .article-detail .article-body ol { padding-left: 22px; }
.article-detail .article-body li { margin-bottom: 6px; }
.article-detail .article-body code {
    background: #f3f4f6; padding: 2px 7px; border-radius: 5px; font-size: 13.5px;
}
.article-detail .article-body blockquote {
    border-left: 3px solid #4f6ef7; padding: 12px 18px; color: #6b7280;
    margin: 16px 0; background: #f8f9ff; border-radius: 0 8px 8px 0;
    font-size: 14.5px;
}
.article-detail .article-body table {
    width: 100%; border-collapse: collapse; margin: 16px 0;
}
.article-detail .article-body th, .article-detail .article-body td {
    padding: 10px 14px; border: 1px solid #e8eaf0; text-align: left; font-size: 14px;
}
.article-detail .article-body th {
    background: #f8f9fc; font-weight: 600;
}

/* Breadcrumb */
.breadcrumb {
    font-family: 'Inter', sans-serif; font-size: 13px; color: #9ca3af;
    margin: 20px auto 0; max-width: 820px;
}
.breadcrumb a { color: #4f6ef7; text-decoration: none; }
.breadcrumb a:hover { text-decoration: underline; }

/* Category header */
.category-header {
    background: linear-gradient(135deg, #0a0a23 0%, #1a1a3e 100%);
    padding: 36px 40px; margin: 0 -4rem; text-align: center;
    border-bottom: 3px solid #4f6ef7;
}
.category-header h2 {
    color: white; font-family: 'Inter', sans-serif; font-weight: 700;
    font-size: 28px; margin: 0 0 6px 0;
}
.category-header p {
    color: rgba(255,255,255,0.5); font-family: 'Inter', sans-serif;
    font-size: 14px; margin: 0;
}

/* Section card (for browse view) */
.section-card {
    background: white; border-radius: 16px; padding: 28px;
    border: 1px solid #e8eaf0; transition: all 0.2s;
    height: 100%;
}
.section-card:hover { border-color: #4f6ef7; box-shadow: 0 4px 16px rgba(79,110,247,0.08); }
.section-card h3 {
    font-family: 'Inter', sans-serif; font-weight: 700; font-size: 18px;
    color: #1a1a2e; margin: 0 0 6px 0;
}
.section-card .sec-count {
    font-family: 'Inter', sans-serif; font-size: 13px; color: #9ca3af; margin: 0 0 16px 0;
}
.section-card .sec-article {
    padding: 10px 0; border-bottom: 1px solid #f3f4f6;
    font-family: 'Inter', sans-serif; font-size: 14px; color: #374151;
    display: flex; align-items: center; gap: 8px;
}
.section-card .sec-article:last-child { border-bottom: none; }
.section-card .sec-article .dot { color: #4f6ef7; font-size: 8px; }

/* Search result */
.search-result {
    background: white; border-radius: 12px; padding: 22px;
    border: 1px solid #e8eaf0; margin-bottom: 10px; transition: all 0.2s;
}
.search-result:hover { border-color: #4f6ef7; box-shadow: 0 4px 12px rgba(79,110,247,0.08); }
.search-result h3 {
    font-family: 'Inter', sans-serif; font-weight: 600; font-size: 16px;
    color: #1a1a2e; margin: 0 0 6px 0;
}
.search-result .snippet {
    font-family: 'Inter', sans-serif; font-size: 13.5px; color: #6b7280; line-height: 1.6;
}

/* Empty / vote */
.empty-state { text-align: center; padding: 60px 40px; }
.empty-state h3 {
    font-family: 'Inter', sans-serif; font-weight: 600; font-size: 18px;
    color: #1a1a2e; margin: 12px 0 6px 0;
}
.empty-state p { font-family: 'Inter', sans-serif; font-size: 14px; color: #9ca3af; }
.vote-section {
    text-align: center; padding: 28px; margin: 28px 0 0; border-top: 1px solid #f0f0f5;
}
.vote-section p {
    font-family: 'Inter', sans-serif; font-size: 14px; color: #6b7280; margin: 0 0 10px 0;
}

/* Footer */
.footer {
    text-align: center; padding: 36px; margin: 50px -4rem 0;
    background: #0a0a23; color: rgba(255,255,255,0.35);
    font-family: 'Inter', sans-serif; font-size: 12.5px;
}
.footer a { color: rgba(255,255,255,0.45); text-decoration: none; }

/* Streamlit button overrides */
.stButton > button {
    background: #4f6ef7; color: white; border: none; border-radius: 8px;
    font-family: 'Inter', sans-serif; font-weight: 600; padding: 7px 18px;
    font-size: 13px; transition: all 0.2s;
}
.stButton > button:hover {
    background: #3b5de7; box-shadow: 0 4px 12px rgba(79,110,247,0.25);
}
.stTextInput > div > div > input {
    border-radius: 10px; border: 2px solid #e8eaf0;
    font-family: 'Inter', sans-serif; padding: 11px 16px; font-size: 14.5px;
}
.stTextInput > div > div > input:focus {
    border-color: #4f6ef7; box-shadow: 0 0 0 3px rgba(79,110,247,0.1);
}
</style>
""", unsafe_allow_html=True)


# ── API helpers ───────────────────────────────────────────────────────────────
@st.cache_data(ttl=CACHE_TTL)
def fetch_sections():
    try:
        r = requests.get(f"{ZENDESK_BASE}/{LOCALE}/sections.json?per_page=100", timeout=10)
        r.raise_for_status()
        return r.json().get("sections", [])
    except Exception:
        return []

@st.cache_data(ttl=CACHE_TTL)
def fetch_all_articles():
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

@st.cache_data(ttl=CACHE_TTL)
def fetch_article(article_id):
    try:
        r = requests.get(f"{ZENDESK_BASE}/{LOCALE}/articles/{article_id}.json", timeout=10)
        r.raise_for_status()
        return r.json().get("article")
    except Exception:
        return None

@st.cache_data(ttl=CACHE_TTL)
def search_articles(query):
    try:
        r = requests.get(
            f"{ZENDESK_BASE}/articles/search.json",
            params={"query": query, "per_page": 25}, timeout=10,
        )
        r.raise_for_status()
        return r.json().get("results", [])
    except Exception:
        return []


# ── Helpers ───────────────────────────────────────────────────────────────────
def strip_html(text, max_len=150):
    if not text:
        return ""
    clean = re.sub(r'<[^>]+>', ' ', text)
    clean = html.unescape(clean)
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

def section_name_by_id(sections, sid):
    s = next((s for s in sections if s["id"] == sid), None)
    return s["name"] if s else ""


# ── State ─────────────────────────────────────────────────────────────────────
if "page" not in st.session_state:
    st.session_state.page = "home"
if "article_id" not in st.session_state:
    st.session_state.article_id = None
if "section_id" not in st.session_state:
    st.session_state.section_id = None
if "search_query" not in st.session_state:
    st.session_state.search_query = ""

def go_home():
    st.session_state.page = "home"
    st.session_state.article_id = None
    st.session_state.section_id = None
    st.session_state.search_query = ""

def go_article(aid):
    st.session_state.page = "article"
    st.session_state.article_id = aid

def go_section(sid):
    st.session_state.page = "section"
    st.session_state.section_id = sid

def go_search():
    st.session_state.page = "search"


# ── Fetch data ────────────────────────────────────────────────────────────────
sections = fetch_sections()
all_articles = fetch_all_articles()


# ── Top bar ───────────────────────────────────────────────────────────────────
st.markdown("""
<div class="topbar">
    <div class="topbar-logo">US Mobile <span>Help Center</span></div>
    <div class="topbar-links">
        <a href="https://www.usmobile.com" target="_blank">US Mobile</a>
        <a href="https://www.usmobile.com/community" target="_blank">Community</a>
        <a href="https://www.usmobile.com/contact" target="_blank">Contact Us</a>
    </div>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# HOME
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.page == "home":

    # Hero
    st.markdown("""
    <div class="hero">
        <h1>How can we help?</h1>
        <p>Search our knowledge base or browse by topic</p>
    </div>
    """, unsafe_allow_html=True)

    # Search bar
    _, col_s, _ = st.columns([1, 3, 1])
    with col_s:
        q = st.text_input("Search", placeholder="Search for help articles...", label_visibility="collapsed", key="hs")
        if q:
            st.session_state.search_query = q
            go_search()
            st.rerun()

    # Section pills (these are the main navigational categories)
    if sections:
        pills = '<div class="pill-grid">'
        for sec in sections:
            pills += f'<span class="pill">{html.escape(sec["name"])}</span>'
        pills += '</div>'
        st.markdown(pills, unsafe_allow_html=True)

        # Functional section buttons
        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
        ncols = min(len(sections), 6)
        scols = st.columns(ncols)
        for i, sec in enumerate(sections):
            with scols[i % ncols]:
                if st.button(sec["name"], key=f"sec_{sec['id']}", use_container_width=True):
                    go_section(sec["id"])
                    st.rerun()

    # ── Recently Updated ──────────────────────────────────────────────────────
    if all_articles:
        recent = sorted(all_articles, key=lambda a: a.get("updated_at", ""), reverse=True)[:6]
        st.markdown('<div class="section-heading">Recently Updated</div>', unsafe_allow_html=True)
        for row_start in range(0, len(recent), 3):
            cols = st.columns(3)
            for j, art in enumerate(recent[row_start:row_start+3]):
                with cols[j]:
                    sname = section_name_by_id(sections, art.get("section_id"))
                    excerpt = strip_html(art.get("body", ""))
                    st.markdown(f"""
                    <div class="article-card">
                        <h3>{html.escape(art['title'])}</h3>
                        <p class="excerpt">{html.escape(excerpt)}</p>
                        <div class="meta">
                            {'<span class="badge">'+html.escape(sname)+'</span>' if sname else ''}
                            <span>{format_date(art.get('updated_at',''))}</span>
                        </div>
                    </div>""", unsafe_allow_html=True)
                    if st.button("Read", key=f"r_{art['id']}", use_container_width=True):
                        go_article(art["id"])
                        st.rerun()

    # ── Most Popular (by votes) ───────────────────────────────────────────────
    if all_articles:
        popular = sorted(all_articles, key=lambda a: a.get("vote_sum", 0), reverse=True)[:6]
        # Only show if there are articles with votes
        if popular[0].get("vote_sum", 0) > 0:
            st.markdown('<div class="section-heading">Most Popular</div>', unsafe_allow_html=True)
            for row_start in range(0, len(popular), 3):
                cols = st.columns(3)
                for j, art in enumerate(popular[row_start:row_start+3]):
                    with cols[j]:
                        sname = section_name_by_id(sections, art.get("section_id"))
                        excerpt = strip_html(art.get("body", ""))
                        st.markdown(f"""
                        <div class="article-card">
                            <h3>{html.escape(art['title'])}</h3>
                            <p class="excerpt">{html.escape(excerpt)}</p>
                            <div class="meta">
                                {'<span class="badge">'+html.escape(sname)+'</span>' if sname else ''}
                                <span>{format_date(art.get('updated_at',''))}</span>
                            </div>
                        </div>""", unsafe_allow_html=True)
                        if st.button("Read", key=f"p_{art['id']}", use_container_width=True):
                            go_article(art["id"])
                            st.rerun()

    # ── Browse All Sections ───────────────────────────────────────────────────
    if sections:
        st.markdown('<div class="section-heading">Browse by Topic</div>', unsafe_allow_html=True)
        for row_start in range(0, len(sections), 3):
            cols = st.columns(3)
            for j, sec in enumerate(sections[row_start:row_start+3]):
                with cols[j]:
                    sec_articles = [a for a in all_articles if a.get("section_id") == sec["id"]]
                    preview = sec_articles[:4]
                    items_html = ""
                    for pa in preview:
                        items_html += f'<div class="sec-article"><span class="dot">&#9679;</span> {html.escape(pa["title"])}</div>'
                    if len(sec_articles) > 4:
                        items_html += f'<div class="sec-article" style="color:#4f6ef7;font-weight:500;">+ {len(sec_articles)-4} more articles</div>'

                    st.markdown(f"""
                    <div class="section-card">
                        <h3>{html.escape(sec['name'])}</h3>
                        <p class="sec-count">{len(sec_articles)} articles</p>
                        {items_html}
                    </div>""", unsafe_allow_html=True)
                    if st.button("View all", key=f"vs_{sec['id']}", use_container_width=True):
                        go_section(sec["id"])
                        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# ARTICLE DETAIL
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "article":
    article = fetch_article(st.session_state.article_id)
    if not article:
        # fallback to cached list
        article = next((a for a in all_articles if a["id"] == st.session_state.article_id), None)

    if article:
        sname = section_name_by_id(sections, article.get("section_id"))
        st.markdown(f"""
        <div class="breadcrumb">
            <a href="#">Home</a> / <a href="#">{html.escape(sname)}</a> / {html.escape(article['title'])}
        </div>""", unsafe_allow_html=True)

        if st.button("← Back", key="back_art"):
            go_home()
            st.rerun()

        labels = article.get("label_names", [])
        labels_html = " ".join(f'<span class="badge" style="margin-right:4px;">{html.escape(l)}</span>' for l in labels[:6]) if labels else ""

        st.markdown(f"""
        <div class="article-detail">
            <h1>{html.escape(article['title'])}</h1>
            <div class="article-meta">
                <span>Updated {format_date(article.get('updated_at',''))}</span>
                <span>Created {format_date(article.get('created_at',''))}</span>
                {f'<span>&#9650; {article.get("vote_sum",0)} votes</span>' if article.get('vote_sum') else ''}
            </div>
            <div class="article-body">
                {article.get('body', '<p>No content available.</p>')}
            </div>
            {('<div style="margin-top:20px;">'+labels_html+'</div>') if labels_html else ''}
            <div class="vote-section">
                <p>Was this article helpful?</p>
            </div>
        </div>""", unsafe_allow_html=True)

        c1, c2, _ = st.columns([1, 1, 4])
        with c1:
            st.button("Yes, thanks!", key="vu")
        with c2:
            st.button("Not really", key="vd")

        # Related articles from same section
        same = [a for a in all_articles if a.get("section_id") == article.get("section_id") and a["id"] != article["id"]][:4]
        if same:
            st.markdown(f'<div class="section-heading" style="max-width:820px;margin-left:auto;margin-right:auto;">More from {html.escape(sname)}</div>', unsafe_allow_html=True)
            cols = st.columns(min(len(same), 4))
            for i, rel in enumerate(same):
                with cols[i]:
                    st.markdown(f"""
                    <div class="article-card">
                        <h3>{html.escape(rel['title'])}</h3>
                        <p class="excerpt">{html.escape(strip_html(rel.get('body',''), 100))}</p>
                    </div>""", unsafe_allow_html=True)
                    if st.button("Read", key=f"rel_{rel['id']}", use_container_width=True):
                        go_article(rel["id"])
                        st.rerun()
    else:
        st.warning("Article not found.")
        if st.button("← Home"):
            go_home()
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# SECTION PAGE
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "section":
    sec = next((s for s in sections if s["id"] == st.session_state.section_id), None)
    if sec:
        sec_articles = [a for a in all_articles if a.get("section_id") == sec["id"]]
        st.markdown(f"""
        <div class="category-header">
            <h2>{html.escape(sec['name'])}</h2>
            <p>{len(sec_articles)} articles</p>
        </div>""", unsafe_allow_html=True)

        if st.button("← Back to Home", key="back_sec"):
            go_home()
            st.rerun()

        if sec_articles:
            for art in sec_articles:
                excerpt = strip_html(art.get("body", ""), 200)
                st.markdown(f"""
                <div class="search-result">
                    <h3>{html.escape(art['title'])}</h3>
                    <p class="snippet">{html.escape(excerpt)}</p>
                </div>""", unsafe_allow_html=True)
                if st.button(art["title"][:50], key=f"sa_{art['id']}", use_container_width=True):
                    go_article(art["id"])
                    st.rerun()
        else:
            st.markdown("""
            <div class="empty-state">
                <h3>No articles yet</h3>
                <p>Articles will appear here once published.</p>
            </div>""", unsafe_allow_html=True)
    else:
        st.warning("Section not found.")
        if st.button("← Home"):
            go_home()
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# SEARCH
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "search":
    st.markdown("""
    <div class="category-header">
        <h2>Search Results</h2>
    </div>""", unsafe_allow_html=True)

    if st.button("← Back to Home", key="back_search"):
        go_home()
        st.rerun()

    sq = st.text_input("Search", value=st.session_state.search_query, placeholder="Search...", label_visibility="collapsed", key="spi")
    if sq != st.session_state.search_query:
        st.session_state.search_query = sq

    if st.session_state.search_query:
        results = search_articles(st.session_state.search_query)
        if results:
            st.markdown(f"<p style='font-family:Inter;color:#6b7280;margin:6px 0 16px;font-size:14px;'>{len(results)} result{'s' if len(results)!=1 else ''} for \"{html.escape(st.session_state.search_query)}\"</p>", unsafe_allow_html=True)
            for art in results:
                snippet = strip_html(art.get("body", art.get("snippet", "")), 200)
                st.markdown(f"""
                <div class="search-result">
                    <h3>{html.escape(art.get('title','Untitled'))}</h3>
                    <p class="snippet">{html.escape(snippet)}</p>
                </div>""", unsafe_allow_html=True)
                if st.button("View", key=f"sr_{art['id']}", use_container_width=True):
                    go_article(art["id"])
                    st.rerun()
        else:
            st.markdown("""
            <div class="empty-state">
                <h3>No results found</h3>
                <p>Try different keywords or browse by topic.</p>
            </div>""", unsafe_allow_html=True)


# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="footer">
    <p>&copy; 2026 US Mobile Inc. All rights reserved.</p>
    <p style="margin-top:6px;">
        <a href="https://www.usmobile.com">usmobile.com</a> &middot;
        <a href="https://www.usmobile.com/privacy">Privacy</a> &middot;
        <a href="https://www.usmobile.com/terms">Terms</a>
    </p>
</div>""", unsafe_allow_html=True)
