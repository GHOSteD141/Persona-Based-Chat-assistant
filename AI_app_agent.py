print("[DEBUG] Importing libraries...")
import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
import asyncio
import ollama
import speech_recognition as sr
import edge_tts
import pygame
import os
import json
import sys
import time
import glob
import datetime
import tempfile
import warnings

# --- 🛠️ LIBRARY FIXES ---
# Suppress annoying warnings
warnings.filterwarnings("ignore", category=RuntimeWarning)

# Try importing the new search library name first, then fallback
try:
    from ddgs import DDGS
    print("[DEBUG] Loaded 'ddgs' library.")
except ImportError:
    try:
        from duckduckgo_search import DDGS
        print("[DEBUG] Loaded 'duckduckgo_search' library.")
    except ImportError:
        print("[CRITICAL] Search library missing. Run: pip install ddgs")
        sys.exit()

print("[DEBUG] Libraries imported successfully.")

# --- ⚙️ DEFAULT CONFIGURATION ---
DEFAULT_CONFIG = {
    "model": "gemma3:4b",
    "voice": "en-US-EricNeural",
    "system_prompt": (
        "You are Predator the Fifth, a highly advanced AI assistant. "
        "Your primary directive is to understand the user's true intent and assist them with ANY task provided. "
        "You possess a dry sense of humor and occasionally tell terrible 'dad jokes'. "
        "CRITICAL PROTOCOL: You must ALWAYS listen to the user and respond. "
        "Never go silent."
    )
}
CONFIG_FILE = "app_config.json"

# Theme Colors
COLOR_BG = "#131314"
COLOR_SIDEBAR = "#1E1F20"
COLOR_USER_BUBBLE = "#284b63" 
COLOR_AI_BUBBLE = "#3c4043"
COLOR_ACCENT = "#8AB4F8"

# --- 🧠 BACKEND LOGIC ---
class AssistantBackend:
    def __init__(self):
        print("[DEBUG] Initializing Backend...")
        self.config = self.load_config()
        self.recognizer = sr.Recognizer()
        self.recognizer.pause_threshold = 2.0 
        self.noise_duration = 0.5
        self.recognizer.dynamic_energy_threshold = True
        
        print("[DEBUG] Initializing Pygame Audio...")
        try:
            pygame.mixer.init()
        except Exception as e:
            print(f"[ERROR] Failed to init Audio: {e}")

        # Session Management
        self.sessions_dir = "saved_chats"
        if not os.path.exists(self.sessions_dir):
            os.makedirs(self.sessions_dir)
            
        self.current_session_file = None
        self.history = []
        self.start_new_session()
        print("[DEBUG] Backend Ready.")

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    return json.load(f)
            except: pass
        return DEFAULT_CONFIG.copy()

    def save_config(self):
        with open(CONFIG_FILE, "w") as f:
            json.dump(self.config, f, indent=4)

    def get_available_models(self):
        """Fetches list of models from Ollama (Robust Fix)"""
        print("[DEBUG] Fetching Ollama models...")
        try:
            models_info = ollama.list()
            model_list = []
            
            # Helper to find the name key safely
            if 'models' in models_info:
                for m in models_info['models']:
                    # Try 'model', then 'name', then default to unknown
                    name = m.get('model') or m.get('name')
                    if name:
                        model_list.append(name)
            
            if not model_list:
                print("[WARN] No models found in list, using fallback.")
                return ["gemma3:4b"]
                
            return model_list
            
        except Exception as e:
            print(f"[ERROR] Ollama connection failed: {e}")
            return ["gemma3:4b"] 

    def start_new_session(self):
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_session_file = os.path.join(self.sessions_dir, f"chat_{timestamp}.json")
        self.history = []
        self.save_history()

    def load_session(self, filepath):
        if os.path.exists(filepath):
            try:
                with open(filepath, "r") as f:
                    data = json.load(f)
                    self.history = data.get("messages", [])
                self.current_session_file = filepath
                return True
            except: return False
        return False

    def save_history(self):
        if not self.current_session_file: return
        title = "New Chat"
        for msg in self.history:
            if msg['role'] == 'user':
                words = msg['content'].split()[:5]
                title = " ".join(words) + "..."
                break
        
        data = {
            "title": title,
            "timestamp": str(datetime.datetime.now()),
            "messages": self.history
        }
        with open(self.current_session_file, "w") as f:
            json.dump(data, f, indent=4)

    def get_saved_sessions(self):
        files = glob.glob(os.path.join(self.sessions_dir, "*.json"))
        files.sort(key=os.path.getmtime, reverse=True)
        session_list = []
        for f in files:
            try:
                with open(f, "r") as json_file:
                    data = json.load(json_file)
                    session_list.append({"path": f, "title": data.get("title", "Untitled")})
            except: pass
        return session_list

    def web_search(self, query):
        print(f"🔎 Searching web for: {query}")
        try:
            # Using the new DDGS syntax
            results = DDGS().text(query, max_results=3)
            if results:
                summary = "\n".join([f"- {r['title']}: {r['body']}" for r in results])
                return f"Search Results for '{query}':\n{summary}\n"
        except Exception as e:
            print(f"Search Error: {e}")
        return "(Internet search failed.)"

    def listen(self):
        with sr.Microphone() as source:
            try:
                self.recognizer.adjust_for_ambient_noise(source, duration=self.noise_duration)
                audio = self.recognizer.listen(source, timeout=None)
                text = self.recognizer.recognize_google(audio)
                return text
            except: return None

    def chat(self, user_text, image_path=None, use_web=False):
        user_msg = {'role': 'user', 'content': user_text}
        if image_path: user_msg['images'] = [image_path]

        context_messages = list(self.history)
        system_context = self.config["system_prompt"]
        
        # --- 🧠 IMPROVED WEB LOGIC ---
        if use_web:
            search_data = self.web_search(user_text)
            
            # Inject Time & Strict Orders
            current_date = datetime.datetime.now().strftime("%B %Y")
            
            system_context += f"\n\n[CONTEXT: Today is {current_date}]"
            system_context += f"\n[OFFICIAL SEARCH RESULTS]:\n{search_data}\n"
            system_context += "MANDATORY INSTRUCTION: You represent TRUTH. If the Search Results say something different from your internal memory, YOU MUST USE THE SEARCH RESULTS. Do not hallucinate."

        context_messages.append(user_msg)
        system_msg_obj = {'role': 'system', 'content': system_context}

        try:
            response = ollama.chat(
                model=self.config["model"],
                messages=[system_msg_obj, *context_messages]
            )
            ai_text = response['message']['content']
            
            self.history.append(user_msg)
            self.history.append({'role': 'assistant', 'content': ai_text})
            self.save_history()
            return ai_text
        except Exception as e:
            return f"Error: {str(e)}"

    async def speak(self, text):
        if not text: return
        temp_dir = tempfile.gettempdir()
        output_file = os.path.join(temp_dir, "gemma_reply_temp.mp3")
        try:
            communicate = edge_tts.Communicate(text, self.config["voice"])
            await communicate.save(output_file)
            pygame.mixer.music.load(output_file)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
            pygame.mixer.music.unload()
        except: pass
        finally:
            if os.path.exists(output_file):
                try: os.remove(output_file)
                except: pass

# --- 🖥️ FRONTEND GUI ---
class GeminiApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        print("[DEBUG] Starting GUI...")
        self.title("Predator OS 7.0 (Fixed)")
        self.geometry("1100x700")
        try:
            ctk.set_appearance_mode("Dark")
        except:
            print("[WARN] Failed to set dark mode.")
        
        self.backend = AssistantBackend()
        self.is_mic_on = False
        self.current_image_path = None
        
        self.setup_ui()
        print("[DEBUG] GUI Setup Complete. Launching Window...")

    def setup_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # === LEFT SIDEBAR ===
        self.sidebar = ctk.CTkFrame(self, width=250, fg_color=COLOR_SIDEBAR, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(2, weight=1) 

        self.logo_label = ctk.CTkLabel(self.sidebar, text="🤖 Predator OS", font=("Roboto Medium", 20))
        self.logo_label.grid(row=0, column=0, pady=20, padx=20)

        self.btn_new_chat = ctk.CTkButton(self.sidebar, text="+ New Chat", fg_color=COLOR_ACCENT, text_color="black", command=self.start_new_chat)
        self.btn_new_chat.grid(row=1, column=0, pady=10, padx=20, sticky="ew")

        # History
        self.history_label = ctk.CTkLabel(self.sidebar, text="Previous Chats:", text_color="gray", anchor="w")
        self.history_label.grid(row=2, column=0, padx=20, pady=(20,5), sticky="w")
        
        self.history_frame = ctk.CTkScrollableFrame(self.sidebar, fg_color="transparent")
        self.history_frame.grid(row=3, column=0, padx=10, pady=5, sticky="nsew")
        self.refresh_history_ui()

        # Settings
        self.settings_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.settings_frame.grid(row=4, column=0, padx=20, pady=20, sticky="ew")

        self.btn_settings = ctk.CTkButton(self.settings_frame, text="⚙️ Settings", fg_color="gray", command=self.open_settings_window)
        self.btn_settings.pack(pady=5, fill="x")

        self.mic_switch = ctk.CTkSwitch(self.settings_frame, text="Voice Mode", command=self.toggle_mic_mode, onvalue=True, offvalue=False)
        self.mic_switch.pack(pady=10, anchor="w")

        self.web_switch = ctk.CTkSwitch(self.settings_frame, text="Web Search 🌐", onvalue=True, offvalue=False)
        self.web_switch.pack(pady=10, anchor="w")

        self.status_label = ctk.CTkLabel(self.settings_frame, text="Status: Idle", text_color="gray", font=("Consolas", 11))
        self.status_label.pack(pady=5)

        self.btn_exit = ctk.CTkButton(self.settings_frame, text="🛑 Terminate", fg_color="#cf6679", hover_color="#b00020", command=self.terminate_app)
        self.btn_exit.pack(pady=10, fill="x")

        # === MAIN CHAT AREA ===
        self.main_area = ctk.CTkFrame(self, fg_color=COLOR_BG, corner_radius=0)
        self.main_area.grid(row=0, column=1, sticky="nsew")
        self.main_area.grid_rowconfigure(0, weight=1)
        self.main_area.grid_columnconfigure(0, weight=1)

        self.chat_display = ctk.CTkTextbox(self.main_area, fg_color=COLOR_BG, text_color="white", font=("Segoe UI", 16), wrap="word")
        self.chat_display.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.chat_display.configure(state="disabled")

        # Input Area
        self.input_frame = ctk.CTkFrame(self.main_area, fg_color=COLOR_SIDEBAR, height=80)
        self.input_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=20)
        self.input_frame.grid_columnconfigure(1, weight=1)

        self.btn_image = ctk.CTkButton(self.input_frame, text="📷", width=40, fg_color=COLOR_BG, command=self.select_image)
        self.btn_image.grid(row=0, column=0, padx=10, pady=10)

        self.entry_msg = ctk.CTkEntry(self.input_frame, placeholder_text="Type a message...", height=40, border_width=0, fg_color=COLOR_BG)
        self.entry_msg.grid(row=0, column=1, sticky="ew", padx=10)
        self.entry_msg.bind("<Return>", self.on_send_click)

        # === MODEL SELECTOR (SAFE) ===
        self.available_models = self.backend.get_available_models()
        self.model_var = ctk.StringVar(value=self.backend.config["model"])
        
        self.model_dropdown = ctk.CTkOptionMenu(
            self.input_frame, 
            values=self.available_models,
            command=self.change_model,
            variable=self.model_var,
            width=140,
            fg_color=COLOR_ACCENT,
            text_color="black"
        )
        self.model_dropdown.grid(row=0, column=2, padx=(10, 5))

        self.btn_refresh = ctk.CTkButton(self.input_frame, text="🔄", width=30, fg_color="gray", command=self.refresh_model_list)
        self.btn_refresh.grid(row=0, column=3, padx=(0, 10))

        self.btn_send = ctk.CTkButton(self.input_frame, text="➤", width=40, command=self.on_send_click)
        self.btn_send.grid(row=0, column=4, padx=10)
        
        self.load_chat_ui()

    # --- REFRESH MODELS ---
    def refresh_model_list(self):
        self.update_status("Fetching Models...", "yellow")
        threading.Thread(target=self._fetch_models_thread).start()

    def _fetch_models_thread(self):
        models = self.backend.get_available_models()
        self.after(0, lambda: self._update_dropdown_ui(models))

    def _update_dropdown_ui(self, models):
        self.model_dropdown.configure(values=models)
        self.update_status(f"Found {len(models)} models", "green")
        messagebox.showinfo("Models Refreshed", f"Found: {', '.join(models)}")

    # --- SETTINGS WINDOW ---
    def open_settings_window(self):
        self.settings_window = ctk.CTkToplevel(self)
        self.settings_window.title("System Settings")
        self.settings_window.geometry("500x400")
        
        ctk.CTkLabel(self.settings_window, text="System Persona (Prompt):", font=("Roboto", 14, "bold")).pack(pady=10)
        self.txt_system_prompt = ctk.CTkTextbox(self.settings_window, height=150)
        self.txt_system_prompt.pack(padx=20, fill="x")
        self.txt_system_prompt.insert("0.0", self.backend.config["system_prompt"])
        
        ctk.CTkLabel(self.settings_window, text="Voice Name (EdgeTTS):").pack(pady=10)
        self.entry_voice = ctk.CTkEntry(self.settings_window)
        self.entry_voice.pack(padx=20, fill="x")
        self.entry_voice.insert("0", self.backend.config["voice"])
        
        ctk.CTkButton(self.settings_window, text="Save & Apply", command=self.save_settings).pack(pady=20)
        self.settings_window.grab_set()

    def save_settings(self):
        new_prompt = self.txt_system_prompt.get("0.0", "end").strip()
        new_voice = self.entry_voice.get().strip()
        self.backend.config["system_prompt"] = new_prompt
        self.backend.config["voice"] = new_voice
        self.backend.save_config()
        messagebox.showinfo("Settings", "Configuration saved!")
        self.settings_window.destroy()

    def change_model(self, choice):
        self.backend.config["model"] = choice
        self.backend.save_config()
        self.update_status(f"Model: {choice}", "#8AB4F8")

    # --- UI & LOGIC ---
    def refresh_history_ui(self):
        for widget in self.history_frame.winfo_children():
            widget.destroy()
        sessions = self.backend.get_saved_sessions()
        for session in sessions:
            title = session["title"][:25] + "..." if len(session["title"]) > 25 else session["title"]
            btn = ctk.CTkButton(self.history_frame, text=title, fg_color="transparent", border_width=1, border_color="gray", anchor="w", command=lambda p=session["path"]: self.load_old_chat(p))
            btn.pack(fill="x", pady=2)

    def start_new_chat(self):
        self.backend.start_new_session()
        self.chat_display.configure(state="normal")
        self.chat_display.delete("1.0", "end")
        self.chat_display.insert("0.0", "System: New Session.\n\n")
        self.chat_display.configure(state="disabled")
        self.refresh_history_ui()

    def load_old_chat(self, filepath):
        if self.backend.load_session(filepath):
            self.load_chat_ui()
        
    def load_chat_ui(self):
        self.chat_display.configure(state="normal")
        self.chat_display.delete("1.0", "end")
        for msg in self.backend.history:
            role = "You" if msg['role'] == 'user' else "AI"
            self.chat_display.insert("end", f"\n{role}: {msg['content']}\n")
        self.chat_display.see("end")
        self.chat_display.configure(state="disabled")

    def select_image(self):
        file_path = filedialog.askopenfilename(filetypes=[("Images", "*.png;*.jpg;*.jpeg")])
        if file_path:
            self.current_image_path = file_path
            self.entry_msg.configure(placeholder_text=f"Image: {os.path.basename(file_path)}")
            self.btn_image.configure(fg_color="green")

    def toggle_mic_mode(self):
        if self.mic_switch.get():
            self.is_mic_on = True
            self.entry_msg.configure(placeholder_text="Listening...", state="disabled")
            threading.Thread(target=self.voice_loop, daemon=True).start()
        else:
            self.is_mic_on = False
            self.update_status("Idle", "gray")
            self.entry_msg.configure(placeholder_text="Type a message...", state="normal")

    def update_status(self, text, color):
        try: self.status_label.configure(text=f"Status: {text}", text_color=color)
        except: pass

    def voice_loop(self):
        while self.is_mic_on:
            self.update_status("🎤 Listening...", "#00ff00")
            user_text = self.backend.listen()
            if not self.is_mic_on: break 
            if user_text:
                self.update_status("⏳ Processing...", "#ffff00")
                self.after(0, lambda: self.process_message(user_text))
            pygame.time.wait(500)

    def on_send_click(self, event=None):
        text = self.entry_msg.get()
        if text.strip() != "":
            self.entry_msg.delete(0, "end")
            self.process_message(text)

    def process_message(self, text):
        self.chat_display.configure(state="normal")
        self.chat_display.insert("end", f"\nYou: {text}\n")
        self.chat_display.see("end")
        self.chat_display.configure(state="disabled")
        threading.Thread(target=self.run_backend_inference, args=(text, self.web_switch.get())).start()

    def run_backend_inference(self, user_text, use_web):
        self.update_status("🧠 Thinking...", "#3B8ED0")
        response = self.backend.chat(user_text, self.current_image_path, use_web)
        self.current_image_path = None
        self.btn_image.configure(fg_color=COLOR_BG)
        self.after(0, lambda: self.display_ai_reply(response))
        self.after(0, self.refresh_history_ui)
        if self.mic_switch.get(): asyncio.run(self.backend.speak(response))
        else: self.update_status("Idle", "gray")

    def display_ai_reply(self, text):
        self.chat_display.configure(state="normal")
        self.chat_display.insert("end", f"\nAI: {text}\n")
        self.chat_display.see("end")
        self.chat_display.configure(state="disabled")

    def terminate_app(self):
        self.destroy()
        sys.exit()

if __name__ == "__main__":
    print("[DEBUG] Main entry point hit.")
    try:
        app = GeminiApp()
        print("[DEBUG] Mainloop starting...")
        app.mainloop()
    except Exception as e:
        print(f"[CRITICAL ERROR] App crashed: {e}")
        input("Press Enter to close...")