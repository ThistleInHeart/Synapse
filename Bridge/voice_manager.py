# -*- coding: utf-8 -*-
"""
Synapse Local Voice Input Manager (Windows WinMM capture + whisper.cpp offline STT).

Zero extra Python audio dependencies required:
  - Microphone enumeration & 16 kHz PCM capture use Windows `winmm.dll` via `ctypes`.
  - Speech-to-text uses an optional user-downloaded `whisper.cpp` Windows x64 binary
    (`whisper-cli.exe`) + quantized GGML model (`ggml-base-q5_1.bin` or `ggml-small-q5_1.bin`)
    stored in `<SynapseDir>/voice/` so the base Synapse distribution stays lightweight.
"""

import ctypes
from ctypes import wintypes
import io
import json
import math
import os
import re
import ssl
import struct
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
import wave
import zipfile
from typing import Any, Callable, Dict, List, Optional, Tuple


def get_bridge_base_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def get_voice_dir(create: bool = False) -> str:
    p = os.path.join(get_bridge_base_dir(), "voice")
    if create:
        os.makedirs(p, exist_ok=True)
    return p


def get_voice_bin_dir(create: bool = False) -> str:
    p = os.path.join(get_voice_dir(create=create), "bin")
    if create:
        os.makedirs(p, exist_ok=True)
    return p


def get_voice_models_dir(create: bool = False) -> str:
    p = os.path.join(get_voice_dir(create=create), "models")
    if create:
        os.makedirs(p, exist_ok=True)
    return p


VOICE_MODELS: Dict[str, Dict[str, Any]] = {
    "fast": {
        "key": "fast",
        "filename": "ggml-base-q5_1.bin",
        "size_mb": 60,
        "url": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base-q5_1.bin",
    },
    "accurate": {
        "key": "accurate",
        "filename": "ggml-small-q5_1.bin",
        "size_mb": 190,
        "url": "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small-q5_1.bin",
    },
}

_WHISPER_RELEASES_API = "https://api.github.com/repos/ggml-org/whisper.cpp/releases?per_page=10"
_WHISPER_WIN64_FALLBACK_URL = "https://github.com/ggml-org/whisper.cpp/releases/download/b5907/whisper-bin-x64.zip"

_SAMPLE_RATE = 16000
_CHANNELS = 1
_BITS_PER_SAMPLE = 16
_BUFFER_MS = 100
_BUFFER_BYTES = (_SAMPLE_RATE * (_BITS_PER_SAMPLE // 8) * _CHANNELS * _BUFFER_MS) // 1000
_NUM_BUFFERS = 4
_MAX_RECORD_SECS = 60.0

_WHISPER_ARTIFACT_RE = re.compile(
    r"(\[(?:BLANK_AUDIO|MUSIC|APPLAUSE|LAUGHTER|SILENCE|МУЗЫКА|АПЛОДИСМЕНТЫ|СМЕХ|ТИШИНА|ЗВУК)[^\]]*\]"
    r"|\((?:music|applause|laughter|музыка|аплодисменты|смех)\))",
    re.IGNORECASE,
)


def _make_ssl_context() -> ssl.SSLContext:
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def find_whisper_cli_path() -> Optional[str]:
    bin_dir = get_voice_bin_dir(create=False)
    for exe_name in ("whisper-cli.exe", "main.exe"):
        candidate = os.path.join(bin_dir, exe_name)
        if os.path.isfile(candidate):
            return candidate
    return None


def get_model_spec(model_key: str) -> Dict[str, Any]:
    k = str(model_key or "accurate").strip().lower()
    if k not in VOICE_MODELS:
        k = "accurate"
    return VOICE_MODELS[k]


def find_model_path(model_key: str = "accurate") -> Optional[str]:
    mdir = get_voice_models_dir(create=False)
    spec = get_model_spec(model_key)
    preferred = os.path.join(mdir, spec["filename"])
    if os.path.isfile(preferred) and os.path.getsize(preferred) > 5 * 1024 * 1024:
        return preferred
    # Fallback to other valid model if user downloaded the alternative profile
    for other_key, other_spec in VOICE_MODELS.items():
        alt = os.path.join(mdir, other_spec["filename"])
        if os.path.isfile(alt) and os.path.getsize(alt) > 5 * 1024 * 1024:
            return alt
    return None


def is_voice_installed(model_key: str = "accurate") -> bool:
    return bool(find_whisper_cli_path() and find_model_path(model_key))


def is_voice_ready(cfg: Optional[Dict[str, Any]] = None) -> bool:
    if not isinstance(cfg, dict):
        return False
    if not bool(cfg.get("voice_enabled", False)):
        return False
    return is_voice_installed(str(cfg.get("voice_model") or "accurate"))


# =====================================================================
# WINDOWS WINMM AUDIO CAPTURE (CTYPES, 0 THIRD-PARTY PACKAGES)
# =====================================================================

_WAVE_FORMAT_PCM = 1
_WAVE_MAPPER = 0xFFFFFFFF
_CALLBACK_EVENT = 0x00050000
_WHDR_DONE = 0x00000001
_WAIT_OBJECT_0 = 0x00000000


class _WAVEFORMATEX(ctypes.Structure):
    _fields_ = [
        ("wFormatTag", wintypes.WORD),
        ("nChannels", wintypes.WORD),
        ("nSamplesPerSec", wintypes.DWORD),
        ("nAvgBytesPerSec", wintypes.DWORD),
        ("nBlockAlign", wintypes.WORD),
        ("wBitsPerSample", wintypes.WORD),
        ("cbSize", wintypes.WORD),
    ]


class _WAVEHDR(ctypes.Structure):
    _fields_ = [
        ("lpData", ctypes.c_char_p),
        ("dwBufferLength", wintypes.DWORD),
        ("dwBytesRecorded", wintypes.DWORD),
        ("dwUser", ctypes.c_void_p),
        ("dwFlags", wintypes.DWORD),
        ("dwLoops", wintypes.DWORD),
        ("lpNext", ctypes.c_void_p),
        ("reserved", ctypes.c_void_p),
    ]


class _WAVEINCAPSW(ctypes.Structure):
    _fields_ = [
        ("wMid", wintypes.WORD),
        ("wPid", wintypes.WORD),
        ("vDriverVersion", wintypes.UINT),
        ("szPname", wintypes.WCHAR * 32),
        ("dwFormats", wintypes.DWORD),
        ("wChannels", wintypes.WORD),
        ("wReserved1", wintypes.WORD),
    ]


def list_input_devices(is_en: bool = False) -> List[Dict[str, Any]]:
    default_lbl = "System Default Microphone" if is_en else "По умолчанию (Системный микрофон)"
    devices: List[Dict[str, Any]] = [{"id": -1, "name": default_lbl}]
    if sys.platform != "win32":
        return devices
    try:
        winmm = ctypes.windll.winmm
        count = int(winmm.waveInGetNumDevs())
        for idx in range(count):
            caps = _WAVEINCAPSW()
            res = winmm.waveInGetDevCapsW(ctypes.c_uint(idx), ctypes.byref(caps), ctypes.sizeof(caps))
            if res == 0:
                nm = str(caps.szPname or "").strip() or f"Microphone #{idx + 1}"
                devices.append({"id": idx, "name": nm})
    except Exception:
        pass
    return devices


def _pcm_to_wav_bytes(pcm_bytes: bytes) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(_CHANNELS)
        wf.setsampwidth(_BITS_PER_SAMPLE // 8)
        wf.setframerate(_SAMPLE_RATE)
        wf.writeframes(pcm_bytes)
    return buf.getvalue()


def _compute_rms_level(pcm_chunk: bytes) -> float:
    n = len(pcm_chunk) // 2
    if n <= 0:
        return 0.0
    try:
        samples = struct.unpack(f"<{n}h", pcm_chunk[: n * 2])
        sq = sum(s * s for s in samples)
        rms = math.sqrt(sq / n) / 32768.0
        # Boost perceptual speech scale so speaking hits 0.35..0.95 smoothly
        return max(0.0, min(1.0, rms * 4.5))
    except Exception:
        return 0.0


def _configure_winapi_types():
    """Set explicit Win64 argtypes/restype on kernel32/winmm calls to avoid 32-bit handle truncation."""
    winmm = ctypes.windll.winmm
    kernel32 = ctypes.windll.kernel32
    if not getattr(kernel32, "_synapse_typed", False):
        kernel32.CreateEventW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.BOOL, wintypes.LPCWSTR]
        kernel32.CreateEventW.restype = wintypes.HANDLE
        kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel32.WaitForSingleObject.restype = wintypes.DWORD
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL
        kernel32._synapse_typed = True
    if not getattr(winmm, "_synapse_typed", False):
        winmm.waveInOpen.argtypes = [
            ctypes.POINTER(wintypes.HANDLE),
            wintypes.UINT,
            ctypes.POINTER(_WAVEFORMATEX),
            ctypes.c_void_p,
            ctypes.c_void_p,
            wintypes.DWORD,
        ]
        winmm.waveInOpen.restype = wintypes.UINT
        winmm.waveInPrepareHeader.argtypes = [wintypes.HANDLE, ctypes.POINTER(_WAVEHDR), wintypes.UINT]
        winmm.waveInPrepareHeader.restype = wintypes.UINT
        winmm.waveInAddBuffer.argtypes = [wintypes.HANDLE, ctypes.POINTER(_WAVEHDR), wintypes.UINT]
        winmm.waveInAddBuffer.restype = wintypes.UINT
        winmm.waveInStart.argtypes = [wintypes.HANDLE]
        winmm.waveInStart.restype = wintypes.UINT
        winmm.waveInStop.argtypes = [wintypes.HANDLE]
        winmm.waveInStop.restype = wintypes.UINT
        winmm.waveInReset.argtypes = [wintypes.HANDLE]
        winmm.waveInReset.restype = wintypes.UINT
        winmm.waveInUnprepareHeader.argtypes = [wintypes.HANDLE, ctypes.POINTER(_WAVEHDR), wintypes.UINT]
        winmm.waveInUnprepareHeader.restype = wintypes.UINT
        winmm.waveInClose.argtypes = [wintypes.HANDLE]
        winmm.waveInClose.restype = wintypes.UINT
        winmm._synapse_typed = True
    return winmm, kernel32


class WinMMRecorder:
    """Thread-safe 16kHz mono PCM recorder backed by Windows `winmm.dll`."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._recording = False
        self._stop_req = threading.Event()
        self._done_ev = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._chunks: List[bytes] = []
        self.last_level: float = 0.0
        self.peak_level: float = 0.0
        self.error: str = ""

    @property
    def is_recording(self) -> bool:
        with self._lock:
            return self._recording

    def start(
        self,
        device_id: int = -1,
        max_secs: float = _MAX_RECORD_SECS,
        on_level: Optional[Callable[[float], None]] = None,
        on_auto_stop: Optional[Callable[[bytes], None]] = None,
    ) -> Tuple[bool, str]:
        if sys.platform != "win32":
            return False, "Microphone capture via WinMM is only supported on Windows."
        with self._lock:
            if self._recording:
                return False, "Already recording"
            self._chunks = []
            self.last_level = 0.0
            self.peak_level = 0.0
            self.error = ""
            self._stop_req.clear()
            self._done_ev.clear()
            self._recording = True

            self._thread = threading.Thread(
                target=self._record_worker,
                args=(int(device_id), float(max_secs), on_level, on_auto_stop),
                daemon=True,
                name="Synapse-WinMMRecorder",
            )
            self._thread.start()
        return True, ""

    def stop(self, timeout: float = 3.0) -> bytes:
        with self._lock:
            if not self._recording and self._done_ev.is_set():
                return _pcm_to_wav_bytes(b"".join(self._chunks))
            self._stop_req.set()
            thr = self._thread
        if thr is not None and thr.is_alive():
            self._done_ev.wait(timeout=timeout)
        with self._lock:
            self._recording = False
            pcm = b"".join(self._chunks)
            return _pcm_to_wav_bytes(pcm) if pcm else b""

    def cancel(self) -> None:
        self._stop_req.set()
        with self._lock:
            self._recording = False

    def _record_worker(
        self,
        device_id: int,
        max_secs: float,
        on_level: Optional[Callable[[float], None]],
        on_auto_stop: Optional[Callable[[bytes], None]],
    ) -> None:
        winmm, kernel32 = _configure_winapi_types()
        h_wave_in = wintypes.HANDLE()
        ev_handle = None
        headers: List[_WAVEHDR] = []
        raw_bufs: List[ctypes.Array] = []
        opened = False
        timed_out = False

        try:
            ev_handle = kernel32.CreateEventW(None, False, False, None)
            if not ev_handle:
                raise RuntimeError("CreateEventW failed")

            wfx = _WAVEFORMATEX()
            wfx.wFormatTag = _WAVE_FORMAT_PCM
            wfx.nChannels = _CHANNELS
            wfx.nSamplesPerSec = _SAMPLE_RATE
            wfx.wBitsPerSample = _BITS_PER_SAMPLE
            wfx.nBlockAlign = (_CHANNELS * _BITS_PER_SAMPLE) // 8
            wfx.nAvgBytesPerSec = _SAMPLE_RATE * wfx.nBlockAlign
            wfx.cbSize = 0

            dev_arg = _WAVE_MAPPER if device_id < 0 else ctypes.c_uint(device_id)
            rc = winmm.waveInOpen(
                ctypes.byref(h_wave_in),
                dev_arg,
                ctypes.byref(wfx),
                ev_handle,
                0,
                _CALLBACK_EVENT,
            )
            if rc != 0:
                # Fallback to WAVE_MAPPER if chosen device index changed
                if device_id >= 0:
                    rc = winmm.waveInOpen(
                        ctypes.byref(h_wave_in),
                        _WAVE_MAPPER,
                        ctypes.byref(wfx),
                        ev_handle,
                        0,
                        _CALLBACK_EVENT,
                    )
                if rc != 0:
                    raise RuntimeError(f"waveInOpen failed (code={rc})")
            opened = True

            for _ in range(_NUM_BUFFERS):
                cb = ctypes.create_string_buffer(_BUFFER_BYTES)
                hdr = _WAVEHDR()
                hdr.lpData = ctypes.cast(cb, ctypes.c_char_p)
                hdr.dwBufferLength = _BUFFER_BYTES
                hdr.dwFlags = 0
                raw_bufs.append(cb)
                headers.append(hdr)
                rc_prep = winmm.waveInPrepareHeader(h_wave_in, ctypes.byref(hdr), ctypes.sizeof(hdr))
                if rc_prep != 0:
                    raise RuntimeError(f"waveInPrepareHeader failed (code={rc_prep})")
                rc_add = winmm.waveInAddBuffer(h_wave_in, ctypes.byref(hdr), ctypes.sizeof(hdr))
                if rc_add != 0:
                    raise RuntimeError(f"waveInAddBuffer failed (code={rc_add})")

            rc_start = winmm.waveInStart(h_wave_in)
            if rc_start != 0:
                raise RuntimeError(f"waveInStart failed (code={rc_start})")

            t_start = time.time()
            while not self._stop_req.is_set():
                if max_secs > 0 and (time.time() - t_start) >= max_secs:
                    timed_out = True
                    break
                kernel32.WaitForSingleObject(ev_handle, 120)
                for idx, hdr in enumerate(headers):
                    if (hdr.dwFlags & _WHDR_DONE) != 0:
                        rec_len = int(hdr.dwBytesRecorded)
                        if rec_len > 0:
                            chunk = bytes(raw_bufs[idx][:rec_len])
                            self._chunks.append(chunk)
                            lvl = _compute_rms_level(chunk)
                            self.last_level = lvl
                            if lvl > self.peak_level:
                                self.peak_level = lvl
                            if on_level is not None:
                                try:
                                    on_level(lvl)
                                except Exception:
                                    pass
                        if not self._stop_req.is_set() and not timed_out:
                            hdr.dwFlags &= ~_WHDR_DONE
                            hdr.dwBytesRecorded = 0
                            winmm.waveInAddBuffer(h_wave_in, ctypes.byref(hdr), ctypes.sizeof(hdr))

            try:
                winmm.waveInStop(h_wave_in)
                winmm.waveInReset(h_wave_in)
                # Flush any final partial buffer marked done by waveInReset
                for idx, hdr in enumerate(headers):
                    if (hdr.dwFlags & _WHDR_DONE) != 0 and int(hdr.dwBytesRecorded) > 0:
                        chunk = bytes(raw_bufs[idx][: int(hdr.dwBytesRecorded)])
                        self._chunks.append(chunk)
                    winmm.waveInUnprepareHeader(h_wave_in, ctypes.byref(hdr), ctypes.sizeof(hdr))
            except Exception:
                pass
        except Exception as e:
            self.error = str(e)
        finally:
            if opened:
                try:
                    winmm.waveInClose(h_wave_in)
                except Exception:
                    pass
            if ev_handle:
                try:
                    kernel32.CloseHandle(ev_handle)
                except Exception:
                    pass
            with self._lock:
                self._recording = False
            self._done_ev.set()

        if timed_out and on_auto_stop is not None:
            try:
                pcm = b"".join(self._chunks)
                if pcm:
                    on_auto_stop(_pcm_to_wav_bytes(pcm))
            except Exception:
                pass


def run_mic_test(
    device_id: int = -1,
    duration_secs: float = 3.0,
    on_level: Optional[Callable[[float], None]] = None,
) -> Tuple[bool, float, str]:
    rec = WinMMRecorder()
    ok, err = rec.start(device_id=device_id, max_secs=duration_secs, on_level=on_level)
    if not ok:
        return False, 0.0, err
    time.sleep(max(0.5, duration_secs) + 0.2)
    wav_bytes = rec.stop(timeout=2.0)
    if rec.error:
        return False, 0.0, rec.error
    if not wav_bytes or len(wav_bytes) < 200:
        return False, 0.0, "No audio data captured"
    return True, rec.peak_level, ""


# =====================================================================
# WHISPER.CPP DOWNLOADER & TRANSCRIPTION
# =====================================================================

def _resolve_whisper_win64_zip_url(ssl_ctx: ssl.SSLContext) -> str:
    try:
        req = urllib.request.Request(
            _WHISPER_RELEASES_API,
            headers={"User-Agent": "Synapse-VoiceInstaller", "Accept": "application/vnd.github+json"},
        )
        with urllib.request.urlopen(req, context=ssl_ctx, timeout=15) as resp:
            releases = json.loads(resp.read().decode("utf-8"))
        if isinstance(releases, list):
            for rel in releases:
                for asset in (rel.get("assets") or []):
                    name = str(asset.get("name") or "")
                    if name == "whisper-bin-x64.zip" and asset.get("browser_download_url"):
                        return str(asset["browser_download_url"])
    except Exception:
        pass
    return _WHISPER_WIN64_FALLBACK_URL


def _download_with_progress(
    url: str,
    dest_path: str,
    ssl_ctx: ssl.SSLContext,
    pct_start: float,
    pct_end: float,
    stage_label: str,
    progress_cb: Optional[Callable[[float, str], None]] = None,
) -> None:
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    tmp_path = f"{dest_path}.{os.getpid()}.tmp"
    req = urllib.request.Request(url, headers={"User-Agent": "Synapse-VoiceInstaller"})
    try:
        with urllib.request.urlopen(req, context=ssl_ctx, timeout=60) as resp:
            total = int(resp.headers.get("Content-Length") or 0)
            downloaded = 0
            chunk_sz = 131072
            with open(tmp_path, "wb") as out_f:
                while True:
                    blk = resp.read(chunk_sz)
                    if not blk:
                        break
                    out_f.write(blk)
                    downloaded += len(blk)
                    if progress_cb is not None and total > 0:
                        frac = min(1.0, downloaded / float(total))
                        pct = pct_start + (pct_end - pct_start) * frac
                        mb_done = downloaded / (1024.0 * 1024.0)
                        mb_tot = total / (1024.0 * 1024.0)
                        progress_cb(pct, f"{stage_label} ({mb_done:.1f} / {mb_tot:.1f} MB)")
        os.replace(tmp_path, dest_path)
    except Exception:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass
        raise


def install_voice_pack(
    model_key: str = "accurate",
    progress_cb: Optional[Callable[[float, str], None]] = None,
    is_en: bool = False,
) -> Tuple[bool, str]:
    """Downloads whisper.cpp Win64 binaries and the selected GGML model into `<bridge>/voice/`."""
    ssl_ctx = _make_ssl_context()
    bin_dir = get_voice_bin_dir(create=True)
    models_dir = get_voice_models_dir(create=True)
    spec = get_model_spec(model_key)

    need_bin = (find_whisper_cli_path() is None)
    model_dest = os.path.join(models_dir, spec["filename"])
    need_model = not (os.path.isfile(model_dest) and os.path.getsize(model_dest) > 5 * 1024 * 1024)

    try:
        if need_bin:
            lbl_bin = "Downloading whisper.cpp engine..." if is_en else "Скачивание движка whisper.cpp..."
            if progress_cb:
                progress_cb(2.0, lbl_bin)
            zip_url = _resolve_whisper_win64_zip_url(ssl_ctx)
            zip_path = os.path.join(bin_dir, "_whisper_bin.zip")
            _download_with_progress(
                zip_url,
                zip_path,
                ssl_ctx,
                pct_start=2.0,
                pct_end=25.0 if need_model else 95.0,
                stage_label=lbl_bin,
                progress_cb=progress_cb,
            )
            lbl_ext = "Extracting engine..." if is_en else "Распаковка движка..."
            if progress_cb:
                progress_cb(26.0 if need_model else 96.0, lbl_ext)
            with zipfile.ZipFile(zip_path, "r") as zf:
                for member in zf.infolist():
                    if member.is_dir():
                        continue
                    base_name = os.path.basename(member.filename)
                    if not base_name.lower().endswith((".exe", ".dll")):
                        continue
                    out_file = os.path.join(bin_dir, base_name)
                    with zf.open(member) as src_f, open(out_file, "wb") as dst_f:
                        dst_f.write(src_f.read())
            try:
                os.remove(zip_path)
            except Exception:
                pass
            if find_whisper_cli_path() is None:
                raise RuntimeError("whisper-cli.exe was not found in downloaded archive")

        if need_model:
            lbl_mod = (
                f"Downloading model ({spec['size_mb']} MB)..."
                if is_en
                else f"Скачивание голосовой модели ({spec['size_mb']} МБ)..."
            )
            _download_with_progress(
                spec["url"],
                model_dest,
                ssl_ctx,
                pct_start=28.0 if need_bin else 3.0,
                pct_end=99.0,
                stage_label=lbl_mod,
                progress_cb=progress_cb,
            )

        if progress_cb:
            progress_cb(100.0, "Ready!" if is_en else "Готово!")
        return True, model_dest
    except Exception as e:
        return False, str(e)


def _clean_transcript(raw_text: str) -> str:
    txt = str(raw_text or "").strip()
    if not txt:
        return ""
    txt = _WHISPER_ARTIFACT_RE.sub(" ", txt)
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt


def transcribe_wav_bytes(wav_bytes: bytes, cfg: Optional[Dict[str, Any]] = None) -> Tuple[bool, str]:
    """Runs whisper-cli.exe on captured WAV audio and returns clean transcribed text."""
    if not wav_bytes or len(wav_bytes) < 500:
        return True, ""

    cli_path = find_whisper_cli_path()
    model_key = str((cfg or {}).get("voice_model") or "accurate")
    model_path = find_model_path(model_key)
    if not cli_path or not model_path:
        return False, "Voice pack not installed"

    # Choose target language: if "auto", follow Bridge language so Russian mic noise won't misdetect language
    v_lang = str((cfg or {}).get("voice_lang") or "auto").strip().lower()
    if v_lang == "auto":
        app_lang = str((cfg or {}).get("language") or "ru").strip().lower()
        v_lang = "en" if app_lang == "en" else "ru"
    if v_lang not in ("ru", "en", "auto"):
        v_lang = "ru"

    tmp_wav = None
    try:
        fd, tmp_wav = tempfile.mkstemp(prefix="synapse_voice_", suffix=".wav")
        os.close(fd)
        with open(tmp_wav, "wb") as wf:
            wf.write(wav_bytes)

        threads = max(2, min(8, os.cpu_count() or 4))
        cmd = [
            cli_path,
            "-m", model_path,
            "-f", tmp_wav,
            "-l", v_lang,
            "-nt",
            "--no-prints",
            "-t", str(threads),
        ]
        creation_flags = 0x08000000 if sys.platform == "win32" else 0
        proc = subprocess.run(
            cmd,
            cwd=os.path.dirname(cli_path),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=45,
            creationflags=creation_flags,
        )
        raw_out = (proc.stdout or b"").decode("utf-8", errors="replace")
        if proc.returncode != 0 and not raw_out.strip():
            err_s = (proc.stderr or b"").decode("utf-8", errors="replace").strip()
            return False, err_s or f"whisper-cli exited with code {proc.returncode}"
        return True, _clean_transcript(raw_out)
    except Exception as e:
        return False, str(e)
    finally:
        if tmp_wav and os.path.exists(tmp_wav):
            try:
                os.remove(tmp_wav)
            except Exception:
                pass


# =====================================================================
# SINGLETON VOICE SESSION MANAGER (FOR AI_BRIDGE HTTP ENDPOINTS)
# =====================================================================

class VoiceSessionManager:
    """Manages toggle-based recording and async STT results for Sims 4 UI polling."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._recorder = WinMMRecorder()
        self._transcribing = False
        self._seq = 0
        self._last_text = ""
        self._last_target = "sulnet"
        self._last_auto_send = False
        self._last_error = ""
        self._active_target = "sulnet"
        self._active_cfg: Dict[str, Any] = {}

    def get_status(self, cfg: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        with self._lock:
            ready = is_voice_ready(cfg) if cfg is not None else is_voice_installed()
            return {
                "success": True,
                "ready": ready,
                "recording": self._recorder.is_recording,
                "transcribing": self._transcribing,
                "seq": self._seq,
                "text": self._last_text,
                "target": self._last_target,
                "auto_send": self._last_auto_send,
                "error": self._last_error,
            }

    def toggle(self, cfg: Dict[str, Any], target: str = "sulnet") -> Dict[str, Any]:
        clean_target = "dd" if str(target or "").strip().lower() == "dd" else "sulnet"
        if not is_voice_ready(cfg):
            return {
                "success": True,
                "ready": False,
                "recording": False,
                "transcribing": False,
                "seq": self._seq,
            }

        with self._lock:
            if self._recorder.is_recording:
                self._stop_and_transcribe_locked(cfg, clean_target)
                return {
                    "success": True,
                    "ready": True,
                    "recording": False,
                    "transcribing": self._transcribing,
                    "seq": self._seq,
                }

            if self._transcribing:
                return {
                    "success": True,
                    "ready": True,
                    "recording": False,
                    "transcribing": True,
                    "seq": self._seq,
                }

            self._active_target = clean_target
            self._active_cfg = dict(cfg)
            self._last_error = ""
            dev_id = int(cfg.get("voice_device_id", -1) if cfg.get("voice_device_id") is not None else -1)

            def _on_auto(wav_bytes: bytes) -> None:
                with self._lock:
                    if not self._transcribing:
                        self._launch_transcribe_thread(wav_bytes, dict(self._active_cfg), self._active_target)

            ok, err = self._recorder.start(
                device_id=dev_id,
                max_secs=_MAX_RECORD_SECS,
                on_auto_stop=_on_auto,
            )
            if not ok:
                self._last_error = err
            return {
                "success": True,
                "ready": True,
                "recording": ok,
                "transcribing": False,
                "seq": self._seq,
                "error": self._last_error,
            }

    def cancel(self) -> Dict[str, Any]:
        with self._lock:
            if self._recorder.is_recording:
                self._recorder.cancel()
        return {"success": True, "recording": False, "transcribing": self._transcribing}

    def _stop_and_transcribe_locked(self, cfg: Dict[str, Any], target: str) -> None:
        wav_bytes = self._recorder.stop(timeout=2.5)
        self._launch_transcribe_thread(wav_bytes, dict(cfg), target)

    def _launch_transcribe_thread(self, wav_bytes: bytes, cfg: Dict[str, Any], target: str) -> None:
        self._transcribing = True

        def _worker() -> None:
            ok, txt_or_err = transcribe_wav_bytes(wav_bytes, cfg)
            with self._lock:
                self._transcribing = False
                self._last_target = target
                self._last_auto_send = bool(cfg.get("voice_auto_send", False))
                if ok:
                    self._last_text = txt_or_err
                    self._last_error = ""
                else:
                    self._last_text = ""
                    self._last_error = txt_or_err
                self._seq += 1

        threading.Thread(target=_worker, daemon=True, name="Synapse-WhisperSTT").start()


VOICE_SESSION = VoiceSessionManager()
