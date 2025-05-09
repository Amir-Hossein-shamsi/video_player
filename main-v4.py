import sys
import os
import tempfile
from PyQt5.QtCore import (
    Qt, QUrl, QTime, QThread, pyqtSignal, pyqtSlot, QObject
)
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QSlider, QLabel, QFileDialog, QStatusBar,
    QSizePolicy, QStyle, QInputDialog, QLineEdit
)
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend


def resource_path(relative_path: str) -> str:
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(__file__)
    return os.path.join(base_path, relative_path)


class DecryptorWorker(QObject):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    progress = pyqtSignal(int)

    def __init__(self, input_path, password, output_dir):
        super().__init__()
        self.input_path = input_path
        self.password = password
        self.output_dir = output_dir
        self._cancel_requested = False

    @pyqtSlot()
    def decrypt(self):
        try:
            HEADER_SIZE = 1 + 256 + 1 + 16 + 16
            PBKDF2_ITERATIONS = 100000
            CIPHER_MODE = modes.CTR

            with open(self.input_path, 'rb') as fin:
                ext_length = fin.read(1)[0]
                ext_bytes = fin.read(256)[:ext_length]
                is_directory = bool(fin.read(1)[0])
                salt = fin.read(16)
                nonce = fin.read(16)

                original_ext = ext_bytes.decode('utf-8')
                if is_directory:
                    self.error.emit("Cannot play encrypted directories.")
                    return

                base_name = os.path.basename(self.input_path)
                if base_name.lower().endswith('.enc'):
                    base_name = base_name[:-4]

                if not base_name.endswith(original_ext):
                    clean_name = f"{base_name}{original_ext}"
                else:
                    clean_name = base_name

                output_file = os.path.join(self.output_dir, clean_name)

                os.makedirs(os.path.dirname(output_file), exist_ok=True)

                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=salt,
                    iterations=PBKDF2_ITERATIONS,
                    backend=default_backend()
                )
                key = kdf.derive(self.password.encode())

                cipher = Cipher(algorithms.AES(key), CIPHER_MODE(nonce), backend=default_backend())
                decryptor = cipher.decryptor()

                total_size = os.path.getsize(self.input_path) - HEADER_SIZE
                processed = 0
                last_progress = -1

                with open(output_file, 'wb') as fout:
                    while not self._cancel_requested:
                        chunk = fin.read(4096)
                        if not chunk:
                            break

                        decrypted = decryptor.update(chunk)
                        fout.write(decrypted)
                        processed += len(chunk)

                        current_progress = int((processed / total_size) * 100)
                        if current_progress != last_progress:
                            self.progress.emit(current_progress)
                            last_progress = current_progress

                    if not self._cancel_requested:
                        fout.write(decryptor.finalize())

                self.finished.emit(output_file)
        except Exception as e:
            self.error.emit(str(e))


class MediaPlayer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Secure Media Player")
        icon_file = resource_path('assets/logo.png')
        self.setWindowIcon(QIcon(icon_file))
        self.setMinimumSize(800, 500)
        self.setStyleSheet("background-color: #1a1a1a; color: white;")

        self.media_player = QMediaPlayer()
        self.video_widget = QVideoWidget()
        self.setup_media_player()

        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_files = []

        self.create_controls()
        self.setup_layout()
        self.setup_connections()

        self.normal_window_geometry = None

    def setup_media_player(self):
        self.media_player.setVideoOutput(self.video_widget)
        self.video_widget.setStyleSheet("background: black;")
        self.video_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video_widget.setAspectRatioMode(Qt.KeepAspectRatio)
        self.media_player.error.connect(self.show_error)
        self.media_player.mediaStatusChanged.connect(self.handle_media_status)

    def handle_media_status(self, status):
        if status == QMediaPlayer.LoadedMedia:
            self.status_bar.showMessage("Media loaded - ready to play")
            self.btn_play.setEnabled(True)
            self.media_player.play()
        elif status == QMediaPlayer.InvalidMedia:
            self.status_bar.showMessage("Error: Unsupported media format")
        elif status == QMediaPlayer.NoMedia:
            self.status_bar.showMessage("No media loaded")

    def create_controls(self):
        style = self.style()

        self.btn_open = self.create_button("Open File", QStyle.SP_DialogOpenButton)
        self.btn_play = self.create_button("Play", QStyle.SP_MediaPlay)
        self.btn_pause = self.create_button("Pause", QStyle.SP_MediaPause)
        self.btn_stop = self.create_button("Stop", QStyle.SP_MediaStop)
        self.btn_fullscreen = self.create_button("Fullscreen", QStyle.SP_TitleBarMaxButton)
        self.btn_mute = self.create_button("Mute", QStyle.SP_MediaVolume, checkable=True)

        self.seek_slider = QSlider(Qt.Horizontal)
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(100)
        self.lbl_current = QLabel("00:00:00")
        self.lbl_duration = QLabel("00:00:00")

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self.style_controls()

    def create_button(self, tooltip, icon_style, checkable=False):
        btn = QPushButton()
        btn.setIcon(self.style().standardIcon(icon_style))
        btn.setToolTip(tooltip)
        btn.setCheckable(checkable)
        return btn

    def style_controls(self):
        slider_style = """
            QSlider::groove:horizontal {
                background: #404040;
                height: 5px;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #fff;
                width: 14px;
                margin: -6px 0;
                border-radius: 7px;
            }
            QSlider::sub-page:horizontal {
                background: #2196F3;
            }
        """

        button_style = """
            QPushButton {
                background: #333;
                border: none;
                padding: 8px;
                border-radius: 4px;
                min-width: 36px;
            }
            QPushButton:hover { background: #444; }
            QPushButton:pressed { background: #2a2a2a; }
            QPushButton:disabled { background: #2a2a2a; color: #666; }
        """

        for btn in [self.btn_open, self.btn_play, self.btn_pause,
                    self.btn_stop, self.btn_fullscreen, self.btn_mute]:
            btn.setStyleSheet(button_style)

        self.seek_slider.setStyleSheet(slider_style)
        self.volume_slider.setStyleSheet(slider_style)
        self.lbl_current.setStyleSheet("font: 10pt;")
        self.lbl_duration.setStyleSheet("font: 10pt;")

    def setup_layout(self):
        time_layout = QHBoxLayout()
        time_layout.addWidget(self.lbl_current)
        time_layout.addStretch()
        time_layout.addWidget(self.lbl_duration)

        control_layout = QHBoxLayout()
        control_layout.addWidget(self.btn_open)
        control_layout.addWidget(self.btn_play)
        control_layout.addWidget(self.btn_pause)
        control_layout.addWidget(self.btn_stop)
        control_layout.addStretch()
        control_layout.addWidget(self.btn_mute)
        control_layout.addWidget(self.volume_slider)
        control_layout.addWidget(self.btn_fullscreen)

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.video_widget, 10)
        main_layout.addLayout(time_layout)
        main_layout.addWidget(self.seek_slider)
        main_layout.addLayout(control_layout)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

    def setup_connections(self):
        self.btn_open.clicked.connect(self.open_file)
        self.btn_play.clicked.connect(self.media_player.play)
        self.btn_pause.clicked.connect(self.media_player.pause)
        self.btn_stop.clicked.connect(self.stop)
        self.btn_fullscreen.clicked.connect(self.toggle_fullscreen)
        self.btn_mute.clicked.connect(self.toggle_mute)

        self.volume_slider.valueChanged.connect(self.media_player.setVolume)
        self.seek_slider.sliderMoved.connect(self.media_player.setPosition)

        self.media_player.positionChanged.connect(self.update_position)
        self.media_player.durationChanged.connect(self.update_duration)
        self.media_player.stateChanged.connect(self.update_buttons)

    def open_file(self):
        file, _ = QFileDialog.getOpenFileName(
            self, "Open Media File", "",
            "Media Files (*.mp4 *.avi *.mkv *.mov *.mp3 *.wav *.enc)")

        if file:
            if file.endswith('.enc'):
                password, ok = QInputDialog.getText(
                    self, 'Password Required', 'Enter decryption password:',
                    QLineEdit.Password)
                if ok and password:
                    self.start_decryption(file, password)
                else:
                    self.status_bar.showMessage("Decryption canceled.")
            else:
                self.load_media_file(file)

    def load_media_file(self, file_path):
        self.media_player.setMedia(QMediaContent(QUrl.fromLocalFile(file_path)))
        self.btn_play.setEnabled(True)
        self.status_bar.showMessage(f"Loaded: {os.path.basename(file_path)}")

    def start_decryption(self, file_path, password):
        self.decrypt_worker = DecryptorWorker(file_path, password, self.temp_dir.name)
        self.thread = QThread()
        self.decrypt_worker.moveToThread(self.thread)
        self.thread.started.connect(self.decrypt_worker.decrypt)
        self.decrypt_worker.finished.connect(self.handle_decrypted_file)
        self.decrypt_worker.error.connect(self.show_decryption_error)
        self.decrypt_worker.progress.connect(self.update_decryption_progress)
        self.decrypt_worker.finished.connect(self.thread.quit)
        self.thread.finished.connect(self.thread.deleteLater)
        self.status_bar.showMessage("Decrypting...")
        self.thread.start()

    def handle_decrypted_file(self, output_file):
        if not os.path.exists(output_file):
            self.status_bar.showMessage("Decryption failed: No output file created")
            return

        file_size = os.path.getsize(output_file)
        if file_size == 0:
            self.status_bar.showMessage("Decryption failed: Empty file")
            return

        self.temp_files.append(output_file)
        self.load_media_file(output_file)

    def show_decryption_error(self, error_msg):
        self.status_bar.showMessage(f"Decryption error: {error_msg}")

    def update_decryption_progress(self, progress):
        self.status_bar.showMessage(f"Decrypting... {progress}%")

    def update_position(self, position):
        self.seek_slider.setValue(position)
        self.lbl_current.setText(QTime(0, 0, 0).addMSecs(position).toString("HH:mm:ss"))

    def update_duration(self, duration):
        self.seek_slider.setRange(0, duration)
        self.lbl_duration.setText(QTime(0, 0, 0).addMSecs(duration).toString("HH:mm:ss"))

    def update_buttons(self, state):
        self.btn_play.setEnabled(state != QMediaPlayer.PlayingState)
        self.btn_pause.setEnabled(state == QMediaPlayer.PlayingState)
        self.btn_stop.setEnabled(state != QMediaPlayer.StoppedState)

    def stop(self):
        self.media_player.stop()
        self.seek_slider.setValue(0)
        self.lbl_current.setText("00:00:00")

    def toggle_mute(self, checked):
        if checked:
            self.media_player.setVolume(0)
            self.btn_mute.setIcon(self.style().standardIcon(QStyle.SP_MediaVolumeMuted))
        else:
            self.media_player.setVolume(self.volume_slider.value())
            self.btn_mute.setIcon(self.style().standardIcon(QStyle.SP_MediaVolume))

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
            if self.normal_window_geometry:
                self.setGeometry(self.normal_window_geometry)
        else:
            self.normal_window_geometry = self.geometry()
            self.showFullScreen()

    def show_error(self):
        self.status_bar.showMessage(f"Player error: {self.media_player.errorString()}")

    def closeEvent(self, event):
        for file in self.temp_files:
            try:
                if os.path.exists(file):
                    os.remove(file)
            except Exception as e:
                print(f"Error deleting temp file: {str(e)}")
        self.temp_dir.cleanup()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    player = MediaPlayer()
    player.showMaximized()
    sys.exit(app.exec_())