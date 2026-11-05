"""Video Downloader: TikTok videos/profiles and YouTube videos/channels (GUI, yt-dlp)."""
import os
import queue
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import yt_dlp

try:
    import imageio_ffmpeg
    FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:  # ffmpeg optional; falls back to single-file formats
    FFMPEG = None


class Logger:
    def __init__(self, q):
        self.q = q

    def debug(self, msg):
        pass

    def info(self, msg):
        pass

    def warning(self, msg):
        self.q.put(("log", "تحذير: " + str(msg)))

    def error(self, msg):
        self.q.put(("log", "خطأ: " + str(msg)))


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("برنامج تحميل TikTok / YouTube")
        self.geometry("720x520")
        self.q = queue.Queue()
        self.stop_flag = False
        self.folder = tk.StringVar(value=os.path.join(os.path.expanduser("~"), "Downloads", "VideoDownloader"))
        self.quality = tk.StringVar(value="أفضل جودة (فيديو)")
        self.limit = tk.StringVar(value="")
        self._build()
        self.after(100, self._poll)

    def _build(self):
        pad = {"padx": 8, "pady": 4}
        ttk.Label(self, text="الروابط (رابط في كل سطر): فيديو تيك توك، حساب تيك توك، فيديو يوتيوب، أو قناة يوتيوب").pack(anchor="w", **pad)
        self.urls = tk.Text(self, height=6)
        self.urls.pack(fill="x", **pad)

        row = ttk.Frame(self)
        row.pack(fill="x", **pad)
        ttk.Label(row, text="مجلد الحفظ:").pack(side="left")
        ttk.Entry(row, textvariable=self.folder).pack(side="left", fill="x", expand=True, padx=6)
        ttk.Button(row, text="تصفح", command=self._browse).pack(side="left")

        row2 = ttk.Frame(self)
        row2.pack(fill="x", **pad)
        ttk.Label(row2, text="الجودة:").pack(side="left")
        ttk.Combobox(row2, textvariable=self.quality, state="readonly", width=22,
                     values=["أفضل جودة (فيديو)", "720p", "480p", "صوت فقط (MP3)"]).pack(side="left", padx=6)
        ttk.Label(row2, text="أقصى عدد فيديوهات للقناة (فارغ = الكل):").pack(side="left", padx=(16, 4))
        ttk.Entry(row2, textvariable=self.limit, width=6).pack(side="left")

        row3 = ttk.Frame(self)
        row3.pack(fill="x", **pad)
        self.start_btn = ttk.Button(row3, text="ابدأ التحميل", command=self._start)
        self.start_btn.pack(side="left")
        self.stop_btn = ttk.Button(row3, text="إيقاف", command=self._stop, state="disabled")
        self.stop_btn.pack(side="left", padx=6)

        self.bar = ttk.Progressbar(self, maximum=100)
        self.bar.pack(fill="x", **pad)
        self.status = ttk.Label(self, text="جاهز")
        self.status.pack(anchor="w", **pad)
        self.log = tk.Text(self, height=12, state="disabled")
        self.log.pack(fill="both", expand=True, **pad)

    def _browse(self):
        d = filedialog.askdirectory()
        if d:
            self.folder.set(d)

    def _log(self, msg):
        self.log.configure(state="normal")
        self.log.insert("end", msg + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _poll(self):
        try:
            while True:
                kind, val = self.q.get_nowait()
                if kind == "log":
                    self._log(val)
                elif kind == "progress":
                    self.bar["value"] = val[0]
                    self.status.configure(text=val[1])
                elif kind == "done":
                    self.start_btn.configure(state="normal")
                    self.stop_btn.configure(state="disabled")
                    self.status.configure(text="انتهى")
        except queue.Empty:
            pass
        self.after(100, self._poll)

    def _stop(self):
        self.stop_flag = True
        self._log("جارٍ الإيقاف...")

    def _start(self):
        urls = [u.strip() for u in self.urls.get("1.0", "end").splitlines() if u.strip()]
        if not urls:
            messagebox.showwarning("تنبيه", "أدخل رابطًا واحدًا على الأقل")
            return
        limit = None
        if self.limit.get().strip():
            try:
                limit = int(self.limit.get())
            except ValueError:
                messagebox.showwarning("تنبيه", "العدد يجب أن يكون رقمًا")
                return
        os.makedirs(self.folder.get(), exist_ok=True)
        self.stop_flag = False
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        threading.Thread(target=self._run, args=(urls, limit), daemon=True).start()

    def _opts(self, limit):
        def hook(d):
            if self.stop_flag:
                raise yt_dlp.utils.DownloadCancelled("stopped")
            if d["status"] == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                pct = d.get("downloaded_bytes", 0) * 100 / total if total else 0
                name = os.path.basename(d.get("filename", ""))
                self.q.put(("progress", (pct, f"{pct:.0f}%  {name}")))
            elif d["status"] == "finished":
                self.q.put(("log", "تم: " + os.path.basename(d.get("filename", ""))))

        q = self.quality.get()
        opts = {
            "outtmpl": os.path.join(self.folder.get(), "%(uploader)s", "%(title).80B [%(id)s].%(ext)s"),
            "progress_hooks": [hook],
            "logger": Logger(self.q),
            "ignoreerrors": True,
            "noplaylist": False,
            "download_archive": os.path.join(self.folder.get(), "archive.txt"),
            "windowsfilenames": True,
        }
        if FFMPEG:
            opts["ffmpeg_location"] = FFMPEG
        if limit:
            opts["playlistend"] = limit
        if q.startswith("صوت"):
            opts["format"] = "bestaudio/best"
            opts["postprocessors"] = [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3"}]
        elif q == "720p":
            opts["format"] = "bv*[height<=720]+ba/b[height<=720]/b"
            opts["merge_output_format"] = "mp4"
        elif q == "480p":
            opts["format"] = "bv*[height<=480]+ba/b[height<=480]/b"
            opts["merge_output_format"] = "mp4"
        else:
            opts["format"] = "bv*+ba/b"
            opts["merge_output_format"] = "mp4"
        return opts

    def _run(self, urls, limit):
        try:
            with yt_dlp.YoutubeDL(self._opts(limit)) as ydl:
                for u in urls:
                    if self.stop_flag:
                        break
                    # YouTube channel root -> its videos tab
                    if "youtube.com" in u and any(x in u for x in ("/@", "/channel/", "/c/", "/user/")) \
                            and not u.rstrip("/").endswith(("/videos", "/shorts", "/streams")):
                        u = u.rstrip("/") + "/videos"
                    self.q.put(("log", "بدء: " + u))
                    try:
                        ydl.download([u])
                    except yt_dlp.utils.DownloadCancelled:
                        break
                    except Exception as e:
                        self.q.put(("log", f"فشل: {e}"))
        finally:
            self.q.put(("done", None))


if __name__ == "__main__":
    App().mainloop()
