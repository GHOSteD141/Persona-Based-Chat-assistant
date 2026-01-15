# 🤖 Predator OS: Ultimate AI Desktop Assistant

**Predator OS** is a fully customizable, voice-enabled AI desktop assistant that runs locally on your machine. It bridges the gap between local LLMs (via Ollama) and real-time internet data, packaged in a sleek "Dark Mode" GUI.

It features **Smart Search**, **Persistent Memory**, and **Hot-Swappable Personas**, allowing for a completely personalized AI experience without relying on paid cloud subscriptions.

---

## 🚀 Key Features

* **🧠 Local Intelligence:** Powered by **Ollama**. Runs models like `gemma3`, `llama3`, or `mistral` entirely on your CPU/GPU.
* **🌐 Smart Web Search:** Connects to DuckDuckGo to fetch real-time data.
    * *Query Rewriting:* The AI intelligently rewrites your conversational questions into effective search keywords.
    * *Fact-Check Mode:* Automatically switches to a strict "Reporter Persona" during searches to minimize hallucinations and cite sources.
* **🗣️ Voice Interaction:**
    * **Listen:** Integrated Google Speech-to-Text for voice commands.
    * **Speak:** High-quality, natural-sounding TTS via Microsoft Edge (offline-ready caching).
* **💾 Persistent Memory:**
    * Auto-saves all conversations to local JSON files.
    * Resumes your last active session on startup.
    * **Right-Click Management:** Delete old chats directly from the sidebar.
* **⚙️ Dynamic Control Center:**
    * **Hot-Swap Models:** Switch between AI models (e.g., from Gemma to Llama) instantly via the UI.
    * **Custom Personas:** Change the AI's personality (System Prompt) and Voice ID in the Settings menu without restarting code.
* **🖼️ Multimodal Vision:** Upload images for the AI to analyze (requires a vision-capable model like `llava` or `gemma`).

---

## 🛠️ Prerequisites

Before running Predator OS, ensure you have the following installed:

1.  **Python 3.10+**
2.  **[Ollama](https://ollama.com/)** (The backend that runs the AI models).
    * After installing, pull a model: `ollama pull gemma:2b` (or your preferred model).
    * Ensure Ollama is running (`ollama serve`).

---

## 📦 Installation

1.  **Clone the Repository**
    ```bash
    git clone [https://github.com/YourUsername/Predator-OS.git](https://github.com/YourUsername/Predator-OS.git)
    cd Predator-OS
    ```

2.  **Install Python Dependencies**
    ```bash
    pip install customtkinter ollama SpeechRecognition edge-tts pygame duckduckgo-search packaging Pillow
    ```
    *(Note: If you encounter search library errors, try `pip install ddgs`)*

3.  **Run the App**
    ```bash
    python AI_app_agent.py
    ```

---

## 🏗️ Building the Executable (.exe)

To compile Predator OS into a standalone `.exe` file that you can share or run without a terminal:

1.  Install PyInstaller:
    ```bash
    pip install pyinstaller
    ```

2.  Run the Build Command:
    ```bash
    pyinstaller --noconsole --onefile --name "PredatorOS_Ultimate" --collect-all="customtkinter" --collect-all="duckduckgo_search" --hidden-import="ddgs" --hidden-import="ollama" --hidden-import="edge_tts" --hidden-import="speech_recognition" AI_app_agent.py
    ```

3.  Find your app in the **`dist/`** folder.

---

## 🎮 Usage Guide

* **Chatting:** Type in the box or toggle **"Voice Mode"** to speak.
* **Web Search:** Toggle the **"Web Search 🌐"** switch to enable internet access. The AI will cite sources for its answers.
* **Changing Models:** Use the dropdown menu next to the "Send" button to switch AI brains on the fly.
* **Settings:** Click **⚙️ Settings** in the sidebar to change the System Prompt (give it a new personality!) or the Voice ID.
* **Managing Chats:** Right-click any chat in the left sidebar to delete it.

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:
1.  Fork the project.
2.  Create your feature branch (`git checkout -b feature/AmazingFeature`).
3.  Commit your changes (`git commit -m 'Add some AmazingFeature'`).
4.  Push to the branch (`git push origin feature/AmazingFeature`).
5.  Open a Pull Request.

---

## 📜 License

Distributed under the MIT License. See `LICENSE` for more information.

---

## 🙏 Acknowledgements

* [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) for the beautiful UI components.
* [Ollama](https://ollama.com/) for making local AI accessible.
* [duckduckgo_search](https://pypi.org/project/duckduckgo-search/) for the search API.
