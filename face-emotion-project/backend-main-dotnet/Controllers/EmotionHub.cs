using Microsoft.AspNetCore.SignalR;
using BackendMainDotnet.Services;
using BackendMainDotnet.Protos;

namespace BackendMainDotnet.Controllers
{
    public class EmotionHub : Hub
    {
        private readonly IEmotionGrpcClient _grpcClient;
        private readonly ILogger<EmotionHub> _logger;

        public EmotionHub(IEmotionGrpcClient grpcClient, ILogger<EmotionHub> logger)
        {
            _grpcClient = grpcClient;
            _logger = logger;
        }

        /// <summary>
        /// Tiếp nhận frame ảnh dạng Base64 từ Frontend gửi qua SignalR
        /// </summary>
        public async Task SendFrame(string base64Image)
        {
            if (string.IsNullOrEmpty(base64Image))
            {
                await Clients.Caller.SendAsync("ReceiveEmotion", new { emotion = "No Data", confidence = 0.0 });
                return;
            }

            try
            {
                // Loại bỏ tiền tố base64 nếu có (data:image/jpeg;base64,...)
                var base64Data = base64Image;
                if (base64Image.Contains(","))
                {
                    base64Data = base64Image.Split(',')[1];
                }

                byte[] imageBytes = Convert.FromBase64String(base64Data);

                // Gọi dịch vụ Python qua gRPC để nhận diện khuôn mặt và cảm xúc
                var response = await _grpcClient.DetectEmotionAsync(imageBytes);

                // Gửi kết quả ngược lại cho Client đã gửi frame
                await Clients.Caller.SendAsync("ReceiveEmotion", new
                {
                    emotion = response.Emotion,
                    confidence = response.Confidence,
                    boundingBox = new
                    {
                        xmin = response.BoundingBox.Xmin,
                        ymin = response.BoundingBox.Ymin,
                        xmax = response.BoundingBox.Xmax,
                        ymax = response.BoundingBox.Ymax
                    }
                });
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Lỗi khi xử lý frame trong SignalR Hub");
                await Clients.Caller.SendAsync("ReceiveEmotion", new
                {
                    emotion = "Server Error",
                    confidence = 0.0,
                    error = ex.Message
                });
            }
        }
    }
}
