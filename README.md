# Ứng dụng Chuyển Đổi Ảnh Sang PDF

![Version](https://img.shields.io/badge/version-1.1.0-blue)
![Python](https://img.shields.io/badge/python-3.9-green)
![License](https://img.shields.io/badge/license-MIT-orange)

Ứng dụng Python để chuyển đổi hàng loạt ảnh thành file PDF với nhiều tùy chọn đa dạng, hỗ trợ nhiều tỷ lệ khung hình và tối ưu hóa GPU.



## 📋 Tính năng chính

- **Chuyển đổi hàng loạt:** Xử lý nhiều file ảnh cùng lúc
- **Hỗ trợ nhiều định dạng:** JPG, JPEG, PNG, WEBP
- **Giữ nguyên tỷ lệ khung hình:** Đảm bảo ảnh 16:9 không bị thu nhỏ thành 9:16
- **Tạo PDF riêng theo tỷ lệ:** Phân loại ảnh theo tỷ lệ khung hình và tạo file PDF riêng
- **Tận dụng GPU:** Hỗ trợ tăng tốc GPU cho máy tính có card đồ họa NVIDIA
- **Quản lý file tạm:** Tự động hoặc thủ công dọn dẹp các file tạm để tiết kiệm dung lượng
- **Giao diện thân thiện:** Hiển thị tiến trình xử lý và nhật ký hoạt động

## 🖥️ Yêu cầu hệ thống

- **Hệ điều hành:** Windows 10/11, macOS, Linux
- **Python:** Phiên bản 3.9 trở lên
- **GPU (tùy chọn):** NVIDIA GPU với driver cập nhật
- **Dung lượng trống:** Tối thiểu 2GB
- **RAM:** Tối thiểu 4GB

## 📦 Thư viện sử dụng

- [Pillow (PIL)](https://python-pillow.org/): Xử lý ảnh
- [img2pdf](https://gitlab.mister-muffin.de/josch/img2pdf): Chuyển đổi ảnh sang PDF
- [ReportLab](https://www.reportlab.com/): Tạo và điều chỉnh PDF
- [PyTorch](https://pytorch.org/) (tùy chọn): Tận dụng GPU để tăng tốc xử lý
- [tkinter](https://docs.python.org/3/library/tkinter.html): Xây dựng giao diện người dùng

## 🔧 Cài đặt

### Cài đặt với Conda (Khuyến nghị)

```bash
# Tạo môi trường mới
conda create --name img2pdf_env python=3.9
conda activate img2pdf_env

# Cài đặt các thư viện cần thiết
conda install pillow
pip install img2pdf reportlab wmi

# Cài đặt PyTorch với CUDA (nếu có GPU NVIDIA)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121

# Cài đặt với pip và venv

```bash
# Tạo môi trường ảo
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# Cài đặt các thư viện cần thiết
pip install -r requirements.txt
```

Nội dung file `requirements.txt`:

```plaintext
pillow>=9.0.0
img2pdf>=0.4.0
reportlab>=3.6.0
wmi>=1.5.1;platform_system=="Windows"
# PyTorch cần được cài đặt riêng với lệnh:
# pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
```

## Cài đặt trực tiếp (không dùng môi trường ảo)

Nếu bạn không muốn sử dụng môi trường ảo, bạn có thể cài đặt trực tiếp các thư viện cần thiết:

```bash
# Cài đặt các thư viện cần thiết
pip install pillow img2pdf reportlab
pip install wmi  # Chỉ cho Windows

# Cài đặt PyTorch (Tùy vào hệ thống của bạn)
# Với CUDA:
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
# Hoặc phiên bản CPU:
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

## Cài đặt trên VSCode

Nếu bạn sử dụng VSCode, bạn có thể làm theo các bước sau:

1. Mở VSCode và cài đặt extension Python
2. Mở terminal trong VSCode và tạo môi trường ảo:

```bash
python -m venv .venv
```

3. Chọn môi trường này làm interpreter trong VSCode:
   - Nhấn `Ctrl+Shift+P` (hoặc `Cmd+Shift+P` trên macOS)
   - Tìm và chọn "Python: Select Interpreter"
   - Chọn môi trường vừa tạo (`.venv`)

4. Cài đặt các thư viện cần thiết:

```bash
pip install pillow img2pdf reportlab
```

5. Mở file `app.py` và chạy trực tiếp trong VSCode

---

## 🚀 Cách sử dụng

### Chạy ứng dụng

```bash
# Kích hoạt môi trường (nếu sử dụng)
conda activate img2pdf_env  # nếu dùng conda
source venv/bin/activate    # Linux/macOS với venv
venv\Scripts\activate       # Windows với venv

# Chạy ứng dụng
python app.py
```

### Các bước sử dụng

1. **Chọn thư mục chứa ảnh**  
   Nhấn nút "Chọn thư mục" và duyệt đến thư mục chứa các file ảnh cần chuyển đổi

2. **Chọn vị trí lưu file PDF**  
   Nhấn nút "Chọn vị trí" và chỉ định nơi lưu và tên file PDF đầu ra

3. **Cấu hình tùy chọn**
   - Sắp xếp theo tên file: Sắp xếp các ảnh theo tên file
   - Giữ nguyên tỷ lệ khung hình: Đảm bảo ảnh 16:9 không bị thu nhỏ khi chuyển sang PDF
   - Tạo PDF riêng cho các tỷ lệ khác nhau: Tự động tạo các file PDF riêng cho ảnh 16:9 và 9:16
   - Ép buộc sử dụng GPU: Kích hoạt khi có GPU nhưng không được nhận diện tự động
   - Tự động dọn dẹp file tạm: Xóa các file tạm sau khi hoàn tất chuyển đổi

4. **Bắt đầu chuyển đổi**  
   Nhấn nút "Chuyển đổi" để bắt đầu quá trình  
   Theo dõi tiến trình trong khung nhật ký hoạt động

---

### Dọn dẹp file tạm

Ứng dụng tạo ra các file tạm khi xử lý ảnh, đặc biệt là ảnh WebP và ảnh có kênh alpha. Để dọn dẹp:

1. Nhấn nút "Dọn dẹp file tạm" trong giao diện
2. Chọn một trong các tùy chọn:
   - Dọn dẹp file tạm của phiên hiện tại
   - Dọn dẹp tất cả file tạm (bao gồm cả file của phiên trước)
3. Nhấn "Dọn dẹp ngay" để thực hiện

---

## 📋 Cấu trúc mã nguồn

```plaintext
image_to_pdf/
├── app.py     # Mã nguồn chính của ứng dụng
├── requirements.txt    # Danh sách các thư viện cần thiết
├── README.md           # Tài liệu hướng dẫn

```

---

## ⚠️ Xử lý vấn đề thường gặp

1. **Không phát hiện GPU**
   - Đảm bảo đã cài đặt driver NVIDIA mới nhất
   - Kiểm tra xem CUDA có được cài đặt đúng cách không
   - Đánh dấu vào tùy chọn "Ép buộc sử dụng GPU"

2. **Lỗi "Out of Memory" khi xử lý ảnh lớn**
   - Đảm bảo biến môi trường đã được thiết lập: `PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512`
   - Xử lý ít ảnh hơn mỗi lần hoặc giảm kích thước ảnh

3. **Ảnh không hiển thị đúng trong PDF**
   - Đảm bảo đã chọn tùy chọn "Giữ nguyên tỷ lệ khung hình"
   - Đối với ảnh 16:9, hãy sử dụng tùy chọn "Tạo PDF riêng cho các tỷ lệ khác nhau"

4. **Dung lượng ổ đĩa giảm sau khi sử dụng**
   - Nhấn nút "Dọn dẹp file tạm" để giải phóng dung lượng
   - Đánh dấu vào tùy chọn "Tự động dọn dẹp file tạm sau khi chuyển đổi"

5. **Trang PDF bị trùng lặp**
   - Đảm bảo bạn đang sử dụng phiên bản mới nhất của ứng dụng
   - Tránh thêm cùng một thư mục ảnh nhiều lần
   - Xóa toàn bộ file tạm trước khi thực hiện chuyển đổi mới

6. **Lỗi "No module named..." khi chạy ứng dụng**
   - Đảm bảo đã kích hoạt môi trường ảo đúng cách
   - Kiểm tra xem đã cài đặt đầy đủ các thư viện trong `requirements.txt` chưa
   - Thử cài đặt lại thư viện đang bị lỗi: `pip install [tên_thư_viện]`

7. **Lỗi khi sử dụng VSCode**
   - Đảm bảo đã chọn đúng interpreter Python trong VSCode
   - Kích hoạt môi trường ảo trong terminal VSCode trước khi chạy
   - Nếu sử dụng Windows, có thể cần thiết lập chính sách thực thi script: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

---

## 🔒 Bảo mật

- Ứng dụng chỉ xử lý file cục bộ và không gửi dữ liệu qua mạng
- Các file tạm được lưu trong thư mục `%TEMP%/ImageToPDF` và được dọn dẹp sau khi sử dụng
- Không có thông tin người dùng nào được thu thập
- Mã nguồn hoàn toàn mở và có thể kiểm tra

Vị trí lưu file tạm:
- **Windows:** `C:\Users\<Username>\AppData\Local\Temp\ImageToPDF`
- **macOS/Linux:** `/tmp/ImageToPDF`

---

## 🛠️ Phát triển

### Các tính năng đang phát triển
- Hỗ trợ nén PDF
- Hỗ trợ mật khẩu bảo vệ PDF
- Thêm chế độ dòng lệnh (CLI)
- Hỗ trợ xử lý đa luồng

### Đóng góp

Đóng góp luôn được chào đón! Nếu bạn muốn đóng góp vào dự án:

1. Fork dự án
2. Tạo nhánh tính năng mới (`git checkout -b feature/amazing-feature`)
3. Commit thay đổi của bạn (`git commit -m 'Add some amazing feature'`)
4. Push lên nhánh (`git push origin feature/amazing-feature`)
5. Mở Pull Request

---

## 📄 Giấy phép

Dự án này được phân phối dưới Giấy phép MIT. Xem tệp `LICENSE` để biết thêm thông tin.

---

## 📞 Liên hệ

[HoangThinh2024 - GitHub Profile](https://github.com/HoangThinh2024)
