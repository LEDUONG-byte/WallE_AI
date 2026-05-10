import os
import re
import urllib.request

# ==========================================
# CẤU HÌNH ĐƯỜNG DẪN THEO CHUẨN CỦA ĐẠI CA
# ==========================================
HTML_PATH = 'frontend/templates/index.html'
STATIC_DIR = 'frontend/static'

os.makedirs(STATIC_DIR, exist_ok=True)

with open(HTML_PATH, 'r', encoding='utf-8') as f:
    html = f.read()

# Quét toàn bộ link CDN (http/https) trong thẻ src hoặc href
links = re.findall(r'(?:src|href)="([^"]*?//[^"]+)"', html)

for url in set(links): 
    filename = url.split('/')[-1].split('?')[0]
    
    # Lọc: Chỉ hút các file tài nguyên giao diện
    if not filename.endswith(('.js', '.css', '.png', '.jpg', '.woff', '.woff2', '.ttf')):
        continue

    local_path = os.path.join(STATIC_DIR, filename)
    
    print(f"[*] Đang kéo tài nguyên: {filename}...")
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as resp, open(local_path, 'wb') as out:
            out.write(resp.read())
        
        # Tráo link mạng thành link nội bộ chuẩn Flask/Local
        # Flask sẽ tự động map đường dẫn /static/ vào thư mục frontend/static/
        html = html.replace(url, f"/static/{filename}")
    except Exception as e:
        print(f"[X] Bỏ qua {url} (Lỗi: {e})")

# Ghi đè trực tiếp lên file index.html gốc để dùng luôn (nhớ backup trước nếu cần)
with open(HTML_PATH, 'w', encoding='utf-8') as f:
    f.write(html)

print("\n[+] ĐÃ XONG! Toàn bộ thư viện đã được gom vào thư mục 'frontend/static'.")
print("[+] Các link mạng trong 'index.html' đã được chuyển thành Local.")