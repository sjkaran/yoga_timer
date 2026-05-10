import customtkinter as ctk
from tkinter import font
import threading
import time
from voice_engine import voice_engine as ve
from PIL import Image

class TimerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        #imported functions
        self.vr = ve()
        
        # Configure dark theme and setting Icon
        logo_image = Image.open("clock_icon.ico")
        my_icon = ctk.CTkImage(light_image=logo_image,dark_image=logo_image,size=(20,30))
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        #defining fonts
        my_clock_font = ctk.CTkFont(family="Times", size=50, weight="bold")
        
        # Window setup
        self.title("Timer")
        self.geometry("350x300")
        self.resizable(False, False)
        self.iconbitmap("clock_icon.ico")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # Timer variables
        self.elapsed_time = 0
        self.is_running = False
        self.timer_thread = None
        self.start_time = None
        self.paused_time = 0
        self.voice_enabled = False
        
        # Main container
        main_frame = ctk.CTkFrame(self, fg_color="#000000")
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Title
        title_label = ctk.CTkLabel(
            main_frame,
            text="Timer",
            font=ctk.CTkFont(family="Times new roman", size=18, weight="bold"),
            text_color="#ffffff"
        )
        title_label.pack(pady=(10, 10))
        
        # Display frame for timer
        display_frame = ctk.CTkFrame(main_frame, fg_color="#0C2819", corner_radius=0)
        display_frame.pack(fill="both", expand=True, pady=8)
        
        # Timer display label with large font
        self.time_display = ctk.CTkLabel(
            display_frame,
            text="00:00:00.00",
            font=my_clock_font,
            text_color="#ff9706"
        )
        self.time_display.pack(expand=True, fill="both", padx=10, pady=15)
        
        # Buttons frame
        button_frame = ctk.CTkFrame(main_frame, fg_color="#1a1a1a")
        button_frame.pack(fill="both", expand=False, pady=10)
        
        # Start/Stop button
        self.start_stop_btn = ctk.CTkButton(
            button_frame,
            text="Start",
            font=ctk.CTkFont(size=12, weight="bold"),
            height=35,
            fg_color="#ade372",
            hover_color="#18cc00",
            text_color="#000000",
            command= self.toggle_timer
        )
        self.start_stop_btn.pack(side="left", expand=True, padx=(5, 5))
        
        # Voice button
        self.voice_btn = ctk.CTkButton(
            button_frame,
            text="🎤",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=35,
            width=40,
            fg_color="#63636C",
            hover_color="#2cbf44",
            text_color="#1b0f0f",
            command=self.voice_toggle
        )
        self.voice_btn.pack(side="right", expand=False, padx=(5, 5))
        
        # Reset button
        self.reset_btn = ctk.CTkButton(
            button_frame,
            text="Reset",
            font=ctk.CTkFont(size=12, weight="bold"),
            height=35,
            fg_color="#ff6b6b",
            hover_color="#cc5555",
            text_color="#ffffff",
            command=self.reset_timer
        )
        self.reset_btn.pack(side="right", expand=True, padx=(5, 0))

    

    def voice_toggle(self):
        self.voice_enabled = not self.voice_enabled
        
        if self.voice_enabled:
            # 1. UI Update
            self.voice_btn.configure(fg_color="#ffd900")
            
            # 2. Setup the "Stop Signal"
            self.stop_voice_event = threading.Event()
            
            # 3. Create and start the thread
            self.voice_thread = threading.Thread(
                target=self.voice_listener_loop, 
                args=(self.stop_voice_event,),
                daemon=True
            )
            self.voice_thread.start()
        else:
            # 1. UI Update
            self.voice_btn.configure(fg_color="#73737C")
            
            # 2. Tell the thread to die
            if hasattr(self, 'stop_voice_event'):
                self.stop_voice_event.set()
            
            # 3. Optional: Clear the thread reference
            self.voice_thread = None

    def voice_listener_loop(self, stop_event):
        """This runs in the background"""
        while not stop_event.is_set():
            # Check for voice commands
            # Note: Your recognizer should ideally have a timeout so it doesn't 
            # block this loop forever, allowing it to check stop_event.is_set()

            if self.is_running:
                result = self.vr.recognizer(word="stop")
            else:
                result = self.vr.recognizer(word="start") 
            
            # Immediate check after a potentially long-running recognition task
            if stop_event.is_set():
                break

            if result:
                self.after(0, self.toggle_timer)
                
            # Example of specific word checks
            # We check is_set() frequently to ensure the mic stops immediately
            if not stop_event.is_set() and self.is_running:
                self.vr.recognizer(word="stop") 
                self.after(0, self.toggle_timer)
                
            if not stop_event.is_set() and not self.is_running :
                self.vr.recognizer(word="reset")
                self.after(0, self.reset_timer)

        print("Voice listener thread safely stopped.")
                
                

            
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
