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
# CẤU HÌNH HỆ THỐNG
# ==========================================
ESP_PORT = 8080         
DROIDCAM_PORT = 4747    
WS_PORT = 8765          
HTTP_PORT = 5000        

# Biến trạng thái toàn cục
ESP_IP = None
droidcam_ip = None
esp_socket = None
connected_websockets = set()
main_loop = None

# ==========================================
# HÀM QUÉT RADAR
# ==========================================
def check_port(ip, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(0.2)
    result = sock.connect_ex((ip, port))
    sock.close()
    return ip if result == 0 else None

def scan_network(port):
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
    with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
        futures = [executor.submit(check_port, ip, port) for ip in ips]
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res:
                found_ip = res
                break
    return found_ip

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
        esp_socket.settimeout(None)
        print("[+] ĐÃ KẾT NỐI ROBOT THÀNH CÔNG!")
        return True
    except:
        esp_socket = None
        print(f"[-] Không thể kết nối tới Robot tại {ip}")
        return False

def esp_receive_task():
    global esp_socket, main_loop
    while True:
        if esp_socket and main_loop:
            try:
                data = esp_socket.recv(1024)
                if data:
                    msg = json.dumps({
                        "type": "esp_data", 
                        "data": data.decode('utf-8', errors='ignore')
                    })
                    for ws in list(connected_websockets):
                        asyncio.run_coroutine_threadsafe(ws.send(msg), main_loop)
                else:
                    print("[-] ESP ngắt kết nối.")
                    esp_socket.close()
                    esp_socket = None
            except Exception:
                if esp_socket: esp_socket.close()
                esp_socket = None
        else:
            time.sleep(1)

# ==========================================
# WEBSOCKET HANDLER 
# ==========================================
async def bridge_handler(websocket, *args, **kwargs):
    global esp_socket, connected_websockets, droidcam_ip
    print(f"\n[+] Giao diện Web đã kết nối vào luồng điều khiển!")
    connected_websockets.add(websocket)
    
    try:
        if droidcam_ip:
            await websocket.send(json.dumps({"type": "droidcam", "ip": droidcam_ip}))

        async for message in websocket:
            if esp_socket:
                try:
                    esp_socket.sendall((message + '\n').encode('utf-8'))
                except:
                    print("[-] Mất kết nối TCP với Robot.")
                    esp_socket = None
    except websockets.exceptions.ConnectionClosed:
        pass
    except Exception as e:
        print(f"[-] Lỗi WebSocket: {e}")
    finally:
        if websocket in connected_websockets:
            connected_websockets.remove(websocket)
        print("[-] Giao diện Web đã ngắt kết nối.")

async def start_ws_server():
    global main_loop
    main_loop = asyncio.get_running_loop()
    print(f"[*] Khởi tạo WebSocket Bridge trên cổng {WS_PORT}...")
    async with websockets.serve(bridge_handler, "0.0.0.0", WS_PORT):
        await asyncio.Future()

# ==========================================
# HTTP SERVER 
# ==========================================
def start_http_server():
    # Lấy đường dẫn tuyệt đối của thư mục chứa script (tools/)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Lùi ra ngoài 1 cấp và chui vào thư mục frontend
    target_dir = os.path.abspath(os.path.join(current_dir, '..', 'frontend'))
    
    if not os.path.exists(target_dir):
        print(f"[-] CẢNH BÁO: Không tìm thấy thư mục frontend tại: {target_dir}")
        return

    # ÉP SERVER CHẠY TỪ GỐC FRONTEND
    os.chdir(target_dir)

    class NoCacheHandler(SimpleHTTPRequestHandler):
        def end_headers(self):
            self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Expires', '0')
            super().end_headers()

    try:
        httpd = HTTPServer(("0.0.0.0", HTTP_PORT), NoCacheHandler)
        print(f"[*] Dashboard Web Server: http://localhost:{HTTP_PORT}/templates/index.html")
        httpd.serve_forever()
    except Exception as e:
        print(f"[-] Lỗi HTTP Server: {e}")

def discovery_task():
    global droidcam_ip, ESP_IP, esp_socket, main_loop
    while True:
        if not esp_socket:
            print("[*] Radar: Đang quét tìm ESP...")
            found_esp = scan_network(ESP_PORT)
            if found_esp:
                ESP_IP = found_esp
                connect_to_esp(ESP_IP)
        
        if not droidcam_ip:
            print("[*] Radar: Đang quét tìm DroidCam...")
            found_cam = scan_network(DROIDCAM_PORT)
            if found_cam:
                droidcam_ip = found_cam
                print(f"[+] Tìm thấy DroidCam tại: {droidcam_ip}")
                if main_loop:
                    msg = json.dumps({"type": "droidcam", "ip": droidcam_ip})
                    for ws in list(connected_websockets):
                        asyncio.run_coroutine_threadsafe(ws.send(msg), main_loop)

        if esp_socket and droidcam_ip: break
        time.sleep(10)

def open_browser():
    time.sleep(1.5) # Đợi HTTP Server chạy xong
    # Mở đúng file index.html nằm trong templates
    url = f"http://localhost:{HTTP_PORT}/templates/index.html"
    print(f"[*] Đang tự động mở trình duyệt: {url}")
    webbrowser.open(url)

if __name__ == "__main__":
    threading.Thread(target=discovery_task, daemon=True).start()
    threading.Thread(target=esp_receive_task, daemon=True).start()
    threading.Thread(target=start_http_server, daemon=True).start()
    threading.Thread(target=open_browser, daemon=True).start()
    
    try:
        asyncio.run(start_ws_server())
    except KeyboardInterrupt:   
        print("\n[*] Đang dừng hệ thống...")
        if esp_socket: esp_socket.close()