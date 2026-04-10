import socket
import sys
import concurrent.futures
import time
import math

ESP_PORT = 8080

def get_local_ip():
    """Tìm IP của máy tính (laptop) hiện tại để suy ra dải mạng"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

def scan_ip(ip):
    """Gõ cửa từng IP với timeout 1 giây để đảm bảo không bị rớt gói"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1.0) 
    try:
        sock.connect((ip, ESP_PORT))
        return ip
    except:
        return None
    finally:
        sock.close()

def auto_discover_walle():
    """Radar quét mạng LAN với kỹ thuật ThreadPool chống nghẽn"""
    local_ip = get_local_ip()
    subnet = '.'.join(local_ip.split('.')[:-1])
    
    print(f"[*] IP Laptop của đại ca: {local_ip}")
    print(f"[*] Đang quét chậm và chắc dải {subnet}.x (Chống nghẽn Router)...")
    
    found_ip = None
    ips_to_scan = [f"{subnet}.{i}" for i in range(1, 255) if f"{subnet}.{i}" != local_ip]
    
    # Chỉ cho phép 50 luồng chạy cùng lúc để Router khỏi bị ngợp
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        results = executor.map(scan_ip, ips_to_scan)
        for res in results:
            if res:
                found_ip = res
                # Hủy các luồng còn lại ngay khi tìm thấy để tiết kiệm thời gian
                executor.shutdown(wait=False, cancel_futures=True)
                break
                
    return found_ip

# ==========================================
# HÀM MÚA (DƯỠNG SINH CHỐNG NGỢP ARDUINO)
# ==========================================
def ease_in_out(t):
    return (1 - math.cos(t * math.pi)) / 2

def move_sync_servos(sock, movements, duration_sec=2.0):
    fps = 10 
    total_frames = int(duration_sec * fps)

    for frame in range(total_frames + 1):
        t = frame / total_frames if total_frames > 0 else 1.0
        ease_factor = ease_in_out(t)
        
        for channel, (start_angle, target_angle) in movements.items():
            current_angle = int(start_angle + (target_angle - start_angle) * ease_factor)
            cmd = f"S:{channel}:{current_angle}\n"
            
            try:
                sock.sendall(cmd.encode('utf-8'))
            except Exception as e:
                print(f"[-] Rớt mạng: {e}")
                return 
                
            # Bắt buộc nghỉ 20ms sau mỗi lệnh để Arduino kịp xử lý I2C
            time.sleep(0.02) 

def run_dance_routine(sock):
    print("\n[+] Wall-E đang biểu diễn...")
    
    print("   -> 1. Đưa tất cả về 90 độ")
    move_sync_servos(sock, {
        0: (0, 90), 1: (0, 90), 2: (0, 90), 3: (0, 90), 4: (0, 90)  
    }, duration_sec=1.5)
    time.sleep(0.5)

    print("   -> 2. Giơ tay, trợn mắt (Lên 180)")
    move_sync_servos(sock, {
        0: (90, 120), 1: (90, 180), 2: (90, 180), 3: (90, 180), 4: (90, 180)  
    }, duration_sec=1.5)
    time.sleep(0.5)

    print("   -> 3. Cụp tay, nhắm mắt buồn bã (Về 0)")
    move_sync_servos(sock, {
        0: (120, 45), 1: (180, 0), 2: (180, 0), 3: (180, 0), 4: (180, 0)   
    }, duration_sec=2.0)
    
    print("[+] Hoàn thành màn biểu diễn!\n")

# ==========================================
# CHƯƠNG TRÌNH CHÍNH - TEST LỆNH THỦ CÔNG
# ==========================================
if __name__ == "__main__":
    print("="*50)
    print(" HỆ THỐNG TEST WALL-E BẰNG LỆNH & DÒ TÌM TỰ ĐỘNG ")
    print("="*50)
    
    # Lựa chọn nhanh cho đại ca
    choice = input("Đại ca muốn quét tự động (Enter) hay nhập tay IP (Nhập IP)? [Enter/IP]: ").strip()
    
    if choice == "":
        ESP_IP = auto_discover_walle()
        if not ESP_IP:
            print("[-] Quét xong nhưng không thấy! Đại ca thử nhập tay IP xem sao.")
            sys.exit()
        print(f"[+] TÌM THẤY! Wall-E đang nấp ở IP: {ESP_IP}")
    else:
        ESP_IP = choice
        print(f"[*] Bypass Radar. Bắt thẳng vào IP: {ESP_IP}")

    # Bắt đầu quá trình kết nối điều khiển
    try:
        print(f"[+] Đang kéo cáp TCP tới {ESP_IP}:{ESP_PORT}...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # Tắt Nagle's Algorithm để truyền đi ngay lập tức khi đại ca gõ lệnh
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        sock.settimeout(3.0) # Cho 3 giây để thực hiện kết nối
        sock.connect((ESP_IP, ESP_PORT))
        sock.settimeout(None) # Kết nối xong thì bỏ timeout để giữ phiên
        
        print("[+] KẾT NỐI THÀNH CÔNG! ĐÃ CÓ THỂ ĐIỀU KHIỂN.")
        print("-" * 50)
        print("Gợi ý lệnh:")
        print("  - S:kênh:góc   (vd: S:0:90 quay servo 0 góc 90 độ)")
        print("  - M:bánh:tốc   (vd: M:1:255 tiến bánh trái, M:2:-255 lùi bánh phải, M:1:0 phanh)")
        print("  - dance        (Để xem Wall-E múa tự động)")
        print("  - Gõ 'q' để thoát")
        print("-" * 50)

        while True:
            cmd = input("Wall-E > Nhập lệnh: ")
            
            if cmd.lower() == 'q':
                break
                
            if cmd.lower() == 'dance':
                run_dance_routine(sock)
                continue
                
            if cmd.strip() == "":
                continue

            # Nén lệnh và bơm đi
            sock.sendall((cmd + '\n').encode('utf-8'))
            print(f"  -> Đã bắn: {cmd}")

    except ConnectionRefusedError:
        print("[-] Bị từ chối. Mạng có thể chặn hoặc ESP chưa chạy code TCP.")
    except socket.timeout:
        print(f"[-] Không thể kết nối tới {ESP_IP}. Có thể sai IP hoặc mất mạng.")
    except Exception as e:
        print(f"[-] Đường truyền đứt gánh do lỗi: {e}")
    finally:
        try:
            sock.close()
            print("[*] Đã đóng kết nối mạng.")
        except:
            pass