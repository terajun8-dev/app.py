import streamlit as st
import time

st.set_page_config(page_title="Make Text Art", layout="centered")

st.markdown("<div style='font-size:12px; text-align:center; margin-bottom:6px; font-weight:600;'>Make Text Art</div>", unsafe_allow_html=True)

text = st.text_input("Enter characters (Example: Hello World)", value="Hello World")
method = st.selectbox("Conversion method", ["pyfiglet (if installed)", "Block characters (no deps)"])

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


def to_text_art(s: str, mode: str) -> str:
    s = s or ""
    if mode.startswith('pyfiglet'):
        try:
            import pyfiglet
            return pyfiglet.figlet_format(s)
        except Exception:
            # fallback to simple block if pyfiglet not available
            return generate_simple_block(s)
    else:
        return generate_simple_block(s)

art = to_text_art(text, method)

st.code(art, language=None)

st.caption("Converted using selected method. pyfiglet support is used when available; otherwise a simple block fallback is shown.")
