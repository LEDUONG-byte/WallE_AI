#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver();

// =====================================================
// [1] CẤU HÌNH CHÂN MẠCH CẦU H (MOTOR DC)
// =====================================================
#define ENA 11
#define IN1 10
#define IN2 9
#define IN3 7
#define IN4 6
#define ENB 5

// =====================================================
// [2] CẤU HÌNH PIN & CẢM BIẾN
// =====================================================
#define PIN_VOLTAGE A0  // Phân áp đo pin 12V
#define ENC_L_PIN 2     // Encoder Trái (INT0)
#define ENC_R_PIN 3     // Encoder Phải (INT1)
#define SW_R_PIN 4      // Công tắc Tay Phải
#define SW_L_PIN 8      // Công tắc Tay Trái

#define OE_PIN 13       // Chân Output Enable của PCA9685

// Biến toàn cục Encoder (bắt buộc dùng volatile trong ngắt)
volatile long encLeftCount = 0;
volatile long encRightCount = 0;

// Biến MPU6050
const int MPU = 0x68;
float gyroZ, yaw = 0;
float gyroZError = 0;

// Biến thời gian vòng lặp
unsigned long prevMPUTime = 0;
unsigned long prevTelemetryTime = 0;

// Trạng thái hiện tại (tránh gửi lệnh thừa)
int currentServoPulse[16];   
int currentMotorSpeed[3];    

// Bộ đệm nhận lệnh
const int MAX_CMD_LEN = 20;
char cmdBuffer[MAX_CMD_LEN];
int bufIndex = 0;

// =====================================================
// HÀM NGẮT (INTERRUPTS)
// =====================================================
void countLeftEncoder() { encLeftCount++; }
void countRightEncoder() { encRightCount++; }

// =====================================================
// SETUP HỆ THỐNG
// =====================================================
void setup() {
  Serial.begin(115200); 
  
  // Khởi tạo Motor
  pinMode(ENA, OUTPUT); pinMode(IN1, OUTPUT); pinMode(IN2, OUTPUT);
  pinMode(IN3, OUTPUT); pinMode(IN4, OUTPUT); pinMode(ENB, OUTPUT);
  
  // Khởi tạo PCA9685
  pinMode(OE_PIN, OUTPUT);
  digitalWrite(OE_PIN, HIGH); 

  // Khởi tạo Encoders (Dùng ngắt cứng)
  pinMode(ENC_L_PIN, INPUT_PULLUP);
  pinMode(ENC_R_PIN, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(ENC_L_PIN), countLeftEncoder, RISING);
  attachInterrupt(digitalPinToInterrupt(ENC_R_PIN), countRightEncoder, RISING);
  
  // Khởi tạo Công tắc tay (Dùng điện trở kéo lên nội bộ)
  pinMode(SW_R_PIN, INPUT_PULLUP);
  pinMode(SW_L_PIN, INPUT_PULLUP);

  // Đặt giá trị mặc định cho Servo và Motor
  for(int i=0; i<16; i++) currentServoPulse[i] = -1;
  for(int i=0; i<3; i++) currentMotorSpeed[i] = -999;

  // Khởi tạo I2C và PCA9685
  Wire.begin();
  pwm.begin();
  pwm.setPWMFreq(60); 

  // Khởi tạo MPU6050
  Wire.beginTransmission(MPU);
  Wire.write(0x6B); Wire.write(0);    
  Wire.endTransmission(true);

  // Calib GyroZ (Khử nhiễu góc Yaw)
  for (int i = 0; i < 200; i++) {
    Wire.beginTransmission(MPU); Wire.write(0x47); Wire.endTransmission(false);
    Wire.requestFrom(MPU, 2, true);
    gyroZError += (int16_t(Wire.read() << 8 | Wire.read()) / 131.0); 
    delay(10);
  }
  gyroZError /= 200; 
}

// =====================================================
// VÒNG LẶP CHÍNH
// =====================================================
void loop() {
  unsigned long currentTime = millis();

  // --- ƯU TIÊN 1: NHẬN LỆNH LÁI TỪ WEB ---
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

  // --- ƯU TIÊN 2: ĐỌC GÓC NGHIÊNG (20ms/lần) ---
  if (currentTime - prevMPUTime >= 20) {
    float elapsedTime = (currentTime - prevMPUTime) / 1000.0;
    prevMPUTime = currentTime;

    Wire.beginTransmission(MPU); Wire.write(0x47); Wire.endTransmission(false);
    Wire.requestFrom(MPU, 2, true);
    gyroZ = (int16_t(Wire.read() << 8 | Wire.read()) / 131.0) - gyroZError;
    if (abs(gyroZ) > 1.0) yaw += gyroZ * elapsedTime;
  }

  // --- ƯU TIÊN 3: GỬI GÓI TELEMETRY (50ms/lần) ---
  if (currentTime - prevTelemetryTime >= 50) {
    if (Serial.availableForWrite() > 32) { // Van xả an toàn (Tránh tràn buffer)
      prevTelemetryTime = currentTime;
      
      int rawVoltage = analogRead(PIN_VOLTAGE); // Gửi Raw 0-1023
      
      // Đảo logic công tắc (1: Đang bấm, 0: Nhả)
      int swRState = !digitalRead(SW_R_PIN); 
      int swLState = !digitalRead(SW_L_PIN);
      
      // Gói dữ liệu: T:yaw,rawBat,encL,encR,swR,swL
      Serial.print("T:");
      Serial.print(yaw);          Serial.print(",");
      Serial.print(rawVoltage);   Serial.print(",");
      Serial.print(encLeftCount); Serial.print(",");
      Serial.print(encRightCount);Serial.print(",");
      Serial.print(swRState);     Serial.print(",");
      Serial.println(swLState);
    }
  }
}

// =====================================================
// HÀM HỖ TRỢ ĐIỀU KHIỂN
// =====================================================
void updateMotor(int id, int value) {
  if (id < 1 || id > 2 || value == currentMotorSpeed[id]) return; 
  int speed = abs(constrain(value, -255, 255));
  
  if (id == 1) { // Bánh Trái
    analogWrite(ENA, speed); 
    digitalWrite(IN1, value > 0); digitalWrite(IN2, value < 0);
  } else if (id == 2) { // Bánh Phải
    analogWrite(ENB, speed); 
    digitalWrite(IN3, value > 0); digitalWrite(IN4, value < 0);
  }
  currentMotorSpeed[id] = value;
}

void processCommand(char* cmd) {
  char type; int val1, val2;
  // Format lệnh: "D:motor1:motor2" hoặc "S:kênh:xung"
  if (sscanf(cmd, "%c:%d:%d", &type, &val1, &val2) != 3) return;
    
  if (type == 'D') {
    updateMotor(1, val1);
    updateMotor(2, val2);
  }
  else if (type == 'S') {
    if (val1 < 0 || val1 > 15 || val2 == currentServoPulse[val1]) return; 
    digitalWrite(OE_PIN, LOW); // Mở khóa PCA9685
    int pulse = constrain(val2, 0, 4095);
    pwm.setPWM(val1, 0, pulse);
    currentServoPulse[val1] = pulse; 
  } 
}