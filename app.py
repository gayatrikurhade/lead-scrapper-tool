import streamlit as st
import pandas as pd
import requests
import time
import json
import os
from time import perf_counter
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

from dashboard_style import (
    inject_css,
    sidebar_brand,
    sidebar_nav,
    topbar,
    icon_stat_card,
    panel,
    COLORS)

try:
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

st.set_page_config(
    page_title="Lead Scrapper Tool",
    layout="wide",
    initial_sidebar_state="expanded")

inject_css()

ICONS = {
    "users": '''<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22"
    viewBox="0 0 24 24" fill="none" stroke="currentColor"
    stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/>
    <circle cx="9" cy="7" r="4"/>
    <path d="M22 21v-2a4 4 0 0 0-3-3.87"/>
    <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
    </svg>''',

    "user": '''<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22"
    viewBox="0 0 24 24" fill="none" stroke="currentColor"
    stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/>
    <circle cx="12" cy="7" r="4"/>
    </svg>''',

    "calendar_clock": '''<svg xmlns="http://www.w3.org/2000/svg" width="22"
    height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor"
    stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <path d="M21 7.5V6a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h4"/>
    <path d="M16 2v4"/>
    <path d="M8 2v4"/>
    <path d="M3 10h18"/>
    <circle cx="18" cy="18" r="4"/>
    <path d="M18 16.5v1.5l1 1"/>
    </svg>''',

    "repeat": '''<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22"
    viewBox="0 0 24 24" fill="none" stroke="currentColor"
    stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <path d="m17 2 4 4-4 4"/>
    <path d="M3 11v-1a4 4 0 0 1 4-4h14"/>
    <path d="m7 22-4-4 4-4"/>
    <path d="M21 13v1a4 4 0 0 1-4 4H3"/>
    </svg>''',

    "check_circle": '''<svg xmlns="http://www.w3.org/2000/svg" width="22"
    height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor"
    stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <path d="M21.801 10A10 10 0 1 1 17 3.335"/>
    <path d="m9 11 3 3L22 4"/>
    </svg>''',

    "x_circle": '''<svg xmlns="http://www.w3.org/2000/svg" width="22"
    height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor"
    stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <circle cx="12" cy="12" r="10"/>
    <path d="m15 9-6 6"/>
    <path d="m9 9 6 6"/>
    </svg>''',

    "building": '''<svg xmlns="http://www.w3.org/2000/svg" width="22"
    height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor"
    stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <path d="M6 22V4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v18Z"/>
    <path d="M6 12H4a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h2"/>
    <path d="M18 9h2a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2h-2"/>
    <path d="M10 6h4"/>
    <path d="M10 10h4"/>
    <path d="M10 14h4"/>
    <path d="M10 18h4"/>
    </svg>''',

    "plus_circle": '''<svg xmlns="http://www.w3.org/2000/svg" width="22"
    height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor"
    stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <circle cx="12" cy="12" r="10"/>
    <path d="M8 12h8"/>
    <path d="M12 8v8"/>
    </svg>''',

    "search": '''<svg xmlns="http://www.w3.org/2000/svg" width="22"
    height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor"
    stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <circle cx="11" cy="11" r="8"/>
    <path d="m21 21-4.3-4.3"/>
    </svg>''',

    "mail": '''<svg xmlns="http://www.w3.org/2000/svg" width="22"
    height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor"
    stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <rect width="20" height="16" x="2" y="4" rx="2"/>
    <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/>
    </svg>''',
}

PLACEHOLDER = "-- Select --"

SEEN_LEADS_FILE = "seen_leads.json"
USAGE_FILE = "daily_usage.json"
SETTINGS_FILE = "settings.json"
HISTORY_FILE = "leads_history.json"

DEFAULT_SETTINGS = { "daily_limit": 200,
                     "max_calls_per_day": 4}


CSC_API_BASE = "https://api.countrystatecity.in/v1"

@st.cache_data(ttl=86400 , show_spinner =False)
def csc_get(endpoint):
    try:
        api_key = st.secrets.get("CSC_API_KEY")
        if not api_key:
            return []
        response = requests.get(
            f"{CSC_API_BASE}{endpoint}",
            headers={"X-CSCAPI-KEY": api_key},
            timeout=15,
        )
        response.raise_for_status()
        return response.json()
    except Exception:
        return []

@st.cache_data(ttl=86400,show_spinner=False)
def get_all_csc_countries():
    return csc_get("/countries")

@st.cache_data(ttl=86400, show_spinner=False)
def get_country_code(country_name):
    for country in get_all_csc_countries():
        if country.get("name") == country_name:
            return country.get("iso2")
    return None

@st.cache_data(ttl=86400,show_spinner=False)
def get_country_names():
    return sorted(
        c["name"] for c in get_all_csc_countries()
        if c.get("name")
    )

@st.cache_data(ttl=86400,show_spinner = False)
def get_states_for_country(country_name):
    code = get_country_code(country_name)
    if not code:
        return []
    return sorted(
        csc_get(f"/countries/{code}/states"),
        key=lambda x: x.get("name", "").lower()
    )

@st.cache_data(ttl=86400 , show_spinner =False)
def get_cities_for_state(country_name, state_code):
    country_code = get_country_code(country_name)
    if not country_code or not state_code:
        return []
    return sorted(
        csc_get(
            f"/countries/{country_code}/states/{state_code}/cities"
        ),
        key=lambda x: x.get("name", "").lower()
    )
def load_seen_leads():

    if os.path.exists(SEEN_LEADS_FILE):
        try:
            with open(
                SEEN_LEADS_FILE,
                "r",
                encoding="utf-8"
            ) as f:
                return json.load(f)

        except Exception as e:
            print(f"[SEEN LEADS LOAD ERROR] {e}")
            return {}
    return {}

def save_seen_leads(seen_leads):

    try:
        with open(
            SEEN_LEADS_FILE,
            "w",
            encoding="utf-8"
        ) as f:
            json.dump(
                seen_leads,
                f,
                ensure_ascii=False,
                indent=2)

    except Exception as e:
        print(f"[SEEN LEADS SAVE ERROR] {e}")

def normalize_domain(website):

    try:
        url = (
            website
            if website.startswith(("http://", "https://"))
            else "https://" + website)
        domain = urlparse(url).netloc.lower()

        if domain.startswith("www."):
            domain = domain[4:]
        return domain

    except Exception:
        return (website or "").strip().lower()

def get_dedup_key(name, address, website):

    if website and website not in ("N/A", ""):
        domain = normalize_domain(website)
        if domain:
            return f"site:{domain}"

    key_str =(f"{(name or '').strip().lower()}|"
              f"{(address or '').strip().lower()}")
    return f"name:{key_str}"

def load_settings():

    if os.path.exists(SETTINGS_FILE):
        try:
            with open(
                SETTINGS_FILE,
                "r",
                encoding="utf-8"
            ) as f:
                data = json.load(f)
            merged = {
                **DEFAULT_SETTINGS,
                **data}
            return merged

        except Exception as e:
            print(f"[SETTINGS LOAD ERROR] {e}")
            return dict(DEFAULT_SETTINGS)
    save_settings(DEFAULT_SETTINGS)
    return dict(DEFAULT_SETTINGS)

def save_settings(settings):
    
    try:
        with open(SETTINGS_FILE,"W",encoding="utf-8") as f:
            json.dump(settings,f,ensure_ascii=False,indent=2)

    except Exception as e:
        print(f"[SETTINGS SAVE ERROR] {e}")

@st.cache_data(ttl=10)
def get_app_settings():

    return load_settings()

def load_usage():

    today = time.strftime("%Y-%m-%d")
    if os.path.exists(USAGE_FILE):
        try:
            with open(USAGE_FILE,"r",encoding="utf-8") as f:
                data = json.load(f)

        except Exception as e:
            print(f"[USAGE LOAD ERROR] {e}")
            data = {}

    else:
        data = {}
    if data.get("date") != today:
        data = {"date": today,
                "used": 0,
                "calls": 0,
                "extra_calls": 0}
        save_usage(data)

    if "extra_calls" not in data:
        data["extra_calls"] = 0
    return data

def save_usage(data):

    try:
        with open(USAGE_FILE,"w",encoding="utf-8") as f:
            json.dump(data,f,ensure_ascii=False,indent=2)

    except Exception as e:
        print(f"[USAGE SAVE ERROR] {e}")

@st.cache_data(ttl=3)
def get_current_usage():

    return load_usage()

def load_history():

    if os.path.exists(HISTORY_FILE):

        try:
            with open(
                HISTORY_FILE,
                "r",
                encoding="utf-8"
            ) as f:
                return json.load(f)

        except Exception as e:
            print(f"[HISTORY LOAD ERROR] {e}")
            return []
    return []

@st.cache_data(ttl=5)
def get_history():

    return load_history()

def append_history(
    count,
    new_count,
    duplicates_count):

    history = load_history()
    history.append({
        "date": time.strftime("%Y-%m-%d"),
        "count": count,
        "new": new_count,
        "duplicate": duplicates_count})

    try:
        with open(
            HISTORY_FILE,
            "w",
            encoding="utf-8"
        ) as f:
            json.dump(
                history,
                f,
                ensure_ascii=False,
                indent=2)

    except Exception as e:
        print(f"[HISTORY SAVE ERROR] {e}")

def get_result_breakdown_options(remaining):
    """Builds the 50/100/150/200 breakdown, capped to what's
    actually left in today's quota.
    
    e.g.remaining=200 > [50,100,150,200]
        remaining=180 > [50,100,150,180]
        remaining=90  > [50,90]
        remaining=20  > [20]
        remaining=0   > [0]
    """

    base_steps = [50,100,150,200]
    options = [s for s in base_steps if s <= remaining]

    if remaining > 0 and remaining not in options:
        options.append(remaining)
    if not options:
        options = [max(remaining,0)]
    return options

if "logs" not in st.session_state:
    st.session_state.logs = []
if "last_results_df" not in st.session_state:
    st.session_state.last_results_df = None
if "last_duplicates_skipped" not in st.session_state:
    st.session_state.last_duplicates_skipped = 0

def classify_log(message):
    upper = message.upper()
    if("ERROR" in upper
        or "FAILED" in upper
        or upper.startswith("STOPPED")):

        return "❌", "#ff5f5f"
    if ("RETRYING" in upper
        or "WAITING" in upper
        or upper.startswith("SENDING")):

        return "⏳", "#facc15"
    if ("COMPLETED" in upper
        or "SUCCESS" in upper
        or "FOUND" in upper):

        return "✅", "#4ade80"
    if upper.startswith("PROCESSING"):

        return "🔎", "#38bdf8"
    return "🔹", "#e2e8f0"

def log(message, console_placeholder):
    timestamp = time.strftime("%H:%M:%S")
    icon, color = classify_log(message)
    st.session_state.logs.append(
        f'<span style="color:#7d8590;">[{timestamp}]</span> '
        f'{icon} '
        f'<span style="color:{color};">{message}</span>')

    console_html = (
        '<div style="'
        'background-color: #0d1117;'
        'color: #e2e8f0;'
        'padding: 15px;'
        'border-radius: 14px;'
        'font-family: Consolas, monospace;'
        'font-size: 13px;'
        'line-height: 1.7;'
        'height: 260px;'
        'overflow-y: auto;'
        'white-space: pre-wrap;'
        'border: 1px solid #30363d;'
        '">'
        + "<br>".join(st.session_state.logs) +
        '</div>')

    console_placeholder.markdown(
        console_html,
        unsafe_allow_html=True)

def render_progress_bar(
    placeholder,
    fraction,
    label=""):

    percent = ( max(0, min(fraction, 1.0))
               * 100)

    label_html = (f'<div style="color:{COLORS["text_muted"]};'
                  f'font-size:12px;margin-top:4px;">{label}</div>'
                  if label
                  else "")
    bar_html = (
        '<div style="margin-bottom:6px;">'
        '<div style="'
        'position:relative;'
        f'background-color:{COLORS["card_border"]};'
        'border-radius:10px;'
        'height:24px;'
        'width:100%;'
        'overflow:hidden;'
        '">'
        '<div style="'
        'position:absolute;'
        'top:0;'
        'left:0;'
        'height:100%;'
        f'width:{percent}%;'
        f'background-color:{COLORS["accent"]};'
        'transition:width 0.3s ease;'
        '"></div>'
        '<div style="'
        'position:absolute;'
        'top:0;'
        'left:0;'
        'width:100%;'
        'height:100%;'
        'display:flex;'
        'align-items:center;'
        'justify-content:center;'
        f'color:{COLORS["active_text"]};'
        'font-size:12px;'
        'font-weight:700;'
        '">'
        f'{percent:.0f}%'
        '</div>'
        '</div>'
        + label_html +
        '</div>')

    placeholder.markdown(
        bar_html,
        unsafe_allow_html=True)

with st.sidebar:
    sidebar_brand(
        "Kunash Media Solution",
        "Lead Generation")

    page = sidebar_nav(
        items=["Dashboard","Search","Results","Settings"],
        icons=["📊","🔍","📋","⚙️"])

settings = get_app_settings()
usage = get_current_usage()
history = get_history()

remaining_today = max(settings["daily_limit"] - usage["used"],
                    0)

total_calls_allowed_today = (settings["max_calls_per_day"]
                             + usage.get("extra_calls", 0))

calls_left = max( total_calls_allowed_today - usage["calls"],
                  0)
if page == "Dashboard":
    topbar(
        "Dashboard",
        subtitle="Lead Scrapper Tool")

    total_all_time = sum(
        h.get("count", 0)
        for h in history)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        icon_stat_card(
            "Total Leads Collected",
            total_all_time,
            "All-time records",
            icon=ICONS["users"])
    with c2:
        icon_stat_card(
            "Leads Today",
            usage["used"],
            f"of {settings['daily_limit']} daily limit",
            icon=ICONS["check_circle"] )
    with c3:
        icon_stat_card(
            "Daily Limit",
            settings["daily_limit"],
            "companies per day",
            icon=ICONS["building"])
    with c4:
        icon_stat_card(
            "Searches Left Today",
            calls_left,
            f"of {total_calls_allowed_today} allowed"
            + (
                f" (+{usage.get('extra_calls', 0)} bonus)"
                if usage.get("extra_calls", 0) > 0
                else ""
            ),
            icon=ICONS["plus_circle"])

    st.markdown("")
    chart_col1, chart_col2 = st.columns([2, 1])
    with chart_col1:
        with panel(
            "Leads Collected Overview (This Year)"):

            if PLOTLY_AVAILABLE:
                this_year = time.strftime("%Y")
                months = [
                    "Jan", "Feb", "Mar", "Apr",
                    "May", "Jun", "Jul", "Aug",
                    "Sep", "Oct", "Nov", "Dec"]
                monthly_totals = [0] * 12

                for h in history:
                    try:
                        y, m, _ = h["date"].split("-")
                        if y == this_year:
                            monthly_totals[
                                int(m) - 1
                            ] += h["count"]
                    except Exception:
                        continue
                fig = go.Figure(
                    go.Scatter(
                        x=months,
                        y=monthly_totals,
                        mode="lines+markers",
                        line=dict(
                            color=COLORS["accent"],
                            width=3),
                        marker=dict(
                            color=COLORS["accent"] ),
                        fill="tozeroy",
                        fillcolor="rgba(0,210,196,0.12)"))
                fig.update_layout(
                    height=320,
                    margin=dict(
                        l=10,
                        r=10,
                        t=10,
                        b=10),
                    plot_bgcolor=COLORS["card_bg"],
                    paper_bgcolor=COLORS["card_bg"],
                    font=dict(
                        color=COLORS["text_dark"]),
                    xaxis=dict(
                        color=COLORS["text_muted"],
                        gridcolor=COLORS["card_border"]),
                    yaxis=dict(
                        showgrid=True,
                        gridcolor=COLORS["card_border"],
                        color=COLORS["text_muted"]))
                st.plotly_chart(
                    fig,
                    use_container_width=True)
            else:
                st.caption(
                    "Install `plotly` to see this chart.")

    with chart_col2:
        with panel(
            "Latest Search — New vs Duplicate" ):

            if PLOTLY_AVAILABLE and history:
                latest = history[-1]
                fig2 = go.Figure(
                    go.Pie(
                        labels=[
                            "New",
                            "Duplicate"],
                        values=[
                            latest.get("new", 0),
                            latest.get("duplicate", 0)],
                        hole=0.6,
                        marker_colors=[
                            COLORS["accent"],
                            COLORS["card_border"]],
                        textfont=dict(
                            color=COLORS["text_dark"]) ))
                fig2.update_layout(
                    height=320,
                    margin=dict(
                        l=10,
                        r=10,
                        t=10,
                        b=10),

                    plot_bgcolor=COLORS["card_bg"],
                    paper_bgcolor=COLORS["card_bg"],
                    font=dict(
                        color=COLORS["text_dark"]),
                    legend=dict(
                        font=dict(
                            color=COLORS["text_dark"] )
                    ))
                st.plotly_chart(
                    fig2,
                    use_container_width=True)
            else:
                st.caption("Run a search to see this breakdown.")
elif page == "Search":

    topbar(
        "Search",
        subtitle="Find and extract new leads")

    bonus_note = (
        f" (includes +{usage.get('extra_calls', 0)} bonus "
        "auto-granted since limit wasn't full)"
        if usage.get("extra_calls", 0) > 0
        else "")

    st.caption(
        f"📊 Today: "
        f"{usage['used']}/"
        f"{settings['daily_limit']} used · "
        f"{calls_left}/"
        f"{total_calls_allowed_today} searches left"
        f"{bonus_note} "
        f"(base limit set in Settings)" )
    
    form_col, info_col = st.columns([2, 1])
    with form_col:
        with panel("Search Criteria"):
            if "keyword_value" not in st.session_state:
                st.session_state.keyword_value = ""
            keyword = st.text_input(
                "Keyword",
                placeholder="Example: EPC companies",
                key="keyword_value" )
            st.caption(
                "e.g. Manufacturing, IT Services, "
                "Textile, Construction")
            
            country_options = get_country_names()

            country = st.selectbox(
                "Country",
                [PLACEHOLDER] + country_options,
                index=(
                    country_options.index("India") + 1
                    if "India" in country_options
                    else 0
                ),
                key="location_country",
            )

            state = None
            city = None
            state_code = None

            if country != PLACEHOLDER:
                state_records = get_states_for_country(country)

                if state_records:
                    state_names = [
                        s["name"] for s in state_records
                        if s.get("name")
                    ]

                    state = st.selectbox(
                        "State / Province",
                        [PLACEHOLDER] + state_names,
                        key="location_state",
                    )

                    if state != PLACEHOLDER:
                        selected_state = next(
                            (
                                s for s in state_records
                                if s.get("name") == state
                            ),
                            None,
                        )
                        if selected_state:
                            state_code = selected_state.get("iso2")
                else:
                    st.caption(
                        "No state/province data available "
                        "for this country."
                    )

            if (
                country != PLACEHOLDER
                and state
                and state != PLACEHOLDER
                and state_code
            ):
                city_records = get_cities_for_state(
                    country,
                    state_code,
                )

                city_names = [
                    c["name"] for c in city_records
                    if c.get("name")
                ]

                if city_names:
                    city = st.selectbox(
                        "City",
                        [PLACEHOLDER] + city_names,
                        key="location_city",
                    )
                else:
                    city = st.text_input(
                        "City",
                        placeholder="Type city name",
                        key="location_city_manual",
                    )

            area = None
            if city and city != PLACEHOLDER:
                area = st.text_input(
                    "Specific Area (optional)",
                    placeholder="Example: Chinchwad" )
            location_parts = [
                part
                for part in [
                    area,
                        (city
                        if city
                        and city != PLACEHOLDER
                        else None ),
                        (state
                        if state
                        and state != PLACEHOLDER
                        else None),
                        (country
                        if country != PLACEHOLDER
                        else None)]
                if part]
            location = ", ".join(
                location_parts)

            result_options = get_result_breakdown_options(remaining_today)

            st.markdown("**Number of Results**")

            if remaining_today <= 0:

                st.caption(
                    "🚫 Today's limit is expired. "
                    "Try again after midnight (00:00).")
                count = 0
            else:
                count = st.selectbox(
                    "Number of Results",
                    options=result_options,
                    index=len(result_options) - 1,
                    help=(
                        "Capped by today's Settings limit — "
                        f"{remaining_today} remaining."))
 
                st.caption(
                    f"Selected: **{count}** companies "
                    f"(you have {remaining_today} remaining today).")
 
            if remaining_today <= 0:
                pass
            elif calls_left <= 0:
                st.caption(
                    "🚫 You've used all searches for today. "
                    "Try again after midnight (00:00).")
 
            search_button = st.button(
                "Start Scraping",
                use_container_width=True,
                disabled=(
                    remaining_today <= 0
                    or calls_left <= 0))
 
    with info_col:
        with panel("Today's Usage"): 
            icon_stat_card(
                "Used Today",
                usage["used"],
                f"of {settings['daily_limit']}",
                icon=ICONS["check_circle"])
 
            st.markdown("")
            icon_stat_card(
                "Searches Left",
                calls_left,
                f"of {total_calls_allowed_today}"
                + (
                    f" (+{usage.get('extra_calls', 0)} bonus)"
                    if usage.get("extra_calls", 0) > 0
                    else ""),
                icon=ICONS["search"])
    progress_bar = st.empty()
    render_progress_bar(
        progress_bar,
        0,
        "Waiting to start...")
 
    console_placeholder = st.empty()

    if search_button:
        from website_crawler import analyze_website

        def crawl_company(place):
            name = (
                place
                .get("displayName", {})
                .get("text", "N/A")
            )

            website = place.get("websiteUri", "N/A")

            if website != "N/A" and website:
                try:
                    website_data = analyze_website(
                        company=name,
                        website=website,
                        max_pages=5
                    )
                except Exception as e:
                    print(f"[CRAWLER ERROR] {name}: {e}")

                    website_data = {
                        "Email": "Not Found",
                        "Phone": "Not Found",
                        "Director": "Not Found",
                        "LinkedIn URL": "Not Found",
                        "LinkedIn Followers": "Not Available"
                    }
            else:
                website_data = {
                     "Email": "Not Found",
                     "Phone": "Not Found",
                     "Director": "Not Found",
                     "LinkedIn URL": "Not Found",
                     "LinkedIn Followers": "Not Available"
                }

            return place, website_data

        get_current_usage.clear()
        usage = load_usage()
        allowed_calls_today = (
            settings["max_calls_per_day"]
            + usage.get("extra_calls", 0))
 
        if (
            usage["calls"]
            >= allowed_calls_today
            or
            usage["used"]
            >= settings["daily_limit"]):
 
            st.error(
                "🚫 Your today's limit is expired. "
                "Please try again after midnight (00:00).")
            st.stop()
        if count > (
            settings["daily_limit"]
            - usage["used"]):
 
            st.warning(
                f"Only "
                f"{settings['daily_limit'] - usage['used']} "
                f"results remain in today's quota. "
                f"Lower 'Number of Results' "
                f"or come back tomorrow.")
            st.stop()
        st.session_state.logs = []
        render_progress_bar(
            progress_bar,
            0,
            "Starting search...")
 
        log(
            "Starting search...",
            console_placeholder)
 
        if not keyword or not location:
 
            log("Please enter a Keyword and select "
                "at least a Country/State/City.",
                console_placeholder)
            st.warning("Please enter a Keyword and select "
                    "at least a Country/State/City.")
        else:
            log(
                f"Searching Google Maps: "
                f"{keyword} in {location}",
                console_placeholder)
            try:
                api_key = st.secrets["MY_API_KEY"]
 
            except Exception:
                log( "Google Maps API key not found.",
                    console_placeholder)
                st.error(
                    "MY_API_KEY was not found "
                    "in .streamlit/secrets.toml")
                st.stop()
            url = ("https://places.googleapis.com/"
                "v1/places:searchText")
            headers = {
                "Content-Type":
                    "application/json",
                "X-Goog-Api-Key":
                    api_key,
                "X-Goog-FieldMask": (
                    "places.displayName,"
                    "places.formattedAddress,"
                    "places.nationalPhoneNumber,"
                    "places.rating,"
                    "places.userRatingCount,"
                    "places.websiteUri,"
                    "places.googleMapsUri,"
                    "nextPageToken")}
            data_list = []
            seen_leads = load_seen_leads()
 
            log(f"Loaded duplicate-check cache: "
                f"{len(seen_leads)} companies "
                f"previously scraped.",
                console_placeholder)

            page_token = None
            page_number = 1
            progress_text = st.empty()
            total_start = perf_counter()
            retry_count = 0
            max_retries = 3
            duplicates_skipped = 0
            while len(data_list) < count:
                remaining = (
                    count
                    - len(data_list))
                page_size = min(
                    20,
                    remaining)
                data = {
                    "textQuery":
                        f"{keyword} in {location}",
                    "pageSize":
                        page_size}
                if page_token:
                    data["pageToken"] = (
                        page_token)
                    log(
                        "Waiting for next page token "
                        "to become valid...",
                        console_placeholder)
                    time.sleep(2)
                progress_text.info(
                    f"Collecting Google Maps data... "
                    f"{len(data_list)} / {count}")
                render_progress_bar(
                    progress_bar,
                    len(data_list) / count,
                    (
                        f"Fetching companies "
                        f"(page {page_number})... "
                        f"{len(data_list)} / {count}"))
                log(
                    f"Google Maps progress: "
                    f"{len(data_list)} / {count} "
                    f"(page {page_number})",
                    console_placeholder)
                google_start = perf_counter()

                log(
                    "Sending request to Google Maps API...",
                    console_placeholder)
                try:
                    response = requests.post(
                        url,
                        headers=headers,
                        json=data,
                        timeout=30
                    )
                except requests.RequestException as e:
                    google_time = (
                        perf_counter()
                        - google_start)
                    log(
                        "Google API connection failed "
                        f"after {google_time:.2f} seconds.",
                        console_placeholder)
 
                    st.error(
                        f"Could not connect to Google API: {e}")
                    break
                google_time = (
                    perf_counter()
                    - google_start)
                if response.status_code == 200:
                    retry_count = 0
                    log(
                        "Google Maps API completed in "
                        f"{google_time:.2f} seconds.",
                        console_placeholder)
                elif response.status_code == 503:
                    retry_count += 1
                    log(
                        "Google API returned 503 after "
                        f"{google_time:.2f} seconds.",
                        console_placeholder)
                    if retry_count > max_retries:
                        st.error(
                            "Google Places API is temporarily "
                            "unavailable after several retries.")
                        st.code(
                            response.text)
 
                        break
                    log(
                        f"Retrying Google API "
                        f"({retry_count}/{max_retries})...",
                        console_placeholder)
                    time.sleep(3)
                    continue
                else:
                    log(
                        f"Google API error: "
                        f"{response.status_code}",
                        console_placeholder)
                    log(
                        f"Google API error body: "
                        f"{response.text[:500]}",
                        console_placeholder)
                    st.error(
                        f"Google API Error: "
                        f"{response.status_code}" )
                    st.code(
                        response.text)
 
                    break
                results = response.json()
                log(
                    "Google Maps API response received.",
                    console_placeholder)
                places = results.get(
                    "places",
                    [])
                log(
                    f"Google Maps returned "
                    f"{len(places)} companies "
                    f"on page {page_number}.",
                    console_placeholder)
                if not places:
                    log(
                        "STOPPED: Google Maps returned "
                        "0 companies on this page.",
                        console_placeholder)
                    break

                places_to_process = []
                pending_keys = set()

                for place in places:

                    name = (
                        place
                        .get(
                            "displayName",
                            {})
                        .get(
                            "text",
                            "N/A")
                    )

                    address = place.get(
                        "formattedAddress",
                        "N/A"
                    )

                    google_phone = place.get(
                        "nationalPhoneNumber",
                        "N/A"
                    )

                    rating = place.get(
                        "rating",
                        "N/A"
                    )

                    reviews = place.get(
                        "userRatingCount",
                        "N/A"
                    )

                    website = place.get(
                        "websiteUri",
                        "N/A"
                    )

                    maps_link = place.get(
                        "googleMapsUri",
                        "N/A"
                    )

                    dedup_key = get_dedup_key(
                        name,
                        address,
                        website
                    )

                    if (
                        dedup_key in seen_leads
                        or dedup_key in pending_keys
                    ):

                        duplicates_skipped += 1

                        if dedup_key in seen_leads:

                            last_scraped = seen_leads[
                                dedup_key
                            ].get(
                                "scraped_at",
                                "an earlier search"
                            )

                            log(
                                f"Duplicate skipped: {name} "
                                f"was already scraped on "
                                f"{last_scraped} — not added "
                                f"to results.",
                                console_placeholder
                            )

                        else:

                            log(
                                f"Duplicate skipped: {name} "
                                f"appeared more than once on "
                                f"this Google Maps page.",
                                console_placeholder
                            )

                        continue

                    pending_keys.add(
                        dedup_key
                    )

                    places_to_process.append(
                        {
                            "place": place,
                            "name": name,
                            "address": address,
                            "google_phone": google_phone,
                            "rating": rating,
                            "reviews": reviews,
                            "website": website,
                            "maps_link": maps_link,
                            "dedup_key": dedup_key
                        }
                    )

                def crawl_company_with_timing(place):

                    company_name = (
                        place
                        .get(
                            "displayName",
                            {})
                        .get(
                            "text",
                            "N/A"
                        )
                    )

                    crawl_start = perf_counter()

                    try:

                        _, website_data = crawl_company(
                            place
                        )

                        crawl_time = (
                            perf_counter()
                            - crawl_start
                        )

                        return (
                            place,
                            website_data,
                            crawl_time,
                            None
                        )

                    except Exception as e:

                        crawl_time = (
                            perf_counter()
                            - crawl_start
                        )

                        website_data = {
                            "Company":
                                company_name,

                            "Email":
                                "Crawler Error",

                            "Phone":
                                "Crawler Error",

                            "Director":
                                "Crawler Error",

                            "LinkedIn URL":
                                "Crawler Error",

                            "LinkedIn Followers":
                                "Not Available"
                        }

                        return (
                            place,
                            website_data,
                            crawl_time,
                            e
                        )

                crawl_results = {}

                website_places = []

                for item in places_to_process:

                    if (
                        item["website"] != "N/A"
                        and item["website"]
                    ):
                        website_places.append(
                            item["place"]
                        )

                    else:

                        crawl_results[
                            item["dedup_key"]
                        ] = {
                            "website_data": {
                                "Company":
                                    item["name"],

                                "Email":
                                    "Not Found",

                                "Phone":
                                    "Not Found",

                                "Director":
                                    "Not Found",

                                "LinkedIn URL":
                                    "Not Found",

                                "LinkedIn Followers":
                                    "Not Available"
                            },

                            "crawl_time":
                                0.0,

                            "error":
                                None
                        }

                if website_places:

                    log(
                        f"Starting parallel website crawling "
                        f"for {len(website_places)} companies "
                        f"using 3 workers...",
                        console_placeholder
                    )

                    with ThreadPoolExecutor(
                        max_workers=3
                    ) as executor:

                        future_to_place = {}

                        for place in website_places:

                            future = executor.submit(
                                crawl_company_with_timing,
                                place
                            )

                            future_to_place[
                                future
                            ] = place

                        for future in as_completed(
                            future_to_place
                        ):

                            (
                                place,
                                website_data,
                                crawl_time,
                                error
                            ) = future.result()

                            name = (
                                place
                                .get(
                                    "displayName",
                                    {})
                                .get(
                                    "text",
                                    "N/A"
                                )
                            )

                            address = place.get(
                                "formattedAddress",
                                "N/A"
                            )

                            website = place.get(
                                "websiteUri",
                                "N/A"
                            )

                            dedup_key = get_dedup_key(
                                name,
                                address,
                                website
                            )

                            if error is not None:

                                log(
                                    f"CRAWLER ERROR for "
                                    f"{name}",
                                    console_placeholder
                                )

                                log(
                                    f"Error type: "
                                    f"{type(error).__name__}",
                                    console_placeholder
                                )

                                log(
                                    f"Error message: "
                                    f"{str(error)}",
                                    console_placeholder
                                )

                                log(
                                    f"Time before error: "
                                    f"{crawl_time:.2f} seconds",
                                    console_placeholder
                                )

                            else:

                                log(
                                    f"Website crawl completed: "
                                    f"{name} "
                                    f"({crawl_time:.2f} seconds)",
                                    console_placeholder
                                )

                            crawl_results[
                                dedup_key
                            ] = {
                                "website_data":
                                    website_data,

                                "crawl_time":
                                    crawl_time,

                                "error":
                                    error
                            }

                for item in places_to_process:

                    company_start = perf_counter()

                    name = item["name"]
                    address = item["address"]
                    google_phone = item["google_phone"]
                    rating = item["rating"]
                    reviews = item["reviews"]
                    website = item["website"]
                    maps_link = item["maps_link"]
                    dedup_key = item["dedup_key"]

                    log(
                        f"Processing company: {name}",
                        console_placeholder
                    )

                    result = crawl_results.get(
                        dedup_key
                    )

                    if result is None:

                        website_data = {
                            "Company":
                                name,

                            "Email":
                                "Not Found",

                            "Phone":
                                "Not Found",

                            "Director":
                                "Not Found",

                            "LinkedIn URL":
                                "Not Found",

                            "LinkedIn Followers":
                                "Not Available"
                        }

                    else:

                        website_data = result[
                            "website_data"
                        ]

                    if (
                        website == "N/A"
                        or not website
                    ):

                        log(
                            f"No website available "
                            f"for: {name}",
                            console_placeholder
                        )

                    seen_leads[
                        dedup_key
                    ] = {
                        "website_data":
                            website_data,

                        "scraped_at":
                            time.strftime(
                                "%Y-%m-%d %H:%M"
                            )
                    }

                    save_seen_leads(
                        seen_leads
                    )

                    phone = google_phone

                    if (
                        phone == "N/A"
                        or not phone
                    ):

                        phone = website_data.get(
                            "Phone",
                            "Not Found"
                        )

                    linkedin_url = website_data.get(
                        "LinkedIn URL",
                        "Not Found"
                    )

                    data_list.append(
                        {
                            "Company":
                                name,

                            "Address":
                                address,

                            "Phone":
                                phone,

                            "Rating":
                                rating,

                            "Reviews":
                                reviews,

                            "Website":
                                website,

                            "Email":
                                website_data.get(
                                    "Email",
                                    "Not Found"
                                ),

                            "Director":
                                website_data.get(
                                    "Director",
                                    "Not Found"
                                ),

                            "LinkedIn URL":
                                linkedin_url,

                            "LinkedIn Followers":
                                website_data.get(
                                    "LinkedIn Followers",
                                    "Not Available"
                                ),

                            "Google Maps":
                                maps_link
                        }
                    )

                    company_time = (
                        perf_counter()
                        - company_start
                    )

                    log(
                        f"Total time for {name}: "
                        f"{company_time:.2f} seconds",
                        console_placeholder
                    )

                    log(
                        f"Progress: "
                        f"{len(data_list)} / {count}",
                        console_placeholder
                    )

                    render_progress_bar(
                        progress_bar,
                        len(data_list) / count,
                        (
                            f"Processed {name} — "
                            f"{len(data_list)} / "
                            f"{count} companies"
                        )
                    )

                    if len(data_list) >= count:
                        break

                page_token = results.get(
                    "nextPageToken")
                
                page_number += 1
                if not page_token:
                    log(
                        "STOPPED: Google Maps did not "
                        "return a nextPageToken.",
                        console_placeholder)
                    break
            total_time = (
                perf_counter()
                - total_start)
            total_minutes = int(
                total_time // 60)

            total_seconds = (
                total_time
                % 60)
            time_str = (
                f"{total_minutes} min "
                f"{total_seconds:.2f} sec"
                if total_minutes > 0
                else
                f"{total_seconds:.2f} sec")
            log(
                f"TOTAL SEARCH TIME: "
                f"{time_str}",
                console_placeholder)
            log(
                f"Search completed. "
                f"{len(data_list)} NEW companies collected "
                f"(requested {count}), "
                f"{duplicates_skipped} duplicate(s) skipped "
                "(not added to results).",
                console_placeholder)
            progress_text.empty()
            render_progress_bar(
                progress_bar,
                1.0,
                (   f"Done — "
                    f"{len(data_list)} companies collected"
                ))
 
            df = pd.DataFrame(data_list)
 
            if not df.empty:
                usage = load_usage()
                usage["used"] += len(df)
                usage["calls"] += 1
                limit_left_after = max(
                    settings["daily_limit"] - usage["used"],
                    0)
                calls_left_after = max(
                    (settings["max_calls_per_day"]
                     + usage.get("extra_calls", 0)
                    )
                    - usage["calls"],
                    0)
                granted_bonus = False
 
                if (limit_left_after > 0
                    and calls_left_after <= 0):
 
                    usage["extra_calls"] = (
                        usage.get("extra_calls", 0) + 1)
 
                    granted_bonus = True
                    log(
                        "Daily quota not yet complete "
                        f"({usage['used']}/"
                        f"{settings['daily_limit']} companies) — "
                        "auto-granting 1 extra search attempt "
                        "for today.",
                        console_placeholder)
                save_usage(
                    usage)
                get_current_usage.clear()
                df.insert(
                    0,
                    "S.No",
                    range(
                        1,
                        len(df) + 1))
                new_count = len(df)
                log(
                    f"This search: {new_count} new company(ies) "
                    f"crawled and added to results, "
                    f"{duplicates_skipped} duplicate(s) skipped "
                    "(not added to results).",
                    console_placeholder)
                append_history(
                    len(df),
                    new_count,
                    duplicates_skipped)
                get_history.clear()
                st.session_state.last_results_df = df
                st.session_state.last_duplicates_skipped = (
                    duplicates_skipped)
 
                success_msg = (
                    f"{new_count} new companies collected "
                    f"successfully "
                    f"({duplicates_skipped} duplicate(s) skipped). "
                    f"Go to the **Results** page "
                    f"to view and download them.")
 
                if granted_bonus:
                    success_msg += (
                        " Daily quota not complete yet, "
                        "so 1 extra search attempt has been "
                        "added for today — you can search again.")
 
                st.success(
                    success_msg
                )
            else:
                st.session_state.last_duplicates_skipped = (
                    duplicates_skipped
                )
                if duplicates_skipped > 0:
                    st.warning(
                        "No NEW companies found — all "
                        f"{duplicates_skipped} results in this "
                        "search were duplicates already scraped "
                        "before, so nothing was added."
                    )
                else:
                    st.warning(
                        "No companies found.")
elif page == "Results":
    topbar(
        "Results",
        subtitle="Latest extracted leads")
    df = (st.session_state.last_results_df)
    if df is None or df.empty:
        st.info(
            "No results yet — run a search "
            "from the **Search** page first.")
    else:
        duplicates_count = (
            st.session_state.get(
                "last_duplicates_skipped",
                0))
        new_count = len(df)
        emails_found = int(
            (df["Email"]
            != "Not Found"
            ).sum())
        phones_found = int(
            (df["Phone"]
            != "Not Found"
            ).sum())
        directors_found = int(
            (df["Director"]
             != "Not Found"
            ).sum())
        linkedin_found = int(
            (~df[
             "LinkedIn Followers"
                ].isin(
                    ["Not Found",
                    "Not Available"])
            ).sum())
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            icon_stat_card(
                "New Leads",
                new_count,
                icon=ICONS[
                    "plus_circle"
                ])
        with c2:
            icon_stat_card(
                "Duplicates Skipped",
                duplicates_count,
                icon=ICONS[
                    "repeat"
                ])
        with c3:
            icon_stat_card(
                "Emails Found",
                f"{emails_found}/{len(df)}",
                f"{emails_found / len(df):.0%}",
                icon=ICONS[
                    "mail"
                ])
        with c4:
            icon_stat_card(
                "Directors Found",
                f"{directors_found}/{len(df)}",
                f"{directors_found / len(df):.0%}",
                icon=ICONS[
                    "user"
                ])
 
        st.markdown("")
        r1, r2 = st.columns(2)
        with r1:
            st.metric(
                "Phone Numbers Found",
                f"{phones_found}/{len(df)}")
        with r2:
            st.metric(
                "LinkedIn Followers Found",
                f"{linkedin_found}/{len(df)}")
 
        st.markdown("")
        with panel("Search Results"):
            st.dataframe(
                df,
                use_container_width=True,
                height=600,
                hide_index=True)
        dl1, dl2 = st.columns(2)
        with dl1:
            csv_data = df.to_csv(
                index=False)
            st.download_button(
                label="Download CSV",
                data=csv_data,
                file_name=
                    "lead_scrapper_data.csv",
                mime="text/csv",
                use_container_width=True)
        with dl2:
            excel_file = (
                "lead_scrapper_data.xlsx")
            df.to_excel(
                excel_file,
                index=False)
            with open(
                excel_file,
                "rb"
            ) as file:
                excel_data = file.read()
            st.download_button(
                label="Download Excel",
                data=excel_data,
                file_name=excel_file,
                mime=(
                    "application/"
                    "vnd.openxmlformats-officedocument."
                    "spreadsheetml.sheet"),
                use_container_width=True )
elif page == "Settings":
    topbar(
        "Settings",
        subtitle="Configure daily extraction limits")
    with panel(
        "Daily Extraction Limit"):
        st.caption(
            "Controls the maximum companies "
            "that can be scraped per day, "
            "and how many separate searches "
            "a user can run in that day."
        )
        s1, s2 = st.columns(2)
        with s1:
            new_daily_limit = st.number_input(
                "Companies per day",
                min_value=1,
                max_value=1000,
                value=settings[
                    "daily_limit"],
                step=10,
                help=(
                    "Total companies that can "
                    "be extracted across all "
                    "searches today."))
        with s2:
            new_max_calls = st.number_input(
                "Searches per day",
                min_value=1,
                max_value=20,
                value=settings[
                    "max_calls_per_day"
                ],
                step=1,
                help=(
                    "Number of separate search "
                    "runs allowed per day."))
        if st.button(
            "Save Settings",
            use_container_width=False ):
 
            save_settings({
                "daily_limit":
                    int(new_daily_limit),
                "max_calls_per_day":
                    int(new_max_calls)
            })
            get_app_settings.clear()
            st.success(
                f"Saved — "
                f"{int(new_daily_limit)} "
                f"companies/day, "
                f"{int(new_max_calls)} "
                f"searches/day.")
            st.rerun()
    with panel(
        "Today's Usage"):
        u1, u2 = st.columns(2)
        with u1:
            icon_stat_card(
                "Used Today",
                usage["used"],
                f"of {settings['daily_limit']}",
                icon=ICONS[
                    "check_circle"
                ])
        with u2:
            icon_stat_card(
                "Searches Used",
                usage["calls"],
                f"of {total_calls_allowed_today}"
                + (
                    f" (base {settings['max_calls_per_day']} "
                    f"+ {usage.get('extra_calls', 0)} extra)"
                    if usage.get("extra_calls", 0) > 0
                    else ""
                ),
                icon=ICONS[
                    "search"
                ])
    with panel(
        "System Information"):
        st.write(
            "Scraper Status: Ready")
        st.write(
            f"Daily Company Limit: "
            f"{settings['daily_limit']}" )
        st.write(
            f"Daily Search Limit (base): "
            f"{settings['max_calls_per_day']}")
        st.write(
            f"Extra Searches Auto-Granted Today: "
            f"{usage.get('extra_calls', 0)}")
        st.write(
            f"Companies Remaining Today: "
            f"{remaining_today}")
        st.write(
            f"Searches Remaining Today: "
            f"{calls_left}")
    st.caption(
        "Usage resets automatically at midnight (00:00).")
 
