# Gateway Python (Role B)

Doc JSON tu bridge qua Serial, day len CoreIOT bang MQTT Gateway API, nhan RPC tu server de dieu khien ghe,
luu SQLite, co web local va phat hien giu cho bang IsolationForest.

## Cai dat
```powershell
cd gateway
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```
Tao `gateway/.env` (UTF-8, KHONG commit):
```
TB_HOST=<host CoreIOT>
TB_PORT=1883
TB_TOKEN=<access token cua device Library-Gateway>
SERIAL_URL=socket://localhost:7000      # test voi fake_bridge; dung that: COM5
```

## Chay
| Muc dich | Lenh |
|---|---|
| Bridge gia lap (cua so 1) | `python fake_bridge.py --speed 10` |
| Gateway (cua so 2) | `python main.py` |
| Web local | http://localhost:5000 |
| Thu AI tren cac tinh huong mau | `python ai_job.py --demo` |
| AI tren du lieu that trong gateway.db | `python ai_job.py --once` |

Dung that: dat `SERIAL_URL=COM5` (cong cua bridge), dong PlatformIO Monitor truoc (1 cong chi 1 chuong trinh mo).

## File
- `main.py` vong lap chinh, RPC (setWarning/enterOta), tinh loss_pct, free_seats
- `serial_link.py` doc/ghi JSON qua Serial, tu noi lai
- `tb_client.py` MQTT Gateway API toi CoreIOT; mat mang thi telemetry vao outbox, co mang gui bu (giu ts goc)
- `store.py` SQLite: `readings` (cho web/AI) va `outbox`
- `web/app.py` Flask local: `/`, `/api/state`, `/api/history`, `/api/cmd` (ghi thang Serial, khong can internet)
- `ai_job.py` IsolationForest, 5 phut/lan tren cua so 30 phut. **Mo hinh huan luyen tren du lieu gia lap** (hanh vi binh thuong), khong phai du lieu thu thap that.
- `fake_bridge.py` bridge gia lap (Seat-01 co kich ban giu cho)
- Do M3: moi RPC tu CoreIOT ghi 1 dong vao `docs/measurements/rpc_latency.csv`
