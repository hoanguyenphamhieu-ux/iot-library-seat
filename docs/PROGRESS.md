# Tiến độ dự án

> Cập nhật: 18/11/2026 (tuần 2). Trạng thái: **Xong** · **Đang làm** · **Chưa làm** · **Chờ linh kiện** · **Cần xác nhận** (chưa rõ đã làm chưa).
>
> Quy ước tuần: tuần 1 = 10–16/11, tuần 2 = 17–23/11, tuần 3 = 24–30/11, tuần 4 = 1–7/12, tuần 5 = 8–14/12, tuần 6 = 15–21/12. Cần đối chiếu lại với lịch học kỳ để chắc tuần 6 trùng tuần 16 (hạn nộp).

## 1. Tóm tắt

- **Phần mềm đã chạy được từ đầu đến cuối với dữ liệu giả:** `fake_bridge.py` → gateway → CoreIOT. Các ghế `Seat-01..03` và `Room-A` tự xuất hiện dưới `Library-Gateway`.
- **Repo đã sẵn sàng làm việc nhóm:** có 3 nhánh theo vai, `main` đã khóa, đã mời đồng đội.
- **Linh kiện đã đặt, đang chờ hàng.** Mọi bước firmware từ A2 trở đi bị chặn cho tới khi có radar và ToF.
- **Đã chốt 3 cải tiến:** LED 4 màu + mã hóa ESP-NOW, gateway cảnh báo khi mất mạng, dashboard thống kê (chi tiết trong [`ARCHITECTURE.md`](ARCHITECTURE.md) mục 6).

## 2. Trạng thái từng bước

### Chuẩn bị chung

| Bước | Việc | Trạng thái | Ghi chú |
|---|---|---|---|
| 0.1 | Đặt linh kiện | Đang làm | Đã đặt 2 LD2410C, 2 VL53L0X, dây dupont; chờ giao |
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
| A1 | Project PlatformIO cho node và bridge | Xong | Board `yolo_uno` (file json của thầy); chưa nạp thử. Khi có mạch: kiểm tra flash 8 MB bằng `ESP.getFlashChipSize()` |
| A2 | Đọc radar LD2410C | Chờ linh kiện | Dùng thư viện MyLD2410 (có engineering mode) |
| A3 | Đọc ToF, hiệu chỉnh ngưỡng | Chờ linh kiện | |
| A4 | Máy trạng thái + LED 4 màu | Chờ linh kiện | Gồm cải tiến LED cam cho `OBJECT_ONLY` |
| A5 | ESP-NOW node ↔ bridge (T06) | Chờ linh kiện | Gồm cải tiến mã hóa ESP-NOW |
| A6 | OTA (T14) | Chờ linh kiện | |
| A7 | TinyML (T04, T05) | Chờ linh kiện | |
| A8 | Web server trên node (T07, tùy chọn) | Chưa làm | Chỉ làm nếu dư thời gian |

### Vai B — Gateway

| Bước | Việc | Trạng thái | Ghi chú |
|---|---|---|---|
| B1 | venv, `requirements.txt` | Xong | |
| B2 | `fake_bridge.py` | Xong | Đã test telemetry và lệnh warn/ack bằng `test_cmd.py` |
| B3 | Gửi telemetry lên CoreIOT (T08, T15) | Xong | |
| B4 | RPC hai chiều + ACK | Cần xác nhận | Gộp thêm cảnh báo khi mất mạng |
| B5 | SQLite, gửi bù khi mất mạng | Chưa làm | |
| B6 | Web local (T10) | Chưa làm | |
| B7 | AI trên gateway (T09) + số liệu thống kê | Chưa làm | |
| B8 | Chuyển sang bridge thật, README | Chờ linh kiện | |

### Vai C — Cloud và tích hợp

| Bước | Việc | Trạng thái | Ghi chú |
|---|---|---|---|
| C1 | Device profile, server attributes | Xong | `library-seat`, `room`; `hogLimitSec = 120`, `inactivityTimeout = 30000` |
| C2 | Dashboard (T11) + thống kê | Cần xác nhận | |
| C3 | Rule chain `Seat Logic` (T12) | Chưa làm | |
| C4 | Notification (T13) | Chưa làm | |
| C5 | Gói OTA | Chờ linh kiện | Cần A6 |
| C6 | ThingsBoard local trên Docker (N07) | Chưa làm | |
| C7 | Khung báo cáo | Chưa làm | Bắt đầu từ tuần 3 |

## 3. So với kế hoạch

| Tuần | Mục tiêu theo kế hoạch | Thực tế |
|---|---|---|
| 1 (10–16/11) | Đặt linh kiện, repo, CoreIOT, `fake_bridge`, gateway gửi telemetry | Phần mềm vượt kế hoạch (đã xong B3, C1); linh kiện đặt trễ |
| 2 (17–23/11) | Firmware đọc cảm biến, ESP-NOW; RPC; dashboard | Firmware bị chặn vì chưa có linh kiện; nên đẩy nhanh B4–B6 và C2–C4 trong lúc chờ |
| 3 (24–30/11) | Ghép nối lần 1, rule chain, notification | |
| 4 (1–7/12) | OTA, lắp lên bàn thật — **mốc đủ 9 điểm lõi** | |
| 5 (8–14/12) | TinyML, AI gateway, web local, N07 | |
| 6 (15–21/12) | Đo đạc, báo cáo, video, nộp | |

## 4. Việc tiếp theo (ưu tiên)

1. **Trong lúc chờ linh kiện, làm hết phần không cần phần cứng:** B4 (RPC + cảnh báo khi mất mạng), C2 (dashboard), C3 (rule chain), C4 (notification). Tất cả test được bằng `fake_bridge.py`.
2. **Khi linh kiện về:** làm ngay A2 → A5 để kịp buổi ghép nối lần 1 ở tuần 3.
3. **Phân vai cho đồng đội**, mỗi người làm trên nhánh của mình và tự commit, để lịch sử commit thể hiện đóng góp.
4. Xác nhận với thầy về T15 nếu chưa hỏi.

## 5. Rủi ro hiện tại

| Rủi ro | Ảnh hưởng | Cách giảm |
|---|---|---|
| Linh kiện về trễ | Dồn toàn bộ firmware vào tuần 3–4 | Làm xong phần cloud và gateway trước; có `fake_bridge` để test |
| Hiểu sai T15 (2 điểm) | Mất điểm nếu thầy hiểu khác | Hỏi thầy sớm |
| OTA khó (2 điểm) | Có thể không kịp | Đến cuối tuần 4 chưa xong thì bỏ, tổng đăng ký vẫn khoảng 11 điểm |
| Radar bắt nhầm ghế bên | Sai trạng thái khi demo | Test ngay ở A2; đặt 2 chỗ cách nhau ít nhất 1 m |

## 6. Checklist minh chứng

- [ ] T06 — Serial của bridge nhận gói từ 2 ghế; code callback ESP-NOW
- [ ] T08 — log gateway: nhận Serial, publish MQTT, chuyển RPC xuống ghế
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
