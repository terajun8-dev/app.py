import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Art Watch — Retro", layout="centered")

st.title("Art Watch — Retro Style Digital Clock")

show_seconds = st.checkbox("Show seconds", value=True)
use_24h = st.selectbox("Time format", ["24-hour (Recommended)", "12-hour"], index=0)

is24 = "true" if use_24h.startswith("24") else "false"
showSeconds = "true" if show_seconds else "false"

html = """
<!doctype html>
<html>
<head>
  <meta charset='utf-8'>
  <meta name='viewport' content='width=device-width, initial-scale=1'>
  <link href='https://fonts.googleapis.com/css2?family=Press+Start+2P&display=swap' rel='stylesheet'>
  <style>
    :root{{
      --bg:#000000;
      --neon-cyan:#00FFFF;
      --neon-magenta:#FF00FF;
      --glass: rgba(255,255,255,0.03);
    }}
    html,body{{height:100%;margin:0;padding:0;background:linear-gradient(180deg,#000 0%, #060006 100%);font-family: 'Press Start 2P', monospace;}}
    .wrap{{height:280px;display:flex;align-items:center;justify-content:center;flex-direction:column;gap:12px}}
    .panel{{padding:24px;border-radius:12px;background:linear-gradient(180deg, rgba(255,255,255,0.02), rgba(0,0,0,0.2));box-shadow: 0 0 40px rgba(255,0,255,0.05) inset, 0 0 30px rgba(0,255,255,0.03);border:2px solid rgba(255,255,255,0.03);}}
    .clock{{font-size:46px;color:var(--neon-cyan);text-align:center;padding:10px 20px;border-radius:8px;position:relative;}}
    .clock::after{{content:'';position:absolute;inset:0;border-radius:8px;box-shadow:0 0 32px var(--neon-magenta);mix-blend-mode:screen;opacity:0.12;pointer-events:none}}
    .date{{font-size:11px;color:var(--neon-magenta);text-align:center;margin-top:6px;opacity:0.9}}

    /* scanlines */
    .scanline:before{{content:'';position:absolute;left:0;right:0;top:0;bottom:0;background-image:linear-gradient(rgba(0,0,0,0.02) 50%, rgba(255,255,255,0.01) 51%);background-size:100% 4px;mix-blend-mode:overlay;opacity:0.6;border-radius:12px;}}

    /* blinking colon */
    .colon{{animation:blink 1s steps(1) infinite;}}
    @keyframes blink{{50%{{opacity:0}}}}

    /* small screen scaling */
    @media (max-width:420px){{ .clock{{font-size:28px}} }}
  </style>
</head>
<body>
  <div class='wrap'>
    <div class='panel scanline'>
      <div id='clock' class='clock'>--:--</div>
      <div id='date' class='date'></div>
    </div>
  </div>

  <script>
    const is24 = {is24};
    const showSeconds = {showSeconds};

    function pad(n){return n<10?('0'+n):n}
    function update(){
      const d = new Date();
      let h = d.getHours();
      if(!is24) h = h % 12 || 12;
      const m = pad(d.getMinutes());
      const s = pad(d.getSeconds());
      const sep = '<span class="colon">:</span>';
      const time = `${{h}}${{sep}}${{m}}` + (showSeconds ? `${{sep}}${{s}}` : '');
      document.getElementById('clock').innerHTML = time;
      document.getElementById('date').textContent = d.toLocaleDateString(undefined, {{ weekday: 'short', year: 'numeric', month: 'short', day: 'numeric' }});
    }

    // keep high-frequency updates for smooth seconds
    update();
    setInterval(update, 250);
  </script>
</body>
</html>
"""

html = html.replace("{{", "{").replace("}}", "}")
html = html.replace("{is24}", is24).replace("{showSeconds}", showSeconds)

components.html(html, height=360, scrolling=False)

st.caption("Retro digital clock inspired by old-school LED/CRT aesthetics. Use controls above to toggle seconds and time format.")
