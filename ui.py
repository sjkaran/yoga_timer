import customtkinter as ctk
import threading
import time
from datetime import datetime
from voice_engine import voice_engine as VoiceEngine
import sys
import os

# ── optional window icon ────────────────────────────────────────────────────
try:
    from PIL import Image
    _PIL_OK = True
except ImportError:
    _PIL_OK = False


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  Colour palette  (original theme)                                        ║
# ╚══════════════════════════════════════════════════════════════════════════╝
BG          = "#000000"   # pure black
SURFACE     = "#0C2819"   # dark green display frame
BTN_FRAME   = "#1a1a1a"   # button bar background
ACCENT      = "#ade372"   # green  (start)
ACCENT_ON   = "#00d4ff"   # cyan   (after stop)
ACCENT_STOP = "#ff6b6b"   # red    (stop / reset)
ACCENT_GOLD = "#ffd900"   # yellow (voice on)
VOICE_OFF   = "#73737C"   # grey   (voice idle)
TEXT_PRI    = "#ffffff"
TEXT_MUT    = "#ffffff"
DIGIT_COL   = "#ff9706"   # orange digits


class TimerApp(ctk.CTk):

    # ── init ────────────────────────────────────────────────────────────────
    def __init__(self):
        super().__init__()

        # --- voice engine: init eagerly so first listen() has zero startup lag ---
        try:
            self._ve = VoiceEngine()
        except Exception as exc:
            print(f"[voice] engine init failed: {exc}")
            self._ve = None
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")
        self.configure(fg_color=BG)
        self.title("Timer")
        self.geometry("350x580")
        self.resizable(False, False)
        self.image_path = self.resource_path(relative_path="assets/clock_icon.ico")

        if _PIL_OK:
            try:
                self.iconbitmap(self.image_path)
            except Exception:
                pass

        # --- timer state ---
        self.is_running   = False
        self.start_mono   = 0.0    # monotonic timestamp of last start
        self.paused_acc   = 0.0    # seconds accumulated before current start
        self.pose_log: list[tuple[float, str]] = []  # (seconds, hh:mm:ss label)

        # --- voice state ---
        self.voice_on      = False
        self._stop_voice   = threading.Event()
        self._voice_thread: threading.Thread | None = None

        # --- debounce: ignore duplicate voice triggers within this window ---
        self._last_toggle_time = 0.0
        self._debounce_s       = 1.2

        self._build_ui()
        self._tick()          # start display refresh loop

    # ── UI construction ─────────────────────────────────────────────────────
    def _build_ui(self):
        FONT_CLOCK = ctk.CTkFont(family="Times", size=50, weight="bold")
        FONT_TITLE = ctk.CTkFont(family="Times New Roman", size=18, weight="bold")
        FONT_BTN   = ctk.CTkFont(size=12, weight="bold")
        FONT_LOG   = ctk.CTkFont(family="Times New Roman", size=11)

        # ── main container ────────────────────────────────────────────────
        main_frame = ctk.CTkFrame(self, fg_color=BG)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # ── title ─────────────────────────────────────────────────────────
        ctk.CTkLabel(
            main_frame, text="Timer",
            font=FONT_TITLE,
            text_color=TEXT_PRI,
        ).pack(pady=(10, 10))

        # ── display frame ─────────────────────────────────────────────────
        display_frame = ctk.CTkFrame(main_frame, fg_color=SURFACE, corner_radius=0)
        display_frame.pack(fill="both", expand=True, pady=8)

        self.time_label = ctk.CTkLabel(
            display_frame,
            text="00:00:00.00",
            font=FONT_CLOCK,
            text_color=DIGIT_COL,
        )
        self.time_label.pack(expand=True, fill="both", padx=10, pady=15)

        # ── status line (sits just below display, inside display_frame) ───
        self.status_label = ctk.CTkLabel(
            display_frame, text="",
            font=ctk.CTkFont(size=11),
            text_color=DIGIT_COL,
        )
        self.status_label.pack(pady=(0, 6))

        # ── button bar ────────────────────────────────────────────────────
        button_frame = ctk.CTkFrame(main_frame, fg_color=BTN_FRAME)
        button_frame.pack(fill="both", expand=False, pady=10)

        self.start_btn = ctk.CTkButton(
            button_frame,
            text="Start",
            font=FONT_BTN, height=35,
            fg_color=ACCENT, hover_color="#18cc00",
            text_color="#000000",
            command=self.toggle_timer,
        )
        self.start_btn.pack(side="left", expand=True, padx=(5, 5))

        self.voice_btn = ctk.CTkButton(
            button_frame,
            text="🎤",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=35, width=40,
            fg_color="#63636C", hover_color="#2cbf44",
            text_color="#1b0f0f",
            command=self._voice_toggle,
        )
        self.voice_btn.pack(side="right", expand=False, padx=(5, 5))

        self.reset_btn = ctk.CTkButton(
            button_frame,
            text="Reset",
            font=FONT_BTN, height=35,
            fg_color=ACCENT_STOP, hover_color="#cc5555",
            text_color="#ffffff",
            command=self.reset_timer,
        )
        self.reset_btn.pack(side="right", expand=True, padx=(5, 0))

        # ── session log ───────────────────────────────────────────────────
        sep = ctk.CTkFrame(main_frame, fg_color="#333333", height=1)
        sep.pack(fill="x", padx=0, pady=(8, 0))

        hdr = ctk.CTkFrame(main_frame, fg_color=BG)
        hdr.pack(fill="x", pady=(6, 0))

        ctk.CTkLabel(
            hdr, text="SESSION LOG",
            font=ctk.CTkFont(family="Times New Roman", size=11, weight="bold"),
            text_color="#555555",
        ).pack(side="left")

        self.pose_count_lbl = ctk.CTkLabel(
            hdr, text="0 holds",
            font=ctk.CTkFont(family="Times New Roman", size=11),
            text_color="#555555",
        )
        self.pose_count_lbl.pack(side="right")

        self.log_frame = ctk.CTkScrollableFrame(
            main_frame, fg_color=SURFACE, corner_radius=0,
            scrollbar_button_color="#333333",
        )
        self.log_frame.pack(fill="both", expand=True, pady=(4, 0))

        self.empty_lbl = ctk.CTkLabel(
            self.log_frame,
            text="Start timing to record holds.",
            font=FONT_LOG,
            text_color="#555555",
        )
        self.empty_lbl.pack(pady=16)

    # ── display tick (runs on main thread via after()) ───────────────────────
    def _tick(self):
        if self.is_running:
            elapsed = time.monotonic() - self.start_mono + self.paused_acc
            h  = int(elapsed // 3600)
            m  = int((elapsed % 3600) // 60)
            s  = int(elapsed % 60)
            cs = int((elapsed * 100) % 100)
            self.time_label.configure(text=f"{h:02d}:{m:02d}:{s:02d}.{cs:02d}")
        self.after(33, self._tick)   # ~30 fps is plenty

    # ── timer control ────────────────────────────────────────────────────────
    def toggle_timer(self):
        now = time.monotonic()
        if now - self._last_toggle_time < self._debounce_s:
            return                   # swallow duplicate triggers
        self._last_toggle_time = now

        if not self.is_running:
            self._start()
        else:
            self._stop()

    def _start(self):
        self.is_running = True
        self.start_mono = time.monotonic()
        self.start_btn.configure(text="Stop", fg_color=ACCENT_STOP, hover_color="#cc5555")
        self.status_label.configure(text="")

    def _stop(self):
        elapsed = time.monotonic() - self.start_mono + self.paused_acc
        self.paused_acc = elapsed          # persist so display stays correct
        self.is_running = False
        self.start_btn.configure(text="Start", fg_color=ACCENT_ON, hover_color="#00a8cc")
        self.status_label.configure(text="")
        self._log_hold(elapsed)

    def reset_timer(self):
        self.is_running  = False
        self.paused_acc  = 0.0
        self.start_mono  = 0.0
        self.time_label.configure(text="00:00:00.00")
        self.start_btn.configure(text="Start", fg_color=ACCENT, hover_color="#18cc00")
        self.status_label.configure(text="")

    # ── pose log ─────────────────────────────────────────────────────────────
    def _log_hold(self, seconds: float):
        if seconds < 0.5:
            return                   # ignore accidental taps

        h  = int(seconds // 3600)
        m  = int((seconds % 3600) // 60)
        s  = int(seconds % 60)
        label = f"{h:02d}:{m:02d}:{s:02d}"
        ts    = datetime.now().strftime("%H:%M:%S")
        self.pose_log.append((seconds, label))

        # remove "empty" placeholder
        if len(self.pose_log) == 1:
            self.empty_lbl.pack_forget()

        n = len(self.pose_log)
        row = ctk.CTkFrame(self.log_frame, fg_color="transparent")
        row.pack(fill="x", padx=8, pady=2)

        ctk.CTkLabel(
            row,
            text=f"#{n:02d}",
            font=ctk.CTkFont(family="Times New Roman", size=11, weight="bold"),
            text_color="#555555",
            width=32,
        ).pack(side="left")

        ctk.CTkLabel(
            row,
            text=label,
            font=ctk.CTkFont(family="Times New Roman", size=12, weight="bold"),
            text_color=DIGIT_COL,
        ).pack(side="left", padx=(8, 0))

        ctk.CTkLabel(
            row,
            text=f"@ {ts}",
            font=ctk.CTkFont(family="Times New Roman", size=11),
            text_color="#555555",
        ).pack(side="right")

        self.pose_count_lbl.configure(
            text=f"{n} hold{'s' if n > 1 else ''}"
        )

    # ── voice ─────────────────────────────────────────────────────────────────

    def resource_path(self,relative_path):
        base_path = getattr(sys, '_MEIPASS',os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_path,relative_path)
    def _voice_toggle(self):
        self.voice_on = not self.voice_on

        if self.voice_on:
            self.voice_btn.configure(fg_color=ACCENT_GOLD, text_color="#1b0f0f")
            self._stop_voice.clear()
            self._voice_thread = threading.Thread(
                target=self._voice_loop,
                args=(self._stop_voice,),
                daemon=True,
            )
            self._voice_thread.start()
        else:
            self.voice_btn.configure(fg_color=VOICE_OFF, text_color="#1b0f0f")
            self._stop_voice.set()
            self._voice_thread = None

    def _voice_loop(self, stop: threading.Event):
        """
        Background thread.  One listen() call at a time.
        We ask for exactly the words relevant to the current state,
        so the recogniser has less to match and fires faster.
        """
        if self._ve is None:
            print("[voice] engine not available")
            self.after(0, self._voice_toggle)
            return

        while not stop.is_set():
            # decide which words to listen for right now
            if self.is_running:
                targets = ["stop", "pause"]
            else:
                targets = ["start", "begin", "go", "reset", "clear"]

            word = self._ve.listen(words=targets, stop_event=stop, timeout=6.0)

            if stop.is_set() or word is None:
                continue

            # ── dispatch on main thread ───────────────────────────────────
            if word in ("stop", "pause"):
                self.after(0, self.toggle_timer)

            elif word in ("start", "begin", "go"):
                self.after(0, self.toggle_timer)

            elif word in ("reset", "clear"):
                self.after(0, self.reset_timer)

        print("[voice] thread stopped.")


    def _on_close(self):
        """Clean shutdown — stop the audio stream before destroying the window."""
        self._stop_voice.set()
        if self._ve:
            self._ve.close()
        self.destroy()

    # ── entry point ───────────────────────────────────────────────────────────────
def main():
    app = TimerApp()
    app.mainloop()


if __name__ == "__main__":
    main()