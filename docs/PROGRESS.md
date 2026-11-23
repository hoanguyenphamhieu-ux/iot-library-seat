# Tiến độ dự án

> Cập nhật: 23/11/2026 (cuối tuần 2). Trạng thái: **Xong** · **Đang làm** · **Chưa làm** · **Chờ linh kiện** · **Cần xác nhận** (chưa rõ đã làm chưa).
>
> Quy ước tuần: tuần 1 = 10–16/11, tuần 2 = 17–23/11, tuần 3 = 24–30/11, tuần 4 = 1–7/12, tuần 5 = 8–14/12, tuần 6 = 15–21/12. Cần đối chiếu lại với lịch học kỳ để chắc tuần 6 trùng tuần 16 (hạn nộp).

## 1. Tóm tắt

- **Đã chạy được trên phần cứng thật, cả hai chiều:**
  - Chiều lên: node `Seat-01` (radar) → ESP-NOW → bridge → USB → gateway → CoreIOT. `Seat-01`, `Room-A`, `Library-Gateway` đều Active, `loss_pct = 0%`.
  - Chiều xuống: lệnh `setWarning` từ CoreIOT (RPC debug terminal) và từ web local đều tới được LED ghế, có ACK `success: true`.
- **Firmware đã push lên nhánh `a-firmware`:** đọc radar, máy trạng thái, LED 4 màu, ESP-NOW node ↔ bridge.
- **Gateway (Tú) đã có B4–B7:** RPC + ACK, SQLite gửi bù, web local, AI IsolationForest. Đã merge vào `main` (PR #2).
- **Còn thiếu để đủ dữ liệu thật:** ToF chưa hàn chân (chưa có trạng thái `OBJECT_ONLY`), mới có 1 node.
- **Đã chốt 3 cải tiến:** LED 4 màu + mã hóa ESP-NOW, gateway cảnh báo khi mất mạng, dashboard thống kê (chi tiết trong [`ARCHITECTURE.md`](ARCHITECTURE.md) mục 6).

## 2. Trạng thái từng bước

### Chuẩn bị chung

| Bước | Việc | Trạng thái | Ghi chú |
|---|---|---|---|
| 0.1 | Đặt linh kiện | Xong | Đã về: 2 LD2410C, 2 VL53L0X, dây; VL53L0X chưa hàn chân |
| 0.2 | Cài phần mềm | Xong | Mới cài trên máy của Hòa; 2 bạn còn lại cài khi bắt đầu |
| 0.3 | Repo GitHub | Xong | Public, `hoanguyenphamhieu-ux/iot-library-seat`; nhánh `a-firmware`, `b-gateway`, `c-cloud`; `main` khóa, chỉ merge qua Pull Request |
| 0.4 | Device `Library-Gateway` trên CoreIOT | Xong | Token nằm trong `gateway/.env` (không commit) |
| 0.5 | Project Edge Impulse | Xong | |
| 0.6 | Họp chốt hợp đồng | Chưa làm | |
| — | Đăng ký nhóm và đề tài với thầy | Cần xác nhận | |
| — | Email hỏi thầy cách hiểu T15 | Cần xác nhận | |
| 3 | `CONTRACT.md`, `seat_packet.h` | Xong | |

### Vai A — Firmware

| Bước | Việc | Trạng thái | Ghi chú |
|---|---|---|---|
| A1 | Project PlatformIO cho node và bridge | Xong | Board `yolo_uno`; đã nạp thật, flash 8 MB, Arduino core 2.0.17 |
| A2 | Đọc radar LD2410C | Xong | Nối TX radar → D9 (GPIO18), RX radar → D8 (GPIO17); firmware radar 2.44; `setMaxGate(2)` (~1,5 m). Đã test ngồi gần và đi xa |
| A3 | Đọc ToF, hiệu chỉnh ngưỡng | Chờ linh kiện | VL53L0X chưa hàn chân. Sau khi hàn: chạy env `sensors`, đặt `TOF_OBJECT_MM` = khoảng cách ghế trống − 100 |
| A4 | Máy trạng thái + LED 4 màu | Đang làm | EMPTY/OCCUPIED, LED xanh/đỏ, nháy vàng khi có lệnh warn đã chạy. Còn `OBJECT_ONLY` (cam), cần ToF |
| A5 | ESP-NOW node ↔ bridge (T06) | Đang làm | `Seat-01` ↔ bridge chạy 2 chiều, mất gói 0%. Còn: node `Seat-02`, bật mã hóa, đo mất gói theo khoảng cách. Đã sửa RSSI trên core 2.x (promiscuous), cần xác nhận số âm |
| A6 | OTA (T14) | Chưa làm | |
| A7 | TinyML (T04, T05) | Chưa làm | Cần ToF để thu dữ liệu đủ 4 nhãn bằng env `collect` |
| A8 | Web server trên node (T07, tùy chọn) | Chưa làm | Chỉ làm nếu dư thời gian |

### Vai B — Gateway

| Bước | Việc | Trạng thái | Ghi chú |
|---|---|---|---|
| B1 | venv, `requirements.txt` | Xong | `requirements.txt` đang lưu dạng UTF-16, nên lưu lại UTF-8 |
| B2 | `fake_bridge.py` | Xong | |
| B3 | Gửi telemetry lên CoreIOT (T08, T15) | Xong | Đã chạy với bridge thật |
| B4 | RPC hai chiều + ACK | Xong | Test thật 23/11: `setWarning` từ RPC debug terminal → `{"success":true}`, LED nháy vàng; latency ghi vào `docs/measurements/rpc_latency.csv` |
| B5 | SQLite, gửi bù khi mất mạng | Xong (code) | Chưa test rút mạng thật |
| B6 | Web local (T10) | Xong | Đã dùng bật/tắt cảnh báo trên ghế thật. Nên tắt log `werkzeug` cho đỡ rối |
| B7 | AI trên gateway (T09) + số liệu thống kê | Xong (code) | Mô hình huấn luyện trên dữ liệu giả lập; cần chạy lại khi có dữ liệu thật |
| B8 | Chuyển sang bridge thật, README | Xong | `SERIAL_URL=COM10` trên máy Hòa |

### Vai C — Cloud và tích hợp

| Bước | Việc | Trạng thái | Ghi chú |
|---|---|---|---|
| C1 | Device profile, server attributes | Xong | `library-seat`, `room`; `hogLimitSec = 120`, `inactivityTimeout = 30000` |
| C2 | Dashboard (T11) + thống kê | Cần xác nhận | Đã có dashboard `Test RPC` (RPC debug terminal) để test |
| C3 | Rule chain `Seat Logic` (T12) | Chưa làm | |
| C4 | Notification (T13) | Chưa làm | |
| C5 | Gói OTA | Chưa làm | Cần A6 |
| C6 | ThingsBoard local trên Docker (N07) | Chưa làm | |
| C7 | Khung báo cáo | Chưa làm | Bắt đầu từ tuần 3 |

### Ghép nối

| Bước | Việc | Trạng thái | Ghi chú |
|---|---|---|---|
| G1 | Node → bridge → gateway → CoreIOT (1 ghế) | Xong | 23/11, `Seat-01` |
| G2 | Lệnh từ CoreIOT và web local xuống ghế | Xong | 23/11 |
| G3 | Đủ 2 ghế, có `OBJECT_ONLY` | Chưa làm | Cần node 2 và ToF |

## 3. So với kế hoạch

| Tuần | Mục tiêu theo kế hoạch | Thực tế |
|---|---|---|
| 1 (10–16/11) | Đặt linh kiện, repo, CoreIOT, `fake_bridge`, gateway gửi telemetry | Phần mềm vượt kế hoạch (đã xong B3, C1); linh kiện đặt trễ |
| 2 (17–23/11) | Firmware đọc cảm biến, ESP-NOW; RPC; dashboard | Linh kiện về giữa tuần; radar, ESP-NOW, ghép nối 2 chiều đã chạy (sớm hơn mốc ghép nối tuần 3). Gateway xong B4–B8. Còn ToF và dashboard |
| 3 (24–30/11) | Ghép nối lần 1, rule chain, notification | |
| 4 (1–7/12) | OTA, lắp lên bàn thật — **mốc đủ 9 điểm lõi** | |
| 5 (8–14/12) | TinyML, AI gateway, web local, N07 | |
| 6 (15–21/12) | Đo đạc, báo cáo, video, nộp | |

## 4. Việc tiếp theo (ưu tiên)

1. **Hàn chân VL53L0X**, test ToF và hiệu chỉnh ngưỡng (A3), hoàn thiện `OBJECT_ONLY` (A4).
2. **Nạp node `Seat-02`** (cấp nguồn bằng sạc, không cần cắm laptop) để có minh chứng T06 với 2 ghế.
3. **C2, C3, C4:** dashboard, rule chain `Seat Logic`, notification. Đã có dữ liệu thật để test.
4. **Bật mã hóa ESP-NOW** và đo mất gói theo khoảng cách (README firmware bước 7–8).
5. **A6 OTA**, sau đó A7 TinyML.
6. Xác nhận với thầy về T15 nếu chưa hỏi.

## 5. Rủi ro hiện tại

| Rủi ro | Ảnh hưởng | Cách giảm |
|---|---|---|
| Hiểu sai T15 (2 điểm) | Mất điểm nếu thầy hiểu khác | Hỏi thầy sớm |
| OTA khó (2 điểm) | Có thể không kịp | Đến cuối tuần 4 chưa xong thì bỏ, tổng đăng ký vẫn khoảng 11 điểm |
| Radar bắt nhầm ghế bên | Sai trạng thái khi demo | Đã giới hạn ~1,5 m; khi có node 2, đặt 2 chỗ cách nhau ít nhất 1 m và test |
| Tranh chấp cổng COM của bridge | Nạp lỗi `Access is denied` | Mỗi lúc chỉ một việc dùng cổng: nạp, monitor, hoặc gateway |

## 6. Checklist minh chứng

- [ ] T06 — Serial của bridge nhận gói từ 2 ghế; code callback ESP-NOW *(đã có với 1 ghế)*
- [x] T08 — log gateway: nhận Serial, publish MQTT, chuyển RPC xuống ghế *(nhớ lưu ảnh vào `docs/evidence/`)*
- [ ] T15 — danh sách device con và tab Relations của `Library-Gateway`
- [ ] T11 — dashboard đủ 4 màu trạng thái; biểu đồ thống kê
- [ ] T12 — ảnh rule chain `Seat Logic`; tab Events; alarm Active rồi Cleared
- [ ] T13 — thông báo trên web và điện thoại
- [ ] T14 — trang OTA updates; log tải firmware; `current_fw_version` mới
- [ ] T05 — Edge Impulse: Data acquisition, Impulse design, confusion matrix
- [ ] T04 — log nhãn TinyML trên node; biểu đồ `ai` trên dashboard
- [ ] T09 — `ai_job.py`; `hog_anomaly = true` trên dashboard
- [ ] T10 — web local chạy khi không có internet
- [ ] N07 — `docker ps` và dashboard tại `localhost:8080`