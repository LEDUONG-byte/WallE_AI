import os
import yaml
from roboflow import Roboflow
from ultralytics import YOLO
import torch

if __name__ == '__main__':
    print("="*50)
    print("   🚀 KHỞI ĐỘNG LÒ LUYỆN AI v2 CHO WALL-E 🚀   ")
    print("="*50)



    # 1. TẢI DỮ LIỆU MỚI TỪ ROBOFLOW (walleboxdefine v2)
    print("[*] Đang tải Dataset 'walleboxdefine' phiên bản 2...")
    try:
        rf = Roboflow(api_key="DVSIWgM5nVaN1ekVbWpO")
        project = rf.workspace("capcha-ml54g").project("walle-rvfdr")
        version = project.version(1)
        dataset = version.download("yolov8")                    
        print(f"[+] Tải xong! Dữ liệu nằm tại: {dataset.location}")
    except Exception as e:
        print(f"[-] Lỗi khi tải dữ liệu từ Roboflow: {e}")
        exit()

    # ==========================================
    # VÁ LỖI CẤU TRÚC THƯ MỤC (NẾU CẦN)
    # ==========================================
    yaml_path = os.path.join(dataset.location, "data.yaml")
    if os.path.exists(yaml_path):
        with open(yaml_path, 'r', encoding='utf8') as f:
            data_yaml = yaml.safe_load(f)

        # Ép đường dẫn tuyệt đối để tránh lỗi FileNotFoundError
        train_path = os.path.join(dataset.location, "train", "images")
        val_path = os.path.join(dataset.location, "valid", "images")

        data_yaml['train'] = train_path
        
        # Kiểm tra thư mục valid, nếu không có thì dùng tạm thư mục train để không bị crash
        if os.path.exists(val_path):
            data_yaml['val'] = val_path
        else:
            print("[*] Chế độ vá lỗi: Không thấy thư mục valid, dùng tạm thư mục train để kiểm tra...")
            data_yaml['val'] = train_path

        with open(yaml_path, 'w', encoding='utf8') as f:
            yaml.dump(data_yaml, f)
    else:
        print("[-] CẢNH BÁO: Không tìm thấy file data.yaml!")

    # 2. KIỂM TRA PHẦN CỨNG (Sử dụng RTX 3050)
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"\n[*] Thiết bị huấn luyện: [{device.upper()}]")

    # 3. NẠP MÔ HÌNH VÀ TRAINING
    # Sử dụng yolov8n.pt (Nano) làm gốc để đạt tốc độ cao nhất
    model = YOLO("yolov8n.pt")

    print("\n[*] Đang tiến hành huấn luyện 50 Epochs...")
    
    results = model.train(
        data=yaml_path,
        epochs=50,          
        imgsz=512,          # Giữ 512 để học chi tiết tốt nhất
        batch=16,           # RTX 3050 (4GB) có thể chịu được batch 16 cho bản Nano
        device=device,      
        name='walle_v2',    # Đặt tên mới để dễ phân biệt (Sẽ lưu vào walle_v2)
        plots=True,
        amp=True            # Kích hoạt Automatic Mixed Precision để nhanh hơn trên RTX
    )

    print("\n" + "="*50)
    print(" 🎉 HUẤN LUYỆN HOÀN TẤT! 🎉 ")
    print(" - File bộ não mới của đại ca nằm tại:")
    print("   runs/detect/walle_v2/weights/best.pt")
    print("="*50)