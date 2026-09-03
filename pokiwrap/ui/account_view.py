from __future__ import annotations

import sys

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import QCheckBox, QFrame, QLabel, QPushButton, QVBoxLayout, QWidget

from pokiwrap.engine.account import load_account
from pokiwrap.engine.adblock import adblock_enabled, set_adblock_enabled


class _AccountWorker(QThread):
    finished_ok = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, sign_out: bool, parent=None) -> None:
        super().__init__(parent)
        self._sign_out = sign_out

    def run(self) -> None:
        try:
            from pokiwrap.engine.account import connect_account, sign_out_account

            state = sign_out_account() if self._sign_out else connect_account()
            self.finished_ok.emit(state)
        except Exception as exc:
            self.failed.emit(str(exc))


class AccountView(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._worker: _AccountWorker | None = None

        title = QLabel("Poki Account")
        title.setObjectName("title")
        subtitle = QLabel(
            "Sign in so wrapped games can load your cloud progress. "
            "Use the same Google, Apple, Microsoft, or passkey login you use on Poki."
        )
        subtitle.setObjectName("subtitle")
        subtitle.setWordWrap(True)

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 18, 20, 18)
        card_layout.setSpacing(10)

        self.status = QLabel("Not connected")
        self.status.setStyleSheet("font-size: 16px; font-weight: 700; background: transparent; border: none;")
        self.detail = QLabel("Connect your Poki account, then open a game wrapper to pick up saved progress.")
        self.detail.setWordWrap(True)
        self.detail.setStyleSheet("color: #8B90A0; background: transparent; border: none;")

        self.connect_btn = QPushButton("Connect Poki account")
        self.connect_btn.setObjectName("primaryButton")
        self.connect_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.connect_btn.setFixedWidth(220)
        self.connect_btn.clicked.connect(self._connect)

        self.signout_btn = QPushButton("Disconnect")
        self.signout_btn.setObjectName("dangerButton")
        self.signout_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.signout_btn.setFixedWidth(220)
        self.signout_btn.clicked.connect(self._sign_out)

        self.adblock = QCheckBox("Ad blocker (EasyList + EasyPrivacy)")
        self.adblock.setCursor(Qt.CursorShape.PointingHandCursor)
        self.adblock.setChecked(adblock_enabled())
        self.adblock.setStyleSheet("background: transparent; border: none;")
        self.adblock.toggled.connect(set_adblock_enabled)
        adblock_hint = QLabel("Blocks ads and trackers in game windows, like uBlock. Restart a game after changing this.")
        adblock_hint.setWordWrap(True)
        adblock_hint.setStyleSheet("color: #8B90A0; background: transparent; border: none; font-size: 12px;")

        card_layout.addWidget(self.status)
        card_layout.addWidget(self.detail)
        card_layout.addSpacing(6)
        card_layout.addWidget(self.connect_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        card_layout.addWidget(self.signout_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        card_layout.addSpacing(10)
        card_layout.addWidget(self.adblock)
        card_layout.addWidget(adblock_hint)

        note = QLabel(
            "Sign in inside PokiWrap — Chrome on poki.com does not carry over. "
            "Close game windows first. Connect detects an existing PokiWrap sign-in automatically. "
            "Play time comes from the account; cloud game saves need that same session in the game window."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: #6E7384; font-size: 12px;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 24, 16)
        layout.setSpacing(12)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(card)
        layout.addWidget(note)
        layout.addStretch()

        self.refresh()

    def refresh(self) -> None:
        state = load_account()
        connected = bool(state.get("connected"))
        username = str(state.get("username") or "").strip()
        if connected:
            self.status.setText(f"Connected{(' as ' + username) if username else ''}")
            self.detail.setText(
                "This Poki account is linked. Games load play time and cloud saves from it. "
                "Disconnect to sign out."
            )
            self.connect_btn.setText("Reconnect")
            self.connect_btn.setVisible(False)
            self.signout_btn.setVisible(True)
        else:
            self.status.setText("Not connected")
            self.detail.setText(
                "Connect your Poki account. If you are already signed in, PokiWrap will detect it "
                "and show Disconnect."
            )
            self.connect_btn.setText("Connect Poki account")
            self.connect_btn.setVisible(True)
            self.signout_btn.setVisible(False)
        self.adblock.blockSignals(True)
        self.adblock.setChecked(adblock_enabled())
        self.adblock.blockSignals(False)

    def _busy(self, busy: bool, message: str | None = None) -> None:
        self.connect_btn.setEnabled(not busy)
        self.signout_btn.setEnabled(not busy)
        if busy:
            self.detail.setText(message or "Waiting for the Poki sign-in window…")

    def _connect(self) -> None:
        if sys.platform != "win32":
            try:
                from pokiwrap.engine.account import connect_account

                self._busy(True)
                connect_account(self.window())
            except Exception as exc:
                self.detail.setText(str(exc) or "Could not open the Poki sign-in window.")
                self._busy(False)
                return
            self._busy(False)
            self.refresh()
            return
        self._start(False)

    def _sign_out(self) -> None:
        self._start(True)

    def _start(self, sign_out: bool) -> None:
        if self._worker is not None and self._worker.isRunning():
            return
        self._busy(True, "Disconnecting…" if sign_out else "Looking for your Poki sign-in…")
        worker = _AccountWorker(sign_out, self)
        worker.finished_ok.connect(self._on_done)
        worker.failed.connect(self._on_fail)
        worker.finished.connect(lambda: self._busy(False))
        self._worker = worker
        worker.start()

    def _on_done(self, state: object) -> None:
        self.refresh()

    def _on_fail(self, message: str) -> None:
        self.refresh()
        self.detail.setText(message or "Could not open the Poki sign-in window.")
