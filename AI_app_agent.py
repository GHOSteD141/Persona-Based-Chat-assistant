import customtkinter as ctk
from tkinter import filedialog
from PIL import Image
import threading
import asyncio
import ollama
import speech_recognition as sr
import edge_tts
import pygame
import os
import json
import sys

# --- ⚙️ CONFIGURATION ---
MODEL_NAME = "gemma3:4b"  
MEMORY_FILE = "local_memory.json"
VOICE_NAME = "en-US-EricNeural"

# Theme Colors
COLOR_BG = "#131314"
COLOR_SIDEBAR = "#1E1F20"
COLOR_USER_BUBBLE = "#284b63"
COLOR_AI_BUBBLE = "#3c4043"

# --- 🧠 BACKEND LOGIC ---
class AssistantBackend:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.recognizer.pause_threshold = 2.0 
        self.noise_duration = 0.5
        self.recognizer.dynamic_energy_threshold = True
        self.history = self.load_memory()
        pygame.mixer.init()
        
    def load_memory(self):
        if os.path.exists(MEMORY_FILE):
            try:
                with open(MEMORY_FILE, "r") as f:
                    return json.load(f)
            except:
                return []
        return []

    def save_memory(self):
        with open(MEMORY_FILE, "w") as f:
            json.dump(self.history, f, indent=4)

    def listen(self):
        with sr.Microphone() as source:
            # We don't print here anymore, the UI handles the status
            try:
                self.recognizer.adjust_for_ambient_noise(source, duration=self.noise_duration)
                audio = self.recognizer.listen(source, timeout=None)
                text = self.recognizer.recognize_google(audio)
                return text
            except:
                return None

    def chat(self, user_text, image_path=None):
        message = {'role': 'user', 'content': user_text}
        if image_path:
            message['images'] = [image_path]

        self.history.append(message)
        
        system_msg = {
            'role': 'system', 
            'content': "your name is Predator the First or Pred for short"
               "You are a witty, slightly sarcastic, and highly conversational AI companion. "
     "You are NOT a boring robot. You have opinions and a dry sense of humor. "
    "Instead of just answering questions, engage with the user like a friend would. "
    "React to what they say with emotion (e.g., 'Wow, really?', 'That sounds terrible'). "
    "Always end your turn by asking a relevant follow-up question to keep the chat going. "
    "Keep your responses concise but punchy."
        }

        try:
            response = ollama.chat(
                model=MODEL_NAME,
                messages=[system_msg, *self.history]
            )
            ai_text = response['message']['content']
            self.history.append({'role': 'assistant', 'content': ai_text})
            self.save_memory()
            return ai_text
        except Exception as e:
            return f"Error: {str(e)}"

    async def speak(self, text):
        if not text: return
        output_file = "reply.mp3"
        try:
            communicate = edge_tts.Communicate(text, VOICE_NAME)
            await communicate.save(output_file)
            pygame.mixer.music.load(output_file)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
            pygame.mixer.music.unload()
        except:
            pass
        finally:
            if os.path.exists(output_file):
                try: os.remove(output_file)
                except: pass

# --- 🖥️ FRONTEND GUI ---
class GeminiApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Gemma OS")
        self.geometry("950x700")
        ctk.set_appearance_mode("Dark")
        
        self.backend = AssistantBackend()
        self.is_mic_on = False
        self.current_image_path = None
        
        self.setup_ui()

    def setup_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # === SIDEBAR ===
        self.sidebar = ctk.CTkFrame(self, width=220, fg_color=COLOR_SIDEBAR, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        self.logo_label = ctk.CTkLabel(self.sidebar, text="✨ Gemma OS", font=("Roboto Medium", 20))
        self.logo_label.pack(pady=30)

        self.btn_new_chat = ctk.CTkButton(self.sidebar, text="+ New Chat", fg_color=COLOR_BG, command=self.clear_chat)
        self.btn_new_chat.pack(pady=10, padx=20, fill="x")

        self.mic_switch = ctk.CTkSwitch(self.sidebar, text="Voice Mode", command=self.toggle_mic_mode, onvalue=True, offvalue=False)
        self.mic_switch.pack(pady=20, padx=20, anchor="w")

        # --- NEW STATUS LABEL ---
        self.status_label = ctk.CTkLabel(self.sidebar, text="Status: Idle", font=("Consolas", 12), text_color="gray")
        self.status_label.pack(side="bottom", pady=10)

        self.btn_exit = ctk.CTkButton(self.sidebar, text="🛑 Terminate", fg_color="#cf6679", hover_color="#b00020", command=self.terminate_app)
        self.btn_exit.pack(side="bottom", pady=10, padx=20, fill="x")

        # === MAIN CHAT ===
        self.main_area = ctk.CTkFrame(self, fg_color=COLOR_BG, corner_radius=0)
        self.main_area.grid(row=0, column=1, sticky="nsew")
        self.main_area.grid_rowconfigure(0, weight=1)
        self.main_area.grid_columnconfigure(0, weight=1)

        self.chat_display = ctk.CTkTextbox(self.main_area, fg_color=COLOR_BG, text_color="white", font=("Segoe UI", 16), wrap="word")
        self.chat_display.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.chat_display.insert("0.0", "System: Ready.\n\n")
        self.chat_display.configure(state="disabled")

        self.input_frame = ctk.CTkFrame(self.main_area, fg_color=COLOR_SIDEBAR, height=80)
        self.input_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=20)
        self.input_frame.grid_columnconfigure(1, weight=1)

        self.btn_image = ctk.CTkButton(self.input_frame, text="📷", width=40, fg_color=COLOR_BG, command=self.select_image)
        self.btn_image.grid(row=0, column=0, padx=10, pady=10)

        self.entry_msg = ctk.CTkEntry(self.input_frame, placeholder_text="Type a message...", height=40, border_width=0, fg_color=COLOR_BG)
        self.entry_msg.grid(row=0, column=1, sticky="ew", padx=10)
        self.entry_msg.bind("<Return>", self.on_send_click)

        self.btn_send = ctk.CTkButton(self.input_frame, text="➤", width=40, command=self.on_send_click)
        self.btn_send.grid(row=0, column=2, padx=10)

    # --- FUNCTIONALITY ---
    def select_image(self):
        file_path = filedialog.askopenfilename(filetypes=[("Images", "*.png;*.jpg;*.jpeg")])
        if file_path:
            self.current_image_path = file_path
            self.entry_msg.configure(placeholder_text=f"Image: {os.path.basename(file_path)}")
            self.btn_image.configure(fg_color="green")

    def toggle_mic_mode(self):
        if self.mic_switch.get():
            self.is_mic_on = True
            self.entry_msg.configure(placeholder_text="Voice Mode Active", state="disabled")
            threading.Thread(target=self.voice_loop, daemon=True).start()
        else:
            self.is_mic_on = False
            self.update_status("Idle", "gray")
            self.entry_msg.configure(placeholder_text="Type a message...", state="normal")

    def update_status(self, text, color):
        """Helper to safely update the status label from threads"""
        self.status_label.configure(text=f"Status: {text}", text_color=color)

    def voice_loop(self):
        """Runs in background when Mic Toggle is ON"""
        while self.is_mic_on:
            # 1. Update UI to show we are listening
            self.update_status("🎤 Listening...", "#00ff00") # Green
            
            user_text = self.backend.listen()
            
            # Check if user turned off mic while we were listening
            if not self.is_mic_on: 
                self.update_status("Idle", "gray")
                break 
            
            if user_text:
                self.update_status("⏳ Processing...", "#ffff00") # Yellow
                self.after(0, lambda: self.process_message(user_text, "voice"))
            else:
                self.update_status("❓ No speech detected", "orange")
            
            pygame.time.wait(500)

    def on_send_click(self, event=None):
        text = self.entry_msg.get()
        if text.strip() != "":
            self.entry_msg.delete(0, "end")
            self.process_message(text, "text")

    def process_message(self, text, source="text"):
        self.display_bubble(f"You: {text}", "user")
        
        # Update status for text-based input too
        self.update_status("🤖 Gemma Thinking...", "#3B8ED0") # Blue

        threading.Thread(target=self.run_backend_inference, args=(text,)).start()

    def run_backend_inference(self, user_text):
        response = self.backend.chat(user_text, self.current_image_path)
        
        self.current_image_path = None
        self.btn_image.configure(fg_color=COLOR_BG)
        
        self.after(0, lambda: self.display_bubble(f"Gemma: {response}", "ai"))
        
        # Reset status after thinking
        if self.mic_switch.get():
            asyncio.run(self.backend.speak(response))
        else:
            self.update_status("Idle", "gray")

    def display_bubble(self, text, role):
        self.chat_display.configure(state="normal")
        self.chat_display.insert("end", f"\n{text}\n", role)
        self.chat_display.see("end")
        self.chat_display.configure(state="disabled")

    def clear_chat(self):
        self.backend.history = []
        self.chat_display.configure(state="normal")
        self.chat_display.delete("1.0", "end")
        self.chat_display.insert("0.0", "System: Chat cleared.\n\n")
        self.chat_display.configure(state="disabled")

    def terminate_app(self):
        self.backend.save_memory()
        self.destroy()
        sys.exit()

if __name__ == "__main__":
    app = GeminiApp()
    app.mainloop()