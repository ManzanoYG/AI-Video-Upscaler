import os
import subprocess
import threading
import time
import json
import shutil
from PySide6.QtWidgets import (
    QApplication, QLineEdit, QWidget, QPushButton, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox, QProgressBar, QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt, QTimer, Signal
import pyqtgraph as pg

# ================= CONFIGURATION =================
FFMPEG = r"C:\ffmpeg\bin\ffmpeg.exe"
FFPROBE = FFMPEG.replace("ffmpeg.exe", "ffprobe.exe")
REALESRGAN_VULKAN = r"C:\real-esrgan\realesrgan-ncnn-vulkan.exe"

BASE_DIR = r"C:\upscale"
FRAMES_DIR = f"{BASE_DIR}\\frames"
UPSCALED_DIR = f"{BASE_DIR}\\upscaled"
PROFILE_PATH = f"{BASE_DIR}\\gpu_profile.json"

# ================= GPU DETECTION =================
def detect_gpus():
    # Simple Vulkan GPU list (adjust to your system)
    return ["GPU 0 Vulkan", "GPU 1 Vulkan"]

# ================= UTILITY FUNCTIONS =================
def run_command(cmd):
    subprocess.run(cmd, check=True)

def count_png(folder):
    return len([f for f in os.listdir(folder) if f.endswith(".png")])

def get_video_resolution(video_path):
    # Extract width and height of a video
    cmd = [
        FFPROBE, "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "csv=p=0", video_path
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, text=True)
    w, h = result.stdout.strip().split(",")
    return int(w), int(h)

def cleanup():
    # Delete all temporary frames
    for folder in [FRAMES_DIR, UPSCALED_DIR]:
        if os.path.exists(folder):
            for root, dirs, files in os.walk(folder, topdown=False):
                for name in files:
                    try:
                        os.remove(os.path.join(root, name))
                    except Exception as e:
                        print(f"Could not delete {name}: {e}")
                for name in dirs:
                    try:
                        os.rmdir(os.path.join(root, name))
                    except Exception as e:
                        print(f"Could not delete folder {name}: {e}")
            try:
                os.rmdir(folder)
            except Exception as e:
                print(f"Could not delete folder {folder}: {e}")

def get_possible_resolutions(width, height, factor):
    """
    Return a list of resolutions that are possible after upscaling by `factor`.
    """
    final_width = width * factor
    final_height = height * factor

    # List of standard resolutions
    standard_res = {
        "HD (720p)": (1280, 720),
        "Full HD (1080p)": (1920, 1080),
        "4K (2160p)": (3840, 2160)
    }

    # Keep only resolutions that are <= final size
    valid_res = [name for name, (w, h) in standard_res.items()
                 if w <= final_width and h <= final_height]
    return valid_res

def get_video_framerate(video_path):
    cmd = [
        FFPROBE, "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=avg_frame_rate",
        "-of", "csv=p=0", video_path
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, text=True)
    num, denom = map(int, result.stdout.strip().split("/"))
    return num / denom

# ================= GPU PROFILE MANAGEMENT =================
def load_profiles():
    if os.path.exists(PROFILE_PATH):
        with open(PROFILE_PATH, "r") as f:
            return json.load(f)
    return {}

def save_profiles(profile):
    with open(PROFILE_PATH, "w") as f:
        json.dump(profile, f, indent=2)

def profile_key(width, height, factor, model, gpu):
    kind = "anime" if "anime" in model else "film"
    return f"{gpu}_{width}x{height}_x{factor}_{kind}"

# ================= MAIN APPLICATION =================
class UpscaleApp(QWidget):
    cleanup_signal = Signal()
    open_video_signal = Signal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI Video Upscaler")
        self.resize(900, 600)
        self.dark_mode = True
        self.cancel_requested = False
        self.fps_data = []

        # Main layout
        main_layout = QVBoxLayout()

        # --- Video selection ---
        video_layout = QHBoxLayout()
        self.video_label = QLabel("Video:")
        self.video_path_label = QLabel("None")
        self.video_path_label.setStyleSheet("color: #aaffaa;")
        video_btn = QPushButton("Browse")
        video_btn.clicked.connect(self.select_video)
        video_layout.addWidget(self.video_label)
        video_layout.addWidget(self.video_path_label)
        video_layout.addWidget(video_btn)
        main_layout.addLayout(video_layout)

        # --- GPU selection ---
        gpu_layout = QHBoxLayout()
        self.gpu_label = QLabel("GPU:")
        self.gpu_combo = QComboBox()
        self.gpu_combo.addItems(detect_gpus())
        gpu_layout.addWidget(self.gpu_label)
        gpu_layout.addWidget(self.gpu_combo)
        main_layout.addLayout(gpu_layout)

        # --- Preset selection ---
        preset_layout = QHBoxLayout()
        self.preset_label = QLabel("Preset:")
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(["Anime SD (x4)", "Film SD (x4)", "Fast (x2)"])
        self.preset_combo.currentIndexChanged.connect(self.update_resolutions)
        preset_layout.addWidget(self.preset_label)
        preset_layout.addWidget(self.preset_combo)
        main_layout.addLayout(preset_layout)

        # --- Resolution selection ---
        res_layout = QHBoxLayout()
        self.res_label = QLabel("Resolution:")
        self.res_combo = QComboBox()
        self.res_combo.addItems(["HD (720p)", "Full HD (1080p)", "4K (2160p)"])
        res_layout.addWidget(self.res_label)
        res_layout.addWidget(self.res_combo)
        main_layout.addLayout(res_layout)

        # --- Output format ---
        format_layout = QHBoxLayout()
        self.format_label = QLabel("Format:")
        self.format_combo = QComboBox()
        self.format_combo.addItems([
            "MP4 (H.264)", "MKV (H.264)", "MP4 (H.265 / HEVC)", "MKV (H.265 / HEVC)"
        ])
        format_layout.addWidget(self.format_label)
        format_layout.addWidget(self.format_combo)
        main_layout.addLayout(format_layout)

        # Title input
        title_layout = QHBoxLayout()
        self.title_label = QLabel("Metadata Title:")
        self.title_input = QLineEdit()
        self.title_input.setText("Upscaled Video")
        title_layout.addWidget(self.title_label)
        title_layout.addWidget(self.title_input)
        main_layout.addLayout(title_layout)

        # Output filename input
        output_layout = QHBoxLayout()
        self.output_label = QLabel("Output filename:")
        self.output_input = QLineEdit()
        self.output_input.setText("video_upscaled")
        output_layout.addWidget(self.output_label)
        output_layout.addWidget(self.output_input)
        main_layout.addLayout(output_layout)

        # --- Dark mode toggle ---
        self.dark_btn = QPushButton("Toggle Dark Mode")
        self.dark_btn.clicked.connect(self.toggle_dark)
        main_layout.addWidget(self.dark_btn)

        # --- Progress bar ---
        self.progress = QProgressBar()
        main_layout.addWidget(self.progress)

        # --- Stats display ---
        self.stats_label = QLabel("Stats: Waiting...")
        main_layout.addWidget(self.stats_label)

        # --- Start / Cancel buttons ---
        btn_layout = QHBoxLayout()
        self.start_btn = QPushButton("Start")
        self.start_btn.clicked.connect(self.start_upscale)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.cancel)
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.cancel_btn)
        main_layout.addLayout(btn_layout)

        # --- FPS graph ---
        self.graph = pg.PlotWidget(title="FPS / Frame Time")
        self.graph.showGrid(x=True, y=True)
        self.plot_line = self.graph.plot([], [])
        main_layout.addWidget(self.graph)

        self.setLayout(main_layout)
        self.toggle_dark()  # enable dark mode by default

        # Connect signal for cleanup popup
        self.cleanup_signal.connect(self.ask_cleanup)
        self.open_video_signal.connect(self.ask_open_video)

    # -------------------- UI FUNCTIONS --------------------
    def toggle_dark(self):
        self.dark_mode = not self.dark_mode
        if self.dark_mode:
            self.setStyleSheet("""
                QWidget { background-color: #121212; color: #e0e0e0; }
                QPushButton { background-color: #1f1f1f; color: #e0e0e0; border: 1px solid #333; padding: 5px; border-radius: 4px; }
                QPushButton:hover { background-color: #333; }
                QProgressBar { border: 1px solid #333; text-align: center; color: #e0e0e0; }
                QComboBox { background-color: #1f1f1f; color: #e0e0e0; border: 1px solid #333; padding: 2px; }
                QLabel { color: #e0e0e0; }
            """)
        else:
            self.setStyleSheet("")
    def update_resolutions(self):
        video = self.video_path_label.text()
        if not os.path.exists(video):
            return
        width, height = get_video_resolution(video)
        preset = self.preset_combo.currentText()
        factor = 4 if "x4" in preset else 2
        resolutions = get_possible_resolutions(width, height, factor)
        self.res_combo.clear()
        self.res_combo.addItems(resolutions)

    def select_video(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select video", "", "Video files (*.mp4 *.avi *.mkv)")
        if path:
            self.video_path_label.setText(path)
            width, height = get_video_resolution(path)

            # Determine factor from preset
            preset = self.preset_combo.currentText()
            factor = 4 if "x4" in preset else 2

            # Get only resolutions possible after upscale
            resolutions = get_possible_resolutions(width, height, factor)
            self.res_combo.clear()
            self.res_combo.addItems(resolutions)

    def start_upscale(self):
        video = self.video_path_label.text()
        if not os.path.exists(video):
            self.stats_label.setText("Error: Invalid video file")
            return
        self.cancel_requested = False
        threading.Thread(target=self.upscale_process, args=(video,)).start()

    def cancel(self):
        self.cancel_requested = True

    def ask_cleanup(self):
        # Show popup in UI thread
        def callback():
            reply = QMessageBox.question(
                self,
                "Cleanup",
                "Delete temporary frames?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                try:
                    cleanup()
                except Exception as e:
                    print("Error during cleanup:", e)

        QTimer.singleShot(0, callback)

    def ask_open_video(self, filepath):
        reply = QMessageBox.question(
            self,
            "Open Video",
            "Upscaling complete. Do you want to open the video?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                os.startfile(filepath)
            except Exception as e:
                print(f"Could not open video: {e}")

        self.cleanup_signal.emit()  # trigger cleanup popup in main thread

    # -------------------- UPSCALING LOGIC --------------------
    def upscale_process(self, video):
        os.makedirs(FRAMES_DIR, exist_ok=True)
        os.makedirs(UPSCALED_DIR, exist_ok=True)

        # Extract frames
        self.stats_label.setText("Extracting frames...")
        run_command([FFMPEG, "-y", "-i", video, f"{FRAMES_DIR}\\frame_%06d.png"])
        total_frames = count_png(FRAMES_DIR)

        # Preset and scale factor
        preset = self.preset_combo.currentText()
        factor = 4 if "x4" in preset else 2
        model = "realesrgan-x4plus-anime" if "Anime" in preset else "realesrgan-x4plus"

        # GPU selection
        gpu_sel = self.gpu_combo.currentText()
        exec_file = REALESRGAN_VULKAN

        start_time = time.time()
        processed = 0
        window = []

        proc = subprocess.Popen([
            exec_file, "-i", FRAMES_DIR, "-o", UPSCALED_DIR,
            "-n", model, "-s", str(factor), "-t", "0", "-j", "1:1:1"
        ])

        while proc.poll() is None:
            if self.cancel_requested:
                proc.terminate()
                self.stats_label.setText("❌ Cancelled")
                return
            processed = count_png(UPSCALED_DIR)
            elapsed = time.time() - start_time
            spf_live = elapsed / (processed + 1)
            window.append(spf_live)
            if len(window) > 20: window.pop(0)
            spf_avg = sum(window)/len(window)
            fps = processed / elapsed
            eta = int(spf_avg * (total_frames - processed))
            self.stats_label.setText(f"Frames: {processed}/{total_frames} | FPS: {fps:.2f} | ETA: {eta//60}m {eta%60}s")
            self.progress.setValue(int(processed / total_frames * 100))
            self.fps_data.append(fps)
            self.plot_line.setData(self.fps_data)
            QApplication.processEvents()
            time.sleep(0.4)

        # Restore original framerate
        fps_orig = get_video_framerate(video)
        # Retrieve selected final resolution
        res_text = self.res_combo.currentText()
        res_dict = {"HD (720p)": (1280,720), "Full HD (1080p)": (1920,1080), "4K (2160p)": (3840,2160)}
        final_w, final_h = res_dict.get(res_text, (1920,1080))

        # Retrieve output file title and name
        title_meta = self.title_input.text() or "Upscaled Video"

        # Recompose video
        fmt = self.format_combo.currentText()
        ext, codec = {
            "MP4 (H.264)": ("mp4","libx264"),
            "MKV (H.264)": ("mkv","libx264"),
            "MP4 (H.265 / HEVC)": ("mp4","libx265"),
            "MKV (H.265 / HEVC)": ("mkv","libx265")
        }[fmt]

        # --- construct final filename with resolution and codec ---
        res_short = res_text.split("(")[-1].replace(")","")  # "1080p"
        codec_short = "h264" if "H.264" in fmt else "h265"
        base_name = self.output_input.text() or os.path.splitext(os.path.basename(video))[0]
        out_file_name = f"{base_name} - {res_short} - {codec_short}.{ext}"
        out_file = os.path.join(os.path.dirname(video), out_file_name)

        self.stats_label.setText("Rebuilding video...")
        run_command([
            FFMPEG, 
            "-framerate", str(fps_orig),
            "-i", f"{UPSCALED_DIR}\\frame_%06d.png",
            "-i", video, 
            "-map","0:v",           # upscaled video
            "-map","1:a?",          # audio if present
            "-map_metadata","1",    # Copy the source metadata
            "-metadata", f"title={title_meta}",
            "-vf", f"scale={final_w}:{final_h}:flags=lanczos,setsar=1",
            "-c:v", codec, 
            "-crf","18", 
            "-preset","slow",
            "-pix_fmt","yuv420p", 
            "-c:a","copy", 
            out_file
        ])
        self.stats_label.setText("✅ Done!")
        self.open_video_signal.emit(out_file)

# ================= APP LAUNCH =================
if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    window = UpscaleApp()
    window.show()
    sys.exit(app.exec())
