import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, scrolledtext
import img2pdf
from PIL import Image
import threading
import io
import glob
from reportlab.lib.pagesizes import A4, landscape
import tempfile
import subprocess
import sys
import platform
import shutil
import datetime
import re

# Thử import torch, nếu không được thì bỏ qua phần kiểm tra GPU
try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

class ImageToPDFConverter:
    def __init__(self, root):
        self.root = root
        self.root.title("Chuyển Đổi Ảnh Sang PDF")
        self.root.geometry("700x600")
        self.root.resizable(True, True)
        
        # Kiểm tra GPU một cách an toàn
        self.has_gpu = False
        self.gpu_name = "Không có"
        self.gpu_info = "Không có thông tin"
        self.cuda_version = "Không có"
        
        # Các biến cho quản lý file tạm
        self.temp_folder = os.path.join(tempfile.gettempdir(), "ImageToPDF")
        self.temp_files = []
        self.temp_folders = []
        
        # Đảm bảo thư mục tạm tồn tại
        os.makedirs(self.temp_folder, exist_ok=True)
        
        # Thực hiện kiểm tra GPU chi tiết
        self.check_gpu_detailed()
        
        # Các biến
        self.input_folder = tk.StringVar()
        self.output_file = tk.StringVar()
        self.status = tk.StringVar()
        self.progress = tk.DoubleVar()
        self.current_file = tk.StringVar()
        self.preserve_ratio = tk.BooleanVar(value=True)
        self.separate_by_ratio = tk.BooleanVar(value=True)
        self.force_gpu = tk.BooleanVar(value=False)
        self.auto_clean_temp = tk.BooleanVar(value=True)
        
        self.create_widgets()
        
        # Kiểm tra và hiển thị thông tin về dung lượng tạm khi khởi động
        self.check_temp_storage()
        
        # Thiết lập xử lý khi đóng ứng dụng
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def check_gpu_detailed(self):
        """Kiểm tra GPU với nhiều phương pháp khác nhau"""
        gpu_info = []
        
        # Phương pháp 1: Kiểm tra bằng PyTorch
        if TORCH_AVAILABLE:
            try:
                self.has_gpu = torch.cuda.is_available()
                if self.has_gpu:
                    try:
                        self.gpu_name = torch.cuda.get_device_name(0)
                        gpu_info.append(f"PyTorch: {self.gpu_name}")
                        
                        # Hiển thị phiên bản CUDA từ PyTorch
                        if hasattr(torch.version, 'cuda'):
                            torch_cuda_version = torch.version.cuda
                            gpu_info.append(f"PyTorch CUDA: {torch_cuda_version}")
                        
                    except Exception as e:
                        gpu_info.append(f"PyTorch lỗi: {str(e)}")
                else:
                    gpu_info.append("PyTorch: Không phát hiện GPU")
            except Exception as e:
                gpu_info.append(f"Lỗi PyTorch: {str(e)}")
        
        # Phương pháp 2: Kiểm tra bằng NVIDIA-SMI (cho cả Windows và Linux)
        try:
            result = subprocess.run(['nvidia-smi', '--query-gpu=gpu_name,driver_version,cuda_version', '--format=csv,noheader'], 
                                    capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                gpu_lines = result.stdout.strip().split('\n')
                for line in gpu_lines:
                    parts = line.strip().split(', ')
                    if len(parts) >= 3:
                        gpu_name, driver_ver, cuda_ver = parts
                        self.cuda_version = cuda_ver
                        gpu_info.append(f"NVIDIA-SMI: {gpu_name}, Driver: {driver_ver}, CUDA: {cuda_ver}")
                    else:
                        gpu_info.append(f"NVIDIA-SMI: {line.strip()}")
                
                if not self.has_gpu:  # Nếu PyTorch không phát hiện nhưng nvidia-smi có
                    self.has_gpu = True
                    self.gpu_name = "NVIDIA GPU (PyTorch không nhận diện)"
        except (subprocess.SubprocessError, FileNotFoundError):
            gpu_info.append("NVIDIA-SMI: Không có hoặc không chạy được")
        
        # Phương pháp 3: Kiểm tra bằng DirectX Info (chỉ Windows)
        if platform.system() == 'Windows':
            try:
                import wmi
                c = wmi.WMI()
                for gpu in c.Win32_VideoController():
                    gpu_info.append(f"DirectX: {gpu.Name} ({gpu.AdapterRAM/(1024**2):.0f} MB)")
                    # Nếu tên GPU chứa NVIDIA và chưa phát hiện GPU
                    if 'nvidia' in gpu.Name.lower() and not self.has_gpu:
                        self.has_gpu = True
                        self.gpu_name = gpu.Name
            except Exception:
                try:
                    result = subprocess.run(['dxdiag', '/t', 'dxdiag_output.txt'], 
                                           shell=True, capture_output=True, text=True)
                    if os.path.exists('dxdiag_output.txt'):
                        with open('dxdiag_output.txt', 'r') as f:
                            content = f.read()
                            if 'NVIDIA' in content:
                                gpu_info.append("DirectX: Phát hiện GPU NVIDIA")
                                if not self.has_gpu:
                                    self.has_gpu = True
                                    self.gpu_name = "NVIDIA GPU (phát hiện qua DirectX)"
                        os.remove('dxdiag_output.txt')
                except Exception:
                    gpu_info.append("DirectX: Không thể kiểm tra")
        
        # Thêm thông tin CUDA 
        gpu_info.append(f"CUDA  đã được phát hiện trên hệ thống")
        self.cuda_version = ""
        
        self.gpu_info = "\n".join(gpu_info) if gpu_info else "Không có thông tin GPU"
    
    def check_temp_storage(self):
        """Kiểm tra dung lượng tạm và hiển thị thông tin"""
        temp_size = 0
        temp_files_count = 0
        
        # Kiểm tra thư mục tạm của ứng dụng
        if os.path.exists(self.temp_folder):
            for root, dirs, files in os.walk(self.temp_folder):
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        temp_size += os.path.getsize(file_path)
                        temp_files_count += 1
                    except OSError:
                        pass
        
        # Kiểm tra các thư mục tạm khác được tạo bởi tempfile
        pattern = re.compile(r'^tmp.*|.*_img2pdf_.*$')
        for root, dirs, files in os.walk(tempfile.gettempdir()):
            for file in files:
                if pattern.match(file):
                    file_path = os.path.join(root, file)
                    try:
                        temp_size += os.path.getsize(file_path)
                        temp_files_count += 1
                    except OSError:
                        pass
        
        # Chuyển đổi kích thước sang MB
        temp_size_mb = temp_size / (1024 * 1024)
        
        # Cập nhật thông tin dung lượng tạm
        if hasattr(self, 'temp_storage_label'):
            self.temp_storage_label.config(
                text=f"Dung lượng tạm: {temp_size_mb:.2f} MB ({temp_files_count} files)",
                foreground="red" if temp_size_mb > 100 else "black"
            )
        
        return temp_size_mb, temp_files_count
    
    def clean_temp_files(self, all_temps=False):
        """Dọn dẹp các file tạm"""
        files_removed = 0
        size_freed = 0
        
        try:
            # Dọn dẹp các file tạm đã theo dõi
            for temp_file in self.temp_files:
                if os.path.exists(temp_file):
                    try:
                        size = os.path.getsize(temp_file)
                        os.unlink(temp_file)
                        size_freed += size
                        files_removed += 1
                    except OSError:
                        pass
            
            # Dọn dẹp các thư mục tạm đã theo dõi
            for temp_dir in self.temp_folders:
                if os.path.exists(temp_dir):
                    try:
                        # Tính kích thước thư mục trước
                        dir_size = 0
                        for root, dirs, files in os.walk(temp_dir):
                            for file in files:
                                file_path = os.path.join(root, file)
                                try:
                                    dir_size += os.path.getsize(file_path)
                                except OSError:
                                    pass
                        
                        # Xóa thư mục
                        shutil.rmtree(temp_dir, ignore_errors=True)
                        size_freed += dir_size
                        files_removed += 1
                    except OSError:
                        pass
            
            # Xóa tất cả file tạm nếu được yêu cầu
            if all_temps:
                # Dọn dẹp thư mục tạm của ứng dụng
                if os.path.exists(self.temp_folder):
                    for root, dirs, files in os.walk(self.temp_folder):
                        for file in files:
                            file_path = os.path.join(root, file)
                            try:
                                size = os.path.getsize(file_path)
                                os.unlink(file_path)
                                size_freed += size
                                files_removed += 1
                            except OSError:
                                pass
                
                # Tìm và xóa các file tạm khác liên quan đến img2pdf
                pattern = re.compile(r'^tmp.*|.*_img2pdf_.*$')
                for root, dirs, files in os.walk(tempfile.gettempdir()):
                    for file in files:
                        if pattern.match(file):
                            file_path = os.path.join(root, file)
                            try:
                                # Kiểm tra thời gian tạo file, chỉ xóa nếu đã cũ hơn 1 giờ
                                file_time = os.path.getctime(file_path)
                                if (datetime.datetime.now().timestamp() - file_time) > 3600:
                                    size = os.path.getsize(file_path)
                                    os.unlink(file_path)
                                    size_freed += size
                                    files_removed += 1
                            except OSError:
                                pass
            
            # Đặt lại danh sách file tạm đang theo dõi
            self.temp_files = []
            self.temp_folders = []
            
            # Chuyển đổi kích thước sang MB
            size_freed_mb = size_freed / (1024 * 1024)
            
            # Cập nhật lại thông tin dung lượng
            self.check_temp_storage()
            
            return files_removed, size_freed_mb
            
        except Exception as e:
            self.log(f"Lỗi khi dọn dẹp file tạm: {str(e)}")
            return 0, 0
    
    def create_widgets(self):
        # Frame chính
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Thông tin ứng dụng
        info_frame = ttk.Frame(main_frame)
        info_frame.pack(fill=tk.X, pady=5)
        
        app_info = f"Ứng dụng Chuyển Đổi Ảnh Sang PDF "
        ttk.Label(info_frame, text=app_info, font=("Arial", 8)).pack(anchor=tk.W)
        
        # Thông báo GPU và CUDA
        gpu_frame = ttk.LabelFrame(main_frame, text="Thông tin GPU", padding="5")
        gpu_frame.pack(fill=tk.X, pady=5)
        
        gpu_status = f"Đã phát hiện GPU: {self.gpu_name if self.has_gpu else 'Không có'}"
        gpu_label = ttk.Label(gpu_frame, text=gpu_status, foreground="green" if self.has_gpu else "red")
        gpu_label.pack(anchor=tk.W)
        

        
        # Hiển thị thông tin dung lượng tạm
        self.temp_storage_label = ttk.Label(gpu_frame, text="Dung lượng tạm: Đang kiểm tra...")
        self.temp_storage_label.pack(anchor=tk.W)
        
        # Nút hiển thị thông tin GPU chi tiết
        buttons_frame = ttk.Frame(gpu_frame)
        buttons_frame.pack(fill=tk.X, pady=2)
        
        ttk.Button(buttons_frame, text="Xem chi tiết GPU", 
                  command=lambda: messagebox.showinfo("Thông tin GPU Chi tiết", self.gpu_info)).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(buttons_frame, text="Dọn dẹp file tạm", 
                  command=self.show_cleanup_dialog).pack(side=tk.LEFT, padx=2)
        
        # Tùy chọn ép buộc sử dụng GPU nếu phát hiện
        if self.has_gpu:
            ttk.Checkbutton(gpu_frame, text="Ép buộc sử dụng GPU (với CUDA )", 
                           variable=self.force_gpu).pack(anchor=tk.W)
        
        # Tùy chọn tự động dọn dẹp file tạm
        ttk.Checkbutton(gpu_frame, text="Tự động dọn dẹp file tạm sau khi chuyển đổi", 
                       variable=self.auto_clean_temp).pack(anchor=tk.W)
        
        # Chọn thư mục đầu vào
        input_frame = ttk.LabelFrame(main_frame, text="Thư mục chứa ảnh", padding="5")
        input_frame.pack(fill=tk.X, pady=5)
        
        ttk.Entry(input_frame, textvariable=self.input_folder, width=50).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(input_frame, text="Chọn thư mục", command=self.select_input_folder).pack(side=tk.RIGHT)
        
        # Chọn file đầu ra
        output_frame = ttk.LabelFrame(main_frame, text="File PDF đầu ra", padding="5")
        output_frame.pack(fill=tk.X, pady=5)
        
        ttk.Entry(output_frame, textvariable=self.output_file, width=50).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(output_frame, text="Chọn vị trí", command=self.select_output_file).pack(side=tk.RIGHT)
        
        # Các tùy chọn
        options_frame = ttk.LabelFrame(main_frame, text="Tùy chọn", padding="5")
        options_frame.pack(fill=tk.X, pady=5)
        
        self.sort_by_name = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Sắp xếp theo tên file", variable=self.sort_by_name).pack(anchor=tk.W)
        
        ttk.Checkbutton(options_frame, text="Giữ nguyên tỷ lệ khung hình", variable=self.preserve_ratio).pack(anchor=tk.W)
        
        ttk.Checkbutton(options_frame, text="Tạo PDF riêng cho các tỷ lệ khác nhau (16:9 và 9:16)", 
                       variable=self.separate_by_ratio).pack(anchor=tk.W)
        
        # Nút chuyển đổi
        convert_button = ttk.Button(main_frame, text="Chuyển đổi", command=self.start_conversion)
        convert_button.pack(pady=10)
        
        # Thanh tiến trình
        progress_frame = ttk.Frame(main_frame)
        progress_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(progress_frame, text="Tiến trình tổng thể:").pack(anchor=tk.W)
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress, maximum=100)
        self.progress_bar.pack(fill=tk.X)
        
        # File hiện tại đang xử lý
        file_frame = ttk.Frame(main_frame)
        file_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(file_frame, text="File đang xử lý:").pack(anchor=tk.W)
        ttk.Label(file_frame, textvariable=self.current_file, wraplength=500).pack(anchor=tk.W)
        
        # Khung log
        log_frame = ttk.LabelFrame(main_frame, text="Nhật ký hoạt động", padding="5")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.log_area = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=10)
        self.log_area.pack(fill=tk.BOTH, expand=True)
        self.log_area.config(state=tk.DISABLED)
        
        # Thanh trạng thái
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(status_frame, textvariable=self.status).pack(anchor=tk.W)
        
        # Khởi tạo trạng thái
        self.status.set("Sẵn sàng")
        self.current_file.set("")
        
        # Log thông tin GPU
        self.log(f"Thông tin GPU: {self.gpu_name}")
        if self.has_gpu:
            self.log("GPU đã được phát hiện và sẵn sàng sử dụng với CUDA .")
        else:
            self.log("Không phát hiện GPU, sẽ sử dụng CPU.")
    
    def show_cleanup_dialog(self):
        """Hiển thị hộp thoại dọn dẹp tệp tạm"""
        # Tạo cửa sổ dialog
        cleanup_dialog = tk.Toplevel(self.root)
        cleanup_dialog.title("Quản lý file tạm")
        cleanup_dialog.geometry("500x400")
        cleanup_dialog.transient(self.root)
        cleanup_dialog.grab_set()
        
        # Cho phép thu phóng cửa sổ
        cleanup_dialog.resizable(True, True)
        
        # Thiết lập kích thước tối thiểu để giao diện không bị vỡ
        cleanup_dialog.minsize(400, 300)
        
        # Khung chính - cấu hình để mở rộng khi cửa sổ thay đổi kích thước
        main_frame = ttk.Frame(cleanup_dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Hiển thị thông tin dung lượng hiện tại
        temp_size, temp_count = self.check_temp_storage()
        info_text = f"Phát hiện {temp_count} file tạm, chiếm {temp_size:.2f} MB"
        ttk.Label(main_frame, text=info_text, font=("Arial", 10, "bold")).pack(pady=5, anchor=tk.W)
        
        # Giải thích
        explanation = (
            "File tạm được tạo ra trong quá trình chuyển đổi ảnh sang PDF, "
            "đặc biệt khi xử lý ảnh định dạng WebP hoặc ảnh có kênh trong suốt (RGBA).\n\n"
            "Bạn có thể lựa chọn dọn dẹp các loại file tạm sau:"
        )
        ttk.Label(main_frame, text=explanation, wraplength=480, justify=tk.LEFT).pack(pady=10, fill=tk.X)
        
        # Các tùy chọn
        options_frame = ttk.LabelFrame(main_frame, text="Tùy chọn dọn dẹp", padding="10")
        options_frame.pack(fill=tk.X, pady=5)
        
        # Tùy chọn chỉ dọn file hiện tại
        current_session = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Dọn dẹp file tạm của phiên làm việc hiện tại", 
                       variable=current_session).pack(anchor=tk.W, pady=2)
        
        # Tùy chọn dọn tất cả file tạm
        all_temp = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="Dọn dẹp tất cả file tạm (bao gồm cả file của các phiên trước)", 
                       variable=all_temp).pack(anchor=tk.W, pady=2)
        
        # Tùy chọn tự động dọn dẹp
        ttk.Checkbutton(options_frame, text="Tự động dọn dẹp file tạm sau mỗi lần chuyển đổi", 
                       variable=self.auto_clean_temp).pack(anchor=tk.W, pady=2)
        
        # Khung hiển thị kết quả - cấu hình để mở rộng khi cửa sổ thay đổi kích thước
        result_frame = ttk.LabelFrame(main_frame, text="Kết quả dọn dẹp", padding="10")
        result_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        result_text = scrolledtext.ScrolledText(result_frame, height=8, wrap=tk.WORD)
        result_text.pack(fill=tk.BOTH, expand=True)
        result_text.insert(tk.END, "Nhấn 'Dọn dẹp ngay' để bắt đầu quá trình dọn dẹp...\n")
        result_text.config(state=tk.DISABLED)
        
        # Hàm xử lý khi nhấn nút dọn dẹp
        def do_cleanup():
            try:
                result_text.config(state=tk.NORMAL)
                result_text.delete(1.0, tk.END)
                result_text.insert(tk.END, "Đang dọn dẹp file tạm...\n")
                
                # Thực hiện dọn dẹp
                files_removed, size_freed = self.clean_temp_files(all_temp.get())
                
                # Hiển thị kết quả
                result_text.insert(tk.END, f"Đã xóa {files_removed} file tạm.\n")
                result_text.insert(tk.END, f"Đã giải phóng {size_freed:.2f} MB dung lượng.\n")
                
                # Cập nhật thông tin dung lượng hiện tại
                new_temp_size, new_temp_count = self.check_temp_storage()
                result_text.insert(tk.END, f"\nDung lượng tạm hiện tại: {new_temp_size:.2f} MB ({new_temp_count} files)")
                
                if new_temp_count == 0:
                    result_text.insert(tk.END, "\n\nĐã dọn sạch tất cả file tạm!")
                
                # Cập nhật UI
                self.check_temp_storage()
                
                result_text.config(state=tk.DISABLED)
            except Exception as e:
                result_text.insert(tk.END, f"Lỗi khi dọn dẹp: {str(e)}")
                result_text.config(state=tk.DISABLED)
        
        # Nút điều khiển - sử dụng Frame với fill=X để các nút có thể điều chỉnh khi cửa sổ thay đổi
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(button_frame, text="Dọn dẹp ngay", command=do_cleanup).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Đóng", command=cleanup_dialog.destroy).pack(side=tk.RIGHT, padx=5)
        
        # Cập nhật tham số wraplength của label giải thích khi cửa sổ thay đổi kích thước
        def on_resize(event):
            for widget in main_frame.winfo_children():
                if isinstance(widget, ttk.Label) and hasattr(widget, 'cget') and widget.cget('wraplength') == 480:
                    # Đặt wraplength mới dựa trên kích thước hiện tại của cửa sổ (trừ đi padding)
                    widget.configure(wraplength=event.width - 30)
        
        # Gắn sự kiện thay đổi kích thước
        cleanup_dialog.bind("<Configure>", on_resize)
        
        # Đặt focus cho cửa sổ
        cleanup_dialog.focus_set()
    
    def select_input_folder(self):
        folder = filedialog.askdirectory(title="Chọn thư mục chứa ảnh")
        if folder:
            self.input_folder.set(folder)
            self.status.set(f"Đã chọn thư mục: {folder}")
            self.log(f"Đã chọn thư mục đầu vào: {folder}")
    
    def select_output_file(self):
        file = filedialog.asksaveasfilename(
            title="Lưu file PDF",
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        if file:
            if not file.lower().endswith('.pdf'):
                file += '.pdf'
            self.output_file.set(file)
            self.status.set(f"File đầu ra: {file}")
            self.log(f"Đã chọn file đầu ra: {file}")
    
    def log(self, message):
        self.log_area.config(state=tk.NORMAL)
        # Thêm timestamp
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_area.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_area.see(tk.END)  # Cuộn xuống cuối
        self.log_area.config(state=tk.DISABLED)
        # Cập nhật giao diện ngay lập tức
        self.root.update()
    
    def start_conversion(self):
        input_folder = self.input_folder.get()
        output_file = self.output_file.get()
        
        if not input_folder or not os.path.isdir(input_folder):
            messagebox.showerror("Lỗi", "Vui lòng chọn thư mục chứa ảnh hợp lệ")
            return
        
        if not output_file:
            messagebox.showerror("Lỗi", "Vui lòng chọn vị trí lưu file PDF")
            return
        
        # Xóa nội dung log cũ
        self.log_area.config(state=tk.NORMAL)
        self.log_area.delete(1.0, tk.END)
        self.log_area.config(state=tk.DISABLED)
        
        # Reset tiến trình
        self.progress.set(0)
        self.current_file.set("")
        
        # Đặt lại danh sách file tạm
        self.temp_files = []
        self.temp_folders = []
        
        # Thiết lập GPU nếu được yêu cầu
        if self.has_gpu and self.force_gpu.get() and TORCH_AVAILABLE:
            try:
                self.log("Đang kích hoạt GPU với CUDA ...")
                if torch.cuda.is_available():
                    # Thiết lập torch để sử dụng GPU
                    torch.cuda.set_device(0)
                    # Thử tạo một tensor nhỏ trên GPU để kiểm tra
                    test_tensor = torch.tensor([1.0, 2.0], device='cuda')
                    self.log(f"Đã kích hoạt GPU thành công: {torch.cuda.get_device_name(0)} với CUDA ")
                else:
                    self.log("Không thể kích hoạt GPU thông qua PyTorch.")
                    # Thiết lập biến môi trường để cố gắng sử dụng GPU
                    os.environ['CUDA_VISIBLE_DEVICES'] = '0'
            except Exception as e:
                self.log(f"Lỗi khi kích hoạt GPU: {str(e)}")
        
        # Bắt đầu chuyển đổi trong một luồng riêng biệt
        threading.Thread(target=self.convert_images_to_pdf, daemon=True).start()
    
    def is_landscape(self, img):
        width, height = img.size
        return width > height
    
    def get_aspect_ratio(self, img):
        width, height = img.size
        if self.is_landscape(img):
            # Tỷ lệ gần 16:9
            return "landscape" if (width / height) > 1.5 else "other"
        else:
            # Tỷ lệ gần 9:16
            return "portrait" if (height / width) > 1.5 else "other"
    
    def convert_images_to_pdf(self):
        try:
            input_folder = self.input_folder.get()
            output_file = self.output_file.get()
            preserve_ratio = self.preserve_ratio.get()
            separate_by_ratio = self.separate_by_ratio.get()
            
            self.log("Bắt đầu quá trình chuyển đổi...")
            self.status.set("Đang tìm các file ảnh...")
            
            # Tìm tất cả các file ảnh
            image_extensions = ["*.jpg", "*.jpeg", "*.png", "*.webp"]
            image_files = []
            
            for ext in image_extensions:
                image_files.extend(glob.glob(os.path.join(input_folder, ext)))
                image_files.extend(glob.glob(os.path.join(input_folder, ext.upper())))
            
            if not image_files:
                self.log("Không tìm thấy file ảnh nào trong thư mục.")
                self.status.set("Không có file ảnh")
                messagebox.showerror("Lỗi", "Không tìm thấy file ảnh nào trong thư mục")
                return
            
            # Sắp xếp file theo tên
            if self.sort_by_name.get():
                image_files.sort()
                self.log(f"Đã sắp xếp {len(image_files)} file ảnh theo tên.")
            
            self.log(f"Tìm thấy {len(image_files)} file ảnh.")
            self.status.set(f"Đang xử lý {len(image_files)} file ảnh...")
            
            # Phân loại ảnh theo tỷ lệ khung hình nếu được yêu cầu
            if separate_by_ratio:
                landscape_images = []  # 16:9
                portrait_images = []   # 9:16
                other_images = []      # Tỷ lệ khác
                
                self.log("Phân loại ảnh theo tỷ lệ khung hình...")
                
                for i, img_path in enumerate(image_files):
                    # Cập nhật tiến trình
                    progress = (i / len(image_files)) * 50  # 50% cho việc phân loại
                    self.progress.set(progress)
                    self.current_file.set(os.path.basename(img_path))
                    self.status.set(f"Đang phân loại ảnh: {i+1}/{len(image_files)}")
                    
                    try:
                        with Image.open(img_path) as img:
                            ratio_type = self.get_aspect_ratio(img)
                            
                            if ratio_type == "landscape":
                                landscape_images.append(img_path)
                                self.log(f"Ảnh {os.path.basename(img_path)}: Tỷ lệ 16:9 (ngang)")
                            elif ratio_type == "portrait":
                                portrait_images.append(img_path)
                                self.log(f"Ảnh {os.path.basename(img_path)}: Tỷ lệ 9:16 (dọc)")
                            else:
                                other_images.append(img_path)
                                self.log(f"Ảnh {os.path.basename(img_path)}: Tỷ lệ khác")
                    except Exception as e:
                        self.log(f"Lỗi khi phân loại ảnh {os.path.basename(img_path)}: {str(e)}")
                        continue
                
                self.log(f"Kết quả phân loại: {len(landscape_images)} ảnh 16:9, {len(portrait_images)} ảnh 9:16, {len(other_images)} ảnh tỷ lệ khác.")
                
                # Tạo các file PDF riêng cho từng nhóm
                output_base = os.path.splitext(output_file)[0]
                
                if landscape_images:
                    landscape_pdf = f"{output_base}_16x9.pdf"
                    self.create_pdf_for_images(landscape_images, landscape_pdf, "landscape", 50, 75)
                
                if portrait_images:
                    portrait_pdf = f"{output_base}_9x16.pdf"
                    self.create_pdf_for_images(portrait_images, portrait_pdf, "portrait", 75, 100)
                
                if other_images:
                    other_pdf = f"{output_base}_other.pdf"
                    self.create_pdf_for_images(other_images, other_pdf, "other", 50, 75)
                
                self.log("Đã hoàn thành việc tạo các file PDF theo tỷ lệ khung hình.")
                self.status.set("Đã hoàn thành")
                self.progress.set(100)
                
                message = f"Đã tạo thành công các file PDF:\n"
                if landscape_images:
                    message += f"- {len(landscape_images)} ảnh 16:9: {os.path.basename(landscape_pdf)}\n"
                if portrait_images:
                    message += f"- {len(portrait_images)} ảnh 9:16: {os.path.basename(portrait_pdf)}\n"
                if other_images:
                    message += f"- {len(other_images)} ảnh tỷ lệ khác: {os.path.basename(other_pdf)}\n"
                
                # Tự động dọn dẹp nếu được cấu hình
                if self.auto_clean_temp.get():
                    files_removed, size_freed = self.clean_temp_files()
                    self.log(f"Đã tự động dọn dẹp {files_removed} file tạm, giải phóng {size_freed:.2f} MB.")
                
                messagebox.showinfo("Thành công", message)
            
            else:
                # Tạo một PDF duy nhất cho tất cả các ảnh
                self.create_pdf_for_images(image_files, output_file, "all", 0, 100)
                
                # Tự động dọn dẹp nếu được cấu hình
                if self.auto_clean_temp.get():
                    files_removed, size_freed = self.clean_temp_files()
                    self.log(f"Đã tự động dọn dẹp {files_removed} file tạm, giải phóng {size_freed:.2f} MB.")
                
                self.log(f"Đã tạo thành công file PDF: {output_file}")
                messagebox.showinfo("Thành công", f"Đã chuyển đổi {len(image_files)} ảnh thành file PDF")
            
        except Exception as e:
            self.log(f"Lỗi: {str(e)}")
            self.status.set(f"Lỗi: {str(e)}")
            messagebox.showerror("Lỗi", f"Đã xảy ra lỗi: {str(e)}")
    
    def create_pdf_for_images(self, image_files, output_file, ratio_type, progress_start, progress_end):
        try:
            self.log(f"Đang tạo file PDF cho {len(image_files)} ảnh {ratio_type}...")
            self.status.set(f"Đang tạo file PDF cho ảnh {ratio_type}...")
            
            # Nếu không có file nào, không tạo PDF
            if not image_files:
                self.log(f"Không có ảnh nào thuộc loại {ratio_type}, bỏ qua.")
                return
            
            # Đảm bảo không có đường dẫn trùng lặp ngay từ đầu
            image_files = list(dict.fromkeys(image_files))
            self.log(f"Số ảnh sau khi loại bỏ trùng lặp ban đầu: {len(image_files)}")
            
            if self.preserve_ratio:
                # Sử dụng cách đơn giản hơn để giữ tỷ lệ khung hình
                temp_files = []
                actual_images = []  # Danh sách chỉ chứa các đường dẫn hợp lệ để chuyển đổi
                
                # Tạo thư mục tạm thời cho phiên làm việc này
                session_temp_dir = os.path.join(self.temp_folder, f"session_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}")
                os.makedirs(session_temp_dir, exist_ok=True)
                self.temp_folders.append(session_temp_dir)
                
                for i, img_path in enumerate(image_files):
                    progress = progress_start + ((i / len(image_files)) * (progress_end - progress_start))
                    self.progress.set(progress)
                    self.current_file.set(os.path.basename(img_path))
                    self.status.set(f"Đang xử lý ảnh ({ratio_type}): {i+1}/{len(image_files)}")
                    
                    try:
                        with Image.open(img_path) as img:
                            # Xử lý ảnh webp hoặc RGBA
                            if img_path.lower().endswith('.webp') or img.mode == 'RGBA':
                                img = img.convert('RGB')
                                
                                # Tạo file tạm thời trong thư mục tạm của phiên làm việc
                                tmp_file = os.path.join(session_temp_dir, f"temp_{i}_{os.path.basename(img_path)}.jpg")
                                img.save(tmp_file, 'JPEG')
                                temp_files.append(tmp_file)
                                self.temp_files.append(tmp_file)  # Theo dõi để dọn dẹp sau
                                
                                # Thêm vào danh sách chuyển đổi
                                actual_images.append(tmp_file)
                            else:
                                # Nếu là file thông thường, thêm vào danh sách
                                actual_images.append(img_path)
                    
                        self.log(f"Đã xử lý: {os.path.basename(img_path)}")
                    except Exception as e:
                        self.log(f"Lỗi khi xử lý ảnh {os.path.basename(img_path)}: {str(e)}")
                        continue
                
                # Kiểm tra và lọc danh sách một lần nữa để đảm bảo không có trùng lặp
                actual_images = list(dict.fromkeys(actual_images))
                self.log(f"Số ảnh sau khi lọc và loại bỏ trùng lặp: {len(actual_images)}")
                
                # Chỉ giữ lại những file thực sự tồn tại
                actual_images = [img for img in actual_images if os.path.exists(img)]
                
                # Sử dụng giải pháp thay thế an toàn hơn, không dùng layout_fun
                try:
                    if actual_images:
                        # Debug: Ghi ra danh sách file thực sự được chuyển đổi
                        self.log(f"Chuyển đổi {len(actual_images)} file ảnh sang PDF...")
                        
                        # Chuyển đổi thành PDF
                        with open(output_file, "wb") as f:
                            # Sử dụng cài đặt img2pdf đơn giản, để nó tự giữ tỷ lệ
                            pdf_data = img2pdf.convert(actual_images)
                            f.write(pdf_data)
                        
                        # Kiểm tra kết quả
                        file_size = os.path.getsize(output_file) / 1024  # kB
                        self.log(f"File PDF đã được tạo: {output_file} (kích thước: {file_size:.2f} kB)")
                        
                        # Phân tích file PDF để kiểm tra số trang
                        try:
                            from pikepdf import Pdf
                            with Pdf.open(output_file) as pdf:
                                page_count = len(pdf.pages)
                                self.log(f"Số trang trong file PDF: {page_count} (mong đợi: {len(actual_images)})")
                                
                                # Cảnh báo nếu số trang khác với số ảnh
                                if page_count != len(actual_images):
                                    self.log("Cảnh báo: Số trang PDF không khớp với số ảnh đầu vào!")
                        except ImportError:
                            self.log("Thư viện pikepdf không có sẵn, bỏ qua kiểm tra số trang PDF.")
                    else:
                        self.log("Không có ảnh nào được xử lý thành công.")
                        raise Exception("Không có ảnh nào được xử lý thành công")
                except Exception as e:
                    self.log(f"Lỗi khi tạo PDF với img2pdf: {str(e)}")
                    self.log("Thử phương pháp thay thế với Pillow...")
                    
                    # Phương pháp thay thế nếu img2pdf gặp vấn đề
                    first_image = None
                    pdf_images = []
                    
                    for img_path in actual_images:
                        try:
                            with Image.open(img_path) as img:
                                if img.mode == 'RGBA':
                                    img = img.convert('RGB')
                                
                                # Lưu bản sao của ảnh để tránh ảnh hưởng đến file gốc
                                img_copy = img.copy()
                                
                                if not first_image:
                                    first_image = img_copy
                                else:
                                    pdf_images.append(img_copy)
                        except Exception as img_err:
                            self.log(f"Bỏ qua ảnh lỗi: {os.path.basename(img_path)}: {str(img_err)}")
                    
                    if first_image:
                        # Nếu chỉ có một ảnh
                        if len(pdf_images) == 0:
                            first_image.save(output_file, 'PDF')
                            self.log(f"Đã lưu 1 ảnh sang PDF bằng Pillow")
                        else:
                            # Nhiều ảnh - sử dụng append_images
                            first_image.save(
                                output_file, 
                                'PDF', 
                                save_all=True, 
                                append_images=pdf_images
                            )
                            self.log(f"Đã lưu {len(pdf_images) + 1} ảnh sang PDF bằng Pillow")
                    else:
                        raise Exception("Không thể tạo PDF với cả hai phương pháp")
            
            else:
                # Phương pháp cũ (không giữ nguyên tỷ lệ)
                valid_images = []
                
                for i, img_path in enumerate(image_files):
                    progress = progress_start + ((i / len(image_files)) * (progress_end - progress_start))
                    self.progress.set(progress)
                    self.current_file.set(os.path.basename(img_path))
                    self.status.set(f"Đang xử lý ảnh ({ratio_type}): {i+1}/{len(image_files)}")
                    
                    try:
                        with Image.open(img_path) as img:
                            if img_path.lower().endswith('.webp') or img.mode == 'RGBA':
                                img = img.convert('RGB')
                                img_buffer = io.BytesIO()
                                img.save(img_buffer, format='JPEG')
                                img_buffer.seek(0)
                                valid_images.append(img_buffer.read())
                            else:
                                valid_images.append(img_path)
                        
                        self.log(f"Đã xử lý: {os.path.basename(img_path)}")
                    except Exception as e:
                        self.log(f"Lỗi khi xử lý ảnh {os.path.basename(img_path)}: {str(e)}")
                        continue
                
                # Loại bỏ trùng lặp trong danh sách các ảnh đệm
                # Với files, chúng ta có thể kiểm tra đường dẫn
                # Với dữ liệu đệm, không thể kiểm tra trùng lặp dễ dàng nên cứ giữ nguyên
                unique_images = []
                seen_paths = set()
                
                for item in valid_images:
                    if isinstance(item, str):  # Nếu là đường dẫn file
                        if item not in seen_paths:
                            seen_paths.add(item)
                            unique_images.append(item)
                    else:  # Nếu là dữ liệu đệm
                        unique_images.append(item)
                
                # Tạo PDF
                if unique_images:
                    with open(output_file, "wb") as f:
                        f.write(img2pdf.convert(unique_images))
                        
                        # Ghi log số lượng ảnh đã chuyển đổi
                        self.log(f"Đã chuyển đổi {len(unique_images)} ảnh sang PDF (không giữ tỷ lệ)")
                else:
                    self.log("Không có ảnh nào được xử lý thành công.")
                    raise Exception("Không có ảnh nào được xử lý thành công")
            
            self.log(f"Đã tạo thành công file PDF: {output_file}")
            
        except Exception as e:
            self.log(f"Lỗi khi tạo PDF: {str(e)}")
            raise
    
    def on_closing(self):
        """Xử lý khi đóng ứng dụng"""
        # Hỏi người dùng có muốn dọn dẹp trước khi thoát nếu có file tạm
        temp_size, temp_count = self.check_temp_storage()
        
        if temp_count > 0:
            if messagebox.askyesno("Dọn dẹp file tạm", 
                                 f"Đã phát hiện {temp_count} file tạm ({temp_size:.2f} MB). Bạn có muốn dọn dẹp trước khi thoát không?"):
                files_removed, size_freed = self.clean_temp_files(all_temps=True)
                messagebox.showinfo("Đã dọn dẹp", f"Đã xóa {files_removed} file tạm, giải phóng {size_freed:.2f} MB dung lượng.")
        
        # Đóng ứng dụng
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageToPDFConverter(root)
    root.mainloop()