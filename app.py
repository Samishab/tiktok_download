"""Video Downloader: TikTok & YouTube (modern GUI, yt-dlp)."""
import os
import queue
import threading
from tkinter import filedialog, messagebox

import customtkinter as ctk
import yt_dlp

try:
    import imageio_ffmpeg
    FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    FFMPEG = None

ACCENT = "#fe2c55"      # TikTok red
ACCENT_HOVER = "#d81e45"
CYAN = "#25f4ee"
BG = "#0f0f14"
CARD = "#1a1a24"

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")


class Logger:
    def __init__(self, q):
        self.q = q

    def debug(self, msg): pass
    def info(self, msg): pass

    def warning(self, msg):
        if "impersonat" not in str(msg):
            self.q.put(("log", "⚠ " + str(msg)))

    def error(self, msg):
        self.q.put(("log", "✖ " + str(msg)))


class App(ctk.CTk):
    def __init__(self):
        super().__init__(fg_color=BG)
        self.title("Video Downloader")
        self.geometry("780x680")
        self.minsize(680, 600)
        self.q = queue.Queue()
        self.stop_flag = False
        self.folder = ctk.StringVar(value=os.path.join(os.path.expanduser("~"), "Downloads", "VideoDownloader"))
        self.quality = ctk.StringVar(value="أفضل جودة")
        self.limit = ctk.StringVar(value="")
        self._build()
        self.after(100, self._poll)

    def _card(self, parent):
        return ctk.CTkFrame(parent, fg_color=CARD, corner_radius=16)

    def _build(self):
        head = ctk.CTkFrame(self, fg_color="transparent")
        head.pack(fill="x", padx=24, pady=(20, 8))
        ctk.CTkLabel(head, text="⬇  Video Downloader", font=ctk.CTkFont(size=28, weight="bold")).pack(side="left")
        ctk.CTkLabel(head, text="TikTok  •  YouTube", text_color=CYAN,
                     font=ctk.CTkFont(size=14, weight="bold")).pack(side="right")

        c1 = self._card(self)
        c1.pack(fill="x", padx=24, pady=8)
        ctk.CTkLabel(c1, text="الروابط (رابط في كل سطر) — فيديو، حساب تيك توك، أو قناة يوتيوب",
                     anchor="w", text_color="#b8b8c8").pack(fill="x", padx=16, pady=(14, 4))
        self.urls = ctk.CTkTextbox(c1, height=110, corner_radius=10, fg_color="#12121a", border_width=1,
                                   border_color="#2c2c3c", font=ctk.CTkFont(size=13))
        self.urls.pack(fill="x", padx=16, pady=(0, 14))

        c2 = self._card(self)
        c2.pack(fill="x", padx=24, pady=8)
        r1 = ctk.CTkFrame(c2, fg_color="transparent")
        r1.pack(fill="x", padx=16, pady=(14, 6))
        ctk.CTkEntry(r1, textvariable=self.folder, corner_radius=10, height=36).pack(side="left", fill="x", expand=True)
        ctk.CTkButton(r1, text="📁 تصفح", width=90, height=36, fg_color="#2c2c3c", hover_color="#3a3a4e",
                      command=self._browse).pack(side="left", padx=(8, 0))
        r2 = ctk.CTkFrame(c2, fg_color="transparent")
        r2.pack(fill="x", padx=16, pady=(6, 14))
        ctk.CTkLabel(r2, text="الجودة", text_color="#b8b8c8").pack(side="left")
        ctk.CTkOptionMenu(r2, variable=self.quality, width=150, fg_color="#2c2c3c", button_color=ACCENT,
                          button_hover_color=ACCENT_HOVER,
                          values=["أفضل جودة", "720p", "480p", "صوت فقط (MP3)"]).pack(side="left", padx=8)
        ctk.CTkLabel(r2, text="أقصى عدد للقناة", text_color="#b8b8c8").pack(side="left", padx=(16, 4))
        ctk.CTkEntry(r2, textvariable=self.limit, width=70, placeholder_text="الكل").pack(side="left")

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(fill="x", padx=24, pady=8)
        self.start_btn = ctk.CTkButton(btns, text="▶  ابدأ التحميل", height=46, corner_radius=23,
                                       fg_color=ACCENT, hover_color=ACCENT_HOVER,
                                       font=ctk.CTkFont(size=16, weight="bold"), command=self._start)
        self.start_btn.pack(side="left", fill="x", expand=True)
        self.stop_btn = ctk.CTkButton(btns, text="■  إيقاف", height=46, width=120, corner_radius=23,
                                      fg_color="#2c2c3c", hover_color="#3a3a4e", state="disabled", command=self._stop)
        self.stop_btn.pack(side="left", padx=(10, 0))

        c3 = self._card(self)
        c3.pack(fill="both", expand=True, padx=24, pady=(8, 20))
        self.status = ctk.CTkLabel(c3, text="جاهز", anchor="w", text_color=CYAN)
        self.status.pack(fill="x", padx=16, pady=(12, 4))
        self.bar = ctk.CTkProgressBar(c3, progress_color=ACCENT, height=10)
        self.bar.set(0)
        self.bar.pack(fill="x", padx=16, pady=(0, 8))
        self.log = ctk.CTkTextbox(c3, corner_radius=10, fg_color="#12121a", state="disabled",
                                  font=ctk.CTkFont(size=12))
        self.log.pack(fill="both", expand=True, padx=16, pady=(0, 14))

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
                    self.bar.set(val[0] / 100)
                    self.status.configure(text=val[1])
                elif kind == "done":
                    self.start_btn.configure(state="normal")
                    self.stop_btn.configure(state="disabled")
                    self.status.configure(text="✔ انتهى")
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
                self.q.put(("progress", (pct, f"{pct:.0f}%  {os.path.basename(d.get('filename', ''))}")))
            elif d["status"] == "finished":
                self.q.put(("log", "✔ " + os.path.basename(d.get("filename", ""))))

        q = self.quality.get()
        opts = {
            "outtmpl": os.path.join(self.folder.get(), "%(uploader)s", "%(title).80B [%(id)s].%(ext)s"),
            "progress_hooks": [hook],
            "logger": Logger(self.q),
            "ignoreerrors": True,
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
        else:
            h = {"720p": 720, "480p": 480}.get(q)
            cap = f"[height<={h}]" if h else ""
            opts["format"] = f"bv*{cap}+ba/b{cap}/b"
            opts["merge_output_format"] = "mp4"
        return opts

    def _run(self, urls, limit):
        try:
            with yt_dlp.YoutubeDL(self._opts(limit)) as ydl:
                for u in urls:
                    if self.stop_flag:
                        break
                    if "youtube.com" in u and any(x in u for x in ("/@", "/channel/", "/c/", "/user/")) \
                            and not u.rstrip("/").endswith(("/videos", "/shorts", "/streams")):
                        u = u.rstrip("/") + "/videos"
                    self.q.put(("log", "▶ " + u))
                    try:
                        ydl.download([u])
                    except yt_dlp.utils.DownloadCancelled:
                        break
                    except Exception as e:
                        self.q.put(("log", f"✖ {e}"))
        finally:
            self.q.put(("done", None))


if __name__ == "__main__":
    App().mainloop()
