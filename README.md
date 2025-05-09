# Secure PyQt5 Media Player

A cross-platform desktop application for secure video playback, built with Python and PyQt5. It supports loading and playing common media formats as well as on-the-fly decryption of AES-encrypted files.

## 🔒 Features

* **Play, Pause & Stop** media files
* **Seek Bar** for random access within video/audio
* **Volume Control & Mute** toggle
* **Fullscreen Mode**
* **Open File Dialog**: supports `.mp4`, `.avi`, `.mkv`, `.mov`, `.mp3`, `.wav` and encrypted `.enc` files
* **AES-CTR Decryption** of `.enc` files using a password (PBKDF2-HMAC-SHA256 key derivation)
* **Progress Feedback** during decryption
* **Temporary File Cleanup** on exit

## 📦 Prerequisites

* Python 3.8+
* PyQt5
* cryptography

## 🚀 Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/your-username/secure-pyqt5-media-player.git
   cd secure-pyqt5-media-player
   ```

2. **Create and activate a virtual environment (optional but recommended)**

   ```bash
   python -m venv venv
   source venv/bin/activate    # Linux/macOS
   venv\Scripts\activate     # Windows
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

## ⚙️ Usage

Run the application:

```bash
python main.py
```

* Click **Open File** and select a media file.
* For encrypted files (`*.enc`), enter the decryption password when prompted.
* Use the on-screen controls to play, pause, stop, adjust volume, or toggle fullscreen.

## 🛠 How It Works

1. **Encryption Header**: The `.enc` file begins with metadata—original extension, directory flag, salt, and nonce.
2. **Key Derivation**: Uses PBKDF2-HMAC-SHA256 (100,000 iterations) to derive a 256-bit AES key from the user’s password and salt.
3. **AES-CTR Decryption**: Streams decryption in chunks, updating a progress bar.
4. **Playback**: Decrypted output is saved to a temporary directory and loaded into the QMediaPlayer.

## 🧪 Testing

* Test with standard media files to verify playback functionality.
* Encrypt a sample video with the companion encryption script (if provided) and ensure correct decryption and playback.

## 📝 Contributing

Contributions are welcome! Please fork the repo and submit a pull request with:

* Bug fixes
* New features (e.g., playlist support, subtitle rendering)
* Documentation improvements

## 📄 License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

---

*Happy secure viewing!*
