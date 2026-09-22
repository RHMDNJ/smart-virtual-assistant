"""
demo_browser.py
Menjalankan aplikasi di jendela Chrome sungguhan dan mengemudikannya sendiri,
dengan kursor semu, sorotan elemen, dan label langkah agar prosesnya terlihat.

Prasyarat: backend (:8000) dan frontend (:5173) sudah jalan.

    cd backend && .venv/bin/python ../scripts/demo_browser.py
"""
import sys, time
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
import cdp_driver as cdp

OVERLAY = r"""
(() => {
  if (window.__demo) return 'sudah';
  const gaya = document.createElement('style');
  gaya.textContent = `
    #__kursor { position:fixed; width:20px; height:20px; border-radius:50%;
      background:rgba(37,99,235,.35); border:2px solid #2563eb; z-index:2147483647;
      pointer-events:none; left:-50px; top:-50px;
      transition:left .45s cubic-bezier(.3,.8,.3,1), top .45s cubic-bezier(.3,.8,.3,1); }
    #__kursor.klik { animation: __klik .35s ease-out; }
    @keyframes __klik { 0%{transform:scale(1)} 50%{transform:scale(2.2); background:rgba(37,99,235,.7)} 100%{transform:scale(1)} }
    .__sorot { outline:3px solid #2563eb !important; outline-offset:3px; border-radius:10px; }
    #__label { position:fixed; left:50%; transform:translateX(-50%); top:14px;
      background:#111827; color:#fff; padding:8px 18px; border-radius:999px;
      font:600 13px system-ui; z-index:2147483647; box-shadow:0 8px 24px rgba(0,0,0,.25);
      opacity:0; transition:opacity .25s; pointer-events:none; white-space:nowrap; }
    #__label.tampil { opacity:1; }
  `;
  document.head.appendChild(gaya);
  const k = document.createElement('div'); k.id='__kursor'; document.body.appendChild(k);
  const l = document.createElement('div'); l.id='__label'; document.body.appendChild(l);
  window.__demo = {
    label(t){ l.textContent=t; l.classList.add('tampil'); },
    sorot(sel){ const el=document.querySelector(sel); if(!el) return false;
      document.querySelectorAll('.__sorot').forEach(e=>e.classList.remove('__sorot'));
      el.classList.add('__sorot');
      const r=el.getBoundingClientRect();
      k.style.left=(r.left+r.width/2-10)+'px'; k.style.top=(r.top+r.height/2-10)+'px';
      return true; },
    klik(sel){ k.classList.remove('klik'); void k.offsetWidth; k.classList.add('klik');
      document.querySelector(sel)?.click(); },
    bersih(){ document.querySelectorAll('.__sorot').forEach(e=>e.classList.remove('__sorot')); }
  };
  return 'siap';
})()
"""

ws = cdp.launch("http://localhost:5173/", headless=False)
s = cdp.Session(ws)
s.send("Page.enable"); s.send("Runtime.enable"); s.send("DOM.enable")
time.sleep(3)


def pasang():
    s.js(OVERLAY)


def label(t, jeda=0.9):
    pasang(); s.js(f"window.__demo.label({t!r})"); time.sleep(jeda)


def sorot(sel, jeda=0.9):
    pasang(); s.js(f"window.__demo.sorot({sel!r})"); time.sleep(jeda)


def klik(sel):
    sorot(sel); s.js(f"window.__demo.klik({sel!r})"); time.sleep(0.7)


def ketik(sel, teks, proto="HTMLInputElement"):
    sorot(sel, 0.5)
    for i in range(1, len(teks) + 1):
        s.js(f"""(() => {{ const el=document.querySelector({sel!r});
          const set=Object.getOwnPropertyDescriptor(window.{proto}.prototype,'value').set;
          set.call(el,{teks[:i]!r}); el.dispatchEvent(new Event('input',{{bubbles:true}})); }})()""")
        time.sleep(0.03)
    time.sleep(0.5)


def tunggu_jawaban(maks=300):
    t0 = time.time()
    for _ in range(maks * 2):
        selesai = (not s.js("!!document.querySelector('[data-streaming]')")
                   and not s.js("!!document.querySelector('[data-thinking]')")
                   and time.time() - t0 > 3)
        if selesai:
            break
        time.sleep(0.5)
    time.sleep(1)


print(">> Jendela Chrome sudah terbuka. Silakan perhatikan layar.")

# 1. Mulai dari sesi bersih
s.js("localStorage.clear(), 'ok'")
s.send("Page.reload"); time.sleep(3)
label("1/6 · Sesi dibersihkan — layar login muncul", 2)

# 2. Login
label("2/6 · Mengisi kredensial", 1)
ketik("#username", "admin")
ketik("#password", "admin12345")
klik("button[type=submit]")
for _ in range(30):
    if s.js("!!document.querySelector('textarea')"): break
    time.sleep(1)
time.sleep(1)
label("Masuk sebagai ADMIN", 1.5)

# 3. Pertanyaan RAG lewat chip saran
label("3/6 · Mengklik saran pertanyaan", 1)
pasang()
s.js("window.__demo.sorot('.rounded-full.border-line.bg-raised')")
time.sleep(1)
s.js("""(() => {
  const b = [...document.querySelectorAll('button')].find(x => x.innerText.includes('cuti tahunan'));
  document.getElementById('__kursor')?.classList.add('klik');
  b?.click();
})()""")
label("Menunggu jawaban — perhatikan teks mengalir bertahap", 1)
tunggu_jawaban()
label("Jawaban selesai, badge tool & sumber tampil", 2.5)

# 4. Pertanyaan SQL diketik manual
label("4/6 · Mengetik pertanyaan statistik", 1)
ketik("textarea", "Ada berapa dokumen yang tersimpan di knowledge base?", "HTMLTextAreaElement")
klik("button[aria-label='Kirim']")
tunggu_jawaban()
label("Agent memilih tool Database, bukan Dokumen", 2.5)

# 5. Sapaan
label("5/6 · Menguji sapaan — seharusnya tanpa tool", 1)
ketik("textarea", "Selamat pagi!", "HTMLTextAreaElement")
klik("button[aria-label='Kirim']")
tunggu_jawaban()
label("Dijawab langsung, badge 'Jawaban langsung'", 2.5)

# 6. Keluar
label("6/6 · Keluar dari sesi", 1)
s.js("""(() => {
  const b = [...document.querySelectorAll('button')].find(x => x.innerText.trim() === 'Keluar');
  window.__demo.sorot('header button:last-of-type');
  setTimeout(() => b?.click(), 700);
})()""")
time.sleep(3)
pasang()
label("Selesai — kembali ke layar login", 3)
print(">> Demo selesai.")
