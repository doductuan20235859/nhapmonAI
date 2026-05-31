# Dự án Nhận diện Cảm xúc Khuôn mặt (Face Emotion Recognition AI)

Hệ thống nhận diện cảm xúc khuôn mặt thời gian thực (Real-time) và qua ảnh tĩnh tải lên (Static Upload). Dự án sử dụng mô hình học sâu **Emotion FerPlus** của Microsoft, được suy luận siêu tốc qua **ONNX Runtime** ở phía Python, kết hợp với bộ điều phối **.NET Core Web API (SignalR WebSockets)** và giao diện hiển thị **Vite + React**.

---

## 📁 Cấu trúc thư mục dự án

```
face-emotion-project/
│
├── frontend/                     # Giao diện Web (Vite + React)
│   ├── package.json              # Cấu hình cài đặt (tương thích Node v14 trở lên)
│   ├── src/
│   │   ├── App.jsx               # Xử lý webcam stream, vẽ bounding box, SignalR + REST API
│   │   └── index.css             # Giao diện Glassmorphism và màu sắc neon động
│   └── vite.config.js
│
├── backend-main-dotnet/          # Web API kết nối trung tâm (.NET 10.0)
│   ├── Controllers/
│   │   ├── EmotionController.cs  # REST API nhận diện qua tệp ảnh upload
│   │   └── EmotionHub.cs         # Hub SignalR (WebSockets) nhận diện thời gian thực
│   ├── Protos/
│   │   └── emotion.proto         # Định nghĩa dịch vụ gRPC phía .NET
│   ├── Services/
│   │   └── EmotionGrpcClient.cs  # gRPC Client kết nối sang AI Service Python
│   ├── Models/
│   │   └── EmotionModel.cs
│   └── Program.cs                # Cấu hình CORS, đăng ký dịch vụ gRPC, SignalR
│
└── ai-service-python/            # AI Service xử lý hình ảnh (Python)
    ├── protos/
    │   └── emotion.proto         # Định nghĩa dịch vụ gRPC phía Python (giống .NET)
    ├── generated/                # Code Python tự động sinh ra từ file .proto
    ├── requirements.txt          # Danh sách thư viện cần thiết
    ├── compile_protos.py         # Script tự động biên dịch protobuf tránh lỗi import
    ├── face_processor.py         # Phát hiện và cắt mặt (OpenCV Haar Cascade + MediaPipe Fallback)
    ├── emotion_detector.py       # Nhận diện cảm xúc thời gian thực (ONNX Runtime)
    └── app.py                    # Khởi chạy gRPC Server Python (cổng 50051)
```

---

## 🛠️ Yêu cầu môi trường trước khi chạy

Đảm bảo máy tính của bạn đã cài đặt các công cụ sau:
1. **Node.js** (Phiên bản v14.x hoặc mới hơn).
2. **.NET SDK** (Phiên bản 10.0 trở lên).
3. **Python 3.8+** (Khuyên dùng Python 3.10 đến 3.13).

---

## 🚀 Hướng dẫn cài đặt và Khởi chạy chi tiết

Khi bạn clone dự án này từ GitHub về, hãy mở 3 cửa sổ terminal riêng biệt để chạy các thành phần sau:

### Bước 1: Thiết lập & Chạy AI Service (Python - Cổng 50051)
1. Mở Terminal và di chuyển vào thư mục Python:
   ```bash
   cd ai-service-python
   ```
2. Cài đặt các thư viện phụ thuộc:
   ```bash
   pip install -r requirements.txt
   ```
   *(Nếu bạn có GPU Nvidia và muốn tối ưu hóa suy luận, có thể chạy thêm: `pip install onnxruntime-gpu`)*
3. Cài đặt gói tương thích Keras cho TensorFlow mới:
   ```bash
   pip install tf-keras
   ```
4. Biên dịch file định nghĩa Protobuf sang mã nguồn Python:
   ```bash
   python compile_protos.py
   ```
5. Khởi chạy Server gRPC:
   ```bash
   python app.py
   ```
   > 💡 **Lưu ý:** Trong lần khởi chạy đầu tiên, hệ thống sẽ tự động kết nối internet để tải tệp mô hình **`emotion_ferplus.onnx`** (dung lượng khoảng 35MB) về thư mục. Sau khi tải xong, server sẽ bắt đầu lắng nghe tại cổng `50051`.

---

### Bước 2: Thiết lập & Chạy Backend C# (.NET Core - Cổng 5000)
1. Mở Terminal thứ hai và di chuyển vào thư mục backend:
   ```bash
   cd backend-main-dotnet
   ```
2. Khởi chạy dự án:
   ```bash
   dotnet run
   ```
   > 💡 **Lưu ý:** Lệnh này sẽ tự động khôi phục các gói NuGet, tự biên dịch file proto trong thư mục `Protos/` sang mã nguồn C# và khởi chạy Web API tại địa chỉ mặc định: **`http://localhost:5000`**.

---

### Bước 3: Thiết lập & Chạy Giao diện Frontend (React - Cổng 5173)
1. Mở Terminal thứ ba và di chuyển vào thư mục frontend:
   ```bash
   cd frontend
   ```
2. Cài đặt các gói npm:
   ```bash
   npm install
   ```
3. Khởi chạy máy chủ phát triển Vite:
   ```bash
   npm run dev
   ```
4. Truy cập trình duyệt và mở liên kết: **`http://localhost:5173`** để bắt đầu trải nghiệm.

---

## ⚠️ Hướng dẫn sửa các lỗi thường gặp (Troubleshooting)

1. **Lỗi `Address already in use` hoặc `Failed to bind to address [::]:50051`:**
   - **Nguyên nhân:** Cổng `50051` (Python) hoặc cổng `5000` (.NET) đang bị chiếm dụng bởi một tiến trình chạy ngầm chưa tắt hẳn.
   - **Cách sửa:** Bạn cần tắt tiến trình đang chiếm dụng cổng đó, hoặc khởi động lại máy tính, sau đó chạy lại lệnh.

2. **Lỗi không mở được Webcam trên trình duyệt:**
   - **Nguyên nhân:** Trình duyệt Chrome/Edge chỉ cho phép gọi camera (`getUserMedia`) ở các địa chỉ an toàn (Secure Contexts).
   - **Cách sửa:** Đảm bảo bạn đang truy cập trang web thông qua địa chỉ **`http://localhost:5173`** hoặc **`http://127.0.0.1:5173`** thay vì các địa chỉ IP mạng nội bộ khác. Hãy chắc chắn đã cấp quyền cho phép trình duyệt sử dụng Camera.

3. **Cảnh báo thiếu file DLL `cublasLt64_12.dll` (ONNX Runtime):**
   - **Nguyên nhân:** Máy tính của bạn chưa được cài đặt driver CUDA GPU đầy đủ.
   - **Cách sửa:** Hệ thống đã được lập trình để tự động bắt lỗi và **dự phòng chạy bằng CPU (CPUExecutionProvider)** nên bạn không cần cài thêm gì cả, server vẫn chạy rất mượt và ổn định.
