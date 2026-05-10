#include <ESP8266WiFi.h>
#include <WiFiManager.h>

WiFiServer tcpServer(8080);
WiFiClient tcpClient;
String espBuffer = ""; 
bool wasConnected = false; // Thêm cờ theo dõi trạng thái kết nối

void setup() {
  Serial.begin(115200);
  WiFi.mode(WIFI_STA);

  WiFiManager wifiManager;
  if (!wifiManager.autoConnect("Wall_E_Setup", "12345678")) {
    delay(3000);
    ESP.restart();
  }

  tcpServer.begin();
  tcpServer.setNoDelay(true); 
}

void loop() {
  if (tcpServer.hasClient()) {
    if (!tcpClient || !tcpClient.connected()) {
      if (tcpClient) tcpClient.stop();
      tcpClient = tcpServer.available();
    } else {
      tcpServer.available().stop();
    }
  }

  if (tcpClient && tcpClient.connected()) {
    // --- THÊM: Báo có kết nối (chỉ gửi 1 lần lúc vừa kết nối) ---
    if (!wasConnected) {
      wasConnected = true;
      Serial.println("SYS:LINK_UP");
    }

    // Chiều đi: Nhận lệnh từ Web xả thẳng xuống Arduino
    while (tcpClient.available() > 0) {
      Serial.write(tcpClient.read());
    }

    // Chiều về: Gom gói Telemetry từ Arduino rồi bắn lên Web
    while (Serial.available() > 0) {
      char c = Serial.read();
      espBuffer += c;
      if (c == '\n') {
        tcpClient.print(espBuffer); 
        espBuffer = "";
      }
    }
  } else {
    // --- THÊM: Báo rớt kết nối (chỉ gửi 1 lần lúc vừa rớt) ---
    if (wasConnected) {
      wasConnected = false;
      Serial.println("SYS:LINK_DOWN"); // Đẩy lệnh xuống bắt Arduino phanh
    }

    // Đổ rác nếu Web mất kết nối
    espBuffer = ""; 
    
    while (Serial.available() > 0) {
      Serial.read();
    }
  }
}