import os
import cv2
import numpy as np
import urllib.request
import sys

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
        
        # Lịch sử để làm mượt kết quả cho luồng Stream
        self.history = []
        self.history_max_len = 5 # Làm mượt qua 5 frame gần nhất (~1.5 giây)
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
            available_providers = ort.get_available_providers()
            print(f"[*] ONNX Runtime khả dụng với các Providers: {available_providers}")
            
            providers = []
            if "CUDAExecutionProvider" in available_providers:
                providers.append("CUDAExecutionProvider")
            providers.append("CPUExecutionProvider")

            print(f"[*] Đang khởi tạo phiên suy luận với Providers: {providers}...")
            self.session = ort.InferenceSession(self.model_path, providers=providers)
            
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

    def _preprocess(self, cropped_face):
        """
        Tiền xử lý ảnh xám 64x64 dạng float32
        """
        gray = cv2.cvtColor(cropped_face, cv2.COLOR_BGR2GRAY)
        resized = cv2.resize(gray, (64, 64))
        input_data = resized.astype(np.float32)
        return np.expand_dims(np.expand_dims(input_data, axis=0), axis=0)

    def _map_label(self, label):
        """
        Ánh xạ nhãn từ FerPlus sang nhãn Frontend React
        """
        mapping = {
            'Neutral': 'Neutral',
            'Happy': 'Happy',
            'Surprise': 'Surprise',
            'Sad': 'Sad',
            'Angry': 'Angry',
            'Disgust': 'Disgust',
            'Fear': 'Fear',
            'Contempt': 'Neutral' # Contempt được gộp vào Neutral
        }
        return mapping.get(label, 'Neutral')

    def detect_emotion_stream(self, cropped_face):
        """
        Nhận dạng cảm xúc luồng Camera thời gian thực (CÓ bộ lọc làm mượt trung bình động)
        """
        if cropped_face is None or cropped_face.size == 0:
            return "Unknown", 0.0

        if not ONNX_AVAILABLE or self.session is None:
            mock_emotions = ["Happy", "Neutral", "Surprise", "Sad", "Angry"]
            idx = int(np.random.choice(len(mock_emotions)))
            confidence = float(np.random.uniform(0.65, 0.95))
            return mock_emotions[idx], confidence

        try:
            # 1. Tiền xử lý & Suy luận
            input_data = self._preprocess(cropped_face)
            outputs = self.session.run([self.output_name], {self.input_name: input_data})
            logits = outputs[0][0]

            # 2. Xác suất qua Softmax
            probabilities = self._softmax(logits)

            # 3. Đưa vào lịch sử trượt
            self.history.append(probabilities)
            if len(self.history) > self.history_max_len:
                self.history.pop(0)

            # 4. Tính trung bình xác suất trong bộ đệm làm mượt
            avg_probabilities = np.mean(self.history, axis=0)
            dominant_idx = np.argmax(avg_probabilities)
            
            dominant_label = self.labels[dominant_idx]
            confidence = float(avg_probabilities[dominant_idx])

            return self._map_label(dominant_label), confidence

        except Exception as e:
            print(f"[!] Lỗi khi chạy suy luận ONNX Stream: {e}")
            return "Neutral", 0.5

    def detect_emotion_single(self, cropped_face):
        """
        Nhận dạng cảm xúc của ảnh tĩnh tải lên (KHÔNG làm mượt, kết quả tức thời độc lập)
        """
        if cropped_face is None or cropped_face.size == 0:
            return "Unknown", 0.0

        if not ONNX_AVAILABLE or self.session is None:
            mock_emotions = ["Happy", "Neutral", "Surprise", "Sad", "Angry"]
            idx = int(np.random.choice(len(mock_emotions)))
            confidence = float(np.random.uniform(0.65, 0.95))
            return mock_emotions[idx], confidence

        try:
            # 1. Tiền xử lý & Suy luận
            input_data = self._preprocess(cropped_face)
            outputs = self.session.run([self.output_name], {self.input_name: input_data})
            logits = outputs[0][0]

            # 2. Xác suất qua Softmax
            probabilities = self._softmax(logits)
            dominant_idx = np.argmax(probabilities)
            
            dominant_label = self.labels[dominant_idx]
            confidence = float(probabilities[dominant_idx])

            # Khi nhận ảnh tĩnh, ta xóa bộ nhớ đệm Stream để không ảnh hưởng nếu sau đó bật lại camera
            self.history.clear()

            return self._map_label(dominant_label), confidence

        except Exception as e:
            print(f"[!] Lỗi khi chạy suy luận ONNX Single: {e}")
            return "Neutral", 0.5
