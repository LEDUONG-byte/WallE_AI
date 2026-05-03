#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>
#include <ESP8266HTTPUpdateServer.h> 
#include <WiFiManager.h>

ESP8266WebServer httpServer(80);       
ESP8266HTTPUpdateServer httpUpdater;   
WiFiServer tcpServer(8080);            
WiFiClient tcpClient;

void setup() {
  // Đồng bộ tốc độ với Arduino Uno
  Serial.begin(115200);
  
  // Tắt chế độ phát WiFi rác (chỉ dùng Station) để tiết kiệm pin
  WiFi.mode(WIFI_STA); 

  WiFiManager wifiManager;
  wifiManager.setConfigPortalTimeout(180);

  if (!wifiManager.autoConnect("Wall-E_Setup", "12345678")) {
    delay(3000);
    ESP.restart();
  }

  // Cấu hình trang nạp firmware qua mạng (/update)
  httpUpdater.setup(&httpServer);
  httpServer.begin();

  tcpServer.begin();
  tcpServer.setNoDelay(true); 
}

void loop() {
  // Lắng nghe lệnh nạp code qua mạng
  httpServer.handleClient();

  if (!tcpClient.connected()) {
    tcpClient.stop(); 
    tcpClient = tcpServer.available();
  } 
  else {
    // Chiều đi: TCP -> Serial
    if (tcpClient.available()) {
      uint8_t buffer[64];
      size_t bytesRead = tcpClient.read(buffer, sizeof(buffer));
      if (bytesRead > 0) {
        Serial.write(buffer, bytesRead);
      }
    }

    // Chiều về: Serial -> TCP
    if (Serial.available()) {
      size_t len = Serial.available();
      uint8_t sbuf[64];
      if (len > sizeof(sbuf)) len = sizeof(sbuf); 
      
      // Đọc và chuyển tiếp ngay lập tức
      Serial.readBytes(sbuf, len);
      tcpClient.write(sbuf, len);
    }
  }

  yield(); 
}