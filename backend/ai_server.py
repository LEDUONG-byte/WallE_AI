import cv2
from ultralytics import YOLO
import os
import socket
import concurrent.futures
import time
import torch

# ==========================================
# HÀM QUÉT DROIDCAM
# ==========================================
def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

def check_port(ip, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(0.1)
    result = sock.connect_ex((ip, port))
    sock.close()
    return ip if result == 0 else None

def scan_droidcam():
    local_ip = get_local_ip()
    subnet = '.'.join(local_ip.split('.')[:-1])
    ips_to_scan = [f"{subnet}.{i}" for i in range(1, 255)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
        futures = [executor.submit(check_port, ip, 4747) for ip in ips_to_scan]
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res: return res
    return None

if __name__ == "__main__":
    print("[*] Đang khởi động trạm AI với bộ não v2...")

    # 1. NẠP MÔ HÌNH MỚI (Trỏ thẳng vào walle_v2)
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # Đã trỏ vào thư mục walle_v2 như đại ca yêu cầu
        model_path = os.path.join(current_dir, '..', 'runs', 'detect', 'walle_v2', 'weights', 'best.pt')
        
        # Nếu đại ca chưa train xong v2 thì nó sẽ báo lỗi, lúc đó hãy check lại thư mục runs
        model = YOLO(model_path)
        model.to(device)
        print(f"[+] Đã nạp thành công não v2 tại: {model_path}")
    except Exception as e:
        print(f"[-] Lỗi nạp não v2: {e}")
        print("[*] Gợi ý: Kiểm tra xem đã chạy file train_wall_e.py xong chưa.")
        exit()

    # 2. KẾT NỐI CAMERA
    cam_ip = scan_droidcam()
    if not cam_ip:
        cam_ip = input("Nhập IP DroidCam: ").strip()
    
    URL = f"http://{cam_ip}:4747/video"
    cap = cv2.VideoCapture(URL)
    
    # Chỉ giữ lại 1 thiết lập đệm cơ bản nhất
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    print("[+] ĐANG CHẠY CHẾ ĐỘ ĐƠN GIẢN (MƯỢT). NHẤN 'Q' ĐỂ THOÁT.")
    
    prev_time = time.time()

    while True:
        ret, frame = cap.read()
        if not ret: break
        
        # 3. CHẠY AI (Giữ imgsz=640 để nhận diện cho ác như đại ca muốn)
        results = model(frame, conf=0.5, verbose=False, device=device, imgsz=640)
        
        # 4. HIỂN THỊ
        annotated_frame = results[0].plot()
        
        curr_time = time.time()
        fps = 1 / (curr_time - prev_time) if (curr_time - prev_time) > 0 else 0
        prev_time = curr_time
        
        cv2.putText(annotated_frame, f"FPS: {int(fps)} | Model: v2", (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        
        cv2.imshow("Wall-E AI Standalone", annotated_frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()