# 🤖 Dự án Wall-E AI Robot

Hệ thống điều khiển Robot Wall-E qua mạng WiFi với giao diện Web hiện đại (Web UI), hỗ trợ truyền phát video trực tiếp (FPV) qua DroidCam và điều khiển động cơ chính xác bằng thuật toán PID.

## 🌟 Tính năng nổi bật

* **Kiến trúc WiFi Bridge:** ESP8266 đóng vai trò làm cầu nối TCP (Cổng 8080), truyền lệnh trực tiếp từ Python xuống Arduino qua Serial.

* **Auto-Discovery (Radar):** Tự động quét mạng LAN để tìm địa chỉ IP của Robot và điện thoại (DroidCam) mà không cần cấu hình IP tĩnh thủ công.

* **Điều khiển PID:** Tích hợp cảm biến quang chữ U làm Encoder, thuật toán PID giúp robot di chuyển thẳng và ổn định tốc độ trên các địa hình khác nhau.

* **Live FPV Vision:** Tích hợp luồng camera trực tiếp từ ứng dụng DroidCam (Smartphone) ngay trên Web Dashboard.

* **Web Dashboard Hiện Đại:** Giao diện điều khiển thiết kế theo phong cách Glassmorphism, tương thích tốt trên cả Laptop và Điện thoại.

## 📂 Cấu trúc dự án

```text
WallE_AI/
├── firmware/
│   ├── arduino_motor_servo/  # Code C++ cho Arduino Uno (PID, Motor, Servo)
│   └── esp_wifi_bridge/      # Code C++ cho ESP8266 (WiFi Manager, TCP Bridge)
├── frontend/
│   └── templates/
│       └── index.html        # Giao diện điều khiển Web (HTML/JS/TailwindCSS)
├── tools/
│   ├── web_controller.py     # Backend Python (WebSocket Server, HTTP Server, Radar)
│   ├── test_tcp.py           # Tool test kết nối mạng và gửi lệnh qua Terminal
│   └── smooth_dance.py       # Script biểu diễn Servo tự động
├── docs/
│   ├── schematics.pdf        # Sơ đồ đấu nối mạch điện
│   └── wiring_diagram.png    # Ảnh thực tế
└── README.md
```

## 🔌 Sơ đồ chân kết nối (Pinout)

**1. Động cơ & L298N (Băm xung PWM)**

* Motor Trái: `ENA = 3`, `IN1 = 5`, `IN2 = 6`

* Motor Phải: `ENB = 11`, `IN3 = 9`, `IN4 = 10`

**2. Cảm biến tốc độ (Encoder quang chữ U)**

* Encoder Trái (OUT): `D2` (Sử dụng ngắt External Interrupt)

* Encoder Phải (OUT): `D7` (Sử dụng kỹ thuật Polling)

**3. Mạch Servo PCA9685 (I2C)**

* I2C: `SDA = A4`, `SCL = A5`

* Output Enable (OE): `D13` (Ngắt điện Servo lúc khởi động để tránh sụt áp)

**4. Kết nối ESP8266 & Arduino**

* `TX (ESP)` -> `RX (Arduino)`

* `RX (ESP)` -> `TX (Arduino)`

* `GND (ESP)` -> `GND (Arduino)`

## 🚀 Hướng dẫn cài đặt và sử dụng

### Bước 1: Nạp Firmware

1. Nạp `firmware/esp_wifi_bridge/tcp_bridge.ino` cho ESP8266. Dùng điện thoại kết nối vào WiFi `Wall-E_Setup` để cấu hình mạng LAN nhà bạn.

2. Nạp `firmware/arduino_motor_servo/main.ino` cho Arduino Uno (Lưu ý: Rút dây RX/TX trước khi nạp).

### Bước 2: Chuẩn bị Môi trường (Laptop/PC)

Yêu cầu cài đặt Python 3.7+ và thư viện `websockets`:

```bash
pip install websockets
```

### Bước 3: Chuẩn bị Camera (Smartphone)

1. Tải ứng dụng **DroidCam** trên điện thoại (Android/iOS).

2. Kết nối điện thoại cùng chung mạng WiFi với Laptop và Wall-E.

3. Mở app DroidCam và để màn hình sáng (ứng dụng sẽ phát video ở cổng `4747`).

### Bước 4: Khởi động Trạm Điều Khiển

Mở Terminal tại gốc dự án và chạy tệp Backend:

```bash
python tools/web_controller.py
```

* Hệ thống sẽ tự động quét mạng LAN để tìm Robot và Camera.

* Trình duyệt sẽ tự động mở trang Dashboard tại `http://localhost:5000`.

* (Tùy chọn) Để điều khiển bằng điện thoại thứ 2, dùng điện thoại đó truy cập vào `http://<IP_LAPTOP>:5000`.

## ⚙️ Giao thức điều khiển (Command Protocol)

Lệnh được gửi dưới dạng chuỗi Text, kết thúc bằng ký tự ngắt dòng `\n`.

| **Loại Lệnh** | **Cú pháp** | **Ví dụ** | **Mô tả** | 
|---|---|---|---|
| **Servo** | `S:[ID]:[Góc]` | `S:0:90` | Quay Servo kênh 0 tới góc 90 độ (0-180). | 
| **Motor Đơn** | `M:[ID]:[Tốc độ]` | `M:1:200` | Điều khiển motor 1 (Trái) với PWM 200. | 
| **Drive (PID)** | `D:[Xung_T]:[Xung_P]` | `D:10:10` | Hai bánh chạy đồng bộ, mục tiêu 10 xung/50ms. | 

*Lưu ý: Luôn đảm bảo kết nối chung GND (âm) cho toàn bộ hệ thống mạch (Pin, L298N, PCA9685, ESP8266, Arduino).*