using Grpc.Net.Client;
using BackendMainDotnet.Protos;

namespace BackendMainDotnet.Services
{
    public interface IEmotionGrpcClient
    {
        Task<EmotionResponse> DetectEmotionStreamAsync(byte[] imageBytes);
        Task<EmotionResponse> DetectEmotionSingleAsync(byte[] imageBytes);
    }

    public class EmotionGrpcClient : IEmotionGrpcClient
    {
        private readonly IConfiguration _configuration;
        private readonly ILogger<EmotionGrpcClient> _logger;
        private readonly string _pythonServiceUrl;

        public EmotionGrpcClient(IConfiguration configuration, ILogger<EmotionGrpcClient> logger)
        {
            _configuration = configuration;
            _logger = logger;
            // Lấy URL Python Service từ appsettings.json hoặc mặc định localhost:50051
            _pythonServiceUrl = _configuration["AiService:gRpcUrl"] ?? "http://localhost:50051";
        }

        public async Task<EmotionResponse> DetectEmotionStreamAsync(byte[] imageBytes)
        {
            try
            {
                // Cho phép gọi HTTP không an toàn (nếu Python Service chạy http thông thường)
                AppContext.SetSwitch("System.Net.Http.SocketsHttpHandler.Http2UnencryptedSupport", true);

                using var channel = GrpcChannel.ForAddress(_pythonServiceUrl);
                var client = new EmotionService.EmotionServiceClient(channel);

                var request = new EmotionRequest
                {
                    ImageBytes = Google.Protobuf.ByteString.CopyFrom(imageBytes)
                };

                _logger.LogInformation("Gửi yêu cầu gRPC Stream phân tích cảm xúc tới Python service tại: {Url}", _pythonServiceUrl);
                var response = await client.DetectEmotionStreamAsync(request, deadline: DateTime.UtcNow.AddSeconds(5));
                
                return response;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Lỗi khi gọi gRPC DetectEmotionStream");
                // Trả về một phản hồi lỗi thay vì crash hệ thống
                return new EmotionResponse
                {
                    Emotion = "Error",
                    Confidence = 0,
                    BoundingBox = new Box { Xmin = 0, Ymin = 0, Xmax = 0, Ymax = 0 }
                };
            }
        }

        public async Task<EmotionResponse> DetectEmotionSingleAsync(byte[] imageBytes)
        {
            try
            {
                // Cho phép gọi HTTP không an toàn (nếu Python Service chạy http thông thường)
                AppContext.SetSwitch("System.Net.Http.SocketsHttpHandler.Http2UnencryptedSupport", true);

                using var channel = GrpcChannel.ForAddress(_pythonServiceUrl);
                var client = new EmotionService.EmotionServiceClient(channel);

                var request = new EmotionRequest
                {
                    ImageBytes = Google.Protobuf.ByteString.CopyFrom(imageBytes)
                };

                _logger.LogInformation("Gửi yêu cầu gRPC Single phân tích cảm xúc tới Python service tại: {Url}", _pythonServiceUrl);
                var response = await client.DetectEmotionSingleAsync(request, deadline: DateTime.UtcNow.AddSeconds(5));
                
                return response;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Lỗi khi gọi gRPC DetectEmotionSingle");
                // Trả về một phản hồi lỗi thay vì crash hệ thống
                return new EmotionResponse
                {
                    Emotion = "Error",
                    Confidence = 0,
                    BoundingBox = new Box { Xmin = 0, Ymin = 0, Xmax = 0, Ymax = 0 }
                };
            }
        }
    }
}
