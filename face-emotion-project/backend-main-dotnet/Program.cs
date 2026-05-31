using BackendMainDotnet.Services;
using BackendMainDotnet.Controllers;

var builder = WebApplication.CreateBuilder(args);

// 1. Đăng ký các dịch vụ Controller và Swagger/OpenAPI
builder.Services.AddControllers();
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();

// 2. Đăng ký SignalR để kết nối thời gian thực qua WebSockets và cho phép nhận file ảnh kích thước lớn
builder.Services.AddSignalR(options =>
{
    options.MaximumReceiveMessageSize = 1024 * 1024; // 1 MB
});

// 3. Đăng ký EmotionGrpcClient làm Singleton để tái sử dụng kết nối kênh gRPC
builder.Services.AddSingleton<IEmotionGrpcClient, EmotionGrpcClient>();

// 4. Cấu hình CORS để cho phép Frontend (Vite) truy cập các tài nguyên
builder.Services.AddCors(options =>
{
    options.AddPolicy("AllowFrontend", policy =>
    {
        policy.WithOrigins("http://localhost:5173") // Cổng mặc định của Vite
              .AllowAnyHeader()
              .AllowAnyMethod()
              .AllowCredentials(); // Bắt buộc phải có để SignalR hoạt động qua CORS
    });
});

var app = builder.Build();

// Cấu hình HTTP request pipeline
if (app.Environment.IsDevelopment())
{
    app.UseSwagger();
    app.UseSwaggerUI();
}

app.UseHttpsRedirection();

// Kích hoạt chính sách CORS
app.UseCors("AllowFrontend");

app.UseAuthorization();

// Ánh xạ các HTTP Controllers
app.MapControllers();

// Ánh xạ SignalR Hub
app.MapHub<EmotionHub>("/emotionHub");

app.Run();
