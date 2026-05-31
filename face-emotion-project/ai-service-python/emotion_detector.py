import os
import cv2
import numpy as np
import urllib.request
import sys
import time

# Configure UTF-8 encoding for stdout on Windows to prevent UnicodeEncodeError
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except AttributeError:
    pass

try:
    import onnxruntime as ort
    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False

class EmotionDetector:
    def __init__(self, model_path="emotion_ferplus.onnx"):
        self.model_path = model_path
        # Danh sách 8 nhãn của mô hình Microsoft Emotion FerPlus
        self.labels = ['Neutral', 'Happy', 'Surprise', 'Sad', 'Angry', 'Disgust', 'Fear', 'Contempt']
        
        # Lịch sử để làm mượt kết quả
        self.history = []
        self.history_max_len = 5 # Làm mượt qua 5 frame gần nhất (~1.5 giây)
        self.last_detect_time = 0.0 # Lưu mốc thời gian của frame cuối cùng
        self.session = None

        if not ONNX_AVAILABLE:
            print("[!] CẢNH BÁO: Chưa cài đặt thư viện 'onnxruntime'. Trình nhận diện sẽ chạy ở chế độ MOCK.")
            print("[!] Vui lòng chạy lệnh: pip install onnxruntime-gpu để cài đặt.")
            return

        # 1. Tự động tải mô hình ONNX nếu chưa có sẵn
        if not os.path.exists(self.model_path):
            self._download_onnx_model()

        # 2. Khởi tạo phiên suy luận ONNX (Inference Session)
        try:
            # Tự động chọn GPU nếu có, ngược lại sử dụng CPU làm mặc định
            available_providers = ort.get_available_providers()
            print(f"[*] ONNX Runtime khả dụng với các Providers: {available_providers}")
            
            # Ưu tiên CUDA (GPU) trước CPU
            providers = []
            if "CUDAExecutionProvider" in available_providers:
                providers.append("CUDAExecutionProvider")
            providers.append("CPUExecutionProvider")

            print(f"[*] Đang khởi tạo phiên suy luận với Providers: {providers}...")
            self.session = ort.InferenceSession(self.model_path, providers=providers)
            
            # Lấy tên của đầu vào và đầu ra từ mô hình
            self.input_name = self.session.get_inputs()[0].name
            self.output_name = self.session.get_outputs()[0].name
            print("[+] Đã tải thành công mô hình ONNX. Sẵn sàng xử lý suy luận.")
            
        except Exception as e:
            print(f"[!] Lỗi khi tải mô hình ONNX: {e}. Hệ thống sẽ sử dụng chế độ MOCK.")
            self.session = None

    def _download_onnx_model(self):
        """
        Tải mô hình Emotion FerPlus chính thức từ ONNX Model Zoo
        """
        url = "https://github.com/onnx/models/raw/main/validated/vision/body_analysis/emotion_ferplus/model/emotion-ferplus-8.onnx"
        print(f"[!] Không tìm thấy tệp mô hình {self.model_path} cục bộ.")
        print(f"[*] Bắt đầu tự động tải mô hình từ ONNX Model Zoo:\n{url}")
        print("[*] Dung lượng mô hình khoảng 35 MB, vui lòng chờ trong giây lát...")
        
        try:
            urllib.request.urlretrieve(url, self.model_path)
            size_mb = os.path.getsize(self.model_path) / (1024 * 1024)
            print(f"[+] Tải thành công mô hình ONNX! Kích thước: {size_mb:.2f} MB")
        except Exception as e:
            print(f"[!] Không thể tải mô hình tự động: {e}")
            print("[!] Vui lòng tải thủ công tệp .onnx và đặt vào thư mục với tên 'emotion_ferplus.onnx'")

    def _softmax(self, x):
        """
        Hàm Softmax để chuyển đổi logits (điểm số thô) sang phân phối xác suất
        """
        e_x = np.exp(x - np.max(x))
        return e_x / e_x.sum(axis=0)

    def detect_emotion(self, cropped_face):
        """
        Nhận vào ảnh mặt BGR, thực hiện tiền xử lý và chạy suy luận bằng ONNX.
        Trả về: (emotion_label, confidence)
        """
        if cropped_face is None or cropped_face.size == 0:
            return "Unknown", 0.0

        # Tự động xóa lịch sử làm mượt nếu đây là yêu cầu nhận diện ảnh tĩnh đơn lẻ (upload ảnh)
        # Tần suất gửi frame của webcam là 300ms. Nếu thời gian chờ > 1.0 giây, ta coi là một phiên mới.
        current_time = time.time()
        if current_time - self.last_detect_time > 1.0:
            self.history.clear()
        self.last_detect_time = current_time

        if not ONNX_AVAILABLE or self.session is None:
            # Chế độ giả lập (Mock) khi không có thư viện / mô hình
            mock_emotions = ["Happy", "Neutral", "Surprise", "Sad", "Angry"]
            idx = int(np.random.choice(len(mock_emotions)))
            confidence = float(np.random.uniform(0.65, 0.95))
            return mock_emotions[idx], confidence

        try:
            # 1. Tiền xử lý ảnh (Yêu cầu của mô hình Emotion FerPlus)
            # - Chuyển sang ảnh xám (Grayscale)
            gray = cv2.cvtColor(cropped_face, cv2.COLOR_BGR2GRAY)
            # - Resize về kích thước 64x64
            resized = cv2.resize(gray, (64, 64))
            
            # - Định dạng đầu vào: float32, định dạng Tensor [batch, channel, height, width] -> (1, 1, 64, 64)
            input_data = resized.astype(np.float32)
            input_data = np.expand_dims(np.expand_dims(input_data, axis=0), axis=0)

            # 2. Chạy suy luận ONNX Runtime
            outputs = self.session.run([self.output_name], {self.input_name: input_data})
            logits = outputs[0][0] # Kết quả thô dạng mảng 8 phần tử

            # 3. Tính phân phối xác suất bằng Softmax
            probabilities = self._softmax(logits)

            # 4. Thêm xác suất hiện tại vào lịch sử làm mượt kết quả
            self.history.append(probabilities)
            if len(self.history) > self.history_max_len:
                self.history.pop(0)

            # 5. Tính trung bình cộng xác suất trên toàn bộ lịch sử
            avg_probabilities = np.mean(self.history, axis=0)
            dominant_idx = np.argmax(avg_probabilities)
            
            dominant_label = self.labels[dominant_idx]
            confidence = float(avg_probabilities[dominant_idx])

            # 6. Ánh xạ cảm xúc: Nếu là 'Contempt' (Khinh bỉ), gom nhóm thành 'Neutral'
            if dominant_label == 'Contempt':
                emotion = 'Neutral'
            elif dominant_label == 'Contempt' or dominant_label == 'Contempt':
                # Chuyển đổi tên gọi nhãn cho khớp hoàn toàn với Frontend React
                emotion = 'Neutral'
            
            # Ánh xạ tên gọi
            mapping = {
                'Neutral': 'Neutral',
                'Happy': 'Happy',
                'Surprise': 'Surprise',
                'Sad': 'Sad',
                'Angry': 'Angry',
                'Disgust': 'Disgust',
                'Fear': 'Fear',
                'Contempt': 'Neutral'
            }
            emotion = mapping.get(dominant_label, 'Neutral')

            return emotion, confidence

        except Exception as e:
            print(f"[!] Lỗi khi chạy suy luận ONNX: {e}")
            return "Neutral", 0.5
