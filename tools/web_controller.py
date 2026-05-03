import asyncio
import socket
import websockets
import os
from http.server import SimpleHTTPRequestHandler, HTTPServer
import threading
import webbrowser
import time
import json
import concurrent.futures

# ==========================================
# 1. CẤU HÌNH HỆ THỐNG
# ==========================================
ESP_PORT = 8080         
DROIDCAM_PORT = 4747    
WS_PORT = 8765          
HTTP_PORT = 5000        

# Các biến trạng thái toàn cục
ESP_IP = None
droidcam_ip = None
esp_socket = None
connected_websockets = set()
main_loop = None  # Cần biến này để các luồng (thread) phụ có thể gọi lệnh tới asyncio

# ==========================================
# 2. HÀM QUÉT RADAR MẠNG NỘI BỘ
# ==========================================
def check_port(ip, port):
    """Kiểm tra một IP có đang mở cổng cụ thể hay không"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(0.2) # Timeout rất nhanh để quét dải rộng
    result = sock.connect_ex((ip, port))
    sock.close()
    return ip if result == 0 else None

def scan_network(port):
    """Quét toàn bộ dải mạng LAN để tìm thiết bị"""
    # Lấy IP của máy tính hiện tại để suy ra dải mạng
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        local_ip = s.getsockname()[0]
    except:
        local_ip = '127.0.0.1'
    finally:
        s.close()
    
    subnet = '.'.join(local_ip.split('.')[:-1])
    ips = [f"{subnet}.{i}" for i in range(1, 255)]
    
    found_ip = None
    # Sử dụng đa luồng (100 workers) để quét cực nhanh
    with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
        futures = [executor.submit(check_port, ip, port) for ip in ips]
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res:
                found_ip = res
                break # Dừng ngay khi tìm thấy thiết bị đầu tiên
    return found_ip

# ==========================================
# 3. KẾT NỐI TCP TỚI ROBOT (ESP)
# ==========================================
def connect_to_esp(ip):
    global esp_socket
    if esp_socket:
        try: esp_socket.close()
        except: pass
            
    print(f"[*] Đang kết nối Robot tại {ip}...")
    try:
        esp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        esp_socket.settimeout(3)
        esp_socket.connect((ip, ESP_PORT))
        esp_socket.settimeout(None) # Đưa về dạng blocking để luồng nhận dữ liệu hoạt động
        print("[+] ĐÃ KẾT NỐI ROBOT THÀNH CÔNG!")
        return True
    except:
        esp_socket = None
        print(f"[-] Không thể kết nối tới Robot tại {ip}")
        return False

# ==========================================
# 3.1. LUỒNG LẮNG NGHE DỮ LIỆU TỪ ROBOT (CHIỀU VỀ)
# ==========================================
def esp_receive_task():
    """Luồng liên tục đọc phản hồi từ ESP và đẩy lên Web"""
    global esp_socket, main_loop
    while True:
        if esp_socket and main_loop:
            try:
                # Đọc tối đa 1024 byte mỗi lần
                data = esp_socket.recv(1024)
                if data:
                    # Gói dữ liệu lại và ném lên toàn bộ giao diện Web
                    msg = json.dumps({
                        "type": "esp_data", 
                        "data": data.decode('utf-8', errors='ignore')
                    })
                    for ws in list(connected_websockets):
                        asyncio.run_coroutine_threadsafe(ws.send(msg), main_loop)
                else:
                    # Mất kết nối
                    print("[-] ESP ngắt kết nối.")
                    esp_socket.close()
                    esp_socket = None
            except Exception as e:
                if esp_socket:
                    esp_socket.close()
                esp_socket = None
        else:
            time.sleep(1) # Nghỉ ngơi nếu chưa kết nối ESP

# ==========================================
# 4. WEBSOCKET HANDLER (GIAO TIẾP VỚI WEB)
# ==========================================
async def bridge_handler(websocket):
    global esp_socket, connected_websockets, droidcam_ip
    connected_websockets.add(websocket)
    
    # Khi một trang web mới mở ra, gửi ngay IP DroidCam nếu đã tìm thấy
    if droidcam_ip:
        await websocket.send(json.dumps({"type": "droidcam", "ip": droidcam_ip}))

    try:
        async for message in websocket:
            # Chuyển tiếp lệnh điều khiển từ trình duyệt xuống Robot
            if esp_socket:
                try:
                    esp_socket.sendall((message + '\n').encode('utf-8'))
                except:
                    print("[-] Mất kết nối TCP với Robot.")
                    esp_socket = None
            else:
                pass # Đợi Radar tìm lại kết nối
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        if websocket in connected_websockets:
            connected_websockets.remove(websocket)

async def start_ws_server():
    global main_loop
    main_loop = asyncio.get_running_loop() # Lưu lại Loop chính cho các luồng phụ
    print(f"[*] Khởi tạo WebSocket Bridge trên cổng {WS_PORT}...")
    async with websockets.serve(bridge_handler, "0.0.0.0", WS_PORT):
        await asyncio.Future()

# ==========================================
# 5. HTTP SERVER (PHỤC VỤ FILE GIAO DIỆN)
# ==========================================
def start_http_server():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Trỏ đúng vào thư mục giao diện của đại ca
    target_dir = os.path.abspath(os.path.join(current_dir, '..', 'frontend', 'templates'))
    
    if not os.path.exists(target_dir):
        print(f"[-] CẢNH BÁO: Không tìm thấy thư mục frontend tại {target_dir}")
        return

    class MyHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=target_dir, **kwargs)

    try:
        httpd = HTTPServer(("0.0.0.0", HTTP_PORT), MyHandler)
        print(f"[*] Dashboard Web Server: http://localhost:{HTTP_PORT}")
        httpd.serve_forever()
    except Exception as e:
        print(f"[-] Lỗi HTTP Server: {e}")

# ==========================================
# 6. TIẾN TRÌNH TỰ ĐỘNG TÌM KIẾM (DISCOVERY)
# ==========================================
def discovery_task():
    global droidcam_ip, ESP_IP, esp_socket, main_loop
    
    while True:
        # 1. Tìm kiếm Robot
        if not esp_socket:
            print("[*] Radar: Đang quét tìm Robot (ESP)...")
            found_esp = scan_network(ESP_PORT)
            if found_esp:
                ESP_IP = found_esp
                connect_to_esp(ESP_IP)
        
        # 2. Tìm kiếm Camera (DroidCam)
        if not droidcam_ip:
            print("[*] Radar: Đang quét tìm DroidCam...")
            found_cam = scan_network(DROIDCAM_PORT)
            if found_cam:
                droidcam_ip = found_cam
                print(f"[+] Tìm thấy DroidCam tại IP: {droidcam_ip}")
                
                # Thông báo cho tất cả các tab web đang mở để hiện Video
                if main_loop:
                    msg = json.dumps({"type": "droidcam", "ip": droidcam_ip})
                    for ws in list(connected_websockets):
                        # GỌI ĐÚNG LOOP CHÍNH ĐỂ TRÁNH CRASH ĐA LUỒNG
                        asyncio.run_coroutine_threadsafe(ws.send(msg), main_loop)

        # Nghỉ một lúc rồi quét lại nếu vẫn thiếu thiết bị
        if esp_socket and droidcam_ip:
            break # Tìm thấy đủ rồi thì dừng quét để tiết kiệm băng thông
        time.sleep(10)

# ==========================================
# KHỞI CHẠY
# ==========================================
if __name__ == "__main__":
    # Chạy Radar quét mạng trong luồng riêng
    threading.Thread(target=discovery_task, daemon=True).start()
    
    # Chạy luồng lắng nghe dữ liệu trả về từ ESP
    threading.Thread(target=esp_receive_task, daemon=True).start()
    
    # Chạy Web Server phục vụ file tĩnh
    threading.Thread(target=start_http_server, daemon=True).start()
    
    # Tự động mở trình duyệt
    threading.Timer(2, lambda: webbrowser.open(f"http://localhost:{HTTP_PORT}/index.html")).start()
    
    # Chạy WebSocket Server chính (Blocking loop)
    try:
        asyncio.run(start_ws_server())
    except KeyboardInterrupt:
        print("\n[*] Đang dừng hệ thống...")
        if esp_socket: esp_socket.close()