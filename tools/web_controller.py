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

ESP_IP = None
droidcam_ip = None
esp_socket = None
connected_websockets = set()
main_loop = None

# ==========================================
# QUÉT RADAR IP 
# ==========================================
def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

def check_port(ip, port):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.2)
            if sock.connect_ex((ip, port)) == 0:
                return ip
    except:
        pass
    return None

def scan_network(port):
    local_ip = get_local_ip()
    if local_ip == '127.0.0.1': 
        return None
        
    prefix = '.'.join(local_ip.split('.')[:-1]) + '.'
    print(f"[*] Radar: Đang quét mạng {prefix}x tìm cổng {port}...")
    ips = [prefix + str(i) for i in range(1, 255)]
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
        for ip, result in zip(ips, executor.map(lambda x: check_port(x, port), ips)):
            if result:
                return result
    return None

# ==========================================
# GIAO TIẾP TCP (ROBOT) & WEBSOCKET (WEB)
# ==========================================
def connect_to_esp(ip):
    global esp_socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2.0)
        s.connect((ip, ESP_PORT))
        s.setblocking(False)
        esp_socket = s
        print(f"[+] Đã kết nối Robot tại: {ip}")
    except Exception as e:
        print(f"[-] Lỗi kết nối Robot: {e}")
        esp_socket = None

def esp_receive_task():
    global esp_socket, connected_websockets, main_loop
    while True:
        if esp_socket:
            try:
                data = esp_socket.recv(1024)
                if data:
                    if main_loop and main_loop.is_running():
                        msg = json.dumps({"type": "esp_data", "data": data.decode('utf-8', errors='ignore')})
                        for ws in list(connected_websockets):
                            asyncio.run_coroutine_threadsafe(ws.send(msg), main_loop)
                else:
                    esp_socket.close()
                    esp_socket = None
            except BlockingIOError:
                pass
            except Exception:
                if esp_socket: 
                    esp_socket.close()
                esp_socket = None
        time.sleep(0.01)

async def ws_handler(websocket):
    global esp_socket, connected_websockets, droidcam_ip
    connected_websockets.add(websocket)
    if droidcam_ip:
        await websocket.send(json.dumps({"type": "droidcam", "ip": droidcam_ip}))
    try:
        async for message in websocket:
            if esp_socket:
                try:
                    esp_socket.sendall((message + "\n").encode('utf-8'))
                except Exception:
                    pass
    except Exception:
        pass
    finally:
        connected_websockets.remove(websocket)

# ==========================================
# HTTP SERVER (SỬA LỖI TRẮNG TRANG MẠNG OFFLINE)
# ==========================================
def start_http_server():
    target_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'frontend'))
    if os.path.exists(target_dir):
        os.chdir(target_dir)

    class CustomHandler(SimpleHTTPRequestHandler):
        def end_headers(self):
            self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
            super().end_headers()
            
        def guess_type(self, path):
            if path.endswith(".js"): return "application/javascript"
            if path.endswith(".css"): return "text/css"
            return super().guess_type(path)

    try:
        httpd = HTTPServer(("0.0.0.0", HTTP_PORT), CustomHandler)
        print(f"[*] Web Server chạy tại: http://localhost:{HTTP_PORT}/templates/index.html")
        httpd.serve_forever()
    except Exception as e:
        print(f"[-] Lỗi HTTP: {e}")

def discovery_task():
    global droidcam_ip, ESP_IP, esp_socket
    while True:
        if not esp_socket:
            found = scan_network(ESP_PORT)
            if found: connect_to_esp(found)
        if not droidcam_ip:
            found_cam = scan_network(DROIDCAM_PORT)
            if found_cam:
                droidcam_ip = found_cam
                print(f"[+] Tìm thấy DroidCam tại: {droidcam_ip}")
        time.sleep(10)

# FIX LỖI ASYNCIO TRÊN PYTHON MỚI NHẤT
async def start_ws_server():
    global main_loop
    main_loop = asyncio.get_running_loop()
    print(f"[*] WebSocket Server chạy tại port {WS_PORT}")
    async with websockets.serve(ws_handler, "0.0.0.0", WS_PORT):
        await asyncio.Future()

def main():
    threading.Thread(target=discovery_task, daemon=True).start()
    threading.Thread(target=esp_receive_task, daemon=True).start()
    threading.Thread(target=start_http_server, daemon=True).start()
    
    time.sleep(1.5)
    webbrowser.open(f"http://localhost:{HTTP_PORT}/templates/index.html")
    
    try:
        asyncio.run(start_ws_server())
    except KeyboardInterrupt:
        if esp_socket: esp_socket.close()

if __name__ == "__main__":
    main()