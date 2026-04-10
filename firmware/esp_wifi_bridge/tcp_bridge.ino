#include <ESP8266WiFi.h>
#include <DNSServer.h>
#include <ESP8266WebServer.h>
#include <WiFiManager.h> // Thư viện tạo Captive Portal thần thánh

// Mở cổng TCP thô ở port 8080 để giao tiếp thời gian thực với Python
WiFiServer server(8080);
WiFiClient client;

void setup() {
  // Tốc độ cao 115200 để truyền lệnh không độ trễ
  Serial.begin(115200);
  
  // Khởi tạo WiFiManager
  WiFiManager wifiManager;

  // Xóa cấu hình cũ (Mở comment dòng dưới ra nếu đại ca muốn ESP quên WiFi cũ để test cấu hình lại từ đầu)
  // wifiManager.resetSettings();

  // Đặt timeout cho cái Web Portal (ví dụ: 3 phút không ai nhập mật khẩu thì reset)
  wifiManager.setConfigPortalTimeout(180);

  // LỆNH CỐT LÕI: Tự động kết nối WiFi cũ. 
  // Nếu không có WiFi cũ hoặc rớt mạng, nó tự phát ra WiFi tên là "Wall-E_Setup"
  if (!wifiManager.autoConnect("Wall-E_Setup")) {
    Serial.println("[-] Không thể kết nối WiFi, đang khởi động lại...");
    delay(3000);
    ESP.restart(); // Khởi động lại để thử lại
    delay(5000);
  }

  // NÂNG CẤP: IN ĐỊA CHỈ IP RA MÀN HÌNH ĐỂ ĐẠI CA DỄ THẤY
  Serial.println("\n=======================================");
  Serial.println("[+] Wall-E da vao mang LAN thanh cong!");
  Serial.print("[+] IP cua Wall-E hien tai la: ");
  Serial.println(WiFi.localIP());
  Serial.println("=======================================\n");

  // Nếu code chạy qua được dòng trên, tức là đã VÀO ĐƯỢC MẠNG LAN
  // Bắt đầu mở trạm thu TCP ở cổng 8080
  server.begin();
}

void loop() {
  // 1. Nếu chưa có thiết bị nào (như script Python) kết nối tới
  if (!client.connected()) {
    client = server.available();
  } 
  // 2. Nếu đã có kết nối và có dữ liệu từ Python bơm xuống
  else {
    while (client.available()) {
      // Đọc từng byte từ WiFi và ném XUYÊN THỦNG thẳng xuống cổng Serial
      Serial.write(client.read());
    }
  }
}