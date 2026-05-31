import sys
import os
import time
from concurrent import futures
import grpc

# Configure UTF-8 encoding for stdout on Windows to prevent UnicodeEncodeError
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except AttributeError:
    pass

# Thêm thư mục hiện tại và generated vào sys.path để tránh lỗi import
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
sys.path.append(os.path.join(current_dir, "generated"))

from face_processor import FaceProcessor
from emotion_detector import EmotionDetector

try:
    import generated.emotion_pb2 as emotion_pb2
    import generated.emotion_pb2_grpc as emotion_pb2_grpc
    PROTO_COMPILED = True
except ImportError:
    print("[!] CẢNH BÁO: Chưa biên dịch tệp proto. Hãy chạy 'python compile_protos.py' trước.")
    PROTO_COMPILED = False

class EmotionServiceServicer:
    def __init__(self):
        print("[*] Khởi tạo các module AI...")
        self.face_processor = FaceProcessor()
        self.emotion_detector = EmotionDetector()
        print("[+] Khởi tạo AI hoàn tất. Sẵn sàng xử lý dữ liệu.")

    def DetectEmotion(self, request, context):
        """
        Xử lý yêu cầu gRPC từ Backend .NET gửi sang
        """
        # Nếu chưa compile proto, trả về lỗi gRPC
        if not PROTO_COMPILED:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("Proto files not compiled on server side")
            return None

        try:
            image_bytes = request.image_bytes
            if not image_bytes:
                return emotion_pb2.EmotionResponse(
                    emotion="No Image Data",
                    confidence=0.0,
                    bounding_box=emotion_pb2.Box(xmin=0, ymin=0, xmax=0, ymax=0)
                )

            # 1. Phát hiện và cắt mặt bằng MediaPipe
            cropped_face, bbox = self.face_processor.process_image(image_bytes)
            
            if cropped_face is None or bbox is None:
                # Không tìm thấy khuôn mặt
                return emotion_pb2.EmotionResponse(
                    emotion="No Face Detected",
                    confidence=0.0,
                    bounding_box=emotion_pb2.Box(xmin=0, ymin=0, xmax=0, ymax=0)
                )

            # 2. Nhận diện cảm xúc bằng MiniXception
            emotion, confidence = self.emotion_detector.detect_emotion(cropped_face)

            # Trả về kết quả cho client
            return emotion_pb2.EmotionResponse(
                emotion=emotion,
                confidence=confidence,
                bounding_box=emotion_pb2.Box(
                    xmin=bbox["xmin"],
                    ymin=bbox["ymin"],
                    xmax=bbox["xmax"],
                    ymax=bbox["ymax"]
                )
            )
            
        except Exception as e:
            print(f"[!] Lỗi hệ thống khi xử lý DetectEmotion: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Server error: {str(e)}")
            return None

def serve():
    global emotion_pb2, emotion_pb2_grpc, PROTO_COMPILED
    if not PROTO_COMPILED:
        print("[!] Đang tự động chạy compile_protos.py...")
        import compile_protos
        if not compile_protos.compile_proto():
            print("[-] Không thể khởi chạy server do lỗi biên dịch proto.")
            return
        
        # Thử import lại sau khi biên dịch
        try:
            import generated.emotion_pb2 as emotion_pb2
            import generated.emotion_pb2_grpc as emotion_pb2_grpc
            PROTO_COMPILED = True
        except ImportError:
            print("[-] Biên dịch thành công nhưng import vẫn thất bại.")
            return

    # Khởi tạo gRPC server
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    
    # Kế thừa Servicer được sinh ra từ proto
    servicer = EmotionServiceServicer()
    emotion_pb2_grpc.add_EmotionServiceServicer_to_server(servicer, server)
    
    # Lắng nghe tại cổng 50051
    server.add_insecure_port('[::]:50051')
    print("[+] gRPC Server Python đang chạy tại cổng: 50051...")
    server.start()
    
    try:
        while True:
            time.sleep(86400)
    except KeyboardInterrupt:
        print("[*] Đang dừng gRPC Server...")
        server.stop(0)

if __name__ == "__main__":
    serve()
