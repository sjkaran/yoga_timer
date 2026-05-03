import customtkinter as ctk
from tkinter import font
import threading
import time


class TimerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Configure dark theme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")
        
        # Window setup
        self.title("Timer")
        self.geometry("600x700")
        self.resizable(True, True)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # Timer variables
        self.elapsed_time = 0
        self.is_running = False
        self.timer_thread = None
        self.start_time = None
        self.paused_time = 0
        
        # Main container
        main_frame = ctk.CTkFrame(self, fg_color="#1a1a1a")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title
        title_label = ctk.CTkLabel(
            main_frame,
            text="Timer",
            font=ctk.CTkFont(family="Helvetica", size=32, weight="bold"),
            text_color="#ffffff"
        )
        title_label.pack(pady=(0, 40))
        
        # Display frame for timer
        display_frame = ctk.CTkFrame(main_frame, fg_color="#2d2d2d", corner_radius=20)
        display_frame.pack(fill="both", expand=True, pady=20)
        
        # Timer display label with large font
        self.time_display = ctk.CTkLabel(
            display_frame,
            text="00:00:00.00",
            font=ctk.CTkFont(family="Courier", size=120, weight="bold"),
            text_color="#00d4ff"
        )
        self.time_display.pack(expand=True, fill="both", padx=20, pady=40)
        
        # Buttons frame
        button_frame = ctk.CTkFrame(main_frame, fg_color="#1a1a1a")
        button_frame.pack(fill="both", expand=False, pady=20)
        
        # Start/Stop button
        self.start_stop_btn = ctk.CTkButton(
            button_frame,
            text="Start",
            font=ctk.CTkFont(size=16, weight="bold"),
            height=60,
            fg_color="#00d4ff",
            hover_color="#00a8cc",
            text_color="#000000",
            command=self.toggle_timer
        )
        self.start_stop_btn.pack(side="left", expand=True, padx=(0, 10))
        
        # Reset button
        self.reset_btn = ctk.CTkButton(
            button_frame,
            text="Reset",
            font=ctk.CTkFont(size=16, weight="bold"),
            height=60,
            fg_color="#ff6b6b",
            hover_color="#cc5555",
            text_color="#ffffff",
            command=self.reset_timer
        )
        self.reset_btn.pack(side="right", expand=True, padx=(10, 0))
    
    def toggle_timer(self):
        """Start or stop the timer."""
        if not self.is_running:
            self.is_running = True
            self.start_time = time.time() - self.paused_time
            self.start_stop_btn.configure(text="Stop", fg_color="#ff6b6b", hover_color="#cc5555")
            self.timer_thread = threading.Thread(target=self.run_timer, daemon=True)
            self.timer_thread.start()
        else:
            self.is_running = False
            self.paused_time = time.time() - self.start_time
            self.start_stop_btn.configure(text="Start", fg_color="#00d4ff", hover_color="#00a8cc")
    
    def run_timer(self):
        """Run the timer in a separate thread."""
        while self.is_running:
            self.update_display()
            time.sleep(0.001)  # Update every 1ms for smooth display
    
    def update_display(self):
        """Update the timer display."""
        if self.is_running:
            self.elapsed_time = time.time() - self.start_time
            
            hours = int(self.elapsed_time // 3600)
            minutes = int((self.elapsed_time % 3600) // 60)
            seconds = int(self.elapsed_time % 60)
            milliseconds = int((self.elapsed_time * 100) % 100)
            
            time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:02d}"
            self.time_display.configure(text=time_str)
    
    def reset_timer(self):
        """Reset the timer to 00:00:00."""
        self.is_running = False
        self.elapsed_time = 0
        self.paused_time = 0
        self.start_time = None
        self.time_display.configure(text="00:00:00.00")
        self.start_stop_btn.configure(text="Start", fg_color="#00d4ff", hover_color="#00a8cc")


def main():
    app = TimerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
