using Microsoft.AspNetCore.Mvc;
using BackendMainDotnet.Services;

namespace BackendMainDotnet.Controllers
{
    [ApiController]
    [Route("api/[controller]")]
    public class EmotionController : ControllerBase
    {
        private readonly IEmotionGrpcClient _grpcClient;
        private readonly ILogger<EmotionController> _logger;

        public EmotionController(IEmotionGrpcClient grpcClient, ILogger<EmotionController> logger)
        {
            _grpcClient = grpcClient;
            _logger = logger;
        }

        /// <summary>
        /// API nhận diện cảm xúc qua tải lên ảnh HTTP POST
        /// </summary>
        [HttpPost("detect")]
        public async Task<IActionResult> Detect([FromForm] IFormFile file)
        {
            if (file == null || file.Length == 0)
            {
                return BadRequest("Không tìm thấy file ảnh tải lên.");
            }

            try
            {
                using var ms = new MemoryStream();
                await file.CopyToAsync(ms);
                byte[] imageBytes = ms.ToArray();

                var response = await _grpcClient.DetectEmotionAsync(imageBytes);

                return Ok(new
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
                _logger.LogError(ex, "Lỗi xảy ra tại HTTP controller");
                return StatusCode(500, $"Lỗi hệ thống: {ex.Message}");
            }
        }
    }
}
