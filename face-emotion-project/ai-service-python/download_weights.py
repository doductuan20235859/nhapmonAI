import urllib.request
import os
import sys

# Configure UTF-8 encoding for stdout on Windows to prevent UnicodeEncodeError
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except AttributeError:
    pass

def download_weights():
    # URL trực tiếp tải trọng số MiniXception từ repo nổi tiếng face_classification của oarriaga
    url = "https://github.com/oarriaga/face_classification/raw/master/trained_models/emotion_models/fer2013_mini_XCEPTION.102-0.66.hdf5"
    filename = "mini_xception_weights.h5"
    
    print(f"[*] Đang bắt đầu tải tệp trọng số từ:\n{url}")
    print("[*] Vui lòng chờ trong giây lát (Dung lượng tệp chỉ khoảng 800 KB)...")
    
    try:
        # Tải file về
        urllib.request.urlretrieve(url, filename)
        if os.path.exists(filename) and os.path.getsize(filename) > 100000:
            print(f"[+] Đã tải thành công tệp trọng số và lưu thành: {filename} ({os.path.getsize(filename) / 1024:.2f} KB)")
            return True
        else:
            print("[-] Tải tệp không hoàn chỉnh hoặc kích thước tệp quá nhỏ.")
            return False
    except Exception as e:
        print(f"[!] Lỗi khi tải tệp trọng số: {e}")
        print("[!] Bạn có thể tải thủ công tại link trên và lưu tên file thành 'mini_xception_weights.h5'")
        return False

if __name__ == "__main__":
    download_weights()
