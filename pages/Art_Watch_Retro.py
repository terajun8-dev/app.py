import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Art Watch", layout="centered")

st.markdown("<div style='font-size:14px; text-align:center; margin-bottom:6px; font-weight:600;'>Art Watch</div>", unsafe_allow_html=True)

variation = st.selectbox("Display variation", ["Neon (Recommended)", "CRT", "Monochrome"], index=0)
# always show seconds and default to 24-hour
is24 = "true"
showSeconds = "true"

html = """
<!doctype html>
<html>
<head>
  <meta charset='utf-8'>
  <meta name='viewport' content='width=device-width, initial-scale=1'>
  <style>
    :root{
      --bg:#000000;
      --neon-cyan:#00FFFF;
      --neon-magenta:#FF00FF;
      --crt-green:#66FF66;
    }
    html,body{height:100%;margin:0;padding:0;background:linear-gradient(180deg,#000 0%, #060006 100%);font-family: 'Courier New', monospace;}
    .container{min-height:72vh;display:flex;align-items:center;justify-content:center;flex-direction:column;padding:8px}
    .panel{width:100%;max-width:1400px;background:rgba(12,12,12,0.65);padding:18px;border-radius:12px;}
    .panel-wrapper{position:relative;border-radius:12px;padding:8px}
    pre.clock-pre{font-family: 'Courier New', monospace;font-size:28px;line-height:0.78;white-space:pre;letter-spacing:2px;margin:0;color:#FFFFFF;background:transparent;padding:8px}

    /* variations */
    .neon pre.clock-pre{color:var(--neon-cyan);text-shadow:0 0 18px var(--neon-cyan), 0 0 36px var(--neon-magenta);}
    .crt pre.clock-pre{color:var(--crt-green);text-shadow:0 0 6px rgba(102,255,102,0.6);filter:contrast(1.15) brightness(1.05);}
    .mono pre.clock-pre{color:#FFFFFF;text-shadow:none;}

    /* CRT scanlines overlay */
    .crt .panel-overlay{position:absolute;inset:0;pointer-events:none;background-image:linear-gradient(rgba(0,0,0,0.08) 50%, rgba(255,255,255,0.02) 51%);background-size:100% 4px;border-radius:12px;opacity:0.6}

    /* responsive sizing */
    @media (min-width:900px){ pre.clock-pre{font-size:28px} }
    @media (min-width:1200px){ pre.clock-pre{font-size:36px} }
    @media (min-width:1600px){ pre.clock-pre{font-size:44px} }

    .note{font-size:12px;color:rgba(255,255,255,0.75);text-align:center;margin-top:14px}

  </style>
</head>
<body>
  <div class='container'>
    <div class='panel-wrapper'>
      <div id='panel' class='panel'>
        <div class='panel-overlay' style='display:none'></div>
        <pre id='clock' class='clock-pre'>LOADING...</pre>
      </div>
    </div>
  </div>

  <script>
    const variation = {variation};

    const DIGITS = {
      '0': [
        ' █████ ',
        '██   ██',
        '██  ███',
        '██ █ ██',
        '███  ██',
        '██   ██',
        ' █████ '
      ],
      '1': [
        '  ██   ',
        ' ███   ',
        '  ██   ',
        '  ██   ',
        '  ██   ',
        '  ██   ',
        ' █████ '
      ],
      '2': [
        ' █████ ',
        '██   ██',
        '    ██ ',
        '  ███  ',
        ' ██    ',
        '██     ',
        '███████'
      ],
      '3': [
        ' █████ ',
        '██   ██',
        '    ██ ',
        '  ███  ',
        '    ██ ',
        '██   ██',
        ' █████ '
      ],
      '4': [
        '   ███ ',
        '  █ ██ ',
        ' █  ██ ',
        '█   ██ ',
        '███████',
        '    ██ ',
        '    ██ '
      ],
      '5': [
        '███████',
        '██     ',
        '█████  ',
        '     ██',
        '     ██',
        '██   ██',
        ' █████ '
      ],
      '6': [
        ' █████ ',
        '██   ██',
        '██     ',
        '██████ ',
        '██   ██',
        '██   ██',
        ' █████ '
      ],
      '7': [
        '███████',
        '     ██',
        '    ██ ',
        '   ██  ',
        '  ██   ',
        '  ██   ',
        '  ██   '
      ],
      '8': [
        ' █████ ',
        '██   ██',
        '██   ██',
        ' █████ ',
        '██   ██',
        '██   ██',
        ' █████ '
      ],
      '9': [
        ' █████ ',
        '██   ██',
        '██   ██',
        ' ██████',
        '     ██',
        '██   ██',
        ' █████ '
      ],
      ':': [
        '   ',
        ' ░ ',
        '   ',
        '   ',
        ' ░ ',
        '   ',
        '   '
      ]
    };

    function pad(n){return n<10?('0'+n):n}

    function renderAscii(h,m,s){
      const str = `${h}:${m}:${s}`;
      const lines = Array(7).fill('');
      for(let ch of str){
        const pattern = DIGITS[ch] || DIGITS[' '];
        for(let i=0;i<7;i++) lines[i] += pattern[i] + '  ';
      }
      return lines.join('\n');
    }

    function update(){
      const d = new Date();
      const h = pad(d.getHours());
      const m = pad(d.getMinutes());
      const s = pad(d.getSeconds());
      document.getElementById('clock').textContent = renderAscii(h,m,s);
    }

    // apply variation
    const panel = document.getElementById('panel');
    const overlay = panel.querySelector('.panel-overlay');
    const cls = variation.toLowerCase().includes('crt') ? 'crt' : (variation.toLowerCase().includes('mono') ? 'mono' : 'neon');
    panel.classList.add(cls);
    if(cls==='crt') overlay.style.display='block';

    update();
    setInterval(update,250);
  </script>
</body>
</html>
"""

html = html.replace("{variation}", f'"{variation}"').replace("{is24}", is24).replace("{showSeconds}", showSeconds)

components.html(html, height=920, scrolling=True)

st.caption("Art Watch — retro-inspired digital clock. Use the Display variation selector to change style.")
