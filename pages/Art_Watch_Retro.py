import streamlit as st
import streamlit.components.v1 as components
import json

st.set_page_config(page_title="Art Watch", layout="wide")

# Minimal top label (small)
st.markdown("<div style='font-size:12px; text-align:center; margin-bottom:6px; font-weight:600;'>Art Watch</div>", unsafe_allow_html=True)

variation = st.selectbox("Display variation", ["Neon (Recommended)", "CRT", "Monochrome"], index=0)

# Use a simple client-side HTML/JS clock to avoid server-side looping issues.
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
    html,body{height:100%;margin:0;padding:0;background:var(--bg);}
    body{display:flex;align-items:center;justify-content:center;}
    #panel{width:100vw;max-width:none;margin-left:calc(-50vw + 50%);height:calc(50vw);background:var(--bg);display:flex;align-items:center;justify-content:center;padding:0;border-radius:0;}
    pre{font-family: 'Courier New', monospace; font-size:34px; line-height:0.75; margin:0; white-space:pre; color:#fff}
    /* variations */
    .neon pre{color:var(--neon-cyan); text-shadow:0 0 14px var(--neon-cyan), 0 0 28px var(--neon-magenta);}
    .crt pre{color:var(--crt-green); text-shadow:0 0 6px rgba(102,255,102,0.6); filter:contrast(1.15) brightness(1.05);}
    .mono pre{color:#FFFFFF; text-shadow:none}
  </style>
</head>
<body>
  <div id='panel' class='neon'>
    <pre id='clock'> </pre>
  </div>

  <script>
    const variation = %%VARIATION%%;

    const DIGITS = {
      '0': [ ' █████ ', '██   ██', '██  ███', '██ █ ██', '███  ██', '██   ██', ' █████ ' ],
      '1': [ '  ██   ', ' ███   ', '  ██   ', '  ██   ', '  ██   ', '  ██   ', ' █████ ' ],
      '2': [ ' █████ ', '██   ██', '    ██ ', '  ███  ', ' ██    ', '██     ', '███████' ],
      '3': [ ' █████ ', '██   ██', '    ██ ', '  ███  ', '    ██ ', '██   ██', ' █████ ' ],
      '4': [ '   ███ ', '  █ ██ ', ' █  ██ ', '█   ██ ', '███████', '    ██ ', '    ██ ' ],
      '5': [ '███████', '██     ', '█████  ', '     ██', '     ██', '██   ██', ' █████ ' ],
      '6': [ ' █████ ', '██   ██', '██     ', '██████ ', '██   ██', '██   ██', ' █████ ' ],
      '7': [ '███████', '     ██', '    ██ ', '   ██  ', '  ██   ', '  ██   ', '  ██   ' ],
      '8': [ ' █████ ', '██   ██', '██   ██', ' █████ ', '██   ██', '██   ██', ' █████ ' ],
      '9': [ ' █████ ', '██   ██', '██   ██', ' ██████', '     ██', '██   ██', ' █████ ' ],
      ':': [ '   ', ' ░ ', '   ', '   ', ' ░ ', '   ', '   ' ],
      ' ': [ '       ', '       ', '       ', '       ', '       ', '       ', '       ' ]
    };

    function pad(n){return n<10?('0'+n):n}

    function renderAscii(h,m,s){
      const str = h + ':' + m + ':' + s;
      const lines = ['', '', '', '', '', '', ''];
      for(let i=0;i<str.length;i++){
        const ch = str.charAt(i);
        const pattern = DIGITS[ch] || DIGITS[' '];
        for(let r=0;r<7;r++) lines[r] += pattern[r] + '  ';
      }
      return lines.join('\n');
    }

    function adjust(){
      const panel = document.getElementById('panel');
      if(!panel) return;
      const w = panel.clientWidth || panel.offsetWidth || window.innerWidth;
      const newH = Math.max(120, Math.floor(w/2));
      panel.style.height = newH + 'px';
      const fs = Math.max(10, Math.floor(w/16));
      const el = document.getElementById('clock');
      if(el) el.style.fontSize = fs + 'px';
    }

    function update(){
      try{
        adjust();
        const d = new Date();
        const h = pad(d.getHours());
        const m = pad(d.getMinutes());
        const s = pad(d.getSeconds());
        const ascii = renderAscii(h,m,s);
        const el = document.getElementById('clock');
        if(el) el.textContent = ascii;
        const panel = document.getElementById('panel');
        panel.classList.remove('neon','crt','mono');
        const cls = variation.toLowerCase().includes('crt') ? 'crt' : (variation.toLowerCase().includes('mono') ? 'mono' : 'neon');
        panel.classList.add(cls);
      }catch(e){ console.error('update error', e); }
    }

    window.addEventListener('resize', function(){ setTimeout(adjust,50); });
    document.addEventListener('DOMContentLoaded', function(){ setTimeout(function(){ update(); setInterval(update,500); },50); });
    // fallback
    setTimeout(function(){ update(); setInterval(update,500); },200);
  </script>
</body>
</html>
"""

# safely inject variation
html = html.replace('%%VARIATION%%', json.dumps(variation))

components.html(html, height=700, scrolling=False)

st.caption("Art Watch — retro-inspired digital clock. Use the Display variation selector to change style.")
