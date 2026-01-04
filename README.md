# AI Video Upscaler

AI-powered video upscaling application using Real-ESRGAN to enhance your videos to higher resolutions.

## ✨ Features

- 🎯 **Automatic Intelligent Upscaling** - Automatically calculates the optimal factor (x2, x3, x4) to avoid mosaic artifacts
- 🎨 **Specialized Models** - Support for Anime and Film/Real-world content with dedicated models
- 📊 **Real-time Monitoring** - FPS graph and progress statistics
- 🎬 **Multiple Resolutions** - From 480p to 8K (4320p)
- 🎞️ **Various Formats** - Export to MP4/MKV with H.264 or H.265 (HEVC)
- 🖥️ **Modern Interface** - Dark mode by default, intuitive user interface
- 🎵 **Audio Preservation** - Preserves original audio and metadata
- ⚡ **GPU Acceleration** - Uses Vulkan for optimal performance

## 📋 Prerequisites

### Required Software

1. **Python 3.8+**
   - Download from [python.org](https://www.python.org/downloads/)

2. **FFmpeg**
   - Download from [ffmpeg.org](https://ffmpeg.org/download.html)
   - Extract to `C:\ffmpeg\`

3. **Real-ESRGAN NCNN Vulkan**
   - Download from [GitHub releases](https://github.com/xinntao/Real-ESRGAN/releases)
   - Look for `realesrgan-ncnn-vulkan-YYYYMMDD-windows.zip`
   - Extract to `C:\real-esrgan\`

### Required Models

The following models must be present in `C:\real-esrgan\models\`:

**For Anime:**
- `realesr-animevideov3-x2.bin` / `.param`
- `realesr-animevideov3-x3.bin` / `.param`
- `realesr-animevideov3-x4.bin` / `.param`

**For Film/Real-world:**
- `realesrgan-x4plus.bin` / `.param`
- `realesrgan-x4plus-anime.bin` / `.param`

Models are typically included in the Real-ESRGAN zip file.

## 🚀 Installation

### 1. Clone the repository

```bash
git clone https://github.com/your-username/AI-Video-Upscaler.git
cd AI-Video-Upscaler
```

### 2. Install Python dependencies

```bash
pip install PySide6 pyqtgraph
```

### 3. Verify folder structure

Make sure the following structure exists:

```
C:\
├── ffmpeg\
│   └── bin\
│       ├── ffmpeg.exe
│       └── ffprobe.exe
├── real-esrgan\
│   ├── realesrgan-ncnn-vulkan.exe
│   └── models\
│       ├── realesr-animevideov3-x2.bin
│       ├── realesr-animevideov3-x2.param
│       ├── realesr-animevideov3-x3.bin
│       ├── realesr-animevideov3-x3.param
│       ├── realesr-animevideov3-x4.bin
│       ├── realesr-animevideov3-x4.param
│       ├── realesrgan-x4plus.bin
│       ├── realesrgan-x4plus.param
│       ├── realesrgan-x4plus-anime.bin
│       └── realesrgan-x4plus-anime.param
└── upscale\  (created automatically)
```

### 4. Custom configuration (optional)

If your paths are different, modify the following lines in `AI Video Upscaler.py`:

```python
FFMPEG = r"C:\ffmpeg\bin\ffmpeg.exe"
REALESRGAN_VULKAN = r"C:\real-esrgan\realesrgan-ncnn-vulkan.exe"
BASE_DIR = r"C:\upscale"
```

## 📖 Usage

### Launching the application

```bash
python "AI Video Upscaler.py"
```

### Step-by-step guide

1. **Select a video**
   - Click "Browse"
   - Choose your video file (MP4, AVI, MKV)

2. **Choose GPU** (if multiple available)
   - Select the GPU to use for upscaling

3. **Content type**
   - **Anime**: For animated content, cartoons
   - **Film / Real-world**: For movies, series, real-world content

4. **Target resolution**
   - Only resolutions higher than your source video are displayed
   - The system automatically calculates the best upscaling factor

5. **Output format**
   - MP4 or MKV
   - H.264 (compatible) or H.265 (better compression)

6. **Metadata** (optional)
   - Video title
   - Output filename

7. **Start upscaling**
   - Click "Start"
   - Follow real-time progress
   - The graph displays performance metrics

### Supported Resolutions

| Resolution | Name | Dimensions |
|------------|------|------------|
| 480p | SD | 854×480 |
| 540p | qHD | 960×540 |
| 720p | HD | 1280×720 |
| 900p | HD+ | 1600×900 |
| 1080p | Full HD | 1920×1080 |
| 1440p | QHD | 2560×1440 |
| 1800p | QHD+ | 3200×1800 |
| 2160p | 4K UHD | 3840×2160 |
| 2880p | 5K | 5120×2880 |
| 3160p | 6K | 6144×3160 |
| 4320p | 8K UHD | 7680×4320 |

## 🎯 How does automatic upscaling work?

The application automatically calculates the optimal factor to avoid mosaic artifacts:

- **Source → Target ≤ 1.5x**: Uses x2
- **Source → Target ≤ 2.5x**: Uses x2
- **Source → Target > 2.5x**: Uses x4

### Example

- Source video: 480p (854×480)
- Target: 1080p (1920×1080)
- Required factor: ~2.25x
- **Automatic choice: x2** (to avoid mosaic artifacts)

## 🔧 Troubleshooting

### "Invalid video file" error
- Verify the video file exists and is not corrupted
- Supported formats: MP4, AVI, MKV

### FFmpeg error
- Verify FFmpeg is installed in `C:\ffmpeg\bin\`
- Test in terminal: `C:\ffmpeg\bin\ffmpeg.exe -version`

### Real-ESRGAN error
- Verify `realesrgan-ncnn-vulkan.exe` exists
- Verify models are present in the models folder

### Slow performance
- Use a Vulkan-compatible GPU
- Close other resource-intensive applications
- Use H.264 instead of H.265 (faster to encode)

### Out of memory
- Reduce target resolution
- Close other applications
- Check available disk space in `C:\upscale\`

## 📁 Temporary File Structure

The application creates temporary files in `C:\upscale\`:

```
C:\upscale\
├── frames\         # Extracted frames from source video
├── upscaled\       # Frames after upscaling
└── gpu_profile.json  # Performance profiles (future)
```

These files are automatically cleaned up after upscaling (with confirmation).

## ⚙️ Advanced Configuration

### Modifying encoding parameters

In the `upscale_process` function, line ~350:

```python
run_command([
    FFMPEG, 
    "-framerate", str(fps_orig),
    "-i", f"{UPSCALED_DIR}\\frame_%06d.png",
    "-i", video, 
    "-map","0:v",
    "-map","1:a?",
    "-map_metadata","1",
    "-metadata", f"title={title_meta}",
    "-vf", f"scale={final_w}:{final_h}:flags=lanczos,setsar=1",
    "-c:v", codec, 
    "-crf","18",        # Quality (0-51, lower = better quality)
    "-preset","slow",   # Speed (ultrafast, fast, medium, slow, veryslow)
    "-pix_fmt","yuv420p", 
    "-c:a","copy", 
    out_file
])
```

### Modifying upscaling thresholds

In the `calculate_optimal_scale` function, line ~80:

```python
def calculate_optimal_scale(source_width, source_height, target_width, target_height):
    width_ratio = target_width / source_width
    height_ratio = target_height / source_height
    required_scale = max(width_ratio, height_ratio)
    
    if required_scale <= 1.5:  # Modify these thresholds
        return 2
    elif required_scale <= 2.5:  # according to your needs
        return 2
    else:
        return 4
```

## 📝 Future Improvements

- [ ] Automatic multi-GPU support
- [x] Before/after preview
- [ ] Batch processing
- [ ] Persistent GPU performance profiles
- [ ] Subtitle support
- [x] More accurate time remaining estimation
- [ ] Quality comparison interface

## 📄 License

This project is licensed under the MIT License. See the `LICENSE` file for details.

## 🙏 Acknowledgments

- [Real-ESRGAN](https://github.com/xinntao/Real-ESRGAN) - AI upscaling algorithm
- [FFmpeg](https://ffmpeg.org/) - Video processing
- [PySide6](https://doc.qt.io/qtforpython-6/) - Graphical interface
- [PyQtGraph](https://www.pyqtgraph.org/) - Real-time graphs

## 📧 Contact

For questions or suggestions, open an issue on GitHub.

---

⭐ If this project was useful to you, don't forget to give it a star!
