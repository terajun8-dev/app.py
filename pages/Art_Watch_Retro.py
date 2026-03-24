import streamlit as st
import time

st.set_page_config(page_title="Art Watch", layout="wide")

# Small label
st.markdown("<div style='font-size:12px; text-align:center; margin-bottom:6px; font-weight:600;'>Art Watch</div>", unsafe_allow_html=True)

variation = st.selectbox("Display variation", ["Neon (Recommended)", "CRT", "Monochrome"], index=0)

# Manual refresh button (press to update time)
# Pressing the button causes Streamlit to rerun the script and update the clock.

# ASCII digit patterns (server-side)
DIGITS = {
    '0': ['  #####  ', ' #     # ', ' #    ## ', ' #  #  # ', ' ##   # #', ' #     # ', '  #####  '],
    '1': ['   ##    ', '  ###    ', '   ##    ', '   ##    ', '   ##    ', '   ##    ', '  #####  '],
    '2': ['  #####  ', ' #     # ', '      #  ', '   ###   ', '  ##     ', ' #       ', ' ####### '],
    '3': ['  #####  ', ' #     # ', '      #  ', '   ###   ', '      #  ', ' #     # ', '  #####  '],
    '4': ['     ##  ', '    # #  ', '   #  #  ', '  #   #  ', ' ####### ', '     #   ', '     #   '],
    '5': [' ####### ', ' #       ', ' #####   ', '      #  ', '      #  ', ' #    #  ', '  ####   '],
    '6': ['  #####  ', ' #     # ', ' #       ', ' #####   ', ' #     # ', ' #     # ', '  #####  '],
    '7': [' ####### ', '      #  ', '     #   ', '    #    ', '   #     ', '   #     ', '   #     '],
    '8': ['  #####  ', ' #     # ', ' #     # ', '  #####  ', ' #     # ', ' #     # ', '  #####  '],
    '9': ['  #####  ', ' #     # ', ' #     # ', '  ###### ', '      #  ', ' #    #  ', '  ####   '],
    ':': ['   ', '  o', '   ', '   ', '  o', '   ', '   '],
    ' ': ['         ', '         ', '         ', '         ', '         ', '         ', '         ']
}


def pad(n):
    return str(n).zfill(2)


def render_ascii(h, m, s):
    parts = f"{h}:{m}:{s}"
    lines = ['' for _ in range(7)]
    for ch in parts:
        pattern = DIGITS.get(ch, DIGITS[' '])
        for i in range(7):
            lines[i] += pattern[i] + '  '
    return '\n'.join(lines)

# build HTML wrapper based on variation
color = '#FFFFFF'
text_shadow = ''
if 'neon' in variation.lower():
    color = '#00FFFF'
    text_shadow = 'text-shadow:0 0 14px #00FFFF, 0 0 28px #FF00FF;'
elif 'crt' in variation.lower():
    color = '#66FF66'
    text_shadow = 'text-shadow:0 0 6px rgba(102,255,102,0.6);'

ascii_box_style = f"background:#000;color:{color};font-family:monospace;padding:8px;{text_shadow}"

# render once per run
now = time.localtime()
h = pad(now.tm_hour)
m = pad(now.tm_min)
s = pad(now.tm_sec)
art = render_ascii(h, m, s)

html = f"""
<div style='width:100%;display:flex;justify-content:center;'>
  <div style='width:98%; background:#000; padding:12px;'>
    <pre style='{ascii_box_style}; margin:0; font-size:20px; line-height:0.85;'>{art}</pre>
  </div>
</div>
"""

st.markdown(html, unsafe_allow_html=True)

st.caption("Art Watch — retro-inspired digital clock. Use the Display variation selector to change style.")

# Manual refresh button
if st.button('Refresh now'):
    # Button triggers a rerun automatically; no explicit rerun call needed.
    pass
