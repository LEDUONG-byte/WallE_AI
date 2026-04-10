import time
import math
import socket

# Cấu hình "Ống nước"
ESP_IP = "192.168.1.xxx"  # Đại ca điền IP của con ESP vào đây nhé
ESP_PORT = 8080           # Khớp với cổng 8080 trên code ESP

print(f"[+] Đang kéo ống TCP tới Wall-E tại {ESP_IP}:{ESP_PORT}...")
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((ESP_IP, ESP_PORT))
print("[+] Đã thông ống! Sẵn sàng xả lũ.")

def send_command(cmd):
    """Hàm bơm 1 lệnh thẳng xuống ESP không độ trễ"""
    try:
        # BẮT BUỘC phải cộng thêm '\n' để con Arduino biết chỗ ngắt câu
        # Lệnh encode('utf-8') để dịch chữ sang mã nhị phân truyền qua cáp
        sock.sendall((cmd + '\n').encode('utf-8'))
    except Exception as e:
        print(f"[-] Rớt mạng: {e}")

# ==========================================
# THUẬT TOÁN LÀM MƯỢT (EASING) TRÊN MÁY CHỦ
# ==========================================
def ease_in_out(t):
    """Đường cong gia tốc (0.0 -> 1.0)"""
    return (1 - math.cos(t * math.pi)) / 2

def move_servo_smooth(channel, start_angle, target_angle, duration_sec, fps=60):
    """
    Giờ chạy TCP rồi, đại ca tha hồ đẩy fps lên 60 khung hình/giây
    Wall-E sẽ mượt như bôi mỡ cá tra!
    """
    total_frames = int(duration_sec * fps)
    sleep_time = 1.0 / fps

    for frame in range(total_frames + 1):
        t = frame / total_frames
        ease_factor = ease_in_out(t)
        
        current_angle = int(start_angle + (target_angle - start_angle) * ease_factor)
        
        # Đóng gói và bơm!
        cmd = f"S:{channel}:{current_angle}"
        send_command(cmd)
        
        time.sleep(sleep_time)

# ==========================================
# KHU VỰC TEST THỰC TẾ
# ==========================================
if __name__ == "__main__":
    try:
        print("Test 1: Quay đầu mượt từ 0 lên 120 độ trong 1.5 giây")
        move_servo_smooth(channel=4, start_angle=0, target_angle=120, duration_sec=1.5, fps=60)
        
        time.sleep(1) # Nghỉ 1 giây
        
        print("Test 2: Quay từ từ về lại 0 độ")
        move_servo_smooth(channel=4, start_angle=120, target_angle=0, duration_sec=2.0, fps=60)
        
        # Test gọi lệnh Motor xen kẽ cực nhanh
        print("Test 3: Tiến lên rồi dừng khẩn cấp")
        send_command("M:1:200")  # Bánh trái tiến
        send_command("M:2:200")  # Bánh phải tiến
        time.sleep(1)
        send_command("M:1:0")    # Phanh
        send_command("M:2:0")    # Phanh
        
    except KeyboardInterrupt:
        print("\n[+] Đóng ống nước. Kết thúc test.")
    finally:
        sock.close()