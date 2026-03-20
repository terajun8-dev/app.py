import csv
import io
import json
import urllib.parse
from datetime import datetime
from html import escape
from json import JSONDecodeError
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

import streamlit as st
from streamlit_autorefresh import st_autorefresh
from streamlit_geolocation import streamlit_geolocation


st.set_page_config(page_title="Digital Signage", layout="wide")


SLIDES = [
    ("weather", "01. 天気予報"),
    ("domestic-news", "02. 国内主要ニュース"),
    ("global-news", "03. 海外主要ニュース"),
    ("markets", "04. 株価・指数"),
    ("character", "05. GitHub CLI Guide"),
]

DEFAULT_PLAYLIST = [key for key, _ in SLIDES]
SLIDE_LABELS = dict(SLIDES)
USER_AGENT = "Mozilla/5.0 (compatible; MyStreamlitApp/1.0)"
DEFAULT_MANUAL_LOCATION = "Tokyo"

SAMPLE_WEATHER = {
    "area_label": "Tokyo",
    "temp_c": "18",
    "feels_like_c": "17",
    "humidity": "52",
    "description": "晴れ時々くもり",
    "source": "sample",
    "status": "demo",
    "note": "ライブ天気データを取得できなかったため、サンプル表示です。",
    "fetched_at": "--:--:--",
}

SAMPLE_DOMESTIC_NEWS = [
    {"title": "政府、来年度の成長戦略を発表", "source": "Demo News JP"},
    {"title": "主要都市で春のイベント準備が本格化", "source": "Demo News JP"},
    {"title": "国内製造業の景況感が緩やかに改善", "source": "Demo News JP"},
    {"title": "鉄道各社、混雑緩和へ新たな実証実験", "source": "Demo News JP"},
    {"title": "地方観光の回復基調が続く", "source": "Demo News JP"},
]

SAMPLE_GLOBAL_NEWS = [
    {"title": "Global markets await central bank signals", "source": "Demo World News"},
    {"title": "Major cities expand clean-energy projects", "source": "Demo World News"},
    {"title": "Shipping routes recover after weather delays", "source": "Demo World News"},
    {"title": "AI investment remains a top boardroom priority", "source": "Demo World News"},
    {"title": "Travel demand rises across key regions", "source": "Demo World News"},
]

SAMPLE_MARKETS = [
    {"name": "Nikkei 225", "symbol": "^N225", "close": 39120.45, "change": 215.30, "change_pct": 0.55},
    {"name": "Dow Jones", "symbol": "^DJI", "close": 41120.10, "change": -95.40, "change_pct": -0.23},
    {"name": "S&P 500", "symbol": "^SPX", "close": 5298.25, "change": 22.15, "change_pct": 0.42},
]


def initialize_state() -> None:
    defaults = {
        "signage_current_slide": DEFAULT_PLAYLIST[0],
        "signage_playlist": DEFAULT_PLAYLIST.copy(),
        "signage_autoplay": True,
        "signage_interval": 8,
        "signage_news_items": 5,
        "signage_location_mode": "現在地を優先",
        "signage_manual_location": DEFAULT_MANUAL_LOCATION,
        "signage_last_refresh_count": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def active_playlist() -> list[str]:
    configured = st.session_state.get("signage_playlist", DEFAULT_PLAYLIST)
    playlist = [key for key in configured if key in SLIDE_LABELS]
    return playlist or DEFAULT_PLAYLIST.copy()


def ensure_current_slide(playlist: list[str]) -> None:
    if st.session_state["signage_current_slide"] not in playlist:
        st.session_state["signage_current_slide"] = playlist[0]


def move_slide(step: int, playlist: list[str]) -> None:
    current = st.session_state["signage_current_slide"]
    current_index = playlist.index(current)
    st.session_state["signage_current_slide"] = playlist[(current_index + step) % len(playlist)]


def fetch_text(url: str) -> str:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=8) as response:
        return response.read().decode("utf-8")


@st.cache_data(ttl=900, show_spinner=False)
def cached_fetch_text(url: str) -> str:
    return fetch_text(url)


def timestamp_now() -> str:
    return datetime.now().strftime("%H:%M:%S")


def build_area_label(payload: dict, fallback: str) -> str:
    nearest_areas = payload.get("nearest_area", [])
    if not nearest_areas:
        return fallback
    nearest = nearest_areas[0]
    region = nearest.get("region", [{}])[0].get("value", "").strip()
    area_name = nearest.get("areaName", [{}])[0].get("value", "").strip()
    country = nearest.get("country", [{}])[0].get("value", "").strip()
    parts = [part for part in [region, area_name] if part]
    if not parts and country:
        parts.append(country)
    return " / ".join(dict.fromkeys(parts)) or fallback


@st.cache_data(ttl=900, show_spinner=False)
def fetch_weather_by_query(query: str, fallback_label: str, fallback_note: str = "") -> dict:
    try:
        encoded_query = urllib.parse.quote(query)
        weather_url = f"https://wttr.in/{encoded_query}?format=j1"
        payload = json.loads(cached_fetch_text(weather_url))
        current = payload["current_condition"][0]
        area_label = build_area_label(payload, fallback_label)
        note = "ライブデータを表示中"
        if fallback_note:
            note = f"{note} / {fallback_note}"
        return {
            "area_label": area_label,
            "temp_c": current["temp_C"],
            "feels_like_c": current["FeelsLikeC"],
            "humidity": current["humidity"],
            "description": current["weatherDesc"][0]["value"],
            "source": "wttr.in",
            "status": "live",
            "note": note,
            "fetched_at": timestamp_now(),
        }
    except (HTTPError, URLError, TimeoutError, JSONDecodeError, KeyError, IndexError, UnicodeDecodeError) as exc:
        fallback = SAMPLE_WEATHER.copy()
        fallback["area_label"] = fallback_label
        fallback_note_text = fallback["note"]
        if fallback_note:
            fallback_note_text = f"{fallback_note_text} / {fallback_note}"
        fallback["note"] = f"{fallback_note_text} ({exc.__class__.__name__})"
        fallback["fetched_at"] = timestamp_now()
        return fallback


def resolve_weather() -> tuple[dict, str]:
    manual_location = st.session_state["signage_manual_location"].strip() or DEFAULT_MANUAL_LOCATION
    geolocation = streamlit_geolocation()
    latitude = geolocation.get("latitude") if geolocation else None
    longitude = geolocation.get("longitude") if geolocation else None
    use_current_location = st.session_state["signage_location_mode"] == "現在地を優先"

    if use_current_location and latitude is not None and longitude is not None:
        weather = fetch_weather_by_query(
            query=f"{latitude},{longitude}",
            fallback_label="現在地",
            fallback_note="ブラウザ位置情報を利用",
        )
        return weather, "ブラウザ位置情報"

    if use_current_location:
        weather = fetch_weather_by_query(
            query=manual_location,
            fallback_label=manual_location,
            fallback_note="位置情報が未取得のため入力地域を表示",
        )
        return weather, "位置情報待機中"

    weather = fetch_weather_by_query(
        query=manual_location,
        fallback_label=manual_location,
        fallback_note="手動設定の地域を表示",
    )
    return weather, "手動地域"


@st.cache_data(ttl=900, show_spinner=False)
def fetch_rss_items(url: str, fallback_items: list[dict], source_label: str, limit: int) -> dict:
    try:
        xml_text = cached_fetch_text(url)
        root = ET.fromstring(xml_text)
        parsed_items = []
        for item in root.findall(".//item")[:limit]:
            title = item.findtext("title", default="(no title)")
            source = item.findtext("source", default=source_label)
            parsed_items.append({"title": title.strip(), "source": source.strip()})
        if not parsed_items:
            raise ValueError("RSS feed returned no items.")
        return {
            "items": parsed_items,
            "source": source_label,
            "status": "live",
            "note": "ライブRSSを表示中",
            "fetched_at": timestamp_now(),
        }
    except (HTTPError, URLError, TimeoutError, ET.ParseError, UnicodeDecodeError, ValueError) as exc:
        return {
            "items": fallback_items[:limit],
            "source": "sample",
            "status": "demo",
            "note": f"ライブRSSを取得できなかったため、サンプル表示です。 ({exc.__class__.__name__})",
            "fetched_at": timestamp_now(),
        }


@st.cache_data(ttl=900, show_spinner=False)
def fetch_market_quote(symbol: str, name: str) -> dict:
    try:
        quote_url = f"https://stooq.com/q/l/?s={urllib.parse.quote(symbol)}&i=d"
        csv_text = cached_fetch_text(quote_url)
        row = next(csv.DictReader(io.StringIO(csv_text)))
        close_value = float(row["Close"])
        open_value = float(row["Open"])
        change_value = close_value - open_value
        change_pct = (change_value / open_value) * 100 if open_value else 0.0
        return {
            "name": name,
            "symbol": symbol,
            "close": close_value,
            "change": change_value,
            "change_pct": change_pct,
            "source": "stooq",
            "status": "live",
            "note": "ライブ指数を表示中",
            "fetched_at": timestamp_now(),
        }
    except (HTTPError, URLError, TimeoutError, UnicodeDecodeError, KeyError, StopIteration, ValueError, ZeroDivisionError):
        for fallback in SAMPLE_MARKETS:
            if fallback["symbol"] == symbol:
                return {
                    **fallback,
                    "source": "sample",
                    "status": "demo",
                    "note": "ライブ指数を取得できなかったため、サンプル表示です。",
                    "fetched_at": timestamp_now(),
                }
        raise


def render_status_badge(status: str, note: str, source: str, fetched_at: str) -> None:
    badge_color = "#14b8a6" if status == "live" else "#f59e0b"
    badge_label = "LIVE" if status == "live" else "DEMO"
    st.markdown(
        f"""
        <div class="status-row">
            <span class="status-pill" style="background:{badge_color};">{badge_label}</span>
            <span class="meta-pill">Source: {escape(source)}</span>
            <span class="meta-pill">Updated: {escape(fetched_at)}</span>
            <span class="meta-note">{escape(note)}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_weather_slide(weather: dict, location_status: str) -> None:
    left, right = st.columns([1.45, 1])
    with left:
        st.markdown("## 今日の天気")
        st.markdown(
            f"""
            <div class="feature-panel weather-panel">
                <div class="eyebrow">LOCAL WEATHER</div>
                <div class="feature-location">{escape(weather["area_label"])}</div>
                <div class="feature-value">{escape(weather["temp_c"])}°C</div>
                <div class="feature-subtitle">{escape(weather["description"])}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with right:
        st.metric("体感温度", f'{weather["feels_like_c"]}°C')
        st.metric("湿度", f'{weather["humidity"]}%')
        st.info(f"天気ソース: {location_status}")
    render_status_badge(weather["status"], weather["note"], weather["source"], weather["fetched_at"])


def render_news_slide(title: str, news_data: dict) -> None:
    st.markdown(f"## {title}")
    render_status_badge(news_data["status"], news_data["note"], news_data["source"], news_data["fetched_at"])
    for index, item in enumerate(news_data["items"], start=1):
        st.markdown(
            f"""
            <div class="headline-card">
                <div class="headline-index">HEADLINE {index:02d}</div>
                <div class="headline-title">{escape(item["title"])}</div>
                <div class="headline-source">{escape(item["source"])}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_market_slide(market_rows: list[dict]) -> None:
    st.markdown("## 株価・主要指数")
    market_status = "demo" if any(row["status"] == "demo" for row in market_rows) else "live"
    market_note = " / ".join(sorted({row["note"] for row in market_rows}))
    market_source = ", ".join(sorted({row["source"] for row in market_rows}))
    market_updated = ", ".join(sorted({row["fetched_at"] for row in market_rows}))
    render_status_badge(market_status, market_note, market_source, market_updated)
    columns = st.columns(len(market_rows))
    for column, row in zip(columns, market_rows):
        delta_color = "normal" if row["change"] >= 0 else "inverse"
        column.metric(
            label=f'{row["name"]} ({row["symbol"]})',
            value=f'{row["close"]:,.2f}',
            delta=f'{row["change"]:+.2f} / {row["change_pct"]:+.2f}%',
            delta_color=delta_color,
        )
    st.markdown(
        """
        <div class="feature-panel market-panel">
            主要指数だけを大きく見せる構成に寄せ、短い視認時間でも変化量が読み取りやすいデザインにしています。
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_character_slide(weather: dict) -> None:
    quote_lines = [
        "Navigator が次の情報へスムーズに案内します。",
        f'現在の天気は {weather["area_label"]} で {weather["temp_c"]}°C です。',
        "Copilot Pro CLI を思わせる案内役として設計しています。",
    ]
    st.markdown("## Copilot Navigator")
    st.markdown(
        f"""
        <div class="feature-panel guide-panel">
            <div class="guide-layout">
                <div class="guide-character">
                    <div class="navigator-shell">
                        <div class="navigator-orbit orbit-a"></div>
                        <div class="navigator-orbit orbit-b"></div>
                        <div class="navigator-core">
                            <div class="navigator-eye"></div>
                            <div class="navigator-eye"></div>
                            <div class="navigator-smile"></div>
                        </div>
                        <div class="navigator-badge">NAV</div>
                    </div>
                </div>
                <div class="guide-copy">
                    <div class="eyebrow">COPILOT PRO CLI MOTIF</div>
                    <div class="guide-title">Navigator guide</div>
                    <div class="guide-text">{"<br>".join(escape(line) for line in quote_lines)}</div>
                    <div class="guide-footer">将来的には PNG / GIF / Lottie へ差し替えて、モーションをさらに強化できます。</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


initialize_state()

st.markdown(
    """
    <style>
    .stApp {
        background:
            radial-gradient(circle at top left, rgba(103, 80, 164, 0.2), transparent 26%),
            radial-gradient(circle at top right, rgba(34, 211, 238, 0.12), transparent 22%),
            linear-gradient(180deg, #050816 0%, #0a1020 100%);
    }
    .block-container {
        max-width: 1440px;
        padding-top: 0.8rem;
        padding-bottom: 1.5rem;
    }
    .hero {
        padding: 16px 20px;
        border-radius: 22px;
        background: linear-gradient(135deg, rgba(10,16,32,0.92), rgba(15,23,42,0.78));
        border: 1px solid rgba(125, 211, 252, 0.08);
        box-shadow: 0 14px 34px rgba(0,0,0,0.22);
        margin-bottom: 14px;
    }
    .hero-eyebrow, .eyebrow, .headline-index {
        color: #7dd3fc;
        letter-spacing: 0.12em;
        font-size: 0.72rem;
        font-weight: 700;
    }
    .hero-title {
        font-size: 1.55rem;
        font-weight: 800;
        margin-top: 0.22rem;
    }
    .hero-subtitle, .hero-meta, .meta-note, .headline-source, .guide-footer {
        color: #a5b4cc;
    }
    .hero-meta {
        margin-top: 0.5rem;
        font-size: 0.9rem;
    }
    .feature-panel, .headline-card {
        background: rgba(12, 18, 34, 0.92);
        border: 1px solid rgba(148, 163, 184, 0.12);
        border-radius: 24px;
        box-shadow: 0 14px 30px rgba(0,0,0,0.22);
    }
    .weather-panel {
        min-height: 310px;
        padding: 28px;
        background: linear-gradient(135deg, rgba(67, 56, 202, 0.82), rgba(12, 18, 34, 0.96));
    }
    .feature-location {
        font-size: 1.15rem;
        color: #c4b5fd;
        margin-top: 0.6rem;
    }
    .feature-value {
        font-size: 4.5rem;
        font-weight: 800;
        line-height: 1.08;
        margin-top: 0.5rem;
    }
    .feature-subtitle {
        font-size: 1.1rem;
        color: #d8e3ff;
        margin-top: 0.6rem;
    }
    .status-row {
        display: flex;
        gap: 10px;
        align-items: center;
        flex-wrap: wrap;
        margin: 14px 0 6px;
    }
    .status-pill, .meta-pill {
        display: inline-flex;
        align-items: center;
        border-radius: 999px;
        padding: 6px 12px;
        font-weight: 700;
        color: #04111f;
    }
    .meta-pill {
        background: rgba(148, 163, 184, 0.18);
        color: #dbeafe;
        font-weight: 600;
    }
    .headline-card {
        padding: 18px 20px;
        margin-bottom: 14px;
    }
    .headline-title {
        font-size: 1.22rem;
        font-weight: 700;
        margin-top: 8px;
        line-height: 1.45;
    }
    .headline-source {
        margin-top: 10px;
        font-size: 0.88rem;
    }
    .market-panel {
        margin-top: 18px;
        padding: 18px 20px;
        color: #d1d9e6;
    }
    .guide-panel {
        padding: 28px;
        min-height: 420px;
        background:
            radial-gradient(circle at 22% 22%, rgba(139, 92, 246, 0.18), transparent 20%),
            linear-gradient(135deg, rgba(10, 16, 32, 0.96), rgba(8, 16, 26, 0.98));
    }
    .guide-layout {
        display: flex;
        gap: 32px;
        align-items: center;
        min-height: 360px;
    }
    .guide-character {
        flex: 0 0 34%;
        display: flex;
        justify-content: center;
    }
    .navigator-shell {
        width: 250px;
        height: 250px;
        border-radius: 50%;
        position: relative;
        background: radial-gradient(circle at 30% 30%, rgba(96, 165, 250, 0.22), rgba(15, 23, 42, 0.98));
        border: 1px solid rgba(125, 211, 252, 0.18);
        box-shadow: 0 20px 42px rgba(0,0,0,0.34);
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .navigator-orbit {
        position: relative;
        position: absolute;
        inset: 18px;
        border-radius: 50%;
        border: 1px solid rgba(125, 211, 252, 0.16);
    }
    .orbit-a {
        transform: rotate(24deg);
    }
    .orbit-b {
        inset: 36px;
        transform: rotate(-18deg);
        border-color: rgba(167, 139, 250, 0.2);
    }
    .navigator-core {
        width: 120px;
        height: 120px;
        border-radius: 50%;
        background: linear-gradient(135deg, #60a5fa, #8b5cf6);
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 16px;
        position: relative;
        box-shadow: 0 10px 24px rgba(59, 130, 246, 0.28);
    }
    .navigator-eye {
        width: 12px;
        height: 12px;
        border-radius: 50%;
        background: #f8fafc;
        margin-top: -8px;
    }
    .navigator-smile {
        position: relative;
        position: absolute;
        bottom: 28px;
        width: 36px;
        height: 18px;
        border-bottom: 3px solid #f8fafc;
        border-radius: 0 0 18px 18px;
    }
    .navigator-badge {
        position: absolute;
        bottom: 24px;
        right: 18px;
        text-align: center;
        border-radius: 999px;
        padding: 6px 10px;
        background: rgba(15, 23, 42, 0.92);
        border: 1px solid rgba(125, 211, 252, 0.2);
        color: #e2e8f0;
        font-weight: 700;
        font-size: 0.82rem;
        letter-spacing: 0.12em;
    }
    .guide-copy {
        flex: 1 1 auto;
    }
    .guide-title {
        font-size: 1.55rem;
        font-weight: 800;
        margin-top: 0.35rem;
    }
    .guide-text {
        margin-top: 1rem;
        font-size: 1rem;
        line-height: 1.85;
        color: #d8e3ff;
    }
    .guide-footer {
        margin-top: 1.2rem;
        font-size: 0.9rem;
    }
    div[data-testid="stMetric"] {
        background: rgba(12, 18, 34, 0.92);
        border: 1px solid rgba(148, 163, 184, 0.12);
        padding: 14px;
        border-radius: 18px;
    }
    div[data-testid="stMetric"] label, div[data-testid="stMetric"] [data-testid="stMetricLabel"] {
        font-size: 0.8rem;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.5rem;
    }
    @media (max-width: 980px) {
        .guide-layout {
            flex-direction: column;
            align-items: stretch;
        }
        .guide-character {
            flex-basis: auto;
        }
        .feature-value {
            font-size: 3.6rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("⚙️ 表示設定")
    st.toggle("自動切替", key="signage_autoplay")
    st.slider("切替秒数", min_value=5, max_value=30, key="signage_interval")
    st.slider("ニュース件数", min_value=3, max_value=8, key="signage_news_items")
    st.multiselect(
        "再生する画面",
        options=DEFAULT_PLAYLIST,
        default=st.session_state["signage_playlist"],
        format_func=lambda key: SLIDE_LABELS[key],
        key="signage_playlist",
    )
    st.radio(
        "天気エリア",
        options=["現在地を優先", "地域を入力"],
        key="signage_location_mode",
    )
    st.text_input(
        "地域名（都道府県 / 市区町村）",
        key="signage_manual_location",
        help="例: Tokyo, Osaka, Yokohama, 北海道札幌市",
    )
    st.caption("位置情報が取得できれば現在地を優先し、未取得時は入力地域を使用します。")

playlist = active_playlist()
ensure_current_slide(playlist)

if st.session_state["signage_autoplay"]:
    refresh_count = st_autorefresh(
        interval=st.session_state["signage_interval"] * 1000,
        key="digital-signage-refresh",
    )
    last_refresh_count = st.session_state["signage_last_refresh_count"]
    if last_refresh_count is None:
        st.session_state["signage_last_refresh_count"] = refresh_count
    elif refresh_count != last_refresh_count:
        move_slide(1, playlist)
        st.session_state["signage_last_refresh_count"] = refresh_count
else:
    st.session_state["signage_last_refresh_count"] = None

playlist = active_playlist()
ensure_current_slide(playlist)
current_slide = st.session_state["signage_current_slide"]
current_position = playlist.index(current_slide)
progress_ratio = (current_position + 1) / len(playlist)
next_slide_label = SLIDE_LABELS[playlist[(current_position + 1) % len(playlist)]]

weather, location_status = resolve_weather()
news_limit = st.session_state["signage_news_items"]
domestic_news = fetch_rss_items(
    url="https://www3.nhk.or.jp/rss/news/cat0.xml",
    fallback_items=SAMPLE_DOMESTIC_NEWS,
    source_label="NHK RSS",
    limit=news_limit,
)
global_news = fetch_rss_items(
    url="https://feeds.bbci.co.uk/news/world/rss.xml",
    fallback_items=SAMPLE_GLOBAL_NEWS,
    source_label="BBC World RSS",
    limit=news_limit,
)
market_rows = [
    fetch_market_quote("^N225", "Nikkei 225"),
    fetch_market_quote("^DJI", "Dow Jones"),
    fetch_market_quote("^SPX", "S&P 500"),
]

st.markdown(
    f"""
    <div class="hero">
        <div class="hero-eyebrow">COPILOT CLI STYLE</div>
        <div class="hero-title">Digital Signage</div>
        <div class="hero-meta">
            NOW PLAYING: <strong>{escape(SLIDE_LABELS[current_slide])}</strong>
            &nbsp;|&nbsp; NEXT: <strong>{escape(next_slide_label)}</strong>
            &nbsp;|&nbsp; WEATHER: <strong>{escape(weather["area_label"])}</strong>
            &nbsp;|&nbsp; {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

nav_left, nav_mid, nav_right = st.columns([1, 2, 1])
with nav_left:
    if st.button("◀ Previous", use_container_width=True):
        move_slide(-1, playlist)
with nav_mid:
    st.progress(progress_ratio, text=f"再生リスト進行: {current_position + 1}/{len(playlist)}")
    st.caption(" ▶ ".join(SLIDE_LABELS[key] for key in playlist))
with nav_right:
    if st.button("Next ▶", use_container_width=True):
        move_slide(1, playlist)

current_slide = st.session_state["signage_current_slide"]
if current_slide == "weather":
    render_weather_slide(weather, location_status)
elif current_slide == "domestic-news":
    render_news_slide("国内主要ニュース", domestic_news)
elif current_slide == "global-news":
    render_news_slide("海外主要ニュース", global_news)
elif current_slide == "markets":
    render_market_slide(market_rows)
else:
    render_character_slide(weather)
