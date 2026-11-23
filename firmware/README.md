# Firmware (vai A) — hướng dẫn nạp và test

Thư mục gồm:

| Đường dẫn | Nội dung |
|---|---|
| `common/board_pins.h` | Số chân GPIO trên YoloUNO (LED, radar, I2C) — **phải điền trước khi nạp** |
| `common/seat_packet.h` | Định dạng gói ESP-NOW (theo `docs/CONTRACT.md`) |
| `common/secrets.example.h` | Mẫu MAC, khóa mã hóa, WiFi, token. Copy thành `secrets.h` (không commit) |
| `node/` | Firmware node ghế, 5 env: `hello`, `sensors`, `collect`, `node1`, `node2` |
| `bridge/` | Firmware bridge, 2 env: `hello`, `bridge` |

Trạng thái ghế và màu LED: xanh lá = `EMPTY`, đỏ = `OCCUPIED`, cam = `OBJECT_ONLY`, vàng nháy = đang bị cảnh báo, tím lúc khởi động = có thành phần lỗi.

---

## Làm hôm nay (chưa cần mạch)

1. **Điền `common/board_pins.h`.** Mở code mẫu NeoPixel trong repo YoloUNO của thầy để lấy chân LED. Chọn chân UART cho radar và I2C cho ToF theo sơ đồ chân YoloUNO. Tránh GPIO 0, 3, 45, 46 (strapping), 19, 20 (USB), 26–37 (flash/PSRAM).
2. **Tạo `common/secrets.h`:** copy `secrets.example.h` thành `secrets.h`. MAC để tạm toàn số 0, ngày mai điền.
3. **Build thử, không cần cắm mạch:**
   - Mở thư mục `firmware/node` bằng File → Open Folder → thanh PlatformIO → Project Tasks → `hello` → Build. Làm tiếp với `sensors`, `node1`.
   - Mở `firmware/bridge` → Build env `bridge`.
   - **Đạt khi** cả 4 lần build đều báo `SUCCESS`. Lần đầu PlatformIO tải thư viện nên lâu hơn.

Build được hôm nay thì ngày mai chỉ còn lo phần cứng, không phải sửa lỗi thư viện.

---

## Ngày mai, theo đúng thứ tự

Nạp code: Project Tasks → chọn env → **Upload**. Xem log: **Monitor** (115200). Nạp không được thì giữ nút BOOT, nhấn RESET, rồi nạp lại.

### Bước 1 — Kiểm tra 3 mạch trần (khoảng 15 phút)

1. Với **từng mạch**: mở `firmware/node`, nạp env `hello`, mở Monitor.
2. **Đạt khi** Monitor in ra:
   ```text
   MAC (chep vao secrets.h): 7C:DF:A1:xx:xx:xx
   Flash: 8388608 byte
   Arduino core: 2.0.17   (hoặc 3.x)
   LED: xanh la (EMPTY) ...
   ```
   và LED trên mạch đổi lần lượt xanh → đỏ → cam → vàng.
3. Ghi MAC lên băng keo dán vào từng mạch: **Seat-01**, **Seat-02**, **Bridge**.
4. Điền vào `common/secrets.h`: MAC của Bridge vào `BRIDGE_MAC`; MAC của Seat-01, Seat-02 vào `NODE_MACS`.
5. **Nếu flash in ra 4194304 (4 MB):** sửa `board_build.partitions = default.csv` trong cả 2 file `platformio.ini`.
6. **Nếu LED không sáng:** sai `LED_PIN`, kiểm tra lại code mẫu của thầy.

### Bước 2 — Đấu và test cảm biến, node 1 (khoảng 30 phút)

**Rút USB trước khi đấu dây.**

| Linh kiện | Chân | Nối vào |
|---|---|---|
| LD2410C | VCC / GND | 5V / GND |
| LD2410C | TX / RX | `RADAR_RX_PIN` / `RADAR_TX_PIN` (chéo nhau) |
| VL53L0X | VIN / GND | 3.3V / GND |
| VL53L0X | SDA / SCL | `I2C_SDA_PIN` / `I2C_SCL_PIN` |

1. Nạp env `sensors` cho node 1.
2. **Đạt khi** đầu log có:
   ```text
   # [I2C] Thay thiet bi tai 0x29  <- VL53L0X
   # [TOF] OK
   # [RADAR] OK, firmware radar: ...
   # [RADAR] setMaxGate(2) OK
   ```
   Sau đó cứ 0,2 giây in một dòng:
   ```text
   radar[ok ] pres=1 mov=0 sta=1 | tof= 230 mm (CO VAT) | movE=  5  3 ... | staE= 40 35 ...
   ```
3. **Test 5 tình huống, xem LED và dòng log:**

   | Tình huống | Kỳ vọng |
   |---|---|
   | Ghế trống | `pres=0`, tof lớn, LED xanh |
   | Ngồi im đọc sách 1 phút | `pres=1` suốt, LED đỏ |
   | Ngồi cựa quậy | `mov=1`, LED đỏ |
   | Đặt balo rồi đi ra | `pres=0`, tof nhỏ `(CO VAT)`, LED cam |
   | Người đứng cách 2 m | `pres=0` (nhờ giới hạn gate 2) |

4. **Hiệu chỉnh ToF:** ghi `tof` khi ghế trống, rồi đặt `TOF_OBJECT_MM` trong `node/include/config.h` bằng giá trị đó trừ khoảng 100.
5. Làm lại bước 2 cho node 2.

### Bước 3 — Bridge (5 phút)

1. Mở `firmware/bridge`, nạp env `bridge` cho mạch Bridge.
2. **Đạt khi** Monitor in `# Bridge san sang, kenh 1, ma hoa TAT`.
3. Để Monitor của bridge mở.

### Bước 4 — Node gửi về bridge, T06 (15 phút)

1. Nạp env `node1` cho Seat-01, `node2` cho Seat-02, cấp nguồn cho cả hai.
2. **Đạt khi** Monitor của bridge hiện:
   ```text
   # Seat-01 co MAC ...
   {"type":"hello","seat":"Seat-01","fw":"1.0"}
   {"type":"telemetry","seat":"Seat-01","seq":2,"state":"EMPTY",...}
   ```
   - Mỗi ghế cứ 10 giây gửi 1 dòng telemetry.
   - Ngồi xuống thì khoảng 3 giây sau có ngay dòng mới với `"state":"OCCUPIED"`.
3. **Chụp màn hình** lưu `docs/evidence/T06/`.

### Bước 5 — Lệnh đi xuống (5 phút)

1. Trong Monitor của bridge, gõ một dòng rồi Enter:
   ```json
   {"type":"cmd","seat":"Seat-01","cmd":"warn","on":1,"rid":1}
   ```
2. **Đạt khi:** LED Seat-01 nháy vàng, và bridge in `{"type":"ack","seat":"Seat-01","rid":1,"ok":true}`.
3. Gửi lại với `"on":0` để tắt. Ngồi xuống ghế đang nháy thì LED cũng tự tắt nháy.

### Bước 6 — Ghép với gateway (10 phút)

1. **Đóng Monitor của bridge**, vì một cổng COM chỉ một chương trình mở được.
2. Xem số cổng COM của bridge trong Device Manager.
3. Trong `gateway/.env` sửa `SERIAL_URL=COMx`, rồi chạy `python main.py`.
4. **Đạt khi** trên CoreIOT, `Seat-01` và `Seat-02` cập nhật theo ghế thật.

### Bước 7 — Bật mã hóa ESP-NOW (10 phút, sau khi bước 4–6 đã chạy ổn)

1. Trong `common/secrets.h`:
   - Đổi `USE_ESPNOW_ENCRYPTION` thành `1`.
   - Đổi `ESPNOW_PMK`, `ESPNOW_LMK` thành 16 ký tự riêng của nhóm.
   - Kiểm tra `NODE_MACS` đúng thứ tự Seat-01, Seat-02.
2. Nạp lại **cả 3 mạch**.
3. **Đạt khi** bridge in `ma hoa BAT` và bước 4 vẫn chạy như cũ.

### Bước 8 — Đo mất gói (sau khi xong, thí nghiệm M4)

Đặt node cách bridge 1, 5, 10, 20 m, mỗi mức 10 phút. Ghi `loss_pct` mà gateway gửi lên.

---

## Lỗi hay gặp

| Hiện tượng | Nguyên nhân | Cách xử lý |
|---|---|---|
| Không thấy cổng COM | Cáp chỉ sạc | Đổi cáp có truyền dữ liệu |
| `[RADAR] radar.begin() that bai` | Đảo TX/RX, thiếu 5V, sai chân | TX radar phải nối vào `RADAR_RX_PIN`; đo 5V ở chân VCC |
| `[I2C] Khong thay thiet bi nao` | Sai SDA/SCL, ToF chưa hàn chân | Kiểm tra mối hàn, đổi SDA ↔ SCL |
| `pres=1` ngay cả khi ghế trống | Radar bắt người ở xa / ghế bên | Giảm `RADAR_MAX_GATE` xuống 1, xoay radar thẳng vào ghế |
| Bridge không nhận gì | Sai `BRIDGE_MAC`, khác kênh | Nạp lại `hello` cho bridge, so MAC với `secrets.h` |
| `[ESPNOW] Gui loi` | Bridge chưa bật hoặc sai MAC | Bật bridge trước, kiểm tra `BRIDGE_MAC` |
| Bật mã hóa xong mất liên lạc | `NODE_MACS` sai hoặc khóa khác nhau | Nạp lại cả 3 mạch với cùng một `secrets.h` |
| Lệnh warn trả `ok:false` | Bridge chưa thấy gói nào từ ghế đó | Đợi ghế gửi heartbeat (tối đa 10 giây) rồi gửi lại |
