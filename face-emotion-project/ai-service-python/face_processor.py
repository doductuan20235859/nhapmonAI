import cv2
import numpy as np

class FaceProcessor:
    def __init__(self):
        self.use_mediapipe = False
        try:
            import mediapipe as mp
            # Thử nghiệm truy cập API Solutions của MediaPipe
            self.mp_face_detection = mp.solutions.face_detection
            self.face_detection = self.mp_face_detection.FaceDetection(
                model_selection=0, # 0 cho khoảng cách gần (< 2m), 1 cho khoảng cách xa (< 5m)
                min_detection_confidence=0.5
            )
            self.use_mediapipe = True
            print("[*] FaceProcessor: Khởi tạo MediaPipe Face Detection thành công.")
        except (ImportError, AttributeError) as e:
            print("[!] FaceProcessor: MediaPipe solutions không khả dụng (bị gỡ bỏ ở phiên bản mới).")
            print("[*] Đang chuyển sang sử dụng OpenCV Haar Cascades làm bộ giải pháp thay thế (Fallback)...")
            self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            if self.face_cascade.empty():
                print("[!] CẢNH BÁO: Không thể tải được file haarcascade XML từ OpenCV.")

    def process_image(self, image_bytes):
        """
        Nhận vào dữ liệu byte của ảnh, giải mã và tìm khuôn mặt.
        Sử dụng MediaPipe nếu có, nếu không sẽ chuyển sang OpenCV Haar Cascades.
        """
        # Giải mã ảnh từ mảng byte
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return None, None

        height, width, _ = img.shape

        if self.use_mediapipe:
            try:
                # Chuyển đổi màu từ BGR sang RGB cho MediaPipe
                img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                results = self.face_detection.process(img_rgb)

                if results.detections:
                    # Lấy khuôn mặt đầu tiên phát hiện được
                    detection = results.detections[0]
                    bbox = detection.location_data.relative_bounding_box
                    
                    xmin = int(bbox.xmin * width)
                    ymin = int(bbox.ymin * height)
                    w = int(bbox.width * width)
                    h = int(bbox.height * height)
                    
                    xmin = max(0, xmin)
                    ymin = max(0, ymin)
                    xmax = min(width, xmin + w)
                    ymax = min(height, ymin + h)

                    cropped_face = img[ymin:ymax, xmin:xmax]
                    bbox_coords = {
                        "xmin": float(bbox.xmin),
                        "ymin": float(bbox.ymin),
                        "xmax": float(bbox.xmin + bbox.width),
                        "ymax": float(bbox.ymin + bbox.height)
                    }
                    return cropped_face, bbox_coords
            except Exception as ex:
                print(f"[!] Lỗi khi chạy MediaPipe: {ex}. Chuyển sang Haar Cascades...")

        # Giải pháp dự phòng OpenCV Haar Cascades
        try:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            # Phát hiện khuôn mặt
            faces = self.face_cascade.detectMultiScale(
                gray, 
                scaleFactor=1.1, 
                minNeighbors=5, 
                minSize=(30, 30)
            )
            
            if len(faces) > 0:
                # Lấy khuôn mặt lớn nhất (sắp xếp theo diện tích w * h giảm dần)
                faces = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)
                (x, y, w, h) = faces[0]
                
                cropped_face = img[y:y+h, x:x+w]
                bbox_coords = {
                    "xmin": float(x / width),
                    "ymin": float(y / height),
                    "xmax": float((x + w) / width),
                    "ymax": float((y + h) / height)
                }
                return cropped_face, bbox_coords
        except Exception as ex:
            print(f"[!] Lỗi khi chạy OpenCV Haar Cascades: {ex}")

        return None, None
