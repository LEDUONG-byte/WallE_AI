import cv2
import numpy as np
import os
import socket
import concurrent.futures

# ==========================================
# CẤU HÌNH HỆ THỐNG
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
    sock.settimeout(0.2)
    result = sock.connect_ex((ip, port))
    sock.close()
    return ip if result == 0 else None

def scan_droidcam():
    local_ip = get_local_ip()
    subnet = '.'.join(local_ip.split('.')[:-1])
    
    print(f"[*] IP Laptop của bạn: {local_ip}")
    print(f"[*] Đang quét tìm DroidCam (Port 4747) trong dải {subnet}.x ...")
    
    found_ip = None
    ips_to_scan = [f"{subnet}.{i}" for i in range(1, 255)]
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
        futures = [executor.submit(check_port, ip, 4747) for ip in ips_to_scan]
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res:
                found_ip = res
                executor.shutdown(wait=False, cancel_futures=True)
                break
                
    return found_ip

def angle_cos(p0, p1, p2):
    """Tính cosin của góc tạo bởi 3 điểm (kiểm tra góc vuông)"""
    d1, d2 = (p0 - p1).astype('float'), (p2 - p1).astype('float')
    return abs(np.dot(d1, d2) / np.sqrt(np.dot(d1, d1) * np.dot(d2, d2)))

def get_color_mask(hsv_frame, color_name):
    """Tạo mask lọc 4 màu HSV cơ bản"""
    mask = None
    if color_name == "red":
        lower1 = np.array([0, 120, 70])
        upper1 = np.array([10, 255, 255])
        lower2 = np.array([170, 120, 70])
        upper2 = np.array([180, 255, 255])
        mask1 = cv2.inRange(hsv_frame, lower1, upper1)
        mask2 = cv2.inRange(hsv_frame, lower2, upper2)
        mask = mask1 + mask2
    elif color_name == "blue":
        lower = np.array([100, 150, 0])
        upper = np.array([140, 255, 255])
        mask = cv2.inRange(hsv_frame, lower, upper)
    elif color_name == "green":
        lower = np.array([35, 50, 50])
        upper = np.array([85, 255, 255])
        mask = cv2.inRange(hsv_frame, lower, upper)
    elif color_name == "yellow":
        lower = np.array([20, 100, 100])
        upper = np.array([30, 255, 255])
        mask = cv2.inRange(hsv_frame, lower, upper)
        
    if mask is not None:
        # Khử nhiễu hình thái học để lấp đầy các đốm sáng/tối trên bề mặt hộp
        kernel = np.ones((5,5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel) 
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        
    return mask

def detect_colored_boxes(frame):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    
    # Danh sách 4 khối hộp cần tìm
    colors_to_detect = {
        "RED Box": {"mask": get_color_mask(hsv, "red"), "color_bgr": (0, 0, 255)},
        "BLUE Box": {"mask": get_color_mask(hsv, "blue"), "color_bgr": (255, 0, 0)},
        "GREEN Box": {"mask": get_color_mask(hsv, "green"), "color_bgr": (0, 255, 0)},
        "YELLOW Box": {"mask": get_color_mask(hsv, "yellow"), "color_bgr": (0, 255, 255)}
    }

    for label, data in colors_to_detect.items():
        mask = data["mask"]
        if mask is None: continue
        color_bgr = data["color_bgr"]
        
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > 2000:  # Diện tích phải đủ lớn
                peri = cv2.arcLength(cnt, True)
                approx = cv2.approxPolyDP(cnt, 0.04 * peri, True)
                
                # Điều kiện 1: Phải có 4 đỉnh
                if len(approx) == 4:
                    x, y, w, h = cv2.boundingRect(approx)
                    
                    # Điều kiện 2: Độ đặc (Extent) > 75%
                    extent = float(area) / (w * h)
                    if extent > 0.75:
                        
                        # Điều kiện 3: Các góc xấp xỉ 90 độ
                        approx = approx.reshape(-1, 2)
                        max_cos = np.max([angle_cos(approx[i], approx[(i+1) % 4], approx[(i+2) % 4]) for i in range(4)])
                        if max_cos < 0.3:
                            
                            # Điều kiện 4: Tỷ lệ Aspect Ratio nới lỏng cho Hình Hộp Chữ Nhật
                            # Dao động từ 0.4 (hộp cao gầy) đến 2.5 (hộp thấp bè)
                            aspect_ratio = float(w) / h
                            if 0.4 <= aspect_ratio <= 2.5: 
                                
                                # Vẽ Bounding Box và Gắn nhãn
                                cv2.rectangle(frame, (x, y), (x + w, y + h), color_bgr, 3)
                                
                                # Vẽ background cho chữ dễ đọc hơn
                                text_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
                                cv2.rectangle(frame, (x, y - text_size[1] - 10), (x + text_size[0], y), color_bgr, -1)
                                cv2.putText(frame, label, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                                
                                # Vẽ điểm trung tâm (để tính toán điều hướng sau này)
                                cv2.circle(frame, (x + w//2, y + h//2), 5, (255, 255, 255), -1)

    return frame

if __name__ == "__main__":
    print("="*50)
    print("  TRẠM AI NHẬN DIỆN 4 KHỐI HỘP MÀU (OPENCV)  ")
    print("="*50)

    DROIDCAM_IP = scan_droidcam()
    if not DROIDCAM_IP:
        DROIDCAM_IP = input("Nhập IP DroidCam: ").strip()
            
    URL = f"http://{DROIDCAM_IP}:4747/video"
    print(f"[*] Đang kết nối tới DroidCam tại {URL}...")
    cap = cv2.VideoCapture(URL)
    
    if not cap.isOpened():
        print("[-] LỖI: Không thể mở luồng DroidCam.")
        exit()

    print("[+] KẾT NỐI THÀNH CÔNG! Đưa các khối hộp màu vào khung hình.")
    
    while True:
        ret, frame = cap.read()
        if not ret: break
        
        processed_frame = detect_colored_boxes(frame.copy())
        cv2.imshow("Wall-E Color Box Tracker", processed_frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()