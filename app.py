
import streamlit as st
import pandas as pd
import requests
import time
import json
import os
import pycountry
from time import perf_counter
from urllib.parse import urlparse
 
from website_crawler import analyze_website
 
st.set_page_config(
    page_title="Lead Scrapper Tool",
    layout="wide"
)
 
st.title("Lead Scrapper Tool")
 
PLACEHOLDER = "-- Select --"
  
@st.cache_data
def get_country_names():
 
    return sorted(
        country.name
        for country in pycountry.countries
    )
  
@st.cache_data
def get_states_for_country(country_name):
 
    try:
 
        country = pycountry.countries.get(
            name=country_name
        )
 
        if not country:
            return []
 
        subdivisions = pycountry.subdivisions.get(
            country_code=country.alpha_2
        )
 
        if not subdivisions:
            return []
 
        return sorted(
            sub.name for sub in subdivisions
        )
 
    except Exception:
 
        return []
 
INDIA_CITIES_BY_STATE = {
 
    "Maharashtra": [
        "Mumbai", "Pune", "Nagpur", "Nashik", "Thane",
        "Navi Mumbai", "Aurangabad", "Solapur", "Kolhapur"
    ],
 
    "Karnataka": [
        "Bengaluru", "Mysuru", "Mangaluru", "Hubballi", "Belagavi"
    ],
 
    "Tamil Nadu": [
        "Chennai", "Coimbatore", "Madurai", "Tiruchirappalli", "Salem"
    ],
 
    "Telangana": [
        "Hyderabad", "Warangal", "Nizamabad"
    ],
 
    "West Bengal": [
        "Kolkata", "Howrah", "Durgapur", "Siliguri"
    ],
 
    "Gujarat": [
        "Ahmedabad", "Surat", "Vadodara", "Rajkot", "Gandhinagar"
    ],
 
    "Rajasthan": [
        "Jaipur", "Jodhpur", "Udaipur", "Kota", "Ajmer"
    ],
 
    "Uttar Pradesh": [
        "Lucknow", "Kanpur", "Noida", "Ghaziabad", "Agra", "Varanasi"
    ],
 
    "Punjab": [
        "Ludhiana", "Amritsar", "Jalandhar", "Patiala"
    ],
 
    "Haryana": [
        "Gurugram", "Faridabad", "Panipat", "Karnal"
    ],
 
    "Madhya Pradesh": [
        "Bhopal", "Indore", "Gwalior", "Jabalpur"
    ],
 
    "Bihar": [
        "Patna", "Gaya", "Bhagalpur"
    ],
 
    "Kerala": [
        "Kochi", "Thiruvananthapuram", "Kozhikode", "Thrissur"
    ],
 
    "Andhra Pradesh": [
        "Visakhapatnam", "Vijayawada", "Guntur", "Tirupati"
    ],
 
    "Odisha": [
        "Bhubaneswar", "Cuttack", "Rourkela"
    ],
 
    "NCT of Delhi": [
        "New Delhi", "Delhi"
    ],
 
    "Chandigarh": [
        "Chandigarh"
    ],
 
    "Puducherry": [
        "Puducherry"
    ],
 
    "Goa": [
        "Panaji", "Margao"
    ],
 
    "Assam": [
        "Guwahati", "Dibrugarh", "Silchar"
    ],
 
    "Jharkhand": [
        "Ranchi", "Jamshedpur", "Dhanbad"
    ],
 
    "Chhattisgarh": [
        "Raipur", "Bhilai", "Bilaspur"
    ],
 
    "Uttarakhand": [
        "Dehradun", "Haridwar", "Nainital"
    ],
 
    "Himachal Pradesh": [
        "Shimla", "Manali", "Dharamshala"
    ],
 
    "Jammu and Kashmir": [
        "Srinagar", "Jammu"
    ],
 
    "Ladakh": [
        "Leh", "Kargil"
    ],
 
    "Manipur": [
        "Imphal"
    ],
 
    "Meghalaya": [
        "Shillong"
    ],
 
    "Mizoram": [
        "Aizawl"
    ],
 
    "Nagaland": [
        "Kohima", "Dimapur"
    ],
 
    "Tripura": [
        "Agartala"
    ],
 
    "Arunachal Pradesh": [
        "Itanagar"
    ],
 
    "Sikkim": [
        "Gangtok"
    ],
 
    "Andaman and Nicobar Islands": [
        "Port Blair"
    ],
 
    "Lakshadweep": [
        "Kavaratti"
    ],
 
    "Dadra and Nagar Haveli and Daman and Diu": [
        "Daman", "Silvassa"
    ]
}
 
st.subheader("Console")
 
SEEN_LEADS_FILE = "seen_leads.json"
  
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
 
            print(
                f"[SEEN LEADS LOAD ERROR] {e}"
            )
 
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
                indent=2
            )
 
    except Exception as e:
 
        print(
            f"[SEEN LEADS SAVE ERROR] {e}"
        )
 
def normalize_domain(website):
 
    try:
 
        url = (
            website
            if website.startswith(("http://", "https://"))
            else "https://" + website
        )
 
        domain = urlparse(url).netloc.lower()
 
        if domain.startswith("www."):
 
            domain = domain[4:]
 
        return domain
 
    except Exception:
 
        return (website or "").strip().lower()
 
def get_dedup_key(name, address, website):
 
    if website and website not in ("N/A", ""):
 
        domain = normalize_domain(
            website
        )
 
        if domain:
 
            return f"site:{domain}"
 
    key_str = (
        f"{(name or '').strip().lower()}"
        f"|{(address or '').strip().lower()}"
    )
 
    return f"name:{key_str}"
 
console = st.empty()
  
def render_progress_bar(placeholder, fraction, label=""):
    """
    Custom progress bar with the percentage shown INSIDE the blue
    fill itself, like a typical download bar — Streamlit's built-in
    st.progress can only show text beside the bar, not on it.
    """
 
    percent = max(
        0,
        min(fraction, 1.0)
    ) * 100
 
    label_html = (
        f'<div style="color:#9ca3af;font-size:12px;'
        f'margin-top:4px;">{label}</div>'
        if label else ""
    )
 
    placeholder.markdown(
        f"""
        <div style="margin-bottom:6px;">
            <div style="
                position:relative;
                background-color:#30363d;
                border-radius:8px;
                height:26px;
                width:100%;
                overflow:hidden;
            ">
                <div style="
                    position:absolute;
                    top:0; left:0;
                    height:100%;
                    width:{percent}%;
                    background-color:#2563eb;
                    transition:width 0.3s ease;
                "></div>
                <div style="
                    position:absolute;
                    top:0; left:0;
                    width:100%; height:100%;
                    display:flex;
                    align-items:center;
                    justify-content:center;
                    color:white;
                    font-size:13px;
                    font-weight:700;
                    text-shadow:0 1px 2px rgba(0,0,0,0.4);
                ">
                    {percent:.0f}%
                </div>
            </div>
            {label_html}
        </div>
        """,
        unsafe_allow_html=True
    )
 
if "logs" not in st.session_state:
 
    st.session_state.logs = []
  
def classify_log(message):
    """
    Picks an icon + color for a log line based on its content, so
    the console reads clearly at a glance — green for success,
    red for errors, yellow for waiting/retrying, blue for
    in-progress — without needing to change every log() call.
    """
 
    upper = message.upper()
 
    if (
        "ERROR" in upper
        or "FAILED" in upper
        or upper.startswith("STOPPED")
    ):
 
        return "❌", "#ff5f5f"
 
    if (
        "RETRYING" in upper
        or "WAITING" in upper
        or upper.startswith("SENDING")
    ):
 
        return "⏳", "#facc15"
 
    if (
        "COMPLETED" in upper
        or "SUCCESS" in upper
        or "FOUND" in upper
    ):
 
        return "✅", "#4ade80"
 
    if upper.startswith("PROCESSING"):
 
        return "🔎", "#38bdf8"
 
    return "🔹", "#e2e8f0"
 
def log(message):
 
    timestamp = time.strftime(
        "%H:%M:%S"
    )
 
    icon, color = classify_log(
        message
    )
 
    st.session_state.logs.append(
        f'<span style="color:#7d8590;">[{timestamp}]</span> '
        f'{icon} <span style="color:{color};">{message}</span>'
    )
 
    console.markdown(
        f"""
        <div style="
            background-color: #0d1117;
            color: #e2e8f0;
            padding: 15px;
            border-radius: 8px;
            font-family: Consolas, monospace;
            font-size: 13px;
            line-height: 1.7;
            height: 300px;
            overflow-y: auto;
            white-space: pre-wrap;
            border: 1px solid #30363d;
        ">
        {"<br>".join(st.session_state.logs)}
        </div>
        """,
        unsafe_allow_html=True
    )
  
search_col, result_col = st.columns(
    [1, 3]
)
 
with search_col:
 
    st.subheader("Search")
 
    if "keyword_value" not in st.session_state:
 
        st.session_state.keyword_value = ""
 
    keyword = st.text_input(
        "Enter Keyword",
        placeholder="Example: EPC companies",
        key="keyword_value"
    )
 
    st.caption(
        "💡 What kind of business to search for — "
        "e.g. (Manufacturing Company, IT Services, "
        "Textile Industries, Real Estate, Construction, "
        "EPC Company, Automobile Dealers)"
    )
 
    country_options = get_country_names()
 
    country = st.selectbox(
        "Country",
        [PLACEHOLDER] + country_options,
        index=(
            country_options.index("India") + 1
            if "India" in country_options
            else 0
        )
    )
 
    state = None
    city = None
 
    if country != PLACEHOLDER:
 
        state_options = get_states_for_country(
            country
        )
 
        if state_options:
 
            state = st.selectbox(
                "State",
                [PLACEHOLDER] + state_options
            )
 
        else:
 
            st.caption(
                "No state/province data available for this country."
            )

    if state and state != PLACEHOLDER:
 
        if country == "India":
 
            city_options = INDIA_CITIES_BY_STATE.get(
                state,
                []
            )
 
            if city_options:
 
                city = st.selectbox(
                    "City",
                    [PLACEHOLDER] + city_options
                )
 
            else:
 
                st.caption(
                    "No curated city list yet for this state — "
                    "type it below."
                )
 
                city = st.text_input(
                    "City",
                    placeholder="Example: Mumbai"
                )
 
        else:
 
            st.caption(
                "Offline city list is currently only available "
                "for India — type the city below."
            )
 
            city = st.text_input(
                "City",
                placeholder="Type city name"
            )
 
    area = None
 
    if city and city != PLACEHOLDER:
 
        area = st.text_input(
            "Specific Area (optional)",
            placeholder="Example: Andheri, Koramangala"
        )
 
    location_parts = [
        part for part in [
            area,
            city if city and city != PLACEHOLDER else None,
            state if state and state != PLACEHOLDER else None,
            country if country != PLACEHOLDER else None
        ]
        if part
    ]
 
    location = ", ".join(location_parts)
 
    count = st.number_input(
        "Number of Results",
        min_value=1,
        max_value=50,
        value=10,
        step=1
    )
 
    search_button = st.button(
        "Search",
        use_container_width=True
    )
 
with result_col:
 
    st.subheader("Search Results")
 
    progress_bar = st.empty()
 
    render_progress_bar(
        progress_bar,
        0,
        "Waiting to start..."
    )
 
    if search_button:
 
        st.session_state.logs = []
 
        render_progress_bar(
            progress_bar,
            0,
            "Starting search..."
        )
 
        log(
            "Starting search..."
        )
 
        if not keyword or not location:
 
            log(
                "Please enter a Keyword and select at least a "
                "Country/State/City."
            )
 
            st.warning(
                "Please enter a Keyword and select at least a "
                "Country/State/City."
            )
 
        else:
 
            log(
                f"Searching Google Maps: "
                f"{keyword} in {location}"
            )
 
            try:
 
                api_key = st.secrets[
                    "MY_API_KEY"
                ]
 
            except Exception:
 
                log(
                    "Google Maps API key not found."
                )
 
                st.error(
                    "MY_API_KEY was not found in "
                    ".streamlit/secrets.toml"
                )
 
                st.stop()
 
            url = (
                "https://places.googleapis.com/"
                "v1/places:searchText"
            )
 
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
                    "nextPageToken"
                )
            }
 
            data_list = []
 
            seen_leads = load_seen_leads()
 
            log(
                f"Loaded duplicate-check cache: "
                f"{len(seen_leads)} companies previously scraped."
            )
 
            page_token = None
 
            page_number = 1
 
            progress_text = st.empty()
 
            total_start = perf_counter()
 
            retry_count = 0
 
            max_retries = 3
 
 
            while len(data_list) < count:
 
                remaining = (
                    count - len(data_list)
                )
 
                page_size = min(
                    20,
                    remaining
                )
 
                data = {
 
                    "textQuery":
                        f"{keyword} in {location}",
 
                    "pageSize":
                        page_size
                }
 
                if page_token:
 
                    data["pageToken"] = (
                        page_token
                    )
 
                    log(
                        "Waiting for next page token to "
                        "become valid..."
                    )
 
                    time.sleep(
                        2
                    )
 
                progress_text.info(
                    f"Collecting Google Maps data... "
                    f"{len(data_list)} / {count}"
                )
 
                render_progress_bar(
                    progress_bar,
                    len(data_list) / count,
                    f"Fetching companies from Google Maps "
                    f"(page {page_number})... "
                    f"{len(data_list)} / {count}"
                )
 
                log(
                    f"Google Maps progress: "
                    f"{len(data_list)} / {count} "
                    f"(page {page_number})"
                )
 
                google_start = perf_counter()
 
                log(
                    "Sending request to Google Maps API..."
                )
 
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
                        - google_start
                    )
 
                    log(
                        "Google API connection failed "
                        f"after {google_time:.2f} seconds."
                    )
 
                    st.error(
                        f"Could not connect to Google API: {e}"
                    )
 
                    break
 
                google_time = (
                    perf_counter()
                    - google_start
                )
 
                if response.status_code == 200:
 
                    retry_count = 0
 
                    log(
                        "Google Maps API completed in "
                        f"{google_time:.2f} seconds."
                    )
 
                elif response.status_code == 503:
 
                    retry_count += 1
 
                    log(
                        "Google API returned 503 "
                        f"after {google_time:.2f} seconds."
                    )
 
                    if retry_count > max_retries:
 
                        st.error(
                            "Google Places API is temporarily "
                            "unavailable after several retries."
                        )
 
                        st.code(
                            response.text
                        )
 
                        break
 
                    log(
                        f"Retrying Google API "
                        f"({retry_count}/{max_retries})..."
                    )
 
                    time.sleep(
                        3
                    )
 
                    continue
 
                else:
 
                    log(
                        "Google API error: "
                        f"{response.status_code}"
                    )
 
                    log(
                        f"Google API error body: {response.text[:500]}"
                    )
 
                    st.error(
                        f"Google API Error: "
                        f"{response.status_code}"
                    )
 
                    st.code(
                        response.text
                    )
 
                    break
 
                results = response.json()
 
                log(
                    "Google Maps API response received."
                )
 
                places = results.get(
                    "places",
                    []
                )
 
                log(
                    f"Google Maps returned "
                    f"{len(places)} companies "
                    f"on page {page_number}."
                )
 
                if not places:
 
                    log(
                        "STOPPED: Google Maps returned 0 companies "
                        "on this page — either there are no more "
                        "matching businesses, or (if this was page "
                        "2+) the page token expired before this "
                        "request went out."
                    )
 
                    break
 
                for place in places:
 
                    company_start = perf_counter()
 
                    name = place.get(
                        "displayName",
                        {}
                    ).get(
                        "text",
                        "N/A"
                    )
 
                    log(
                        f"Processing company: {name}"
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
 
                    is_duplicate = (
                        dedup_key in seen_leads
                    )
 
                    if is_duplicate:
 
                        cached = seen_leads[
                            dedup_key
                        ]
 
                        website_data = cached.get(
                            "website_data",
                            {}
                        )
 
                        last_scraped = cached.get(
                            "scraped_at",
                            "an earlier search"
                        )
 
                        log(
                            f"Duplicate: {name} was already "
                            f"scraped on {last_scraped} — "
                            f"reusing saved data (skipped "
                            f"re-crawling)."
                        )
 
                    elif (
                        website != "N/A"
                        and website
                    ):
 
                        log(
                            f"Starting website crawl: "
                            f"{name}"
                        )
 
                        log(
                            "Extracting Email, Phone, "
                            "Director and LinkedIn data..."
                        )
 
                        crawl_start = (
                            perf_counter()
                        )
 
                        try:
 
                            website_data = (
                                analyze_website(
                                    company=name,
                                    website=website,
                                    max_pages=5
                                )
                            )
 
                            crawl_time = (
                                perf_counter()
                                - crawl_start
                            )
 
                            log(
                                f"Website crawl completed: "
                                f"{name} "
                                f"({crawl_time:.2f} seconds)"
                            )
 
                        except Exception as e:
 
                            crawl_time = (
                                perf_counter()
                                - crawl_start
                            )
 
                            log(
                                f"CRAWLER ERROR for {name}"
                            )
 
                            log(
                                f"Error type: "
                                f"{type(e).__name__}"
                            )
 
                            log(
                                f"Error message: "
                                f"{str(e)}"
                            )
 
                            log(
                                f"Time before error: "
                                f"{crawl_time:.2f} seconds"
                            )
 
                            website_data = {
 
                                "Company":
                                    name,
 
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
 
                        seen_leads[dedup_key] = {
 
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
 
                    else:
 
                        log(
                            f"No website available for: "
                            f"{name}"
                        )
 
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
 
                        seen_leads[dedup_key] = {
 
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
 
                    linkedin_url = (
                        website_data.get(
                            "LinkedIn URL",
                            "Not Found"
                        )
                    )
 
                    data_list.append({
 
                        "Duplicate":
                            "Yes" if is_duplicate else "No",
 
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
                    })
 
                    company_time = (
                        perf_counter()
                        - company_start
                    )
 
                    log(
                        f"Total time for {name}: "
                        f"{company_time:.2f} seconds"
                    )
 
                    log(
                        f"Progress: "
                        f"{len(data_list)} / {count}"
                    )
 
                    render_progress_bar(
                        progress_bar,
                        len(data_list) / count,
                        f"Processed {name} — "
                        f"{len(data_list)} / {count} companies"
                    )
 
                    if (
                        len(data_list)
                        >= count
                    ):
 
                        break
 
                page_token = results.get(
                    "nextPageToken"
                )
 
                page_number += 1
 
                if not page_token:
 
                    log(
                        "STOPPED: Google Maps did not return a "
                        "nextPageToken — this means Google has no "
                        "further matching businesses beyond what "
                        "was already collected."
                    )
 
                    break
 
            total_time = (
                perf_counter()
                - total_start
            )
 
            total_minutes = int(
                total_time // 60
            )
 
            total_seconds = (
                total_time % 60
            )
 
            if total_minutes > 0:
 
                time_str = (
                    f"{total_minutes} min "
                    f"{total_seconds:.2f} sec"
                )
 
            else:
 
                time_str = (
                    f"{total_seconds:.2f} sec"
                )
 
            log(
                f"TOTAL SEARCH TIME: {time_str}"
            )
 
            log(
                f"Search completed. "
                f"{len(data_list)} companies collected "
                f"(requested {count})."
            )
 
            progress_text.empty()
 
            render_progress_bar(
                progress_bar,
                1.0,
                f"Done — {len(data_list)} companies collected"
            )
 
            df = pd.DataFrame(
                data_list
            )
 
            if not df.empty:
 
                df.insert(
                    0,
                    "S.No",
                    range(
                        1,
                        len(df) + 1
                    )
                )
 
                if len(df) < count:
 
                    st.info(
                        f"Only {len(df)} of the requested {count} "
                        f"companies were found — Google Maps has no "
                        f"more matching businesses for this "
                        f"keyword/location combination. Check the "
                        f"Console log above for details."
                    )
 
                st.success(
                    f"{len(df)} companies collected successfully!"
                )
 
                duplicates_count = int(
                    (df["Duplicate"] == "Yes").sum()
                )
 
                new_count = len(df) - duplicates_count
 
                emails_found = int(
                    (df["Email"] != "Not Found").sum()
                )
 
                phones_found = int(
                    (df["Phone"] != "Not Found").sum()
                )
 
                directors_found = int(
                    (df["Director"] != "Not Found").sum()
                )
 
                linkedin_found = int(
                    (
                        ~df["LinkedIn Followers"].isin(
                            ["Not Found", "Not Available"]
                        )
                    ).sum()
                )
 
                st.markdown(
                    "#### 📊 Result Summary"
                )
 
                d1, d2 = st.columns(2)
 
                d1.metric(
                    "🆕 New Leads",
                    new_count
                )
 
                d2.metric(
                    "♻️ Duplicates (Skipped Re-crawl)",
                    duplicates_count
                )
 
                st.caption(
                    "Data Accuracy — % of rows where each field "
                    "was actually found (not \"Not Found\")"
                )
 
                a1, a2, a3, a4 = st.columns(4)
 
                a1.metric(
                    "Email",
                    f"{emails_found}/{len(df)}",
                    f"{emails_found / len(df):.0%}"
                )
 
                a2.metric(
                    "Phone",
                    f"{phones_found}/{len(df)}",
                    f"{phones_found / len(df):.0%}"
                )
 
                a3.metric(
                    "Director",
                    f"{directors_found}/{len(df)}",
                    f"{directors_found / len(df):.0%}"
                )
 
                a4.metric(
                    "LinkedIn Followers",
                    f"{linkedin_found}/{len(df)}",
                    f"{linkedin_found / len(df):.0%}"
                )
 
                st.divider()
 
                st.dataframe(
                    df,
                    use_container_width=True,
                    height=600,
                    hide_index=True
                )
                csv_data = df.to_csv(
                    index=False
                )
 
                st.download_button(
 
                    label="Download CSV",
 
                    data=csv_data,
 
                    file_name=(
                        "lead_scrapper_data.csv"
                    ),
 
                    mime="text/csv",
 
                    use_container_width=True
                )
 
                excel_file = (
                    "lead_scrapper_data.xlsx"
                )
 
                df.to_excel(
                    excel_file,
                    index=False
                )
 
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
                        "application/vnd.openxmlformats-"
                        "officedocument.spreadsheetml.sheet"
                    ),
 
                    use_container_width=True
                )
 
            else:
 
                st.warning(
                    "No companies found.")