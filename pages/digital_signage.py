import email.utils
import json
import random
import urllib.parse
from datetime import datetime, timedelta, timezone
from html import escape
from json import JSONDecodeError
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

import streamlit as st
from deep_translator import GoogleTranslator
from deep_translator.exceptions import BaseError, RequestError, ServerException
from streamlit_autorefresh import st_autorefresh
from streamlit_geolocation import streamlit_geolocation


st.set_page_config(page_title="Digital Signage", layout="wide")


SLIDES = [
    ("weather", "01. 天気予報"),
    ("domestic-news", "02. Domestic News"),
    ("global-news", "03. Global News"),
    ("fun", "04. Fortune / Today"),
]

DEFAULT_PLAYLIST = [key for key, _ in SLIDES]
SLIDE_LABELS = dict(SLIDES)
USER_AGENT = "Mozilla/5.0 (compatible; MyStreamlitApp/1.0)"
DEFAULT_MANUAL_LOCATION = "Tokyo"
JST = timezone(timedelta(hours=9))
CACHE_VERSION = "jst-cache-v2"
TRANSLATION_CACHE_VERSION = "free-translate-v1"

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
    {"title": "政府、来年度の成長戦略を発表", "source": "Demo News JP", "link": "https://news.google.com/rss?hl=ja&gl=JP&ceid=JP:ja", "published_at": "--:--"},
    {"title": "主要都市で春のイベント準備が本格化", "source": "Demo News JP", "link": "https://news.google.com/rss?hl=ja&gl=JP&ceid=JP:ja", "published_at": "--:--"},
    {"title": "国内製造業の景況感が緩やかに改善", "source": "Demo News JP", "link": "https://news.google.com/rss?hl=ja&gl=JP&ceid=JP:ja", "published_at": "--:--"},
]

SAMPLE_GLOBAL_NEWS = [
    {"title": "Global markets await central bank signals", "source": "Demo World News", "link": "https://news.google.com/rss/headlines/section/topic/WORLD?hl=en-US&gl=US&ceid=US:en", "published_at": "--:--"},
    {"title": "Major cities expand clean-energy projects", "source": "Demo World News", "link": "https://news.google.com/rss/headlines/section/topic/WORLD?hl=en-US&gl=US&ceid=US:en", "published_at": "--:--"},
    {"title": "Shipping routes recover after weather delays", "source": "Demo World News", "link": "https://news.google.com/rss/headlines/section/topic/WORLD?hl=en-US&gl=US&ceid=US:en", "published_at": "--:--"},
]

ZODIAC_SIGNS = [
    {"name": "牡羊座", "symbol": "Aries", "lucky": "新しい挑戦", "color": "Crimson", "message": "迷ったら先に一歩。勢いが運を引き寄せます。"},
    {"name": "牡牛座", "symbol": "Taurus", "lucky": "お気に入りの音楽", "color": "Emerald", "message": "落ち着いた判断が光る日。丁寧さが評価につながります。"},
    {"name": "双子座", "symbol": "Gemini", "lucky": "短いメモ", "color": "Sky Blue", "message": "情報運が高め。会話の中にヒントがありそうです。"},
    {"name": "蟹座", "symbol": "Cancer", "lucky": "温かい飲み物", "color": "Silver", "message": "身近な人との連携が運気を押し上げます。"},
    {"name": "獅子座", "symbol": "Leo", "lucky": "明るい挨拶", "color": "Gold", "message": "存在感が増す日。堂々とした表現が吉です。"},
    {"name": "乙女座", "symbol": "Virgo", "lucky": "整理整頓", "color": "Mint", "message": "細部に気づける日。小さな修正が大きな成果に。"},
    {"name": "天秤座", "symbol": "Libra", "lucky": "バランスの良い食事", "color": "Lavender", "message": "調整役としての魅力が高まります。中立な視点が鍵です。"},
    {"name": "蠍座", "symbol": "Scorpio", "lucky": "静かな時間", "color": "Wine Red", "message": "集中力が冴える日。深く掘るほど収穫があります。"},
    {"name": "射手座", "symbol": "Sagittarius", "lucky": "新しい記事", "color": "Royal Blue", "message": "視野を広げると流れが変わります。学びにツキあり。"},
    {"name": "山羊座", "symbol": "Capricorn", "lucky": "チェックリスト", "color": "Charcoal", "message": "着実さが武器。段取りの良さがそのまま結果に。"},
    {"name": "水瓶座", "symbol": "Aquarius", "lucky": "アイデアメモ", "color": "Cyan", "message": "ひらめきが冴える日。少し変化球の発想が当たりです。"},
    {"name": "魚座", "symbol": "Pisces", "lucky": "やさしい言葉", "color": "Pearl", "message": "感受性が高まります。共感が流れをやわらかくします。"},
]

TODAY_FACT_FALLBACKS = [
    "今日は『発明の日』。小さな工夫が大きな改善につながることを意識したい日です。",
    "今日は『新しい習慣を始めるのに向いた日』。1つだけでも続けたいことを決めてみるのがおすすめです。",
    "今日は『記録を見直す日』。過去のメモやログから次のヒントが見つかるかもしれません。",
]


def initialize_state() -> None:
    defaults = {
        "signage_current_slide": DEFAULT_PLAYLIST[0],
        "signage_playlist": DEFAULT_PLAYLIST.copy(),
        "signage_autoplay": True,
        "signage_interval": 8,
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
def cached_fetch_text(url: str, cache_version: str) -> str:
    return fetch_text(url)


@st.cache_data(ttl=300, show_spinner=False)
def cached_fetch_rss_text(url: str, cache_version: str) -> str:
    return fetch_text(url)


def timestamp_now() -> str:
    return datetime.now(JST).strftime("%H:%M:%S")


@st.cache_data(ttl=21600, show_spinner=False)
def translate_text(text: str, source_lang: str, target_lang: str, cache_version: str) -> dict:
    normalized = " ".join(text.split())
    if not normalized:
        return {"text": "", "status": "empty"}
    if source_lang == target_lang:
        return {"text": normalized, "status": "same-language"}
    try:
        translated = GoogleTranslator(source=source_lang, target=target_lang).translate(normalized)
        if not translated:
            raise ValueError("Translator returned no text.")
        return {"text": translated.strip(), "status": "translated"}
    except (BaseError, RequestError, ServerException, ValueError):
        return {"text": "", "status": "failed"}


def format_pub_date(pub_date_text: str) -> str:
    if not pub_date_text:
        return "--:--"
    try:
        parsed = email.utils.parsedate_to_datetime(pub_date_text)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(JST).strftime("%H:%M")
    except (TypeError, ValueError, IndexError, OverflowError):
        return pub_date_text[:16]


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
        payload = json.loads(cached_fetch_text(weather_url, CACHE_VERSION))
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


@st.cache_data(ttl=300, show_spinner=False)
def fetch_rss_items(url: str, fallback_items: list[dict], source_label: str, limit: int, translate_to_ja: bool = False) -> dict:
    try:
        xml_text = cached_fetch_rss_text(url, CACHE_VERSION)
        root = ET.fromstring(xml_text)
        parsed_items = []
        for item in root.findall(".//item")[:limit]:
            title = item.findtext("title", default="(no title)")
            source = item.findtext("source", default=source_label)
            link = item.findtext("link", default=url)
            pub_date = item.findtext("pubDate", default="")
            title_text = title.strip()
            translated_title = ""
            if translate_to_ja:
                translation = translate_text(title_text, "auto", "ja", TRANSLATION_CACHE_VERSION)
                if translation["status"] == "translated" and translation["text"] != title_text:
                    translated_title = translation["text"]
            parsed_items.append(
                {
                    "title": title_text,
                    "translated_title": translated_title,
                    "source": source.strip(),
                    "link": link.strip(),
                    "published_at": format_pub_date(pub_date.strip()),
                }
            )
        if not parsed_items:
            raise ValueError("RSS feed returned no items.")
        return {
            "items": parsed_items,
            "source": source_label,
            "status": "live",
            "note": "ニュースは約5分ごとに更新",
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


@st.cache_data(ttl=21600, show_spinner=False)
def fetch_today_fact(month: int, day: int) -> dict:
    try:
        api_url = f"https://api.wikimedia.org/feed/v1/wikipedia/en/onthisday/events/{month}/{day}"
        payload = json.loads(cached_fetch_text(api_url, CACHE_VERSION))
        events = payload.get("events", [])
        if not events:
            raise ValueError("No on-this-day events returned.")
        picked = random.choice(events[: min(len(events), 20)])
        article_title = picked.get("pages", [{}])[0].get("normalizedtitle", "Wikipedia")
        original_text = picked.get("text", "Today in history")
        translation = translate_text(original_text, "en", "ja", TRANSLATION_CACHE_VERSION)
        translated_text = translation["text"] if translation["status"] == "translated" else ""
        translation_note = "今日は何の日を日本語訳で表示中" if translation["status"] == "translated" else "今日は何の日を表示中"
        return {
            "title": f"{picked.get('year', '--')}年の出来事",
            "description": original_text,
            "translated_description": translated_text,
            "original_description": original_text,
            "link": picked.get("pages", [{}])[0].get("content_urls", {}).get("desktop", {}).get("page", "https://en.wikipedia.org/wiki/Main_Page"),
            "source": f"Wikimedia / {article_title}",
            "status": "live",
            "note": translation_note,
            "fetched_at": timestamp_now(),
        }
    except (HTTPError, URLError, TimeoutError, UnicodeDecodeError, JSONDecodeError, KeyError, IndexError, ValueError):
        return {
            "title": "今日は何の日",
            "description": "Today in history information is unavailable right now.",
            "translated_description": random.choice(TODAY_FACT_FALLBACKS),
            "link": "https://en.wikipedia.org/wiki/Main_Page",
            "source": "fallback",
            "status": "demo",
            "note": "履歴データ取得に失敗したため、固定メッセージを表示中",
            "fetched_at": timestamp_now(),
        }


def build_fortune() -> dict:
    sign = random.choice(ZODIAC_SIGNS)
    return {
        "title": f'{sign["name"]} / {sign["symbol"]}',
        "description": sign["message"],
        "lucky": sign["lucky"],
        "color": sign["color"],
        "source": "local fortune",
        "status": "live",
        "note": "ランダム星占いを表示中",
        "fetched_at": timestamp_now(),
    }


def render_status_badge(status: str, note: str, source: str, fetched_at: str) -> None:
    if status == "live":
        badge_color = "#14b8a6"
        badge_label = "LIVE"
    elif status == "snapshot":
        badge_color = "#60a5fa"
        badge_label = "SNAPSHOT"
    else:
        badge_color = "#f59e0b"
        badge_label = "DEMO"
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
    st.markdown("## Weather")
    st.markdown(
        f"""
        <div class="feature-panel weather-panel compact-weather">
            <div class="weather-copy">
                <div class="eyebrow">LOCAL WEATHER</div>
                <div class="feature-location">{escape(weather["area_label"])}</div>
                <div class="weather-inline">
                    <span class="feature-value">{escape(weather["temp_c"])}°C</span>
                    <span class="feature-subtitle">{escape(weather["description"])}</span>
                </div>
                <div class="weather-meta">Feels like {escape(weather["feels_like_c"])}°C / Humidity {escape(weather["humidity"])}% / {escape(location_status)}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    render_status_badge(weather["status"], weather["note"], weather["source"], weather["fetched_at"])


def render_news_slide(title: str, news_data: dict) -> None:
    st.markdown(f"## {title}")
    render_status_badge(news_data["status"], news_data["note"], news_data["source"], news_data["fetched_at"])
    for index, item in enumerate(news_data["items"], start=1):
        translated_title = item.get("translated_title", "")
        card_html_parts = [
            '<div class="headline-card compact-headline">',
            f'<div class="headline-index">TOP {index}</div>',
            '<div class="headline-title">',
            f'<a href="{escape(item["link"])}" target="_blank" rel="noopener noreferrer">{escape(item["title"])}</a>',
            "</div>",
        ]
        if translated_title:
            card_html_parts.append(f'<div class="headline-translation">{escape(translated_title)}</div>')
        card_html_parts.append(f'<div class="headline-source">{escape(item["published_at"])} / {escape(item["source"])}</div>')
        card_html_parts.append("</div>")
        st.markdown("".join(card_html_parts), unsafe_allow_html=True)


def render_fun_slide(fun_content: dict) -> None:
    st.markdown(f'## {fun_content["heading"]}')
    render_status_badge(fun_content["status"], fun_content["note"], fun_content["source"], fun_content["fetched_at"])
    translated_description = fun_content.get("translated_description", "")
    panel_html_parts = [
        '<div class="feature-panel fun-panel">',
        f'<div class="eyebrow">{escape(fun_content["eyebrow"])}</div>',
        f'<div class="fun-title">{escape(fun_content["title"])}</div>',
        f'<div class="fun-description">{escape(fun_content["description"])}</div>',
    ]
    if translated_description:
        panel_html_parts.append(f'<div class="fun-translation">{escape(translated_description)}</div>')
    panel_html_parts.append(f'<div class="market-panel-copy">{escape(fun_content["footer"])}</div>')
    panel_html_parts.append("</div>")
    st.markdown("".join(panel_html_parts), unsafe_allow_html=True)


initialize_state()

st.markdown(
    """
    <style>
    .stApp, .stApp * {
        font-family: "Cascadia Code", "Consolas", "SFMono-Regular", monospace;
    }
    .stApp {
        background:
            radial-gradient(circle at top left, rgba(88, 28, 135, 0.22), transparent 24%),
            radial-gradient(circle at top right, rgba(59, 130, 246, 0.16), transparent 20%),
            repeating-linear-gradient(180deg, rgba(148, 163, 184, 0.025) 0 1px, transparent 1px 28px),
            linear-gradient(180deg, #030712 0%, #070b16 100%);
    }
    .block-container {
        max-width: 1440px;
        padding-top: 0.55rem;
        padding-bottom: 1.5rem;
    }
    h2 {
        margin-top: 0.2rem;
        margin-bottom: 0.55rem;
        color: #dff7ff;
        font-size: 1.05rem;
        letter-spacing: 0.08em;
        text-transform: uppercase;
    }
    h2::before {
        content: "> ";
        color: #67e8f9;
    }
    .hero-eyebrow, .eyebrow, .headline-index {
        color: #67e8f9;
        letter-spacing: 0.12em;
        font-size: 0.72rem;
        font-weight: 700;
    }
    .meta-note, .headline-source {
        color: #a5b4cc;
    }
    .feature-panel, .headline-card, .market-card {
        background: rgba(8, 14, 28, 0.94);
        border: 1px solid rgba(96, 165, 250, 0.1);
        border-radius: 18px;
        box-shadow: 0 14px 30px rgba(0,0,0,0.2);
        position: relative;
        overflow: hidden;
    }
    .feature-panel::before, .headline-card::before, .market-card::before {
        content: "";
        position: absolute;
        inset: 0;
        background:
            linear-gradient(90deg, rgba(103, 232, 249, 0.06), transparent 24%),
            repeating-linear-gradient(180deg, rgba(148, 163, 184, 0.03) 0 1px, transparent 1px 24px);
        pointer-events: none;
    }
    .feature-panel::after, .headline-card::after, .market-card::after {
        content: "";
        position: absolute;
        inset: 8px;
        border: 1px solid rgba(103, 232, 249, 0.08);
        border-radius: 12px;
        pointer-events: none;
    }
    .weather-panel {
        min-height: 220px;
        padding: 18px 20px;
        background: linear-gradient(135deg, rgba(55, 48, 163, 0.76), rgba(8, 14, 28, 0.98));
    }
    .feature-location {
        font-size: 0.95rem;
        color: #c4b5fd;
        margin-top: 0.35rem;
    }
    .feature-value {
        font-size: 2.55rem;
        font-weight: 800;
        line-height: 1.08;
        margin-top: 0;
    }
    .feature-subtitle {
        font-size: 0.92rem;
        color: #d8e3ff;
        margin-top: 0;
    }
    .weather-inline {
        display: flex;
        align-items: baseline;
        gap: 16px;
        margin-top: 0.5rem;
    }
    .weather-meta {
        margin-top: 0.55rem;
        font-size: 0.82rem;
        color: #cbd5e1;
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
        position: relative;
        z-index: 1;
    }
    .meta-pill {
        background: rgba(15, 23, 42, 0.88);
        border: 1px solid rgba(103, 232, 249, 0.12);
        color: #dbeafe;
        font-weight: 600;
    }
    .headline-card {
        padding: 12px 14px;
        margin-bottom: 10px;
    }
    .headline-title {
        font-size: 0.96rem;
        font-weight: 700;
        margin-top: 4px;
        line-height: 1.35;
    }
    .headline-title a {
        color: #e5f0ff;
        text-decoration: none;
    }
    .headline-title a:hover {
        text-decoration: underline;
    }
    .headline-source {
        margin-top: 6px;
        font-size: 0.78rem;
        letter-spacing: 0.04em;
    }
    .headline-translation {
        margin-top: 6px;
        color: #cbd5e1;
        font-size: 0.78rem;
        line-height: 1.5;
    }
    .market-panel {
        margin-top: 14px;
        padding: 14px 16px;
        color: #d1d9e6;
    }
    .fun-panel {
        margin-top: 14px;
        padding: 18px 20px;
        min-height: 220px;
        background: linear-gradient(135deg, rgba(76, 29, 149, 0.72), rgba(8, 14, 28, 0.98));
    }
    .fun-title {
        margin-top: 12px;
        color: #f8fafc;
        font-size: 1.65rem;
        font-weight: 800;
    }
    .fun-description {
        margin-top: 14px;
        color: #dbeafe;
        line-height: 1.8;
        font-size: 0.98rem;
        white-space: pre-wrap;
    }
    .fun-translation {
        margin-top: 10px;
        color: #cbd5e1;
        line-height: 1.7;
        font-size: 0.9rem;
        white-space: pre-wrap;
    }
    .market-card {
        background: rgba(8, 14, 28, 0.95);
        border: 1px solid rgba(96, 165, 250, 0.1);
        border-radius: 16px;
        padding: 14px 16px;
        min-height: 132px;
    }
    .market-name {
        margin-top: 4px;
        color: #dbeafe;
        font-size: 1rem;
        font-weight: 700;
        letter-spacing: 0.04em;
    }
    .market-close {
        margin-top: 12px;
        font-size: 1.7rem;
        font-weight: 800;
        color: #f8fafc;
    }
    .market-delta {
        margin-top: 10px;
        font-size: 0.92rem;
        font-weight: 700;
    }
    .market-delta.up {
        color: #34d399;
    }
    .market-delta.down {
        color: #f87171;
    }
    .market-panel-copy {
        font-size: 0.84rem;
        line-height: 1.65;
        position: relative;
        z-index: 1;
    }
    div[data-testid="stMetric"] {
        background: rgba(8, 14, 28, 0.95);
        border: 1px solid rgba(96, 165, 250, 0.08);
        padding: 12px;
        border-radius: 14px;
    }
    div[data-testid="stMetric"] label, div[data-testid="stMetric"] [data-testid="stMetricLabel"] {
        font-size: 0.72rem;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.35rem;
    }
    .element-container div[data-testid="stProgress"] {
        margin-top: 0.15rem;
    }
    .stMarkdown {
        position: relative;
        z-index: 1;
    }
    @media (max-width: 980px) {
        .weather-inline {
            flex-direction: column;
            gap: 8px;
            align-items: flex-start;
        }
        .feature-value {
            font-size: 2.2rem;
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
weather, location_status = resolve_weather()
domestic_news = fetch_rss_items(
    url="https://news.google.com/rss?hl=ja&gl=JP&ceid=JP:ja",
    fallback_items=SAMPLE_DOMESTIC_NEWS,
    source_label="Google News JP",
    limit=3,
)
global_news = fetch_rss_items(
    url="https://news.google.com/rss/headlines/section/topic/WORLD?hl=en-US&gl=US&ceid=US:en",
    fallback_items=SAMPLE_GLOBAL_NEWS,
    source_label="Google News World",
    limit=3,
    translate_to_ja=True,
)
today_fact = fetch_today_fact(datetime.now(JST).month, datetime.now(JST).day)
fortune = build_fortune()
fun_content = random.choice(
    [
        {
            "heading": "Fortune",
            "eyebrow": "RANDOM HOROSCOPE",
            "title": fortune["title"],
            "description": fortune["description"],
            "translated_description": "",
            "footer": f'Lucky item: {fortune["lucky"]} / Lucky color: {fortune["color"]}',
            "source": fortune["source"],
            "status": fortune["status"],
            "note": fortune["note"],
            "fetched_at": fortune["fetched_at"],
        },
        {
            "heading": "On This Day",
            "eyebrow": "TODAY IN HISTORY",
            "title": today_fact["title"],
            "description": today_fact["description"],
            "translated_description": today_fact.get("translated_description", ""),
            "footer": f'Open: {today_fact["link"]}',
            "source": today_fact["source"],
            "status": today_fact["status"],
            "note": today_fact["note"],
            "fetched_at": today_fact["fetched_at"],
        },
    ]
)

current_slide = st.session_state["signage_current_slide"]
if current_slide == "weather":
    render_weather_slide(weather, location_status)
elif current_slide == "domestic-news":
    render_news_slide("Domestic News", domestic_news)
elif current_slide == "global-news":
    render_news_slide("Global News", global_news)
else:
    render_fun_slide(fun_content)
