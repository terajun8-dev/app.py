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
import streamlit.components.v1 as components


st.set_page_config(page_title="Signage Prototype", layout="wide")


SLIDES = [
    ("weather", "01. 天気予報"),
    ("domestic-news", "02. 国内主要ニュース"),
    ("global-news", "03. 海外主要ニュース"),
    ("markets", "04. 株価・指数"),
    ("character", "05. キャラクター演出"),
]

SAMPLE_WEATHER = {
    "city": "Tokyo",
    "temp_c": "18",
    "feels_like_c": "17",
    "humidity": "52",
    "description": "晴れ時々くもり",
    "source": "sample",
    "status": "demo",
    "note": "ライブ天気データを取得できなかったため、サンプル表示です。",
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

USER_AGENT = "Mozilla/5.0 (compatible; MyStreamlitApp/1.0)"


def read_query_value(name: str, default: str) -> str:
    value = st.query_params.get(name, default)
    if isinstance(value, list):
        return value[0] if value else default
    return value


def parse_int(value: str, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except ValueError:
        return default
    return max(minimum, min(parsed, maximum))


def parse_bool(value: str, default: bool) -> bool:
    if value.lower() in {"true", "1", "yes", "on"}:
        return True
    if value.lower() in {"false", "0", "no", "off"}:
        return False
    return default


def parse_slide_key(value: str) -> str:
    slide_keys = [key for key, _ in SLIDES]
    if value in slide_keys:
        return value
    if value.isdigit():
        index = parse_int(value, default=0, minimum=0, maximum=len(SLIDES) - 1)
        return SLIDES[index][0]
    return SLIDES[0][0]


def parse_playlist(value: str) -> list[str]:
    valid_keys = {key for key, _ in SLIDES}
    requested = [item.strip() for item in value.split(",") if item.strip()]
    playlist = [item for item in requested if item in valid_keys]
    return playlist or [key for key, _ in SLIDES]


def slide_label(slide_key: str) -> str:
    return dict(SLIDES)[slide_key]


def set_page_state(slide_key: str, autoplay: bool, interval: int, city: str, items: int, playlist: list[str]) -> None:
    desired = {
        "slide": slide_key,
        "autoplay": str(autoplay).lower(),
        "interval": str(interval),
        "city": city,
        "items": str(items),
        "playlist": ",".join(playlist),
    }
    current = {key: read_query_value(key, "") for key in desired}
    if current != desired:
        st.query_params.clear()
        st.query_params.update(desired)


@st.cache_data(ttl=900, show_spinner=False)
def fetch_text(url: str) -> str:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=8) as response:
        return response.read().decode("utf-8")


@st.cache_data(ttl=900, show_spinner=False)
def fetch_weather(city: str) -> dict:
    try:
        encoded_city = urllib.parse.quote(city)
        weather_url = f"https://wttr.in/{encoded_city}?format=j1"
        payload = json.loads(fetch_text(weather_url))
        current = payload["current_condition"][0]
        return {
            "city": city,
            "temp_c": current["temp_C"],
            "feels_like_c": current["FeelsLikeC"],
            "humidity": current["humidity"],
            "description": current["weatherDesc"][0]["value"],
            "source": "wttr.in",
            "status": "live",
            "note": "ライブデータを表示中",
            "fetched_at": datetime.now().strftime("%H:%M:%S"),
        }
    except (HTTPError, URLError, TimeoutError, JSONDecodeError, KeyError, IndexError, UnicodeDecodeError) as exc:
        fallback = SAMPLE_WEATHER.copy()
        fallback["city"] = city
        fallback["note"] = f"{fallback['note']} ({exc.__class__.__name__})"
        fallback["fetched_at"] = datetime.now().strftime("%H:%M:%S")
        return fallback


@st.cache_data(ttl=900, show_spinner=False)
def fetch_rss_items(url: str, fallback_items: list[dict], source_label: str, limit: int) -> dict:
    try:
        xml_text = fetch_text(url)
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
            "fetched_at": datetime.now().strftime("%H:%M:%S"),
        }
    except (HTTPError, URLError, TimeoutError, ET.ParseError, UnicodeDecodeError, ValueError) as exc:
        return {
            "items": fallback_items[:limit],
            "source": "sample",
            "status": "demo",
            "note": f"ライブRSSを取得できなかったため、サンプル表示です。 ({exc.__class__.__name__})",
            "fetched_at": datetime.now().strftime("%H:%M:%S"),
        }


@st.cache_data(ttl=900, show_spinner=False)
def fetch_market_quote(symbol: str, name: str) -> dict:
    try:
        quote_url = f"https://stooq.com/q/l/?s={urllib.parse.quote(symbol)}&i=d"
        csv_text = fetch_text(quote_url)
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
            "fetched_at": datetime.now().strftime("%H:%M:%S"),
        }
    except (HTTPError, URLError, TimeoutError, UnicodeDecodeError, KeyError, StopIteration, ValueError, ZeroDivisionError):
        for fallback in SAMPLE_MARKETS:
            if fallback["symbol"] == symbol:
                return {
                    **fallback,
                    "source": "sample",
                    "status": "demo",
                    "note": "ライブ指数を取得できなかったため、サンプル表示です。",
                    "fetched_at": datetime.now().strftime("%H:%M:%S"),
                }
        raise


def render_status_badge(status: str, note: str, source: str, fetched_at: str) -> None:
    badge_color = "#16a34a" if status == "live" else "#f59e0b"
    st.markdown(
        f"""
        <div style="display:flex; gap:12px; align-items:center; margin-bottom:12px;">
            <span style="background:{badge_color}; color:#071018; font-weight:700; padding:6px 12px; border-radius:999px;">
                {"LIVE" if status == "live" else "DEMO"}
            </span>
            <span style="color:#cdd6f4;">Source: {escape(source)}</span>
            <span style="color:#93c5fd;">Updated: {escape(fetched_at)}</span>
            <span style="color:#94a3b8;">{escape(note)}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_weather_slide(weather: dict) -> None:
    left, right = st.columns([1.2, 1])
    with left:
        st.markdown("## 今日の天気")
        st.markdown(
            f"""
            <div style="background:linear-gradient(135deg,#0f172a,#1d4ed8); padding:28px; border-radius:24px;">
                <div style="font-size:22px; color:#bfdbfe;">{escape(weather["city"])}</div>
                <div style="font-size:80px; font-weight:700;">{escape(weather["temp_c"])}°C</div>
                <div style="font-size:26px; color:#dbeafe;">{escape(weather["description"])}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with right:
        st.metric("体感温度", f'{weather["feels_like_c"]}°C')
        st.metric("湿度", f'{weather["humidity"]}%')
        st.info("朝の掲示板、受付ディスプレイ、待合スペース向けの見せ方です。")
    render_status_badge(weather["status"], weather["note"], weather["source"], weather["fetched_at"])


def render_news_slide(title: str, news_data: dict) -> None:
    st.markdown(f"## {title}")
    render_status_badge(news_data["status"], news_data["note"], news_data["source"], news_data["fetched_at"])
    for index, item in enumerate(news_data["items"], start=1):
        st.markdown(
            f"""
            <div style="background:#111827; border:1px solid #1f2937; border-radius:18px; padding:18px; margin-bottom:14px;">
                <div style="font-size:14px; color:#60a5fa;">HEADLINE {index:02d}</div>
                <div style="font-size:26px; font-weight:600; margin-top:6px;">{escape(item["title"])}</div>
                <div style="font-size:14px; color:#94a3b8; margin-top:10px;">{escape(item["source"])}</div>
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
        <div style="margin-top:18px; background:#0f172a; border-radius:18px; padding:18px; color:#cbd5e1;">
            サイネージ用途では「主要指数だけを大きく見せる」構成が見やすく、滞在時間が短い場所でも情報が伝わりやすいです。
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_character_slide(current_slide: int, weather: dict) -> None:
    quote_lines = [
        "おはようございます。最新情報をお届けします。",
        f'{weather["city"]}の気温は {weather["temp_c"]}°C です。',
        "ニュースと市況は数秒ごとに切り替わります。",
    ]
    st.markdown("## キャラクター演出")
    st.markdown(
        f"""
        <style>
        .stage {{
            position: relative;
            overflow: hidden;
            min-height: 420px;
            border-radius: 26px;
            background: linear-gradient(135deg, #1e1b4b, #0f172a 62%, #083344);
            padding: 30px;
        }}
        .character {{
            position: absolute;
            left: 8%;
            bottom: 18px;
            font-size: 150px;
            animation: floaty 2.4s ease-in-out infinite;
            filter: drop-shadow(0 12px 18px rgba(0,0,0,0.35));
        }}
        .bubble {{
            margin-left: 32%;
            background: rgba(255,255,255,0.1);
            border: 1px solid rgba(255,255,255,0.18);
            backdrop-filter: blur(10px);
            border-radius: 24px;
            padding: 24px;
        }}
        .ticker {{
            position: absolute;
            left: 0;
            bottom: 0;
            width: 100%;
            background: rgba(15,23,42,0.85);
            color: #e2e8f0;
            padding: 10px 0;
            white-space: nowrap;
            overflow: hidden;
        }}
        .ticker span {{
            display: inline-block;
            padding-left: 100%;
            animation: marquee 18s linear infinite;
        }}
        @keyframes floaty {{
            0% {{ transform: translateY(0px); }}
            50% {{ transform: translateY(-12px); }}
            100% {{ transform: translateY(0px); }}
        }}
        @keyframes marquee {{
            0% {{ transform: translateX(0%); }}
            100% {{ transform: translateX(-100%); }}
        }}
        </style>
        <div class="stage">
            <div class="character">{"🧙" if current_slide % 2 == 0 else "🦸"}</div>
            <div class="bubble">
                <div style="font-size:14px; color:#93c5fd;">DIGITAL SIGNAGE MODE</div>
                <div style="font-size:34px; font-weight:700; margin-top:8px;">キャラクター案内ボード</div>
                <div style="font-size:20px; color:#dbeafe; margin-top:18px; line-height:1.8;">
                    {"<br>".join(escape(line) for line in quote_lines)}
                </div>
                <div style="margin-top:18px; color:#cbd5e1;">
                    画像・GIF・Live2D・Lottie に差し替えれば、より本格的な演出にも発展できます。
                </div>
            </div>
            <div class="ticker">
                <span>Weather / Domestic News / Global News / Markets / Character Art を順番に再生する試作です。</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def inject_autoplay(current_slide: str, autoplay: bool, interval: int, city: str, items: int, playlist: list[str]) -> None:
    if not autoplay:
        return
    current_position = playlist.index(current_slide)
    next_slide = playlist[(current_position + 1) % len(playlist)]
    next_query = urllib.parse.urlencode(
        {
            "slide": next_slide,
            "autoplay": str(autoplay).lower(),
            "interval": str(interval),
            "city": city,
            "items": str(items),
            "playlist": ",".join(playlist),
        }
    )
    components.html(
        f"""
        <script>
        const nextQuery = {json.dumps(next_query)};
        const nextPath = window.parent.location.pathname + "?" + nextQuery;
        setTimeout(() => {{
            window.parent.location.href = nextPath;
        }}, {interval * 1000});
        </script>
        """,
        height=0,
    )


st.markdown(
    """
    <style>
    .block-container {
        padding-top: 1.4rem;
        padding-bottom: 1.2rem;
        max-width: 1400px;
    }
    div[data-testid="stMetric"] {
        background: #111827;
        border: 1px solid #1f2937;
        padding: 16px;
        border-radius: 18px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


playlist_default = parse_playlist(read_query_value("playlist", ",".join(key for key, _ in SLIDES)))
current_slide = parse_slide_key(read_query_value("slide", "weather"))
autoplay_default = parse_bool(read_query_value("autoplay", "true"), default=True)
interval_default = parse_int(read_query_value("interval", "8"), default=8, minimum=5, maximum=30)
city_default = read_query_value("city", "Tokyo")
items_default = parse_int(read_query_value("items", "5"), default=5, minimum=3, maximum=8)

st.title("🎭 Signage Prototype")
st.caption("天気・ニュース・株価・キャラクター演出を定期切替する Streamlit 試作ページ")

with st.sidebar:
    st.header("⚙️ 表示設定")
    autoplay = st.toggle("自動切替", value=autoplay_default)
    interval = st.slider("切替秒数", min_value=5, max_value=30, value=interval_default)
    city = st.text_input("天気の都市", value=city_default)
    items = st.slider("ニュース件数", min_value=3, max_value=8, value=items_default)
    playlist = st.multiselect(
        "再生する画面",
        options=[key for key, _ in SLIDES],
        default=playlist_default,
        format_func=slide_label,
    )
    if not playlist:
        playlist = [key for key, _ in SLIDES]
        st.warning("少なくとも1つの画面が必要なため、全画面を再設定しました。")
    st.caption("公開データ取得に失敗した場合は自動でデモ表示に切り替えます。")

if current_slide not in playlist:
    current_slide = playlist[0]

current_position = playlist.index(current_slide)
progress_ratio = (current_position + 1) / len(playlist)
next_slide_label = slide_label(playlist[(current_position + 1) % len(playlist)])

nav_left, nav_mid, nav_right = st.columns([1, 2, 1])
with nav_left:
    if st.button("◀ Previous", use_container_width=True):
        current_slide = playlist[(current_position - 1) % len(playlist)]
        set_page_state(current_slide, autoplay, interval, city, items, playlist)
        st.rerun()
with nav_mid:
    st.markdown(
        f"""
        <div style="text-align:center; background:#0f172a; border-radius:18px; padding:14px;">
            <div style="font-size:14px; color:#60a5fa;">NOW PLAYING</div>
            <div style="font-size:28px; font-weight:700;">{escape(slide_label(current_slide))}</div>
            <div style="color:#94a3b8;">Playlist {current_position + 1} / {len(playlist)} ・ Next: {escape(next_slide_label)} ・ {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with nav_right:
    if st.button("Next ▶", use_container_width=True):
        current_slide = playlist[(current_position + 1) % len(playlist)]
        set_page_state(current_slide, autoplay, interval, city, items, playlist)
        st.rerun()

st.progress(progress_ratio, text=f"再生リスト進行: {current_position + 1}/{len(playlist)}")
st.caption(" ▶ ".join(slide_label(key) for key in playlist))

set_page_state(current_slide, autoplay, interval, city, items, playlist)

weather = fetch_weather(city)
domestic_news = fetch_rss_items(
    url="https://www3.nhk.or.jp/rss/news/cat0.xml",
    fallback_items=SAMPLE_DOMESTIC_NEWS,
    source_label="NHK RSS",
    limit=items,
)
global_news = fetch_rss_items(
    url="https://feeds.bbci.co.uk/news/world/rss.xml",
    fallback_items=SAMPLE_GLOBAL_NEWS,
    source_label="BBC World RSS",
    limit=items,
)
market_rows = [
    fetch_market_quote("^N225", "Nikkei 225"),
    fetch_market_quote("^DJI", "Dow Jones"),
    fetch_market_quote("^SPX", "S&P 500"),
]

if current_slide == "weather":
    render_weather_slide(weather)
elif current_slide == "domestic-news":
    render_news_slide("国内主要ニュース", domestic_news)
elif current_slide == "global-news":
    render_news_slide("海外主要ニュース", global_news)
elif current_slide == "markets":
    render_market_slide(market_rows)
else:
    render_character_slide(current_position, weather)

inject_autoplay(current_slide, autoplay, interval, city, items, playlist)
