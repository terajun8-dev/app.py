import streamlit as st
import time

st.set_page_config(page_title="Make Text Art", layout="centered")

st.markdown("<div style='font-size:12px; text-align:center; margin-bottom:6px; font-weight:600;'>Make Text Art</div>", unsafe_allow_html=True)

text = st.text_input("Enter characters (Example: Hello World)", value="Hello World")
method = st.selectbox("Conversion method", ["pyfiglet (if installed)", "Block characters (no deps)"])

# try to import pyfiglet and collect fonts
PYFIGLET_AVAILABLE = False
AVAILABLE_FONTS = []
try:
    import pyfiglet
    PYFIGLET_AVAILABLE = True
    try:
        AVAILABLE_FONTS = pyfiglet.FigletFont.getFonts()
    except Exception:
        AVAILABLE_FONTS = []
except Exception:
    PYFIGLET_AVAILABLE = False
    AVAILABLE_FONTS = []

# font selection UI (only meaningful for pyfiglet)
selected_font = None
if method.startswith('pyfiglet'):
    if PYFIGLET_AVAILABLE and AVAILABLE_FONTS:
        # favorite fonts short list
        favorites = ['standard','slant','big','banner3-D','digital']
        # filter favorites that exist
        favs_exist = [f for f in favorites if f in AVAILABLE_FONTS]
        if favs_exist:
            sel_group = st.radio('Font group', ['Favorites (recommended)','All fonts'], index=0)
            if sel_group == 'Favorites (recommended)':
                selected_font = st.selectbox('Font (favorites)', favs_exist, index=0)
            else:
                default_idx = 0
                if 'standard' in AVAILABLE_FONTS:
                    default_idx = AVAILABLE_FONTS.index('standard')
                selected_font = st.selectbox('Font (all)', AVAILABLE_FONTS, index=default_idx)
        else:
            # fallback to all fonts if favorites missing
            default_idx = 0
            if 'standard' in AVAILABLE_FONTS:
                default_idx = AVAILABLE_FONTS.index('standard')
            selected_font = st.selectbox('Font', AVAILABLE_FONTS, index=default_idx)
    else:
        st.warning('pyfiglet is not installed or no fonts available. Falling back to block generator.')

# font size for display (affects the rendered <pre> block)
display_size = st.slider('Display font size (for preview)', min_value=12, max_value=48, value=20)

# simple fallback generator (no external deps)
DIGITS_SIMPLE = None

def generate_simple_block(s: str) -> str:
    # For each character, create a 7-line block using the character itself
    rows = ["" for _ in range(7)]
    for ch in s:
        if ch == " ":
            pattern = ['       ', '       ', '       ', '       ', '       ', '       ', '       ']
        else:
            c = ch[0]
            pattern = [
                f"  {c*5}  ",
                f" {c}     {c} ",
                f" {c}     {c} ",
                f" {c*7} ",
                f" {c}     {c} ",
                f" {c}     {c} ",
                f"  {c*5}  ",
            ]
        for i in range(7):
            rows[i] += pattern[i] + '  '
    return "\n".join(rows)


def to_text_art(s: str, mode: str, font: str = None) -> str:
    s = s or ""
    if mode.startswith('pyfiglet') and font and PYFIGLET_AVAILABLE:
        try:
            f = pyfiglet.Figlet(font=font)
            return f.renderText(s)
        except Exception:
            return generate_simple_block(s)
    else:
        return generate_simple_block(s)

art = to_text_art(text, method, selected_font)

# Display using Streamlit's native code/text components (reliable rendering)
st.markdown("<div style='width:100%;display:flex;justify-content:center;'><div style='width:98%; padding:6px;'>", unsafe_allow_html=True)
# show in st.code for monospace and preserved formatting; font-size is limited by Streamlit, but raw text will be correct
st.code(art)
# Also show editable raw text for copy/paste
st.text_area('Raw text output (editable)', value=art, height=320)
st.markdown("</div></div>", unsafe_allow_html=True)

st.caption("Converted using selected method. pyfiglet support is used when available; otherwise a simple block fallback is shown.")

# manual refresh
if st.button('Refresh'):
    # Button causes Streamlit to rerun; explicit experimental_rerun is not called to avoid environment errors
    pass
