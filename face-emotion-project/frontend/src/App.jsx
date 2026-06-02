import React, { useState, useEffect, useRef } from 'react';
import * as signalR from '@microsoft/signalr';
//http://localhost:5173
function App() {
  // State quản lý kết nối và camera
  const [isCameraActive, setIsCameraActive] = useState(false);
  const [connectionState, setConnectionState] = useState('Disconnected');
  const [activeMode, setActiveMode] = useState('realtime'); // 'realtime' hoặc 'upload'
  
  // State chứa kết quả nhận diện
  const [detection, setDetection] = useState({
    emotion: 'None',
    confidence: 0.0,
    boundingBox: null
  });

  // State thống kê lịch sử cảm xúc trong phiên làm việc
  const [history, setHistory] = useState({
    Angry: 0,
    Disgust: 0,
    Fear: 0,
    Happy: 0,
    Sad: 0,
    Surprise: 0,
    Neutral: 0
  });

  // File Upload State
  const [uploadFile, setUploadFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [isUploading, setIsUploading] = useState(false);

  // Các Ref để thao tác DOM và lưu trữ biến tĩnh
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const connectionRef = useRef(null);
  const intervalIdRef = useRef(null);

  const BACKEND_URL = 'http://localhost:5000'; // Cổng chạy thực tế của .NET Core Web API (Kestrel default)

  // 1. Quản lý kết nối SignalR Hub
  useEffect(() => {
    // Tạo đối tượng HubConnection
    const newConnection = new signalR.HubConnectionBuilder()
      .withUrl(`${BACKEND_URL}/emotionHub`)
      .withAutomaticReconnect()
      .configureLogging(signalR.LogLevel.Information)
      .build();

    connectionRef.current = newConnection;

    // Thiết lập các callback nhận dữ liệu
    newConnection.on('ReceiveEmotion', (data) => {
      if (data) {
        setDetection({
          emotion: data.emotion,
          confidence: data.confidence,
          boundingBox: data.boundingBox
        });

        // Cập nhật thống kê nếu có cảm xúc hợp lệ
        if (data.emotion && data.emotion !== 'No Face Detected' && data.emotion !== 'Error') {
          setHistory(prev => ({
            ...prev,
            [data.emotion]: (prev[data.emotion] || 0) + 1
          }));
        }
      }
    });

    // Theo dõi trạng thái kết nối
    newConnection.onclose(() => setConnectionState('Disconnected'));
    newConnection.onreconnecting(() => setConnectionState('Reconnecting'));
    newConnection.onreconnected(() => setConnectionState('Connected'));

    // Bắt đầu kết nối
    const startConnection = async () => {
      try {
        setConnectionState('Connecting');
        await newConnection.start();
        setConnectionState('Connected');
        console.log('[+] Đã kết nối thành công tới .NET SignalR Hub');
      } catch (err) {
        console.error('[-] Lỗi kết nối SignalR Hub:', err);
        setConnectionState('Disconnected');
      }
    };

    startConnection();

    return () => {
      if (newConnection) {
        newConnection.stop();
      }
    };
  }, []);

  // 2. Vẽ Bounding Box lên Canvas chồng lên Video
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Xóa canvas trước khi vẽ đè
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const { boundingBox, emotion, confidence } = detection;
    if (!boundingBox || isZeroBox(boundingBox)) return;

    // Kích thước canvas thực tế
    const width = canvas.width;
    const height = canvas.height;

    // Chuyển tọa độ tương đối từ server (0 -> 1) thành tọa độ pixel thực tế
    const x = boundingBox.xmin * width;
    const y = boundingBox.ymin * height;
    const w = (boundingBox.xmax - boundingBox.xmin) * width;
    const h = (boundingBox.ymax - boundingBox.ymin) * height;

    // Xác định màu sắc viền vẽ dựa trên cảm xúc
    const emotionColors = {
      Happy: '#10b981',
      Sad: '#3b82f6',
      Angry: '#f43f5e',
      Surprise: '#f59e0b',
      Fear: '#e11d48',
      Disgust: '#a855f7',
      Neutral: '#6b7280'
    };
    const drawColor = emotionColors[emotion] || '#6366f1';

    // Vẽ hình chữ nhật bao khuôn mặt
    ctx.strokeStyle = drawColor;
    ctx.lineWidth = 3;
    ctx.shadowBlur = 10;
    ctx.shadowColor = drawColor;
    ctx.strokeRect(x, y, w, h);

    // Vẽ nhãn (Emotion + Confidence)
    ctx.shadowBlur = 0; // Tắt shadow cho text dễ nhìn
    ctx.fillStyle = drawColor;
    ctx.fillRect(x, y - 28, Math.max(w, 120), 28);

    ctx.fillStyle = '#ffffff';
    ctx.font = 'bold 12px Inter, sans-serif';
    ctx.fillText(`${emotion.toUpperCase()} (${(confidence * 100).toFixed(0)}%)`, x + 8, y - 9);

  }, [detection]);

  // Kiểm tra bounding box rỗng
  const isZeroBox = (box) => {
    return box.xmin === 0 && box.ymin === 0 && box.xmax === 0 && box.ymax === 0;
  };

  // 3. Khởi chạy / Tắt Camera
  const startCamera = async () => {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      alert('Trình duyệt của bạn không hỗ trợ camera hoặc bạn đang truy cập qua một kết nối không an toàn (Không phải HTTPS hoặc localhost). Hãy chắc chắn rằng bạn đang truy cập bằng http://localhost:5173 hoặc http://127.0.0.1:5173.');
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 640, height: 480, facingMode: 'user' }
      });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        try {
          await videoRef.current.play();
        } catch (playErr) {
          console.warn('Lỗi khi gọi video.play():', playErr);
        }
        setIsCameraActive(true);
        
        // Căn chỉnh kích thước canvas khớp với video stream
        setTimeout(() => {
          if (videoRef.current && canvasRef.current) {
            canvasRef.current.width = videoRef.current.videoWidth;
            canvasRef.current.height = videoRef.current.videoHeight;
          }
        }, 500);

        // Bắt đầu vòng lặp gửi frame ảnh lên server
        startFrameCaptureLoop();
      }
    } catch (err) {
      console.error('[-] Không thể mở camera:', err);
      alert('Không thể truy cập Camera: ' + err.name + ' - ' + err.message);
    }
  };

  const stopCamera = () => {
    if (videoRef.current && videoRef.current.srcObject) {
      const stream = videoRef.current.srcObject;
      const tracks = stream.getTracks();
      tracks.forEach(track => track.stop());
      videoRef.current.srcObject = null;
    }
    setIsCameraActive(false);
    stopFrameCaptureLoop();
    
    // Clear canvas
    if (canvasRef.current) {
      const ctx = canvasRef.current.getContext('2d');
      ctx.clearRect(0, 0, canvasRef.current.width, canvasRef.current.height);
    }
    setDetection({ emotion: 'None', confidence: 0, boundingBox: null });
  };

  // 4. Vòng lặp chụp ảnh màn hình và gửi đi
  const startFrameCaptureLoop = () => {
    stopFrameCaptureLoop(); // Đảm bảo không bị lặp timer
    
    // Tạo một canvas ẩn dùng để render frame ra ảnh Base64
    const hiddenCanvas = document.createElement('canvas');
    
    intervalIdRef.current = setInterval(() => {
      const video = videoRef.current;
      const connection = connectionRef.current;

      if (!video || !video.srcObject || connectionState !== 'Connected') return;

      // Thu nhỏ độ phân giải ảnh truyền đi (320x240) để giảm tải băng thông và ổn định kết nối.
      // Mô hình MiniXception chỉ cần ảnh 48x48 nên 320x240 là quá đủ để nhận dạng khuôn mặt và cảm xúc.
      hiddenCanvas.width = 320;
      hiddenCanvas.height = 240;
      const ctx = hiddenCanvas.getContext('2d');
      
      // Vẽ frame hiện tại của video lên canvas ẩn
      ctx.drawImage(video, 0, 0, hiddenCanvas.width, hiddenCanvas.height);
      
      // Xuất sang định dạng JPEG chất lượng 0.7 để tiết kiệm băng thông
      const base64Image = hiddenCanvas.toDataURL('image/jpeg', 0.7);
      
      // Gọi phương thức SignalR trên Backend
      connection.invoke('SendFrame', base64Image)
        .catch(err => console.error('[-] Lỗi khi gửi frame qua SignalR:', err));

    }, 300); // Gửi 3.3 frames mỗi giây (độ trễ tốt, tiết kiệm CPU)
  };

  const stopFrameCaptureLoop = () => {
    if (intervalIdRef.current) {
      clearInterval(intervalIdRef.current);
      intervalIdRef.current = null;
    }
  };

  // 5. Xử lý ảnh tải lên bằng REST API (HTTP POST)
  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setUploadFile(file);
      setPreviewUrl(URL.createObjectURL(file));
      setDetection({ emotion: 'None', confidence: 0, boundingBox: null });
    }
  };

  const uploadAndDetect = async () => {
    if (!uploadFile) return;

    setIsUploading(true);
    const formData = new FormData();
    formData.append('file', uploadFile);

    try {
      const response = await fetch(`${BACKEND_URL}/api/emotion/detect`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error('Lỗi từ máy chủ HTTP backend');
      }

      const data = await response.json();
      setDetection({
        emotion: data.emotion,
        confidence: data.confidence,
        boundingBox: data.boundingBox
      });

      if (data.emotion && data.emotion !== 'No Face Detected' && data.emotion !== 'Error') {
        setHistory(prev => ({
          ...prev,
          [data.emotion]: (prev[data.emotion] || 0) + 1
        }));
      }
    } catch (err) {
      console.error('[-] Lỗi upload nhận diện cảm xúc:', err);
      alert('Không thể nhận diện hình ảnh. Kiểm tra xem Backend .NET đã khởi chạy chưa.');
    } finally {
      setIsUploading(false);
    }
  };

  // Render class động theo cảm xúc để cập nhật hiệu ứng card
  const getEmotionClass = () => {
    const emotion = detection.emotion.toLowerCase();
    if (['happy', 'sad', 'angry', 'surprise', 'fear', 'disgust', 'neutral'].includes(emotion)) {
      return emotion;
    }
    return '';
  };

  return (
    <div className="app-container">
      <header>
        <div className="title-area">
          <h1>Face Emotion AI</h1>
          <p>Hệ thống nhận diện cảm xúc khuôn mặt gRPC + SignalR + MiniXception</p>
        </div>
        <div className="status-badge">
          <span className={`status-dot ${connectionState === 'Connected' ? 'connected' : ''}`}></span>
          <span>Backend: {connectionState}</span>
        </div>
      </header>

      <main className="dashboard-grid">
        {/* Cột trái: Camera hoặc Ảnh Upload */}
        <section className="glass-card">
          <div className="card-title">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"></path>
              <circle cx="12" cy="13" r="4"></circle>
            </svg>
            <span>Kênh Nhận Diện Hình Ảnh</span>
            
            <div style={{ marginLeft: 'auto', display: 'flex', gap: '0.5rem' }}>
              <button 
                onClick={() => { stopCamera(); setActiveMode('realtime'); }}
                className={`btn btn-secondary ${activeMode === 'realtime' ? 'btn-primary' : ''}`}
                style={{ padding: '0.25rem 0.75rem', fontSize: '0.8rem', borderRadius: '6px' }}
              >
                Webcam Live
              </button>
              <button 
                onClick={() => { stopCamera(); setActiveMode('upload'); }}
                className={`btn btn-secondary ${activeMode === 'upload' ? 'btn-primary' : ''}`}
                style={{ padding: '0.25rem 0.75rem', fontSize: '0.8rem', borderRadius: '6px' }}
              >
                Tải ảnh lên
              </button>
            </div>
          </div>

          {activeMode === 'realtime' ? (
            <div>
              <div className={`viewport-wrapper ${isCameraActive ? 'active' : ''}`}>
                <video 
                  ref={videoRef} 
                  className="webcam-video" 
                  autoPlay 
                  playsInline 
                  muted
                ></video>
                <canvas 
                  ref={canvasRef} 
                  className="drawing-canvas"
                ></canvas>
                
                {!isCameraActive && (
                  <div className="placeholder-screen">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                      <path d="M15.5 8.5h.01M8.5 8.5h.01M12 17.5c-2.33 0-4.3-1.45-5.11-3.5h10.22c-.81 2.05-2.78 3.5-5.11 3.5zM22 12c0 5.523-4.477 10-10 10S2 17.523 2 12 6.477 2 12 2s10 4.477 10 10z"/>
                    </svg>
                    <p style={{ fontWeight: 500, color: '#9ca3af' }}>Camera chưa được kích hoạt</p>
                    <p style={{ fontSize: '0.8rem' }}>Nhấn nút "Mở Webcam" bên dưới để bắt đầu nhận diện cảm xúc thời gian thực</p>
                  </div>
                )}
              </div>

              <div className="controls-bar">
                {!isCameraActive ? (
                  <button 
                    onClick={startCamera} 
                    className="btn btn-primary"
                    disabled={connectionState !== 'Connected'}
                  >
                    Mở Webcam Live
                  </button>
                ) : (
                  <button onClick={stopCamera} className="btn btn-secondary">
                    Dừng Webcam
                  </button>
                )}
                {connectionState !== 'Connected' && (
                  <span style={{ fontSize: '0.8rem', color: '#ef4444', alignSelf: 'center' }}>
                    Yêu cầu kết nối Backend để mở camera.
                  </span>
                )}
              </div>
            </div>
          ) : (
            <div>
              <div className="viewport-wrapper active" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
                {previewUrl ? (
                  <div style={{ position: 'relative', width: '100%', height: '100%' }}>
                    <img 
                      src={previewUrl} 
                      alt="Preview" 
                      style={{ width: '100%', height: '100%', objectFit: 'contain' }}
                      onLoad={(e) => {
                        // Thiết lập canvas vẽ khung khớp với ảnh preview
                        if (canvasRef.current) {
                          canvasRef.current.width = e.target.clientWidth;
                          canvasRef.current.height = e.target.clientHeight;
                        }
                      }}
                    />
                    <canvas 
                      ref={canvasRef} 
                      className="drawing-canvas"
                      style={{ transform: 'none' }} // Không lật đối xứng khi vẽ ảnh tĩnh
                    ></canvas>
                  </div>
                ) : (
                  <div className="placeholder-screen">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                      <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
                      <circle cx="8.5" cy="8.5" r="1.5"/>
                      <polyline points="21 15 16 10 5 21"/>
                    </svg>
                    <p style={{ fontWeight: 500, color: '#9ca3af' }}>Chưa chọn hình ảnh</p>
                    <p style={{ fontSize: '0.8rem' }}>Chọn file ảnh (.jpg/.png) và bấm nút nhận diện</p>
                  </div>
                )}
              </div>

              <div className="controls-bar">
                <input 
                  type="file" 
                  accept="image/*" 
                  onChange={handleFileChange} 
                  id="image-uploader" 
                  style={{ display: 'none' }}
                />
                <button 
                  onClick={() => document.getElementById('image-uploader').click()}
                  className="btn btn-secondary"
                >
                  Chọn tệp ảnh
                </button>
                <button 
                  onClick={uploadAndDetect} 
                  className="btn btn-primary"
                  disabled={!uploadFile || isUploading}
                >
                  {isUploading ? 'Đang phân tích...' : 'Phân Tích Cảm Xúc'}
                </button>
              </div>
            </div>
          )}
        </section>

        {/* Cột phải: Bảng hiển thị thông tin & Thống kê */}
        <section className="telemetry-panel">
          {/* Card cảm xúc chính */}
          <div className={`glass-card emotion-card ${getEmotionClass()}`}>
            <div className="emotion-label">Cảm Xúc Phát Hiện</div>
            <div className="emotion-value">
              {detection.emotion === 'None' ? '—' : detection.emotion}
            </div>
            
            <div className="confidence-bar-container">
              <div className="confidence-header">
                <span>Độ tin cậy</span>
                <span>{(detection.confidence * 100).toFixed(0)}%</span>
              </div>
              <div className="confidence-track">
                <div 
                  className="confidence-fill"
                  style={{ 
                    width: `${detection.confidence * 100}%`,
                    backgroundColor: detection.emotion === 'Happy' ? 'var(--color-happy)' : 
                                    detection.emotion === 'Sad' ? 'var(--color-sad)' :
                                    detection.emotion === 'Angry' ? 'var(--color-angry)' :
                                    detection.emotion === 'Surprise' ? 'var(--color-surprise)' :
                                    detection.emotion === 'Fear' ? 'var(--color-fear)' :
                                    detection.emotion === 'Disgust' ? 'var(--color-disgust)' :
                                    'var(--color-accent)'
                  }}
                ></div>
              </div>
            </div>
          </div>

          {/* Thống kê lịch sử các cảm xúc */}
          <div className="glass-card">
            <div className="card-title">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="18" y1="20" x2="18" y2="10"></line>
                <line x1="12" y1="20" x2="12" y2="4"></line>
                <line x1="6" y1="20" x2="6" y2="14"></line>
              </svg>
              <span>Thống Kê Trong Phiên</span>
            </div>

            <div className="stats-list">
              {Object.entries(history).map(([emotion, count]) => {
                const colors = {
                  Happy: 'var(--color-happy)',
                  Sad: 'var(--color-sad)',
                  Angry: 'var(--color-angry)',
                  Surprise: 'var(--color-surprise)',
                  Fear: 'var(--color-fear)',
                  Disgust: 'var(--color-disgust)',
                  Neutral: 'var(--color-neutral)'
                };
                return (
                  <div key={emotion} className="stat-item">
                    <div className="stat-emotion">
                      <span className="stat-color-dot" style={{ backgroundColor: colors[emotion] }}></span>
                      <span>{emotion}</span>
                    </div>
                    <div className="stat-count">{count} frames</div>
                  </div>
                );
              })}
            </div>
          </div>
        </section>
      </main>

      <footer>
        Hệ thống Nhận diện Cảm xúc khuôn mặt AI &copy; 2026 - Phát triển trên nền tảng .NET Core C# & Python gRPC & React.
      </footer>
    </div>
  );
}

export default App;
