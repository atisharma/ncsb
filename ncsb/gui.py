#!/usr/bin/env python3
"""ncsb-gui — A minimal GUI for Lyrion Music Server.

Amberol-inspired: album art centric, clean, simple.
Responsive: resize window to progressively hide/show controls.
"""
import sys
import os
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QSlider, QFrame, QComboBox, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer, QSize
from PySide6.QtGui import QPixmap, QFont

from ncsb import lms_controller as lms


class PlayerWindow(QMainWindow):
    """Main player window with responsive layout."""
    
    # Height thresholds for progressive hiding
    THRESHOLD_VOLUME = 280
    THRESHOLD_CONTROLS = 240
    THRESHOLD_PROGRESS = 200
    THRESHOLD_ARTIST = 170
    
    def __init__(self, server, mac=None, player_name=None):
        super().__init__()
        self.server = server
        self.mac = mac
        self.player_name = player_name
        self._current_pixmap = None  # Store original pixmap for scaling
        
        self.setWindowTitle("ncsb")
        self.setMinimumSize(160, 120)
        self.resize(220, 240)
        self.setStyleSheet("""
            QMainWindow { background-color: #1a1a2e; }
            QLabel { color: #eaeaea; }
            QPushButton {
                background-color: #16213e;
                color: #eaeaea;
                border: none;
                border-radius: 10px;
                font-size: 12px;
                min-width: 20px;
                min-height: 20px;
            }
            QPushButton:hover { background-color: #1f3460; }
            QPushButton:pressed { background-color: #0f3460; }
            QPushButton:checked { background-color: #e94560; }
            QSlider::groove:horizontal {
                background: #16213e;
                height: 3px;
                border-radius: 1px;
            }
            QSlider::handle:horizontal {
                background: #e94560;
                width: 10px;
                margin: -3px 0;
                border-radius: 5px;
            }
            QSlider::sub-page:horizontal {
                background: #e94560;
                border-radius: 1px;
            }
            QComboBox {
                background-color: #16213e;
                color: #eaeaea;
                border: none;
                padding: 2px 6px;
                border-radius: 3px;
                font-size: 10px;
            }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView {
                background-color: #16213e;
                color: #eaeaea;
                selection-background-color: #1f3460;
            }
        """)
        
        self._setup_ui()
        self._resolve_player()
        
        # Debounce resize events
        self._resize_timer = QTimer()
        self._resize_timer.setSingleShot(True)
        self._resize_timer.timeout.connect(self._scale_art)
        
        # Poll for updates
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_state)
        self.timer.start(1000)  # 1 second
        
        self._update_state()
    
    def _setup_ui(self):
        """Create the UI layout."""
        central = QWidget()
        self.setCentralWidget(central)
        self._layout = QVBoxLayout(central)
        self._layout.setContentsMargins(12, 12, 12, 12)
        self._layout.setSpacing(6)
        
        # Player selector
        self._player_row = QHBoxLayout()
        player_label = QLabel("Player:")
        player_label.setFont(QFont("Sans", 10))
        self.player_combo = QComboBox()
        self.player_combo.currentTextChanged.connect(self._on_player_changed)
        self._player_row.addWidget(player_label)
        self._player_row.addWidget(self.player_combo)
        self._player_row.addStretch()
        self._layout.addLayout(self._player_row)
        
        # Album art - scalable
        self.art_label = QLabel()
        self.art_label.setAlignment(Qt.AlignCenter)
        self.art_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.art_label.setMinimumSize(80, 80)
        self.art_label.setStyleSheet("""
            QLabel {
                background-color: #16213e;
                border-radius: 6px;
            }
        """)
        self._layout.addWidget(self.art_label, alignment=Qt.AlignCenter, stretch=1)
        
        # Track info
        self.title_label = QLabel("—")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setFont(QFont("Sans", 11, QFont.Bold))
        self.title_label.setWordWrap(True)
        self._layout.addWidget(self.title_label)
        
        self.artist_label = QLabel("—")
        self.artist_label.setAlignment(Qt.AlignCenter)
        self.artist_label.setFont(QFont("Sans", 9))
        self.artist_label.setStyleSheet("color: #a0a0a0;")
        self.artist_label.setWordWrap(True)
        self._layout.addWidget(self.artist_label)
        
        # Progress
        self.progress_slider = QSlider(Qt.Horizontal)
        self.progress_slider.setRange(0, 1000)
        self.progress_slider.setValue(0)
        self.progress_slider.sliderMoved.connect(self._on_seek)
        self._layout.addWidget(self.progress_slider)
        
        self.time_label = QLabel("0:00 / 0:00")
        self.time_label.setAlignment(Qt.AlignCenter)
        self.time_label.setStyleSheet("color: #707070; font-size: 11px;")
        self._layout.addWidget(self.time_label)
        
        # Controls
        self._controls_row = QHBoxLayout()
        self._controls_row.setSpacing(6)
        
        self.shuffle_btn = QPushButton("S")
        self.shuffle_btn.setCheckable(True)
        self.shuffle_btn.clicked.connect(self._on_shuffle)
        self._controls_row.addWidget(self.shuffle_btn)
        
        self.prev_btn = QPushButton("◀")
        self.prev_btn.clicked.connect(self._on_prev)
        self._controls_row.addWidget(self.prev_btn)
        
        self.play_btn = QPushButton("▶")
        self.play_btn.clicked.connect(self._on_play_pause)
        self.play_btn.setStyleSheet("""
            QPushButton {
                background-color: #e94560;
                font-size: 14px;
                min-width: 28px;
                min-height: 28px;
            }
            QPushButton:hover { background-color: #ff6b6b; }
        """)
        self._controls_row.addWidget(self.play_btn)
        
        self.next_btn = QPushButton("▶")
        self.next_btn.clicked.connect(self._on_next)
        self._controls_row.addWidget(self.next_btn)
        
        self.repeat_btn = QPushButton("R")
        self.repeat_btn.setCheckable(True)
        self.repeat_btn.clicked.connect(self._on_repeat)
        self._controls_row.addWidget(self.repeat_btn)
        
        self._layout.addLayout(self._controls_row)
        
        # Volume
        self._volume_row = QHBoxLayout()
        vol_label = QLabel("V")
        vol_label.setFont(QFont("Sans", 10))
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(50)
        self.volume_slider.sliderMoved.connect(self._on_volume)
        self._volume_row.addWidget(vol_label)
        self._volume_row.addWidget(self.volume_slider)
        self._layout.addLayout(self._volume_row)
        
        # Store references for visibility toggling
        self._vol_label = vol_label
        self._player_label = player_label
    
    def resizeEvent(self, event):
        """Handle window resize - progressive hide/show elements."""
        super().resizeEvent(event)
        h = self.height()
        
        # Progressive visibility from bottom up
        # Volume row
        vol_visible = h >= self.THRESHOLD_VOLUME
        self._vol_label.setVisible(vol_visible)
        self.volume_slider.setVisible(vol_visible)
        
        # Controls row (shuffle, prev, next, repeat - keep play always)
        controls_visible = h >= self.THRESHOLD_CONTROLS
        self.shuffle_btn.setVisible(controls_visible)
        self.prev_btn.setVisible(controls_visible)
        self.next_btn.setVisible(controls_visible)
        self.repeat_btn.setVisible(controls_visible)
        
        # Progress slider and time
        progress_visible = h >= self.THRESHOLD_PROGRESS
        self.progress_slider.setVisible(progress_visible)
        self.time_label.setVisible(progress_visible)
        
        # Artist label
        artist_visible = h >= self.THRESHOLD_ARTIST
        self.artist_label.setVisible(artist_visible)
        
        # Player selector - hide when very small
        player_visible = h >= self.THRESHOLD_VOLUME
        self._player_label.setVisible(player_visible)
        self.player_combo.setVisible(player_visible)
        
        # Shrink play button when it's the only control
        if controls_visible:
            self.play_btn.setStyleSheet("""
                QPushButton {
                    background-color: #e94560;
                    font-size: 14px;
                    min-width: 28px;
                    min-height: 28px;
                }
                QPushButton:hover { background-color: #ff6b6b; }
            """)
        else:
            self.play_btn.setStyleSheet("""
                QPushButton {
                    background-color: #e94560;
                    font-size: 12px;
                    min-width: 22px;
                    min-height: 22px;
                }
                QPushButton:hover { background-color: #ff6b6b; }
            """)
        
        # Debounce art scaling - configurable via NCSB_RESIZE_DEBOUNCE_MS env var
        # Default 500ms means scale only after resize finishes
        debounce_ms = int(os.environ.get('NCSB_RESIZE_DEBOUNCE_MS', 500))
        self._resize_timer.start(debounce_ms)
    
    def _scale_art(self):
        """Scale album art to fit available space."""
        if not self._current_pixmap or self._current_pixmap.isNull():
            return
        
        # Calculate available space for art
        # Subtract margins, title, and other visible elements
        h = self.height()
        used_height = 24  # margins
        
        if self.player_combo.isVisible():
            used_height += 24
        if self.title_label.isVisible():
            used_height += 20
        if self.artist_label.isVisible():
            used_height += 16
        if self.progress_slider.isVisible():
            used_height += 20
        if self.time_label.isVisible():
            used_height += 16
        if self._controls_row.geometry().height() > 0 or self.play_btn.isVisible():
            used_height += 32
        if self.volume_slider.isVisible():
            used_height += 24
        
        available = max(80, h - used_height - 12)
        size = min(available, self.width() - 24)
        size = max(80, size)
        
        scaled = self._current_pixmap.scaled(
            size, size,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.art_label.setPixmap(scaled)
    
    def _resolve_player(self):
        """Resolve player and populate combo box."""
        try:
            players = lms.players(self.server)
            player_names = [p['name'] for p in players]
            self.player_combo.addItems(player_names)
            
            # Select specified player
            if self.mac:
                for p in players:
                    if p['playerid'] == self.mac:
                        self.player_combo.setCurrentText(p['name'])
                        break
            elif self.player_name:
                for name in player_names:
                    if name.lower() == self.player_name.lower():
                        self.player_combo.setCurrentText(name)
                        break
            elif player_names:
                self.mac = players[0]['playerid']
        except Exception as e:
            print(f"Error resolving player: {e}")
    
    def _on_player_changed(self, name):
        """Handle player selection change."""
        try:
            players = lms.players(self.server)
            for p in players:
                if p['name'] == name:
                    self.mac = p['playerid']
                    break
            self._update_state()
        except Exception:
            pass
    
    def _update_state(self):
        """Poll LMS for current state."""
        if not self.mac:
            return
        
        try:
            status = lms.status(self.server, self.mac)
            mode = status.get('mode', 'stop')
            
            # Update play button
            if mode == 'play':
                self.play_btn.setText("⏸")
            else:
                self.play_btn.setText("▶")
            
            # Track info
            playlist = status.get('playlist_loop', [])
            current_idx = int(status.get('playlist_cur_index', -1))
            
            if playlist and 0 <= current_idx < len(playlist):
                track = playlist[current_idx]
                self.title_label.setText(track.get('title', '—'))
                self.artist_label.setText(track.get('artist', '—'))
                
                # Album art
                coverid = track.get('coverid')
                if coverid:
                    self._load_coverart(coverid)
                else:
                    self._current_pixmap = None
                    self.art_label.clear()
            else:
                self.title_label.setText("—")
                self.artist_label.setText("—")
                self._current_pixmap = None
                self.art_label.clear()
            
            # Progress
            duration = float(status.get('duration', 0) or 0)
            elapsed = float(lms.track_elapsed(self.server, self.mac) or 0)
            
            if duration > 0:
                progress = int((elapsed / duration) * 1000)
                self.progress_slider.blockSignals(True)
                self.progress_slider.setValue(progress)
                self.progress_slider.blockSignals(False)
                self.time_label.setText(f"{self._fmt_time(elapsed)} / {self._fmt_time(duration)}")
            else:
                self.time_label.setText("0:00 / 0:00")
            
            # Volume
            vol = int(float(status.get('mixer volume', 0) or 0))
            self.volume_slider.blockSignals(True)
            self.volume_slider.setValue(vol)
            self.volume_slider.blockSignals(False)
            
            # Shuffle/Repeat
            shuffle = int(status.get('playlist shuffle', 0) or 0)
            repeat = int(status.get('playlist repeat', 0) or 0)
            self.shuffle_btn.setChecked(shuffle > 0)
            self.repeat_btn.setChecked(repeat > 0)
            
        except Exception as e:
            print(f"Error updating state: {e}")
    
    def _load_coverart(self, coverid):
        """Load cover art from LMS server."""
        try:
            import requests
            
            # Fetch larger image for scaling
            url = f"http://{self.server.ip}:{self.server.port}/music/{coverid}/cover_300x300.png"
            resp = requests.get(url, timeout=5)
            if resp.ok:
                pixmap = QPixmap()
                pixmap.loadFromData(resp.content)
                if not pixmap.isNull():
                    self._current_pixmap = pixmap
                    self._scale_art()
        except Exception:
            self._current_pixmap = None
            self.art_label.clear()
    
    def _fmt_time(self, seconds):
        """Format seconds as M:SS."""
        s = int(seconds)
        return f"{s // 60}:{s % 60:02d}"
    
    def _on_play_pause(self):
        """Toggle play/pause."""
        if self.mac:
            lms.pause(self.server, self.mac)
            self._update_state()
    
    def _on_prev(self):
        """Previous track."""
        if self.mac:
            lms.playlist_prev(self.server, self.mac)
            self._update_state()
    
    def _on_next(self):
        """Next track."""
        if self.mac:
            lms.playlist_skip(self.server, self.mac)
            self._update_state()
    
    def _on_seek(self, value):
        """Seek to position."""
        if not self.mac:
            return
        try:
            status = lms.status(self.server, self.mac)
            duration = float(status.get('duration', 0) or 0)
            if duration > 0:
                pos = (value / 1000) * duration
                self.server.send([self.mac, ["time", str(int(pos))]])
        except Exception:
            pass
    
    def _on_volume(self, value):
        """Set volume."""
        if self.mac:
            lms.volume(self.server, self.mac, value)
    
    def _on_shuffle(self):
        """Toggle shuffle."""
        if not self.mac:
            return
        try:
            status = lms.status(self.server, self.mac)
            current = int(status.get('playlist shuffle', 0) or 0)
            new_val = (current + 1) % 3
            lms.playlist_shuffle(self.server, self.mac, new_val)
            self._update_state()
        except Exception:
            pass
    
    def _on_repeat(self):
        """Toggle repeat."""
        if not self.mac:
            return
        try:
            status = lms.status(self.server, self.mac)
            current = int(status.get('playlist repeat', 0) or 0)
            new_val = (current + 1) % 3
            lms.playlist_repeat(self.server, self.mac, new_val)
            self._update_state()
        except Exception:
            pass


def main(host='localhost', port=9000, player=None, mac=None):
    """Launch the GUI."""
    # Set app-id for Wayland before creating QApplication
    os.environ.setdefault('QT_WAYLAND_APP_ID', 'ncsb')
    
    app = QApplication(sys.argv)
    app.setApplicationName("ncsb")
    app.setDesktopFileName("ncsb")
    
    server = lms.Server(host, port)
    window = PlayerWindow(server, mac=mac, player_name=player)
    window.show()
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
