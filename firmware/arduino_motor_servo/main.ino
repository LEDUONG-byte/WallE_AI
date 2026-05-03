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

// =====================================================
// CẤU HÌNH MPU6050 (GY-521)
// =====================================================
const int MPU = 0x68;
float gyroZ, yaw = 0;
float gyroZError = 0;
unsigned long prevMPUTime = 0;
unsigned long prevReportTime = 0;

// Lưu trữ trạng thái hiện tại
int currentServoPulse[16];   
int currentMotorSpeed[3];    

const int MAX_CMD_LEN = 20;
char cmdBuffer[MAX_CMD_LEN];
int bufIndex = 0;

void setup() {
  Serial.begin(115200);
  
  pinMode(ENA, OUTPUT); pinMode(IN1, OUTPUT); pinMode(IN2, OUTPUT);
  pinMode(IN3, OUTPUT); pinMode(IN4, OUTPUT); pinMode(ENB, OUTPUT);
  pinMode(OE_PIN, OUTPUT);
  digitalWrite(OE_PIN, HIGH); 
  
  for(int i=0; i<16; i++) currentServoPulse[i] = -1;
  for(int i=0; i<3; i++) currentMotorSpeed[i] = -999;

  // Khởi động I2C chung cho cả Servo và MPU
  Wire.begin();
  
  // Khởi động PCA9685
  pwm.begin();
  pwm.setPWMFreq(60); 

  // Khởi động MPU6050
  Wire.beginTransmission(MPU);
  Wire.write(0x6B); // Thanh ghi Power Management
  Wire.write(0);    // Đánh thức MPU
  Wire.endTransmission(true);

  // Calibration MPU6050 (Để xe nằm im lúc bật nguồn)
  for (int i = 0; i < 200; i++) {
    Wire.beginTransmission(MPU);
    Wire.write(0x47); 
    Wire.endTransmission(false);
    Wire.requestFrom(MPU, 2, true);
    int16_t gZ = (Wire.read() << 8 | Wire.read());
    gyroZError += (gZ / 131.0); 
    delay(10);
  }
  gyroZError = gyroZError / 200; 
  
  prevMPUTime = millis();
}

void loop() {
  unsigned long currentTime = millis();

  // 1. XỬ LÝ NHẬN LỆNH TỪ SERVER (Không chặn)
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

  // 2. TÍNH TOÁN GÓC YAW TỪ MPU6050 (Mỗi 20ms - tương đương 50Hz)
  if (currentTime - prevMPUTime >= 20) {
    float elapsedTime = (currentTime - prevMPUTime) / 1000.0;
    prevMPUTime = currentTime;

    Wire.beginTransmission(MPU);
    Wire.write(0x47); 
    Wire.endTransmission(false);
    Wire.requestFrom(MPU, 2, true);
    int16_t gZ = (Wire.read() << 8 | Wire.read());
    
    gyroZ = (gZ / 131.0) - gyroZError;
    if (abs(gyroZ) > 1.0) { // Khử nhiễu tĩnh
      yaw += gyroZ * elapsedTime; 
    }
  }

  // 3. BÁO CÁO GÓC LÊN SERVER (Mỗi 100ms)
  if (currentTime - prevReportTime >= 100) {
    prevReportTime = currentTime;
    // Gửi dữ liệu theo format "Y:goc"
    Serial.print("Y:");
    Serial.println(yaw);
  }
}

void updateMotor(int id, int value) {
  if (id < 1 || id > 2) return;
  if (value == currentMotorSpeed[id]) return; 

  int targetValue = constrain(value, -255, 255);
  int speed = abs(targetValue);
  
  if (id == 1) { 
    analogWrite(ENA, speed); 
    if (targetValue > 0) {
      digitalWrite(IN1, HIGH); digitalWrite(IN2, LOW);
    } else if (targetValue < 0) {
      digitalWrite(IN1, LOW); digitalWrite(IN2, HIGH);
    } else {
      digitalWrite(IN1, LOW); digitalWrite(IN2, LOW);
    }
  }
  else if (id == 2) { 
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

  if (sscanf(cmd, "%c:%d:%d", &type, &val1, &val2) != 3) return;
    
  if (type == 'D') {
    updateMotor(1, val1);
    updateMotor(2, val2);
  }
  else if (type == 'S') {
    if (val1 < 0 || val1 > 15) return;
    if (val2 == currentServoPulse[val1]) return; 

    digitalWrite(OE_PIN, LOW); 
    int pulse = constrain(val2, 0, 4095);
    pwm.setPWM(val1, 0, pulse);
    currentServoPulse[val1] = pulse; 
  } 
  else if (type == 'M') {
    updateMotor(val1, val2);
  }
}