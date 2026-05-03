import cv2
import os
import zipfile
import io
from flask import Flask, render_template, request, send_file

app = Flask(__name__)

# Thư mục tạm để xử lý
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process():
    file = request.files['video']
    interval = int(request.form.get('interval', 10))
    
    if not file:
        return "Bạn chưa chọn file!"

    # Lưu video tạm
    video_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(video_path)
    
    cap = cv2.VideoCapture(video_path)
    count = 0
    saved = 0
    
    # Tạo một file Zip trong bộ nhớ (memory) để người dùng tải về ngay
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w') as zf:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            if count % interval == 0:
                # Mã hóa ảnh sang dạng .jpg trong bộ nhớ
                _, img_encoded = cv2.imencode('.jpg', frame)
                # Ghi ảnh trực tiếp vào file zip
                zf.writestr(f"frame_{saved:05d}.jpg", img_encoded.tobytes())
                saved += 1
            count += 1
            
    cap.release()
    os.remove(video_path) # Xóa video sau khi tách để nhẹ máy
    
    memory_file.seek(0)
    
    return send_file(
        memory_file,
        mimetype='application/zip',
        as_attachment=True,
        download_name='frames_for_ai.zip'
    )

if __name__ == '__main__':
    app.run(debug=True, port=5000)