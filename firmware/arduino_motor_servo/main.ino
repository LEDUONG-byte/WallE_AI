#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

// Khởi tạo mạch điều khiển Servo PCA9685
Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver();

// =====================================================
// CẤU HÌNH MOTOR - CẬP NHẬT THEO ĐÍNH CHÍNH MỚI
// =====================================================

// Cụm Motor Trái (Giữ nguyên)
#define ENA 3   // Chân băm xung PWM
#define IN1 5   // Chân hướng 1
#define IN2 6   // Chân hướng 2

// Cụm Motor Phải (CẬP NHẬT: 9, 10, 11)
#define IN3 9   // Chân hướng 1
#define IN4 10  // Chân hướng 2
#define ENB 11  // Chân băm xung PWM (Đã đổi từ 10 sang 11)

// Chân điều khiển bật/tắt điện mạch Servo (OE)
#define OE_PIN 13

// Bộ đệm nhận lệnh
const int MAX_CMD_LEN = 20;
char cmdBuffer[MAX_CMD_LEN];
int bufIndex = 0;

void setup() {
  // Giao tiếp với ESP qua cổng Serial (Bắt buộc 115200)
  Serial.begin(115200);
  
  // Thiết lập các chân L298N là OUTPUT
  pinMode(ENA, OUTPUT); 
  pinMode(IN1, OUTPUT); 
  pinMode(IN2, OUTPUT);
  pinMode(IN3, OUTPUT); 
  pinMode(IN4, OUTPUT); 
  pinMode(ENB, OUTPUT);
  
  // Cơ chế khởi động an toàn: Tắt điện Servo để ESP vào WiFi trước
  pinMode(OE_PIN, OUTPUT);
  digitalWrite(OE_PIN, HIGH); // Mức HIGH = Tắt mạch PCA9685
  
  // Khởi tạo giao tiếp I2C cho mạch Servo
  pwm.begin();
  pwm.setPWMFreq(60); 
}

void loop() {
  // Đọc dữ liệu từ ESP (đẩy từ Python xuống)
  while (Serial.available() > 0) {
    char c = Serial.read();
    
    if (c == '\n') {
      cmdBuffer[bufIndex] = '\0'; 
      processCommand(cmdBuffer);  
      bufIndex = 0;               
    } 
    else if (c != '\r' && bufIndex < MAX_CMD_LEN - 1) {
      cmdBuffer[bufIndex++] = c;
    }
  }
}

// HÀM XỬ LÝ LỆNH TỪ PYTHON (S:id:angle hoặc M:id:speed)
void processCommand(char* cmd) {
  char type;
  int id, value;

  // Giải mã chuỗi lệnh
  if (sscanf(cmd, "%c:%d:%d", &type, &id, &value) == 3) {
    
    // 1. LỆNH ĐIỀU KHIỂN SERVO (S)
    if (type == 'S') {
      digitalWrite(OE_PIN, LOW); // Mở điện mạch Servo khi có lệnh
      
      value = constrain(value, 0, 180);
      int pulse = map(value, 0, 180, 150, 600);
      pwm.setPWM(id, 0, pulse);
    } 
    
    // 2. LỆNH ĐIỀU KHIỂN MOTOR (M)
    else if (type == 'M') {
      value = constrain(value, -255, 255);
      int speed = abs(value); 
      
      if (id == 1) { // Điều khiển Bánh trái
        analogWrite(ENA, speed); 
        if (value > 0) {
          digitalWrite(IN1, HIGH); digitalWrite(IN2, LOW);
        } else if (value < 0) {
          digitalWrite(IN1, LOW); digitalWrite(IN2, HIGH);
        } else {
          digitalWrite(IN1, LOW); digitalWrite(IN2, LOW);
        }
      }
      else if (id == 2) { // Điều khiển Bánh phải
        analogWrite(ENB, speed); // Chân 11 hỗ trợ băm xung PWM
        if (value > 0) {
          digitalWrite(IN3, HIGH); digitalWrite(IN4, LOW);
        } else if (value < 0) {
          digitalWrite(IN3, LOW); digitalWrite(IN4, HIGH);
        } else {
          digitalWrite(IN3, LOW); digitalWrite(IN4, LOW);
        }
      }
    }
  }
}