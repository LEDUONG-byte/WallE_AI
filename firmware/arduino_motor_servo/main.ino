#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver();

// =====================================================
// CẤU HÌNH MOTOR - PORT 9, 10, 11 CHO MOTOR PHẢI
// =====================================================
#define ENA 3   
#define IN1 5   
#define IN2 6   

#define IN3 9   
#define IN4 10  
#define ENB 11  

#define OE_PIN 13

// Lưu trữ trạng thái hiện tại để tránh ghi đè dữ liệu giống hệt nhau
int currentServoAngles[16];   // Lưu góc của 16 kênh servo
int currentMotorSpeed[3];    // Lưu tốc độ motor 1 và 2

const int MAX_CMD_LEN = 20;
char cmdBuffer[MAX_CMD_LEN];
int bufIndex = 0;

void setup() {
  // Tốc độ Serial cao để giảm độ trễ nhận lệnh
  Serial.begin(115200);
  
  pinMode(ENA, OUTPUT); pinMode(IN1, OUTPUT); pinMode(IN2, OUTPUT);
  pinMode(IN3, OUTPUT); pinMode(IN4, OUTPUT); pinMode(ENB, OUTPUT);
  
  pinMode(OE_PIN, OUTPUT);
  digitalWrite(OE_PIN, HIGH); 
  
  // Khởi tạo mảng trạng thái
  for(int i=0; i<16; i++) currentServoAngles[i] = -1;
  for(int i=0; i<3; i++) currentMotorSpeed[i] = -999;

  pwm.begin();
  pwm.setPWMFreq(60); 
}

void loop() {
  // Đọc Serial không chặn
  while (Serial.available() > 0) {
    char c = Serial.read();
    
    if (c == '\n') {
      cmdBuffer[bufIndex] = '\0'; 
      if (bufIndex > 0) processCommand(cmdBuffer);  
      bufIndex = 0;               
    } 
    else if (c != '\r' && bufIndex < MAX_CMD_LEN - 1) {
      cmdBuffer[bufIndex++] = c;
    }
  }
}

// Hàm hỗ trợ cập nhật động cơ để dùng chung cho nhiều loại lệnh
void updateMotor(int id, int value) {
  if (id < 1 || id > 2) return;
  if (value == currentMotorSpeed[id]) return; // Bỏ qua nếu giá trị không đổi

  int targetValue = constrain(value, -255, 255);
  int speed = abs(targetValue);
  
  if (id == 1) { // Motor Trái
    analogWrite(ENA, speed); 
    if (targetValue > 0) {
      digitalWrite(IN1, HIGH); digitalWrite(IN2, LOW);
    } else if (targetValue < 0) {
      digitalWrite(IN1, LOW); digitalWrite(IN2, HIGH);
    } else {
      digitalWrite(IN1, LOW); digitalWrite(IN2, LOW);
    }
  }
  else if (id == 2) { // Motor Phải
    analogWrite(ENB, speed); 
    if (targetValue > 0) {
      digitalWrite(IN3, HIGH); digitalWrite(IN4, LOW);
    } else if (targetValue < 0) {
      digitalWrite(IN3, LOW); digitalWrite(IN4, HIGH);
    } else {
      digitalWrite(IN3, LOW); digitalWrite(IN4, LOW);
    }
  }
  currentMotorSpeed[id] = value;
}

void processCommand(char* cmd) {
  char type;
  int val1, val2;

  // Giải mã lệnh cơ bản
  if (sscanf(cmd, "%c:%d:%d", &type, &val1, &val2) != 3) return;
    
  // 1. LỆNH DRIVE ĐỒNG BỘ (D:speedLeft:speedRight) -> GIẢM ĐỘ TRỄ
  if (type == 'D') {
    updateMotor(1, val1);
    updateMotor(2, val2);
  }

  // 2. LỆNH SERVO (S:id:angle)
  else if (type == 'S') {
    if (val1 < 0 || val1 > 15) return;
    if (val2 == currentServoAngles[val1]) return;

    digitalWrite(OE_PIN, LOW); 
    val2 = constrain(val2, 0, 180);
    int pulse = map(val2, 0, 180, 150, 600);
    pwm.setPWM(val1, 0, pulse);
    currentServoAngles[val1] = val2;
  } 
  
  // 3. LỆNH MOTOR ĐƠN (M:id:speed)
  else if (type == 'M') {
    updateMotor(val1, val2);
  }
}