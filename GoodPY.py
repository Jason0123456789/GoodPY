#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
好兄弟牌压缩工具 - 给最爱的电影瘦瘦身
基于 FFmpeg 的批量视频压缩工具，内置 FFmpeg 二进制
打包为独立 EXE 单文件运行，无需 Python 环境

打包命令：
  pyinstaller --onefile --windowed --name "好兄弟牌压缩工具" ^
    --add-data "bin\ffmpeg.exe;." --add-data "bin\ffprobe.exe;." ^
    --clean video_converter.py
"""

import os, sys, re, time, queue, shutil, threading, tempfile, subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from datetime import datetime

# Windows 进程挂起/恢复所需（NtSuspendProcess / NtResumeProcess）
if sys.platform.startswith("win"):
    import ctypes
    kernel32 = ctypes.windll.kernel32


# =====================================================================
#  可调整参数（所有界面元素的位置、尺寸、颜色、字体集中在此）
# =====================================================================

WINDOW_TITLE = "好兄弟牌压缩工具 - 给最爱的电影瘦瘦身"
WINDOW_WIDTH = 780
WINDOW_HEIGHT = 545
BACKGROUND_COLOR = "#FFF0F5"        # 薰衣草腮红
BORDER_COLOR = "#F0C0D0"
FONT_FAMILY = "Microsoft YaHei"
FONT_SIZE_NORMAL = 9
FONT_SIZE_BOLD = 10

COLOR_BROWSE_BTN = "#FF69B4"        # 热粉红
COLOR_BROWSE_BTN_TEXT = "white"
COLOR_START_BTN = "#FF1493"          # 深粉红
COLOR_START_BTN_TEXT = "white"
COLOR_PAUSE_BTN = "#FFB6C1"          # 浅粉红
COLOR_PAUSE_BTN_TEXT = "white"
COLOR_STOP_BTN = "#DB7093"           # 中粉红
COLOR_STOP_BTN_TEXT = "white"
COLOR_CHECKBOX_BG = "#FFF0F5"
COLOR_PROGRESS_BAR = "#FF69B4"       # 热粉红
COLOR_PROGRESS_TROUGH = "#FFE4E1"    # 浅粉红
COLOR_PROGRESS_TEXT = "#444444"

# --- 原视频文件夹区域 ---
LABEL_INPUT_X, LABEL_INPUT_Y = 15, 10
LABEL_INPUT_W, LABEL_INPUT_H = 100, 20
ENTRY_INPUT_X, ENTRY_INPUT_Y = 15, 30
ENTRY_INPUT_W, ENTRY_INPUT_H = 570, 28
BTN_INPUT_X, BTN_INPUT_Y = 595, 30
BTN_INPUT_W, BTN_INPUT_H = 165, 28

# --- 压缩输出文件夹区域 ---
LABEL_OUTPUT_X, LABEL_OUTPUT_Y = 15, 64
LABEL_OUTPUT_W, LABEL_OUTPUT_H = 100, 20
ENTRY_OUTPUT_X, ENTRY_OUTPUT_Y = 15, 84
ENTRY_OUTPUT_W, ENTRY_OUTPUT_H = 570, 28
BTN_OUTPUT_X, BTN_OUTPUT_Y = 595, 84
BTN_OUTPUT_W, BTN_OUTPUT_H = 165, 28

# --- 压缩参数设置分组框 ---
PARAM_FRAME_X, PARAM_FRAME_Y = 15, 118
PARAM_FRAME_W, PARAM_FRAME_H = 750, 172
PARAM_FRAME_TITLE = "压缩参数设置"

# CRF/CQ/GQ/QP 值调整（由 QUALITY_PARAMS 动态控制标签、范围、默认值）
LABEL_CRF_X, LABEL_CRF_Y = 20, 24
LABEL_CRF_W, LABEL_CRF_H = 90, 20
SCALE_CRF_X, SCALE_CRF_Y = 120, 26
SCALE_CRF_W, SCALE_CRF_H = 520, 14
ENTRY_CRF_X, ENTRY_CRF_Y = 655, 20
ENTRY_CRF_W, ENTRY_CRF_H = 60, 28

# 分辨率下拉菜单
LABEL_RES_X, LABEL_RES_Y = 20, 60
LABEL_RES_W, LABEL_RES_H = 90, 20
COMBO_RES_X, COMBO_RES_Y = 120, 58
COMBO_RES_W, COMBO_RES_H = 200, 28

# 音频比特率下拉菜单
LABEL_AUDIO_X, LABEL_AUDIO_Y = 360, 60
LABEL_AUDIO_W, LABEL_AUDIO_H = 90, 20
COMBO_AUDIO_X, COMBO_AUDIO_Y = 460, 58
COMBO_AUDIO_W, COMBO_AUDIO_H = 255, 28

# 硬件加速复选框
CHECK_HW_X, CHECK_HW_Y = 20, 94

# 编码格式下拉菜单
LABEL_ENCODER_X, LABEL_ENCODER_Y = 360, 94
LABEL_ENCODER_W, LABEL_ENCODER_H = 90, 20
COMBO_ENCODER_X, COMBO_ENCODER_Y = 460, 92
COMBO_ENCODER_W, COMBO_ENCODER_H = 255, 28

# --- 操作按钮区域 ---
BTN_START_X, BTN_START_Y = 15, 298
BTN_START_W, BTN_START_H = 238, 38
BTN_PAUSE_X, BTN_PAUSE_Y = 261, 298
BTN_PAUSE_W, BTN_PAUSE_H = 238, 38
BTN_STOP_X, BTN_STOP_Y = 507, 298
BTN_STOP_W, BTN_STOP_H = 238, 38

# --- 信息输出区域 ---
LABEL_LOG_X, LABEL_LOG_Y = 15, 342
LABEL_LOG_W, LABEL_LOG_H = 100, 20
TEXT_LOG_X, TEXT_LOG_Y = 15, 364
TEXT_LOG_W, TEXT_LOG_H = 750, 136

# --- 进度条区域 ---
PROGRESS_BAR_X, PROGRESS_BAR_Y = 15, 506
PROGRESS_BAR_W, PROGRESS_BAR_H = 750, 26

# --- 质量参数配置（根据编码器类型动态切换标签、范围、默认值） ---
# 格式：{编码器类型: {"label": 显示标签, "min": 最小值, "max": 最大值, "default": 默认值, "param": FFmpeg参数名}}
QUALITY_PARAMS = {
    "software": {"label": "CRF 值调整", "min": 28, "max": 35, "default": 28, "param": "crf"},
    "nvidia":   {"label": "CQ 值调整", "min": 30, "max": 40, "default": 30, "param": "cq"},
    "intel":    {"label": "GQ 值调整", "min": 30, "max": 45, "default": 30, "param": "global_quality"},
    "amd":      {"label": "QP 值调整", "min": 24, "max": 34, "default": 24, "param": "qp"},
}

# --- 默认转码参数 ---
DEFAULT_ENCODER = "H.265 (HEVC)"
DEFAULT_RESOLUTION = "原分辨率"
DEFAULT_AUDIO_BITRATE = "不压缩"              # 直接复制原音频流
DEFAULT_HW_ACCEL = True

# --- 下拉菜单选项 ---
RESOLUTION_OPTIONS = ["原分辨率", "720p", "1080p", "2K", "4K"]
AUDIO_BITRATE_OPTIONS = ["不压缩", "48kbps", "96kbps", "128kbps", "192kbps", "320kbps"]
ENCODER_OPTIONS = ["H.265 (HEVC)", "H.264 (AVC)"]

# --- 支持的视频格式列表 ---
SUPPORTED_VIDEO_FORMATS = [
    ".mp4", ".mkv", ".mov", ".avi", ".flv", ".wmv", ".webm", ".m4v",
    ".MP4", ".MKV", ".MOV", ".AVI", ".FLV", ".WMV", ".WEBM", ".M4V"
]

# --- 日志目录（与软件同目录） ---
LOG_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))


# =====================================================================
#  工具函数
# =====================================================================

def safe_path(path):
    """处理中文/特殊字符/Windows长路径，仅用于 os 操作，不传给 FFmpeg（不兼容 \\?\ 前缀）"""
    if not path:
        return path
    path = os.path.normpath(path)
    if sys.platform.startswith("win") and isinstance(path, str):
        if not path.startswith("\\\\?\\"):
            path = os.path.abspath(path)
            # 路径超过 240 字符时添加 \\?\ 前缀以支持长路径
            if len(path) > 240:
                path = "\\\\?\\" + path
    return path


def ffmpeg_safe_path(path):
    """给 FFmpeg/ffprobe 命令行用的路径，不做 \\?\ 前缀转换（C 程序可能不兼容）"""
    if not path:
        return path
    return os.path.normpath(path)


def get_subprocess_kwargs():
    """返回隐藏控制台窗口的 subprocess 参数（Windows 下 subprocess 默认弹出黑色控制台）"""
    kwargs = {}
    if sys.platform.startswith("win"):
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = subprocess.SW_HIDE
        kwargs["startupinfo"] = si
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    return kwargs


def format_size(size_bytes):
    """将字节数格式化为可读的大小字符串（B / KB / MB / GB）"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def suspend_process(pid):
    """挂起 Windows 进程（使用 NtSuspendProcess，比 SuspendThread 更安全），返回是否成功"""
    if not sys.platform.startswith("win"):
        return False
    try:
        PROCESS_SUSPEND_RESUME = 0x0800  # 进程挂起/恢复权限
        handle = kernel32.OpenProcess(PROCESS_SUSPEND_RESUME, False, pid)
        if not handle:
            return False
        result = ctypes.windll.ntdll.NtSuspendProcess(handle)
        kernel32.CloseHandle(handle)
        return result == 0
    except Exception:
        return False


def resume_process(pid):
    """恢复 Windows 进程（使用 NtResumeProcess），返回是否成功"""
    if not sys.platform.startswith("win"):
        return False
    try:
        PROCESS_SUSPEND_RESUME = 0x0800
        handle = kernel32.OpenProcess(PROCESS_SUSPEND_RESUME, False, pid)
        if not handle:
            return False
        result = ctypes.windll.ntdll.NtResumeProcess(handle)
        kernel32.CloseHandle(handle)
        return result == 0
    except Exception:
        return False


# =====================================================================
#  FFmpeg 路径管理器
# =====================================================================

class FFmpegManager:
    """
    FFmpeg 二进制文件管理器
    查找优先级：PyInstaller _MEIPASS → EXE同目录 → 脚本同目录 → 系统 PATH
    """
    _ffmpeg_path = None    # 缓存的 ffmpeg 路径
    _ffprobe_path = None   # 缓存的 ffprobe 路径
    _temp_dir = None       # 释放到的临时目录

    @classmethod
    def get_ffmpeg(cls):
        """获取 ffmpeg 可执行文件路径，带缓存"""
        if cls._ffmpeg_path and os.path.exists(cls._ffmpeg_path):
            return cls._ffmpeg_path
        cls._ffmpeg_path = cls._find("ffmpeg")
        return cls._ffmpeg_path

    @classmethod
    def get_ffprobe(cls):
        """获取 ffprobe 可执行文件路径，带缓存"""
        if cls._ffprobe_path and os.path.exists(cls._ffprobe_path):
            return cls._ffprobe_path
        cls._ffprobe_path = cls._find("ffprobe")
        return cls._ffprobe_path

    @classmethod
    def _find(cls, name):
        """按优先级查找 FFmpeg 二进制文件"""
        exe = name + (".exe" if sys.platform.startswith("win") else "")

        # 1. PyInstaller _MEIPASS → 释放到固定临时目录
        if getattr(sys, 'frozen', False):
            meipass = getattr(sys, '_MEIPASS', '')
            if meipass:
                bundled = os.path.join(meipass, exe)
                if os.path.exists(bundled):
                    try:
                        return cls._release_to_temp(bundled, exe)
                    except Exception as e:
                        print(f"释放 {exe} 失败: {e}")
            # EXE 同目录及子目录
            exe_dir = os.path.dirname(sys.executable)
            for sub in ["", "bin", "ffmpeg"]:
                candidate = os.path.join(exe_dir, sub, exe)
                if os.path.exists(candidate):
                    return candidate

        # 2. 脚本同目录及子目录（开发调试用）
        base = os.path.dirname(os.path.abspath(__file__))
        for sub in ["", "bin", "ffmpeg"]:
            candidate = os.path.join(base, sub, exe)
            if os.path.exists(candidate):
                return candidate

        # 3. 系统 PATH
        try:
            cmd = ["where" if sys.platform.startswith("win") else "which", name]
            result = subprocess.run(cmd, capture_output=True, text=True,
                                    timeout=5, **get_subprocess_kwargs())
            if result.returncode == 0:
                found = result.stdout.strip().splitlines()[0].strip()
                if os.path.exists(found):
                    return found
        except Exception:
            pass
        return None

    @classmethod
    def _release_to_temp(cls, src, filename):
        """将 PyInstaller 打包的 FFmpeg 释放到固定临时目录（避免每次启动重新释放）"""
        if cls._temp_dir is None:
            cls._temp_dir = os.path.join(tempfile.gettempdir(), "video_converter_ffmpeg")
            os.makedirs(cls._temp_dir, exist_ok=True)
        dst = os.path.join(cls._temp_dir, filename)
        # 目标文件存在且大小一致时跳过复制（避免多实例冲突）
        if os.path.exists(dst) and os.path.getsize(dst) == os.path.getsize(src):
            return dst
        try:
            shutil.copy2(src, dst)
        except PermissionError:
            # 另一个实例可能正在写入，等待后重试
            time.sleep(1)
            if os.path.exists(dst) and os.path.getsize(dst) > 0:
                return dst
            shutil.copy2(src, dst)
        return dst

    @classmethod
    def cleanup(cls):
        """清理临时目录中的 FFmpeg 文件"""
        if cls._temp_dir and os.path.exists(cls._temp_dir):
            try:
                shutil.rmtree(cls._temp_dir, ignore_errors=True)
            except Exception:
                pass


# =====================================================================
#  硬件加速检测 + 运行时测试
# =====================================================================

class HardwareDetector:
    """硬件加速检测器，支持 NVIDIA / AMD / Intel"""

    @staticmethod
    def detect():
        """检测 FFmpeg 编译了哪些硬件编码器（仅检查编译支持，不代表硬件可用）"""
        detected = {"nvidia": False, "amd": False, "intel": False, "software": True}
        ffmpeg = FFmpegManager.get_ffmpeg()
        if not ffmpeg:
            return detected
        try:
            result = subprocess.run([ffmpeg, "-encoders"], capture_output=True, text=True,
                                    timeout=10, **get_subprocess_kwargs())
            out = result.stdout
            if "hevc_nvenc" in out or "h264_nvenc" in out: detected["nvidia"] = True
            if "hevc_amf" in out or "h264_amf" in out: detected["amd"] = True
            if "hevc_qsv" in out or "h264_qsv" in out: detected["intel"] = True
        except Exception:
            pass
        return detected

    @staticmethod
    def test_encoder(encoder_name):
        """运行时测试编码器是否真正可用（生成1帧黑色视频测试），返回 (是否可用, 错误信息)"""
        ffmpeg = FFmpegManager.get_ffmpeg()
        if not ffmpeg:
            return False, "FFmpeg 未找到"
        try:
            cmd = [
                ffmpeg, "-y",
                "-f", "lavfi", "-i", "color=c=black:s=320x240:d=0.04:r=25",
                "-c:v", encoder_name,
                "-frames:v", "1",
                "-f", "null", "-"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True,
                                    timeout=15, **get_subprocess_kwargs())
            if result.returncode == 0:
                return True, "OK"
            else:
                # 提取关键错误信息（从后往前找含 error/failed 的行）
                err = result.stderr.strip()
                for line in err.split('\n')[::-1]:
                    line = line.strip()
                    if line and ('error' in line.lower() or 'failed' in line.lower()):
                        return False, line[:200]
                return False, err[-200:] if err else "未知错误"
        except subprocess.TimeoutExpired:
            return False, "编码器测试超时"
        except Exception as e:
            return False, str(e)[:200]

    @staticmethod
    def get_best_encoder(encoder_type, hw_enabled, detected_hw, log_func=None):
        """选择最优编码器并运行时测试验证，按优先级尝试：NVIDIA → AMD → Intel → 软件"""
        encoder_map = {
            "H.265 (HEVC)": {"nvidia": "hevc_nvenc", "amd": "hevc_amf",
                             "intel": "hevc_qsv", "software": "libx265"},
            "H.264 (AVC)": {"nvidia": "h264_nvenc", "amd": "h264_amf",
                            "intel": "h264_qsv", "software": "libx264"},
        }

        # 未启用硬件加速，直接使用软件编码
        if not hw_enabled:
            return encoder_map[encoder_type]["software"]

        # 按优先级尝试硬件编码器，运行时测试通过才使用
        for hw in ["nvidia", "amd", "intel"]:
            if detected_hw.get(hw):
                encoder = encoder_map[encoder_type][hw]
                ok, msg = HardwareDetector.test_encoder(encoder)
                if ok:
                    if log_func:
                        log_func(f"硬件编码器 {encoder} 测试通过")
                    return encoder
                else:
                    if log_func:
                        log_msg = msg.replace('\n', ' ').replace('\r', '')
                        log_func(f"硬件编码器 {encoder} 不可用: {log_msg}")
                        log_func(f"将尝试下一个可用编码器...")

        # 所有硬件编码器都不可用，回退到软件编码
        sw = encoder_map[encoder_type]["software"]
        if log_func:
            log_func(f"所有硬件编码器均不可用，使用软件编码: {sw}")
        return sw


# =====================================================================
#  文件处理器
# =====================================================================

class FileHandler:
    """文件扫描、路径计算、视频信息获取"""

    @staticmethod
    def scan_video_files(folder):
        """递归扫描文件夹中所有支持格式的视频文件，返回 [(完整路径, 相对路径), ...]"""
        folder = safe_path(folder)
        video_files = []
        for root, dirs, files in os.walk(folder):
            for file in files:
                if os.path.splitext(file)[1] in SUPPORTED_VIDEO_FORMATS:
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, folder)
                    video_files.append((full_path, rel_path))
        return video_files

    @staticmethod
    def get_output_path(rel_path, output_folder):
        """根据相对路径计算输出文件路径，自动创建子文件夹，输出扩展名固定为 .mp4"""
        output_path = os.path.join(output_folder, rel_path)
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        base, _ = os.path.splitext(output_path)
        return base + ".mp4"

    @staticmethod
    def get_video_duration(video_path):
        """获取视频时长（秒），优先 ffprobe，失败回退 ffmpeg -i 解析 Duration"""
        # 传给 ffprobe/ffmpeg 的路径不做 \\?\ 前缀转换
        video_path_ff = ffmpeg_safe_path(video_path)
        video_path_py = safe_path(video_path)

        ffprobe = FFmpegManager.get_ffprobe()
        if ffprobe:
            try:
                result = subprocess.run(
                    [ffprobe, "-v", "error", "-show_entries", "format=duration",
                     "-of", "default=noprint_wrappers=1:nokey=1", video_path_ff],
                    capture_output=True, text=True, timeout=30, **get_subprocess_kwargs())
                if result.returncode == 0 and result.stdout.strip():
                    return float(result.stdout.strip())
            except Exception:
                pass
        # ffprobe 不可用时，用 ffmpeg -i 解析 Duration
        ffmpeg = FFmpegManager.get_ffmpeg()
        if ffmpeg:
            try:
                result = subprocess.run([ffmpeg, "-i", video_path_ff],
                    capture_output=True, text=True, timeout=30, **get_subprocess_kwargs())
                match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", result.stderr)
                if match:
                    return float(match.group(1)) * 3600 + float(match.group(2)) * 60 + float(match.group(3))
            except Exception:
                pass
        return 0

    @staticmethod
    def get_video_frames(video_path):
        """获取视频总帧数和帧率，优先 ffprobe nb_frames，失败用 duration*fps 估算"""
        video_path_ff = ffmpeg_safe_path(video_path)
        total_frames = 0
        fps = 0

        ffprobe = FFmpegManager.get_ffprobe()
        if ffprobe:
            try:
                probe_cmd = [ffprobe, "-v", "error", "-select_streams", "v:0",
                             "-show_entries", "stream=r_frame_rate,nb_frames",
                             "-of", "default=noprint_wrappers=1", video_path_ff]
                probe_result = subprocess.run(probe_cmd, capture_output=True, text=True,
                                              timeout=15, **get_subprocess_kwargs())
                if probe_result.returncode == 0:
                    for probe_line in probe_result.stdout.strip().split('\n'):
                        if probe_line.startswith('r_frame_rate='):
                            fps_str = probe_line.split('=')[1].strip()
                            if '/' in fps_str:
                                num, den = fps_str.split('/')
                                if float(den) > 0:
                                    fps = float(num) / float(den)
                            elif fps_str:
                                fps = float(fps_str)
                        elif probe_line.startswith('nb_frames='):
                            nb = probe_line.split('=')[1].strip()
                            if nb and nb != 'N/A':
                                try: total_frames = int(nb)
                                except ValueError: pass
            except Exception:
                pass

        # 如果没有 nb_frames，用时长 * 帧率估算
        if total_frames == 0:
            duration = FileHandler.get_video_duration(video_path)
            if duration > 0 and fps > 0:
                total_frames = int(duration * fps)
            elif duration > 0:
                # 帧率也获取不到时，按 25fps 估算
                total_frames = int(duration * 25)
                fps = 25

        return total_frames, fps


# =====================================================================
#  FFmpeg 命令生成器
# =====================================================================

class FFmpegCommandBuilder:
    """根据用户选择的参数构建 FFmpeg 命令行，统一处理不同编码器的参数差异"""

    @staticmethod
    def build(input_path, output_path, crf, resolution, audio_bitrate, encoder, hw_accel):
        """构建 FFmpeg 压缩命令"""
        ffmpeg = FFmpegManager.get_ffmpeg()
        # FFmpeg 命令行路径不做 \\?\ 前缀转换
        input_path = ffmpeg_safe_path(input_path)
        output_path = ffmpeg_safe_path(output_path)

        # -progress pipe:2 输出机器可读进度到 stderr，比 -stats_period 更可靠（不受管道缓冲影响）
        cmd = [ffmpeg, "-y", "-i", input_path, "-progress", "pipe:2", "-nostats"]

        # --- 分辨率缩放 ---
        # 硬件编码器需要 nv12 格式，软件编码器需要 yuv420p 格式
        if resolution != "原分辨率":
            scale_map = {
                "720p": "scale=-2:720",
                "1080p": "scale=-2:1080",
                "2K": "scale=-2:1440",
                "4K": "scale=-2:2160"
            }
            scale_filter = scale_map[resolution]
            if encoder in ["hevc_nvenc", "h264_nvenc", "hevc_amf", "h264_amf", "hevc_qsv", "h264_qsv"]:
                cmd.extend(["-vf", f"{scale_filter},format=nv12"])
            else:
                cmd.extend(["-vf", f"{scale_filter},format=yuv420p"])

        # --- 视频编码器 ---
        cmd.extend(["-c:v", encoder])

        # --- 根据编码器类型设置质量参数 ---
        if encoder in ["libx265", "libx264"]:
            # CRF 恒定质量 + slow 预设（最高压缩效率）
            cmd.extend(["-crf", str(crf), "-preset", "slow"])
        elif encoder in ["hevc_nvenc", "h264_nvenc"]:
            # -cq 恒定质量 + -b:v 0 禁用默认VBR（否则-cq不生效）+ p7 预设 + hq 调优
            cmd.extend(["-cq", str(crf), "-b:v", "0", "-preset", "p7", "-tune", "hq"])
        elif encoder in ["hevc_amf", "h264_amf"]:
            # -rc cqp 恒定QP模式 + -qp_i/-qp_p 设置I/P帧QP + balanced 质量
            cmd.extend(["-rc", "cqp", "-qp_i", str(crf), "-qp_p", str(crf), "-quality", "balanced"])
        elif encoder in ["hevc_qsv", "h264_qsv"]:
            # -global_quality 类似 CRF + slow 预设
            cmd.extend(["-global_quality", str(crf), "-preset", "slow"])

        # --- 码率上限 ---
        # 防止低码率源视频被"提升质量"导致文件变大
        maxrate_map = {"720p": "2M", "1080p": "4M", "2K": "6M", "4K": "12M"}
        if resolution != "原分辨率" and resolution in maxrate_map:
            maxrate = maxrate_map[resolution]
        else:
            # 原分辨率时根据质量值设置码率上限（质量值越大=压缩率越高=码率上限越低）
            if crf <= 24: maxrate = "6M"
            elif crf <= 30: maxrate = "4M"
            elif crf <= 35: maxrate = "2M"
            else: maxrate = "2M"
        # bufsize = maxrate * 2（取整数值）
        maxrate_val = int(float(maxrate.replace("M", "")))
        cmd.extend(["-maxrate", maxrate, "-bufsize", f"{maxrate_val * 2}M"])

        # --- 像素格式 ---
        # 仅软件编码器添加 -pix_fmt yuv420p；硬件编码器有自身格式要求，强制 yuv420p 会报错
        if encoder in ["libx265", "libx264"]:
            cmd.extend(["-pix_fmt", "yuv420p"])

        # --- 音频处理 ---
        if audio_bitrate == "不压缩":
            # 直接复制原音频流（不重新编码）
            cmd.extend(["-c:a", "copy"])
        else:
            # 去掉可能存在的 "bps" 后缀（如 "128kbps" → "128k"），FFmpeg 只认 "k" 后缀
            cmd.extend(["-c:a", "aac", "-b:a", audio_bitrate.rstrip("bps")])

        # 不使用 -f mp4 强制格式，让 FFmpeg 根据输出扩展名自动选择容器
        # 这样当源音频格式与 MP4 不兼容时，FFmpeg 会自动重编码音频
        cmd.append(output_path)
        return cmd


# =====================================================================
#  压缩线程
# =====================================================================

class CompressorThread(threading.Thread):
    """压缩工作线程，支持暂停/继续/停止，硬件编码失败自动回退软件编码"""

    def __init__(self, gui):
        super().__init__(daemon=True)
        self.gui = gui
        self.task_queue = queue.Queue()
        self.current_process = None
        self.is_paused = False
        self.is_stopped = False
        self.pause_event = threading.Event()  # set=继续, clear=暂停
        self.pause_event.set()
        self.failed_files = []
        self.total_files = 0
        self.current_file_index = 0
        self.completed_count = 0
        self.skipped_count = 0
        self.completed_pairs = []

    def run(self):
        """线程主循环：从队列取任务并处理"""
        while not self.is_stopped:
            try:
                task = self.task_queue.get(timeout=0.5)
                if task == "STOP":
                    break
                self.process_task(task)
                self.task_queue.task_done()
            except queue.Empty:
                # 队列为空且所有文件已处理完，退出线程
                if self.current_file_index >= self.total_files:
                    break
                continue
        # 线程正常结束时通知 GUI
        if not self.is_stopped:
            self.gui.root.after(0, self.gui.finish_compressing)

    def process_task(self, task):
        """
        处理单个压缩任务
        硬件编码器失败时自动回退到软件编码重试
        """
        input_path, rel_path, output_path = task
        self.current_file_index += 1

        self.gui.root.after(0, self.gui.log_message,
            f"[{self.current_file_index}/{self.total_files}] 开始压缩: {os.path.basename(input_path)}")

        # 跳过已压缩的文件
        if os.path.exists(safe_path(output_path)):
            self.skipped_count += 1
            self.gui.root.after(0, self.gui.log_message,
                f"文件已存在，跳过: {os.path.basename(output_path)}")
            return

        try:
            duration = FileHandler.get_video_duration(input_path)
            total_frames, _ = FileHandler.get_video_frames(input_path)

            # 先用当前选择的编码器尝试压缩
            encoder = self.gui.selected_encoder
            success = self._run_ffmpeg(input_path, output_path, encoder, duration, total_frames)

            # 硬件编码器失败时自动回退到软件编码
            if not success and encoder not in ["libx265", "libx264"] and not self.is_stopped:
                self.gui.root.after(0, self.gui.log_message,
                    f"[WARN] 硬件编码器 {encoder} 失败，尝试软件编码重试...")
                out_safe = safe_path(output_path)
                if os.path.exists(out_safe):
                    try: os.remove(out_safe)
                    except Exception: pass
                # 回退到软件编码
                encoder_map = {"H.265 (HEVC)": "libx265", "H.264 (AVC)": "libx264"}
                sw_encoder = encoder_map.get(self.gui.encoder_var.get(), "libx265")
                success = self._run_ffmpeg(input_path, output_path, sw_encoder, duration, total_frames)

            if not success and not self.is_stopped:
                self.failed_files.append(input_path)

        except FileNotFoundError:
            if not self.is_stopped:
                self.failed_files.append(input_path)
                self.gui.root.after(0, self.gui.log_message,
                    f"[FAIL] FFmpeg 未找到: {os.path.basename(input_path)}")
        except Exception as e:
            if not self.is_stopped:
                self.failed_files.append(input_path)
                self.gui.root.after(0, self.gui.log_message,
                    f"[FAIL] 异常: {os.path.basename(input_path)} - {str(e)}")

    def _run_ffmpeg(self, input_path, output_path, encoder, duration, total_frames):
        """执行 FFmpeg 压缩命令，返回是否成功"""
        crf = self.gui.crf_value.get()
        resolution = self.gui.resolution_var.get()
        audio_bitrate = self.gui.audio_bitrate_var.get()
        cmd = FFmpegCommandBuilder.build(
            input_path, output_path,
            crf, resolution, audio_bitrate,
            encoder, self.gui.hw_accel_var.get()
        )
        # 构建编码器参数描述
        if encoder in ["libx265", "libx264"]:
            param_desc = f"编码器: {encoder} | CRF: {crf} | 预设: slow"
        elif encoder in ["hevc_nvenc", "h264_nvenc"]:
            param_desc = f"编码器: {encoder} | CQ: {crf} | 预设: p7 | 调优: hq"
        elif encoder in ["hevc_amf", "h264_amf"]:
            param_desc = f"编码器: {encoder} | QP_I: {crf} | QP_P: {crf} | 模式: cqp | 质量: balanced"
        elif encoder in ["hevc_qsv", "h264_qsv"]:
            param_desc = f"编码器: {encoder} | GQ: {crf} | 预设: slow"
        else:
            param_desc = f"编码器: {encoder} | 质量值: {crf}"

        res_desc = f"分辨率: {resolution}"
        audio_desc = f"音频: {'复制' if audio_bitrate == '不压缩' else 'AAC ' + audio_bitrate}"

        self.gui.root.after(0, self.gui.log_message, f"{param_desc} | {res_desc} | {audio_desc}")

        self.current_process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **get_subprocess_kwargs())

        start_time = time.time()
        stderr_lines = []   # 用于错误诊断
        progress_data = {}

        # 逐行读取 FFmpeg 的 stderr 输出（进度信息在 stderr 中）
        # 使用 readline 而非 read(4096)，确保每收到一行就立即处理
        # -progress pipe:2 每秒输出一组 key=value 行，readline 能实时响应
        while True:
            line_bytes = self.current_process.stderr.readline()
            if not line_bytes:
                break

            # 解码：先 strict UTF-8，失败回退 GBK，再失败用 replace
            line = None
            try:
                line = line_bytes.decode('utf-8').strip()
            except UnicodeDecodeError:
                try:
                    line = line_bytes.decode('gbk').strip()
                except UnicodeDecodeError:
                    line = line_bytes.decode('utf-8', errors='replace').strip()

            if not line:
                continue

            # 暂停检查
            self.pause_event.wait()
            if self.is_stopped:
                self.current_process.terminate()
                return False

            # -progress pipe:2 输出格式为 key=value，如：
            #   frame=123
            #   fps=60.0
            #   out_time=00:01:23.456789
            #   speed=2.5x
            #   progress=continue
            # 每个周期以 progress=continue 或 progress=end 结束
            if '=' in line:
                key, _, value = line.partition('=')
                key = key.strip()
                value = value.strip()
                progress_data[key] = value

                # 当收到 progress=continue 时，一个完整的进度周期结束，更新 UI
                if key == "progress" and duration > 0:
                    try:
                        out_time = progress_data.get("out_time", "")
                        if out_time and out_time != "N/A":
                            # out_time 可能是微秒整数或 HH:MM:SS.ffffff
                            try:
                                cur = int(out_time) / 1_000_000.0
                            except ValueError:
                                parts = out_time.split(':')
                                if len(parts) == 3:
                                    cur = float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
                                else:
                                    cur = 0

                            progress = min(cur / duration * 100, 100)
                            elapsed = time.time() - start_time
                            eta = (elapsed / progress * 100 - elapsed) if progress > 0 else 0
                            speed = cur / elapsed if elapsed > 0 else 0

                            current_frame = 0
                            frame_str = progress_data.get("frame", "0")
                            try:
                                current_frame = int(frame_str)
                            except (ValueError, IndexError):
                                pass

                            speed_str = progress_data.get("speed", "0x")
                            try:
                                speed = float(speed_str.rstrip('x'))
                            except (ValueError, AttributeError):
                                pass

                            self.gui.root.after(0, self.gui.update_progress,
                                progress, speed, eta, self.current_file_index, self.total_files,
                                current_frame, total_frames)
                    except Exception:
                        pass
                    # 重置进度数据，准备下一个周期
                    progress_data = {}
            else:
                # 非 key=value 格式的行，用于错误诊断
                stderr_lines.append(line)

        # 等待 FFmpeg 进程结束
        self.current_process.wait()

        if self.current_process.returncode == 0:
            elapsed = time.time() - start_time
            self.completed_count += 1
            self.completed_pairs.append((input_path, output_path))
            self.gui.root.after(0, self.gui.log_message,
                f"[OK] 压缩完成: {os.path.basename(input_path)} (耗时: {elapsed:.1f}秒) [{self.completed_count + self.skipped_count + len(self.failed_files)}/{self.total_files}]")
            return True
        else:
            if not self.is_stopped:
                # 前 5 行 + 后 10 行，避免信息过长
                err_parts = []
                if len(stderr_lines) > 15:
                    err_parts.append(''.join(stderr_lines[:5])[:300])
                    err_parts.append(' ... ')
                    err_parts.append(''.join(stderr_lines[-10:])[:300])
                else:
                    err_parts.append(''.join(stderr_lines[-10:])[:500])
                err = ''.join(err_parts)
                self.gui.root.after(0, self.gui.log_message,
                    f"[FAIL] 编码器 {encoder} 失败: {os.path.basename(input_path)}")
                self.gui.root.after(0, self.gui.log_message, f"  错误: {err}")
                out_safe = safe_path(output_path)
                if os.path.exists(out_safe):
                    try: os.remove(out_safe)
                    except Exception: pass
            return False

    def pause(self):
        """暂停压缩：挂起 FFmpeg 子进程 + 阻塞进度读取循环"""
        self.is_paused = True
        self.pause_event.clear()
        # 挂起 FFmpeg 进程（停止编码）
        if self.current_process and self.current_process.pid:
            ok = suspend_process(self.current_process.pid)
            if not ok:
                self.gui.root.after(0, self.gui.log_message,
                    "[WARN] 挂起 FFmpeg 进程失败，暂停可能不完整")

    def resume(self):
        """继续压缩：恢复 FFmpeg 子进程 + 解除进度读取阻塞"""
        self.is_paused = False
        self.pause_event.set()
        if self.current_process and self.current_process.pid:
            ok = resume_process(self.current_process.pid)
            if not ok:
                self.gui.root.after(0, self.gui.log_message,
                    "[WARN] 恢复 FFmpeg 进程失败")

    def stop(self):
        """停止压缩：终止 FFmpeg 进程并通知线程退出"""
        self.is_stopped = True
        self.pause_event.set()
        if self.current_process and self.current_process.pid:
            # 暂停状态下需先恢复进程才能终止
            if self.is_paused:
                resume_process(self.current_process.pid)
            try:
                self.current_process.terminate()
                # 避免僵尸进程
                try:
                    self.current_process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self.current_process.kill()
            except Exception:
                pass
        self.task_queue.put("STOP")


# =====================================================================
#  主界面
# =====================================================================

class VideoConverterGUI:
    """视频压缩工具主界面"""

    def __init__(self, root):
        self.root = root
        self.root.title(WINDOW_TITLE)
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.resizable(False, False)
        self.root.configure(bg=BACKGROUND_COLOR)

        self.video_files = []
        self.compressor = None
        self.start_time = None
        self._finished = False         # 防止 finish_compressing 被重复调用
        self.detected_hw = HardwareDetector.detect()
        self.selected_encoder = "libx265"
        self.ffmpeg_available = FFmpegManager.get_ffmpeg() is not None

        self.setup_ui()
        self.setup_logger()
        self.check_ffmpeg()

    def check_ffmpeg(self):
        """检查 FFmpeg 是否可用，并在信息框输出检测结果"""
        if not self.ffmpeg_available:
            self.log_message("[ERROR] 未检测到 FFmpeg！")
            self.log_message("  请将 ffmpeg.exe 和 ffprobe.exe 放在程序同目录或 bin 子目录下")
        else:
            hw = [k for k, v in self.detected_hw.items() if v and k != "software"]
            self.log_message(f"已编译的硬件编码器: {', '.join(hw) if hw else '无'}")
            self.log_message("提示：质量参数会根据编码器自动切换（软件CRF/NVIDIA CQ/Intel GQ/AMD QP），可直接使用默认值。")

    def setup_ui(self):
        """初始化所有界面元素"""
        style = ttk.Style()
        style.configure("TLabel", background=BACKGROUND_COLOR, font=(FONT_FAMILY, FONT_SIZE_NORMAL))
        style.configure("TButton", font=(FONT_FAMILY, FONT_SIZE_NORMAL))
        style.configure("TFrame", background=BACKGROUND_COLOR)
        style.configure("TScale", background=BACKGROUND_COLOR)
        style.configure("TCombobox", font=(FONT_FAMILY, FONT_SIZE_NORMAL))

        # --- 原视频文件夹 ---
        ttk.Label(self.root, text="原视频文件夹").place(x=LABEL_INPUT_X, y=LABEL_INPUT_Y, width=LABEL_INPUT_W, height=LABEL_INPUT_H)
        self.input_path_var = tk.StringVar()
        ttk.Entry(self.root, textvariable=self.input_path_var).place(x=ENTRY_INPUT_X, y=ENTRY_INPUT_Y, width=ENTRY_INPUT_W, height=ENTRY_INPUT_H)
        tk.Button(self.root, text="浏览...", bg=COLOR_BROWSE_BTN, fg=COLOR_BROWSE_BTN_TEXT,
                  font=(FONT_FAMILY, FONT_SIZE_NORMAL), relief=tk.FLAT,
                  command=self.browse_input_folder).place(x=BTN_INPUT_X, y=BTN_INPUT_Y, width=BTN_INPUT_W, height=BTN_INPUT_H)

        # --- 压缩输出文件夹 ---
        ttk.Label(self.root, text="压缩输出文件夹").place(x=LABEL_OUTPUT_X, y=LABEL_OUTPUT_Y, width=LABEL_OUTPUT_W, height=LABEL_OUTPUT_H)
        self.output_path_var = tk.StringVar()
        ttk.Entry(self.root, textvariable=self.output_path_var).place(x=ENTRY_OUTPUT_X, y=ENTRY_OUTPUT_Y, width=ENTRY_OUTPUT_W, height=ENTRY_OUTPUT_H)
        tk.Button(self.root, text="浏览...", bg=COLOR_BROWSE_BTN, fg=COLOR_BROWSE_BTN_TEXT,
                  font=(FONT_FAMILY, FONT_SIZE_NORMAL), relief=tk.FLAT,
                  command=self.browse_output_folder).place(x=BTN_OUTPUT_X, y=BTN_OUTPUT_Y, width=BTN_OUTPUT_W, height=BTN_OUTPUT_H)

        # --- 压缩参数设置分组框 ---
        param_frame = ttk.LabelFrame(self.root, text=PARAM_FRAME_TITLE)
        param_frame.place(x=PARAM_FRAME_X, y=PARAM_FRAME_Y, width=PARAM_FRAME_W, height=PARAM_FRAME_H)

        # CRF/CQ/GQ/QP 值调整
        # 标签文本和滑动条范围由 update_quality_slider() 根据编码器类型动态更新
        self.crf_label = ttk.Label(param_frame, text="CRF 值调整")
        self.crf_label.place(x=LABEL_CRF_X, y=LABEL_CRF_Y, width=LABEL_CRF_W, height=LABEL_CRF_H)
        self.crf_value = tk.IntVar(value=QUALITY_PARAMS["software"]["default"])
        self.crf_scale = ttk.Scale(param_frame, from_=QUALITY_PARAMS["software"]["min"],
                                    to=QUALITY_PARAMS["software"]["max"], variable=self.crf_value,
                                    command=self.update_crf_display)
        self.crf_scale.place(x=SCALE_CRF_X, y=SCALE_CRF_Y, width=SCALE_CRF_W, height=SCALE_CRF_H)
        self.crf_display_var = tk.StringVar(value=str(QUALITY_PARAMS["software"]["default"]))
        # 数值框只读，防止用户输入无效值
        tk.Entry(param_frame, textvariable=self.crf_display_var, justify=tk.CENTER,
                 state="readonly").place(x=ENTRY_CRF_X, y=ENTRY_CRF_Y, width=ENTRY_CRF_W, height=ENTRY_CRF_H)

        # 分辨率下拉菜单
        ttk.Label(param_frame, text="分辨率").place(x=LABEL_RES_X, y=LABEL_RES_Y, width=LABEL_RES_W, height=LABEL_RES_H)
        self.resolution_var = tk.StringVar(value=DEFAULT_RESOLUTION)
        ttk.Combobox(param_frame, textvariable=self.resolution_var, state="readonly",
                     values=RESOLUTION_OPTIONS).place(x=COMBO_RES_X, y=COMBO_RES_Y, width=COMBO_RES_W, height=COMBO_RES_H)

        # 音频比特率下拉菜单
        ttk.Label(param_frame, text="音频比特率").place(x=LABEL_AUDIO_X, y=LABEL_AUDIO_Y, width=LABEL_AUDIO_W, height=LABEL_AUDIO_H)
        self.audio_bitrate_var = tk.StringVar(value=DEFAULT_AUDIO_BITRATE)
        ttk.Combobox(param_frame, textvariable=self.audio_bitrate_var, state="readonly",
                     values=AUDIO_BITRATE_OPTIONS).place(x=COMBO_AUDIO_X, y=COMBO_AUDIO_Y, width=COMBO_AUDIO_W, height=COMBO_AUDIO_H)

        # 硬件加速复选框
        self.hw_accel_var = tk.BooleanVar(value=DEFAULT_HW_ACCEL)
        tk.Checkbutton(param_frame, text="启用硬件加速", variable=self.hw_accel_var,
                       background=COLOR_CHECKBOX_BG, font=(FONT_FAMILY, FONT_SIZE_NORMAL),
                       command=self.update_encoder).place(x=CHECK_HW_X, y=CHECK_HW_Y)

        # 编码格式下拉菜单
        ttk.Label(param_frame, text="编码格式").place(x=LABEL_ENCODER_X, y=LABEL_ENCODER_Y, width=LABEL_ENCODER_W, height=LABEL_ENCODER_H)
        self.encoder_var = tk.StringVar(value=DEFAULT_ENCODER)
        combo_enc = ttk.Combobox(param_frame, textvariable=self.encoder_var, state="readonly", values=ENCODER_OPTIONS)
        combo_enc.place(x=COMBO_ENCODER_X, y=COMBO_ENCODER_Y, width=COMBO_ENCODER_W, height=COMBO_ENCODER_H)
        combo_enc.bind("<<ComboboxSelected>>", lambda e: self.update_encoder())

        # --- 操作按钮 ---
        self.start_btn = tk.Button(self.root, text="开始压缩", bg=COLOR_START_BTN, fg=COLOR_START_BTN_TEXT,
                                   font=(FONT_FAMILY, FONT_SIZE_BOLD, "bold"), relief=tk.FLAT, command=self.start_compressing)
        self.start_btn.place(x=BTN_START_X, y=BTN_START_Y, width=BTN_START_W, height=BTN_START_H)

        self.pause_btn = tk.Button(self.root, text="暂停压缩", bg=COLOR_PAUSE_BTN, fg=COLOR_PAUSE_BTN_TEXT,
                                   font=(FONT_FAMILY, FONT_SIZE_BOLD, "bold"), relief=tk.FLAT, command=self.toggle_pause, state=tk.DISABLED)
        self.pause_btn.place(x=BTN_PAUSE_X, y=BTN_PAUSE_Y, width=BTN_PAUSE_W, height=BTN_PAUSE_H)

        self.stop_btn = tk.Button(self.root, text="停止压缩", bg=COLOR_STOP_BTN, fg=COLOR_STOP_BTN_TEXT,
                                  font=(FONT_FAMILY, FONT_SIZE_BOLD, "bold"), relief=tk.FLAT, command=self.stop_compressing, state=tk.DISABLED)
        self.stop_btn.place(x=BTN_STOP_X, y=BTN_STOP_Y, width=BTN_STOP_W, height=BTN_STOP_H)

        # --- 信息输出区域 ---
        ttk.Label(self.root, text="压缩信息").place(x=LABEL_LOG_X, y=LABEL_LOG_Y, width=LABEL_LOG_W, height=LABEL_LOG_H)
        self.log_text = scrolledtext.ScrolledText(self.root, font=("Consolas", 8), state=tk.DISABLED,
                                                   bg="#FFF5F8", fg="#8B0045")
        self.log_text.place(x=TEXT_LOG_X, y=TEXT_LOG_Y, width=TEXT_LOG_W, height=TEXT_LOG_H)

        # --- 进度条（Canvas 实现文字叠加 + 颜色随填充变化） ---
        self.progress_canvas = tk.Canvas(self.root, height=PROGRESS_BAR_H, bg=COLOR_PROGRESS_TROUGH,
                                          highlightthickness=0)
        self.progress_canvas.place(x=PROGRESS_BAR_X, y=PROGRESS_BAR_Y, width=PROGRESS_BAR_W, height=PROGRESS_BAR_H)

        self.update_encoder()

    def setup_logger(self):
        """初始化日志文件"""
        self.log_file = os.path.join(LOG_DIR, f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log")

    def log_message(self, message):
        """向信息输出框和日志文件写入一条消息"""
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {message}\n"
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, line)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(line)
        except Exception:
            pass

    def update_crf_display(self, value):
        """滑动条值变化时更新数值显示框"""
        self.crf_display_var.set(str(int(float(value))))

    def update_quality_slider(self, encoder):
        """根据编码器类型动态更新质量标签、滑动条范围和默认值"""
        if encoder in ["hevc_nvenc", "h264_nvenc"]:
            params = QUALITY_PARAMS["nvidia"]
        elif encoder in ["hevc_qsv", "h264_qsv"]:
            params = QUALITY_PARAMS["intel"]
        elif encoder in ["hevc_amf", "h264_amf"]:
            params = QUALITY_PARAMS["amd"]
        else:
            params = QUALITY_PARAMS["software"]

        self.crf_label.config(text=params["label"])
        self.crf_scale.config(from_=params["min"], to=params["max"])
        self.crf_value.set(params["default"])
        self.crf_display_var.set(str(params["default"]))

    def update_encoder(self):
        """更新编码器选择并进行运行时测试验证"""
        self.selected_encoder = HardwareDetector.get_best_encoder(
            self.encoder_var.get(), self.hw_accel_var.get(), self.detected_hw, self.log_message)
        is_hw = self.selected_encoder not in ["libx265", "libx264"]
        self.log_message(f"当前编码器: {self.selected_encoder} ({'硬件' if is_hw else '软件'})")
        self.update_quality_slider(self.selected_encoder)

    def browse_input_folder(self):
        """浏览选择原视频文件夹"""
        folder = filedialog.askdirectory(title="选择原视频文件夹")
        if folder:
            self.input_path_var.set(folder)
            self.video_files = FileHandler.scan_video_files(folder)
            self.log_message(f"找到 {len(self.video_files)} 个视频文件")
            for _, rp in self.video_files:
                self.log_message(f"  - {rp}")

    def browse_output_folder(self):
        """浏览选择压缩输出文件夹"""
        folder = filedialog.askdirectory(title="选择压缩输出文件夹")
        if folder:
            self.output_path_var.set(folder)

    def start_compressing(self):
        """开始压缩：验证输入 → 创建线程 → 启动"""
        if not FFmpegManager.get_ffmpeg():
            messagebox.showerror("错误", "未检测到 FFmpeg！\n\n请将 ffmpeg.exe 放在程序同目录或 bin 子目录下")
            return

        input_folder = self.input_path_var.get()
        output_folder = self.output_path_var.get()
        if not input_folder or not os.path.exists(safe_path(input_folder)):
            messagebox.showerror("错误", "请选择有效的原视频文件夹")
            return
        if not output_folder:
            messagebox.showerror("错误", "请选择压缩输出文件夹")
            return

        # 输入输出不能相同（防止覆盖原始文件）
        if os.path.normpath(input_folder) == os.path.normpath(output_folder):
            messagebox.showerror("错误", "原视频文件夹和压缩输出文件夹不能相同！\n否则会覆盖原始文件。")
            return

        self.video_files = FileHandler.scan_video_files(input_folder)
        if not self.video_files:
            messagebox.showwarning("提示", "未找到视频文件")
            return

        self._finished = False
        self.compressor = CompressorThread(self)
        self.compressor.total_files = len(self.video_files)
        for input_path, rel_path in self.video_files:
            output_path = FileHandler.get_output_path(rel_path, output_folder)
            self.compressor.task_queue.put((input_path, rel_path, output_path))

        self.start_time = time.time()
        self.compressor.start()

        self.start_btn.config(state=tk.DISABLED)
        self.pause_btn.config(state=tk.NORMAL, text="暂停压缩")
        self.stop_btn.config(state=tk.NORMAL)
        self.draw_progress(0, "")

        self.log_message("=" * 50)
        self.log_message(f"开始压缩，共 {len(self.video_files)} 个文件")
        encoder = self.selected_encoder
        crf = self.crf_value.get()
        if encoder in ["libx265", "libx264"]:
            self.log_message(f"编码器: {encoder} | CRF: {crf} | 预设: slow")
        elif encoder in ["hevc_nvenc", "h264_nvenc"]:
            self.log_message(f"编码器: {encoder} | CQ: {crf} | 预设: p7 | 调优: hq")
        elif encoder in ["hevc_amf", "h264_amf"]:
            self.log_message(f"编码器: {encoder} | QP_I: {crf} | QP_P: {crf} | 模式: cqp | 质量: balanced")
        elif encoder in ["hevc_qsv", "h264_qsv"]:
            self.log_message(f"编码器: {encoder} | GQ: {crf} | 预设: slow")
        else:
            self.log_message(f"编码器: {encoder} | 质量值: {crf}")
        self.log_message(f"分辨率: {self.resolution_var.get()} | 音频: {'复制' if self.audio_bitrate_var.get() == '不压缩' else 'AAC ' + self.audio_bitrate_var.get()}")
        self.log_message("=" * 50)

    def toggle_pause(self):
        """切换暂停/继续状态"""
        if self.compressor:
            if self.compressor.is_paused:
                self.compressor.resume()
                self.pause_btn.config(text="暂停压缩")
                self.log_message("继续压缩")
            else:
                self.compressor.pause()
                self.pause_btn.config(text="继续压缩")
                self.log_message("暂停压缩（FFmpeg 进程已挂起）")

    def stop_compressing(self):
        """停止压缩：终止 FFmpeg → 等待线程结束 → 显示统计"""
        if self.compressor:
            self.compressor.stop()
            self.log_message("停止压缩")
            self.compressor.join(timeout=3)  # 等待线程结束，避免统计数据竞态
            self.finish_compressing()

    def draw_progress(self, progress, text):
        """绘制进度条，深灰色文字叠加在进度条上"""
        self.progress_canvas.delete("all")
        w = PROGRESS_BAR_W
        h = PROGRESS_BAR_H
        fill_w = int(w * progress / 100)

        self.progress_canvas.create_rectangle(0, 0, w, h, fill=COLOR_PROGRESS_TROUGH, outline="")

        if fill_w > 0:
            self.progress_canvas.create_rectangle(0, 0, fill_w, h, fill=COLOR_PROGRESS_BAR, outline="")

        if text:
            cx, cy = w // 2, h // 2
            self.progress_canvas.create_text(cx, cy, text=text, fill=COLOR_PROGRESS_TEXT, font=(FONT_FAMILY, 8, "bold"))

    def update_progress(self, progress, speed, eta, current_file, total_files, current_frame=0, total_frames=0):
        """更新压缩进度显示"""
        eta_min = int(eta) // 60
        eta_sec = int(eta) % 60
        frame_info = ""
        if total_frames > 0 and current_frame > 0:
            remaining = max(total_frames - current_frame, 0)
            frame_info = f" | 帧 {current_frame}/{total_frames} (剩{remaining})"
        elif current_frame > 0:
            frame_info = f" | 帧 {current_frame}"
        text = f"第 {current_file}/{total_files} 个 | {progress:.0f}%{frame_info} | {speed:.1f}x | 剩余 {eta_min}:{eta_sec:02d}"
        self.draw_progress(progress, text)

    def finish_compressing(self):
        """压缩完成处理，使用 _finished 标志防止重复调用"""
        if self._finished:
            return
        self._finished = True

        self.start_btn.config(state=tk.NORMAL)
        self.pause_btn.config(state=tk.DISABLED, text="暂停压缩")
        self.stop_btn.config(state=tk.DISABLED)

        if not self.start_time:
            return

        total_time = time.time() - self.start_time
        self.log_message("=" * 50)
        self.log_message(f"压缩完成！总耗时: {total_time:.1f}秒")

        if self.compressor:
            s = self.compressor.completed_count
            f = len(self.compressor.failed_files)
            k = self.compressor.skipped_count
            self.log_message(f"成功: {s} | 失败: {f} | 跳过: {k}")

            original_total = 0
            compressed_total = 0
            for input_path, output_path in self.compressor.completed_pairs:
                try:
                    inp_size = os.path.getsize(safe_path(input_path))
                    out_size = os.path.getsize(safe_path(output_path))
                    original_total += inp_size
                    compressed_total += out_size
                except Exception:
                    pass

            if original_total > 0:
                saved = original_total - compressed_total
                pct = saved / original_total * 100
                self.log_message(f"原始总大小: {format_size(original_total)}")
                self.log_message(f"压缩后总大小: {format_size(compressed_total)}")
                if saved > 0:
                    self.log_message(f"节省空间: {format_size(saved)} (减少 {pct:.1f}%)")
                elif saved < 0:
                    self.log_message(f"体积增加: {format_size(-saved)} (增大 {-pct:.1f}%)")
                else:
                    self.log_message("体积未变化")

            if self.compressor.failed_files:
                self.log_message("失败文件:")
                for fp in self.compressor.failed_files:
                    self.log_message(f"  - {os.path.basename(fp)}")

        self.log_message("=" * 50)
        self.draw_progress(100, "全部完成！")

    def on_closing(self):
        """窗口关闭时，先停止压缩再退出，避免 FFmpeg 子进程残留"""
        if self.compressor and self.compressor.is_alive():
            self.compressor.stop()
            self.compressor.join(timeout=3)
        FFmpegManager.cleanup()
        self.root.destroy()


# =====================================================================
#  程序入口
# =====================================================================

def main():
    root = tk.Tk()
    app = VideoConverterGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()
