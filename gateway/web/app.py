"""B6 - Trang web local (Flask) cua gateway: xem trang thai ghe va dieu khieu ghe NGAY CA KHI MAT INTERNET.

Khong goi bat ky dich vu ngoai nao (khong CDN, khong CoreIOT): lenh di thang Serial -> bridge -> ghe.
Chi lang nghe 127.0.0.1 (khong co mat khau nen khong mo cho may khac).

  GET  /                     trang HTML
  GET  /api/state            trang thai moi nhat cua cac ghe + tinh trang CoreIOT/outbox/AI
  GET  /api/history?seat=Seat-01&minutes=30   chuoi obj_secs de ve bieu do
  POST /api/cmd              {"seat":"Seat-01","cmd":"warn","on":1}  hoac {"seat":..,"cmd":"ota"}
"""
import time

from flask import Flask, jsonify, request

PAGE = """<!doctype html>
<html lang="vi"><head><meta charset="utf-8"><title>Gateway local - Library Seat</title>
<style>
 body{font-family:system-ui,Segoe UI,sans-serif;margin:20px;background:#f4f5f7;color:#222}
 h1{font-size:20px;margin:0 0 4px} .sub{color:#666;font-size:13px;margin-bottom:14px}
 .bar{display:flex;gap:14px;flex-wrap:wrap;margin-bottom:14px;font-size:14px}
 .pill{padding:3px 10px;border-radius:12px;background:#ddd}.ok{background:#c9f0d0}.bad{background:#f7c9c9}
 .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:14px}
 .card{background:#fff;border-radius:10px;padding:14px;box-shadow:0 1px 3px #0002}
 .card h2{margin:0 0 6px;font-size:17px}
 .st{display:inline-block;padding:2px 10px;border-radius:6px;font-weight:600;font-size:13px}
 .EMPTY{background:#d6f5d6}.OCCUPIED{background:#ffe9b3}.OBJECT_ONLY{background:#f9b4b4}
 table{font-size:13px;margin:8px 0;border-collapse:collapse}td{padding:1px 10px 1px 0}
 button{margin:4px 6px 0 0;padding:5px 10px;border:1px solid #888;border-radius:6px;background:#fafafa;cursor:pointer}
 button:hover{background:#eee} canvas{width:100%;height:70px;background:#fafafa;border-radius:4px}
 .msg{font-size:12px;min-height:16px;color:#555}
</style></head><body>
<h1>Gateway local &mdash; Library Seat</h1>
<div class="sub">Trang nay chay tren may gateway, dieu khien ghe truc tiep qua Serial (khong qua internet).</div>
<div class="bar"><span id="cloud" class="pill">CoreIOT: ?</span><span id="outbox" class="pill">Outbox: ?</span>
<span id="free" class="pill">Ghe trong: ?</span><span id="hog" class="pill">AI: ?</span></div>
<div id="seats" class="grid"></div>
<script>
const msgs = {};
function esc(s){return String(s==null?'-':s).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));}
async function cmd(seat, c, on){
  msgs[seat]='Dang gui...'; render();
  try{
    const r = await fetch('/api/cmd',{method:'POST',headers:{'Content-Type':'application/json'},
                                      body:JSON.stringify({seat:seat,cmd:c,on:on})});
    const j = await r.json();
    msgs[seat] = j.ok ? 'OK - ghe da nhan lenh (' + j.latency_ms + ' ms)' : 'That bai: ' + (j.error||'khong co ACK');
  }catch(e){ msgs[seat]='Loi: '+e; }
  render();
}
let last = null;
function render(){
  if(!last) return;
  const s = last, el = document.getElementById('seats');
  document.getElementById('cloud').textContent = 'CoreIOT: ' + (s.cloud_connected?'dang ket noi':'MAT KET NOI');
  document.getElementById('cloud').className = 'pill ' + (s.cloud_connected?'ok':'bad');
  document.getElementById('outbox').textContent = 'Outbox cho gui bu: ' + s.outbox;
  document.getElementById('free').textContent = 'Ghe trong: ' + s.free_seats;
  const anyHog = Object.values(s.seats).some(x=>x.hog && x.hog.anomaly);
  document.getElementById('hog').textContent = 'AI giu cho: ' + (anyHog?'CO ghe bat thuong':'binh thuong');
  document.getElementById('hog').className = 'pill ' + (anyHog?'bad':'ok');
  el.innerHTML = Object.keys(s.seats).sort().map(name=>{
    const x = s.seats[name];
    return '<div class="card"><h2>'+esc(name)+' <span class="st '+esc(x.state)+'">'+esc(x.state)+'</span></h2>'
     +'<table><tr><td>AI node</td><td>'+esc(x.ai)+' ('+esc(x.conf)+'%)</td></tr>'
     +'<tr><td>ToF</td><td>'+esc(x.tof)+' mm</td></tr>'
     +'<tr><td>obj_secs</td><td>'+esc(x.obj_secs)+' s</td></tr>'
     +'<tr><td>RSSI</td><td>'+esc(x.rssi)+' dBm</td></tr>'
     +'<tr><td>Cap nhat</td><td>'+esc(x.age_s)+' s truoc</td></tr>'
     +'<tr><td>AI giu cho</td><td>'+(x.hog?('score '+x.hog.score+(x.hog.anomaly?' - BAT THUONG':' - binh thuong')):'chua co')+'</td></tr>'
     +'<tr><td>Hom nay</td><td>'+(x.stats?('su dung '+x.stats.usage_pct+'%, giu cho '+x.stats.hog_count+' lan'):'chua co')+'</td></tr></table>'
     +'<canvas id="c-'+esc(name)+'" width="300" height="70"></canvas>'
     +'<div><button onclick="cmd(\\''+name+'\\',\\'warn\\',1)">Bat canh bao</button>'
     +'<button onclick="cmd(\\''+name+'\\',\\'warn\\',0)">Tat canh bao</button>'
     +'<button onclick="if(confirm(\\'Cho '+name+' vao che do OTA?\\'))cmd(\\''+name+'\\',\\'ota\\',0)">OTA</button></div>'
     +'<div class="msg">'+esc(msgs[name]||'')+'</div></div>';
  }).join('');
  Object.keys(s.seats).forEach(drawChart);
}
async function drawChart(name){
  const cv = document.getElementById('c-'+name); if(!cv) return;
  const r = await fetch('/api/history?seat='+encodeURIComponent(name)+'&minutes=30'); const h = (await r.json()).points;
  const g = cv.getContext('2d'); g.clearRect(0,0,cv.width,cv.height);
  if(h.length<2){ g.fillText('chua du du lieu',10,35); return; }
  const t0=h[0][0], t1=h[h.length-1][0], mx=Math.max(120,...h.map(p=>p[1]));
  g.strokeStyle='#d33'; g.setLineDash([4,3]); const yl=cv.height-4-(120/mx)*(cv.height-8);   // hogLimitSec=120
  g.beginPath(); g.moveTo(0,yl); g.lineTo(cv.width,yl); g.stroke(); g.setLineDash([]);
  g.strokeStyle='#27c'; g.beginPath();
  h.forEach((p,i)=>{const x=(p[0]-t0)/Math.max(1,t1-t0)*(cv.width-2)+1, y=cv.height-4-(p[1]/mx)*(cv.height-8); i?g.lineTo(x,y):g.moveTo(x,y);});
  g.stroke(); g.fillStyle='#666'; g.font='10px sans-serif'; g.fillText('obj_secs 30 phut (do: hogLimit 120 s)',4,10);
}
async function tick(){
  try{ last = await (await fetch('/api/state')).json(); render(); }catch(e){}
}
tick(); setInterval(tick, 2000);
</script></body></html>"""

# trang web chạy ngay trên laptop (http://localhost:5000).
# Nó hiện trạng thái ghế và có nút điều khiển, ghi lệnh thẳng xuống Serial nên mất internet vẫn dùng được.
def create_app(gw):
    app = Flask(__name__)

    @app.get("/")
    def index():
        return PAGE

    @app.get("/api/state")
    def state():
        now = int(time.time() * 1000)
        seats = {}
        for name, v in gw.latest.items():
            item = dict(v)
            item["hog"] = gw.hog.get(name)
            item["stats"] = gw.stats.get(name)
            seats[name] = {k: item.get(k) for k in ("state", "ai", "conf", "tof", "obj_secs", "rssi", "age_s", "hog", "stats")}
        free = sum(1 for s in gw.states.values() if s == "EMPTY")
        return jsonify({
            "seats": seats,
            "free_seats": free,
            "cloud_connected": gw.tb.is_connected(),
            "outbox": gw.store.outbox_count(),
        })

    @app.get("/api/history")
    def history():
        seat = request.args.get("seat", "")
        minutes = min(max(int(request.args.get("minutes", 30)), 1), 24 * 60)
        rows = gw.store.readings_since(seat, int(time.time() * 1000) - minutes * 60 * 1000)
        return jsonify({"seat": seat, "points": [[r["ts"], r["obj_secs"] or 0] for r in rows]})

    @app.post("/api/cmd")
    def cmd():
        body = request.get_json(silent=True) or {}
        seat, c = body.get("seat"), body.get("cmd")
        if c not in ("warn", "ota") or seat not in gw.latest:
            return jsonify({"ok": False, "error": "seat/cmd khong hop le"}), 400
        t0 = time.time()
        rid, ok = gw.send_local_cmd(seat, c, 1 if body.get("on") else 0)
        if rid is None:
            return jsonify({"ok": False, "error": "khong ghi duoc Serial (bridge chua noi?)"}), 503
        return jsonify({"ok": ok, "rid": rid, "latency_ms": round((time.time() - t0) * 1000),
                        "error": None if ok else "khong co ACK trong thoi han"})

    return app
