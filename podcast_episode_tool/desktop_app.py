from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Any, Callable

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Qt, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QScrollArea,
    QPushButton,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from dotenv import set_key


def app_home() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


HOME = app_home()
os.environ["PODCAST_APP_HOME"] = str(HOME)
os.environ["PATH"] = f"{HOME}{os.pathsep}{os.environ.get('PATH', '')}"

from pipeline.analyze import analyze_candidates, format_seconds, text_between
from pipeline.config import load_settings
from pipeline.embed import init_db, upsert_approved_clip
from pipeline.media import cut_audio, ffprobe_duration
from pipeline.models import Candidate, Transcript
from pipeline.storage import (
    clip_base_name,
    load_candidates,
    load_transcript,
    recording_dir,
    recording_id,
    save_candidates,
    save_transcript,
    save_upload,
    write_clip_artifacts,
)
from pipeline.transcribe import parse_timed_text, transcribe_audio


class WorkerSignals(QObject):
    finished = Signal(object)
    failed = Signal(str)
    progress = Signal(int, int, str)


class Worker(QRunnable):
    def __init__(self, fn: Callable[..., Any], progress_aware: bool = False) -> None:
        super().__init__()
        self.fn = fn
        self.progress_aware = progress_aware
        self.signals = WorkerSignals()

    @Slot()
    def run(self) -> None:
        try:
            if self.progress_aware:
                result = self.fn(self.signals.progress.emit)
            else:
                result = self.fn()
            self.signals.finished.emit(result)
        except Exception as exc:
            self.signals.failed.emit(str(exc))


class PodcastWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.settings = load_settings()
        self.pool = QThreadPool.globalInstance()
        self.active_workers: set[Worker] = set()
        self.rid: str | None = None
        self.audio_path: Path | None = None
        self.txt_path: Path | None = None
        self.duration: float | None = None
        self.transcript: Transcript | None = None
        self.candidates: list[Candidate] = []
        self.current_index = -1
        self.preview_end_ms: int | None = None
        self.operation_started = 0.0
        self.operation_name = ""
        self.operation_sequence = 0
        self.elapsed_timer = QTimer(self)
        self.elapsed_timer.setInterval(500)
        self.elapsed_timer.timeout.connect(self._update_elapsed)

        init_db()
        self.setWindowTitle("팟캐스트 에피소드 추출")
        self.resize(1180, 780)
        self.setMinimumSize(920, 640)
        self.setStatusBar(QStatusBar())

        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.audio_output.setVolume(0.8)
        self.player.setAudioOutput(self.audio_output)
        self.player.positionChanged.connect(self._stop_preview_at_end)

        self._build_ui()
        self._apply_style()
        self._refresh_state()

    def _build_ui(self) -> None:
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        heading = QLabel("팟캐스트 에피소드 추출")
        heading.setObjectName("heading")
        layout.addWidget(heading)
        subtitle = QLabel("녹음을 전사하고 공개할 에피소드 구간을 검토한 뒤 승인된 결과만 저장합니다.")
        subtitle.setObjectName("subtitle")
        layout.addWidget(subtitle)

        source_bar = QFrame()
        source_bar.setObjectName("panel")
        source_layout = QHBoxLayout(source_bar)
        self.audio_button = QPushButton("음성 파일 선택")
        self.audio_button.clicked.connect(self.choose_audio)
        self.txt_button = QPushButton("시간 녹취록 선택")
        self.txt_button.clicked.connect(self.choose_text)
        self.source_label = QLabel("파일을 선택해 주세요.")
        self.source_label.setObjectName("sourceLabel")
        self.api_label = QLabel()
        self.api_label.setObjectName("apiStatus")
        self.api_button = QPushButton("API 키 설정")
        self.api_button.clicked.connect(self.configure_api_key)
        source_layout.addWidget(self.audio_button)
        source_layout.addWidget(self.txt_button)
        source_layout.addWidget(self.source_label, 1)
        source_layout.addWidget(self.api_label)
        source_layout.addWidget(self.api_button)
        layout.addWidget(source_bar)

        action_bar = QHBoxLayout()
        self.transcribe_button = QPushButton("전사 실행")
        self.transcribe_button.setObjectName("primaryButton")
        self.transcribe_button.clicked.connect(self.run_transcription)
        self.analyze_button = QPushButton("후보 분석")
        self.analyze_button.clicked.connect(self.run_analysis)
        self.save_button = QPushButton("후보 저장")
        self.save_button.clicked.connect(self.save_candidate_changes)
        self.process_button = QPushButton("승인 후보 처리")
        self.process_button.setObjectName("primaryButton")
        self.process_button.clicked.connect(self.process_approved)
        self.folder_button = QPushButton("결과 폴더 열기")
        self.folder_button.clicked.connect(self.open_results)
        for button in (
            self.transcribe_button,
            self.analyze_button,
            self.save_button,
            self.process_button,
            self.folder_button,
        ):
            action_bar.addWidget(button)
        action_bar.addStretch()
        layout.addLayout(action_bar)

        self.progress_panel = QFrame()
        self.progress_panel.setObjectName("progressPanel")
        progress_layout = QVBoxLayout(self.progress_panel)
        progress_layout.setContentsMargins(14, 10, 14, 10)
        progress_header = QHBoxLayout()
        self.progress_title = QLabel("작업 준비")
        self.progress_title.setObjectName("progressTitle")
        self.progress_elapsed = QLabel("0초")
        self.progress_elapsed.setObjectName("progressElapsed")
        progress_header.addWidget(self.progress_title)
        progress_header.addStretch()
        progress_header.addWidget(self.progress_elapsed)
        progress_layout.addLayout(progress_header)
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        progress_layout.addWidget(self.progress_bar)
        self.progress_detail = QLabel("")
        self.progress_detail.setObjectName("progressDetail")
        progress_layout.addWidget(self.progress_detail)
        self.progress_panel.hide()
        layout.addWidget(self.progress_panel)

        self.tabs = QTabWidget()
        self.transcript_view = QPlainTextEdit()
        self.transcript_view.setReadOnly(True)
        self.transcript_view.setPlaceholderText("전사를 실행하면 시간 표시 전사문이 나타납니다.")
        self.tabs.addTab(self.transcript_view, "전사문")

        candidates_page = QWidget()
        candidates_layout = QVBoxLayout(candidates_page)
        candidates_layout.setContentsMargins(0, 10, 0, 0)
        splitter = QSplitter()
        self.candidate_list = QListWidget()
        self.candidate_list.setMinimumWidth(280)
        self.candidate_list.currentRowChanged.connect(self.select_candidate)
        splitter.addWidget(self.candidate_list)
        splitter.addWidget(self._candidate_editor())
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        candidates_layout.addWidget(splitter)
        self.tabs.addTab(candidates_page, "후보 검토")
        layout.addWidget(self.tabs, 1)
        self.setCentralWidget(root)

    def _candidate_editor(self) -> QWidget:
        editor = QFrame()
        editor.setObjectName("editor")
        outer = QVBoxLayout(editor)
        form = QFormLayout()
        form.setLabelAlignment(form.labelAlignment())
        self.title_edit = QLineEdit()
        self.summary_edit = QPlainTextEdit()
        self.summary_edit.setMinimumHeight(115)
        self.summary_edit.setMaximumHeight(160)
        self.question_edit = QLineEdit()
        self.reason_edit = QPlainTextEdit()
        self.reason_edit.setMinimumHeight(90)
        self.reason_edit.setMaximumHeight(130)
        self.start_edit = QDoubleSpinBox()
        self.start_edit.setRange(0, 999999)
        self.start_edit.setDecimals(1)
        self.end_edit = QDoubleSpinBox()
        self.end_edit.setRange(0, 999999)
        self.end_edit.setDecimals(1)
        self.usage_edit = QComboBox()
        self.usage_edit.addItems(["원본 클립", "새 녹음 소재", "짧은 클립"])
        self.status_edit = QComboBox()
        self.status_edit.addItem("보류", "hold")
        self.status_edit.addItem("승인", "approved")
        self.notes_edit = QPlainTextEdit()
        self.notes_edit.setMinimumHeight(75)
        self.notes_edit.setMaximumHeight(110)
        form.addRow("제목", self.title_edit)
        form.addRow("에피소드 내용 요약", self.summary_edit)
        form.addRow("청취자 질문", self.question_edit)
        form.addRow("추천 이유", self.reason_edit)

        times = QHBoxLayout()
        times.addWidget(QLabel("시작(초)"))
        times.addWidget(self.start_edit)
        times.addSpacing(10)
        times.addWidget(QLabel("끝(초)"))
        times.addWidget(self.end_edit)
        form.addRow("구간", times)
        form.addRow("활용 유형", self.usage_edit)
        form.addRow("상태", self.status_edit)
        form.addRow("공개 전 확인", self.notes_edit)
        outer.addLayout(form)

        preview_bar = QHBoxLayout()
        self.preview_button = QPushButton("선택 구간 재생")
        self.preview_button.clicked.connect(self.preview_candidate)
        self.stop_button = QPushButton("정지")
        self.stop_button.clicked.connect(self.player.stop)
        preview_bar.addWidget(self.preview_button)
        preview_bar.addWidget(self.stop_button)
        preview_bar.addStretch()
        outer.addLayout(preview_bar)

        outer.addWidget(QLabel("구간 전사문"))
        self.candidate_transcript = QPlainTextEdit()
        self.candidate_transcript.setMinimumHeight(150)
        outer.addWidget(self.candidate_transcript, 1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(editor)
        return scroll

    def _apply_style(self) -> None:
        self.setStyleSheet("""
            QMainWindow, QWidget { background: #f4f6f8; color: #17202a; font-family: "Malgun Gothic"; font-size: 13px; }
            QLabel#heading { font-size: 25px; font-weight: 700; color: #17202a; }
            QLabel#subtitle { color: #65717e; margin-bottom: 5px; }
            QLabel#sourceLabel { color: #3e4b57; padding-left: 8px; }
            QLabel#apiStatus { font-weight: 700; color: #196c4a; }
            QFrame#panel, QFrame#editor { background: white; border: 1px solid #d8dee5; border-radius: 6px; }
            QFrame#progressPanel { background: #eef6fc; border: 1px solid #94bedf; border-radius: 6px; }
            QLabel#progressTitle { color: #164f7c; font-weight: 700; }
            QLabel#progressElapsed, QLabel#progressDetail { color: #496779; }
            QProgressBar { background: white; border: 1px solid #aebdca; border-radius: 4px; min-height: 16px; text-align: center; }
            QProgressBar::chunk { background: #2878bd; border-radius: 3px; }
            QPushButton { background: white; border: 1px solid #b8c2cc; border-radius: 5px; padding: 8px 13px; }
            QPushButton:hover { border-color: #2878bd; color: #145d9b; }
            QPushButton:disabled { background: #e9edf1; color: #929ca6; }
            QPushButton#primaryButton { background: #1769aa; color: white; border-color: #1769aa; font-weight: 700; }
            QPushButton#primaryButton:hover { background: #12598f; }
            QLineEdit, QPlainTextEdit, QDoubleSpinBox, QComboBox, QListWidget {
                background: white; border: 1px solid #cbd3dc; border-radius: 4px; padding: 6px;
                selection-background-color: #2878bd;
            }
            QListWidget::item { padding: 10px 8px; border-bottom: 1px solid #e6eaee; }
            QListWidget::item:selected { background: #dcecf8; color: #123f62; }
            QTabWidget::pane { border: 1px solid #d8dee5; background: white; }
            QTabBar::tab { padding: 9px 18px; background: #e6eaee; border: 1px solid #d2d8df; }
            QTabBar::tab:selected { background: white; border-bottom-color: white; font-weight: 700; }
            QStatusBar { background: #17202a; color: white; }
        """)

    def _set_busy(self, busy: bool, message: str = "") -> None:
        for button in (self.audio_button, self.txt_button, self.transcribe_button, self.analyze_button, self.process_button):
            button.setEnabled(not busy)
        if busy:
            QApplication.setOverrideCursor(Qt.WaitCursor)
        else:
            QApplication.restoreOverrideCursor()
        self.statusBar().showMessage(message)

    def _run_worker(
        self,
        fn: Callable[..., Any],
        message: str,
        done: Callable[[Any], None],
        *,
        progress_aware: bool = False,
    ) -> None:
        self.operation_sequence += 1
        self.operation_started = time.monotonic()
        self.operation_name = message.rstrip(".")
        self.progress_title.setText(self.operation_name)
        self.progress_detail.setText("요청을 준비하고 있습니다.")
        self.progress_elapsed.setText("0초")
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setFormat("처리 중")
        self.progress_panel.show()
        self.elapsed_timer.start()
        self._set_busy(True, message)
        worker = Worker(fn, progress_aware=progress_aware)
        self.active_workers.add(worker)
        worker.signals.finished.connect(lambda value, active=worker: self._worker_done(value, done, active))
        worker.signals.failed.connect(lambda error, active=worker: self._worker_failed(error, active))
        worker.signals.progress.connect(self._worker_progress)
        self.pool.start(worker)

    def _update_elapsed(self) -> None:
        elapsed = max(0, int(time.monotonic() - self.operation_started))
        minutes, seconds = divmod(elapsed, 60)
        self.progress_elapsed.setText(f"{minutes}분 {seconds:02d}초" if minutes else f"{seconds}초")

    def _worker_progress(self, current: int, total: int, detail: str) -> None:
        self.progress_bar.setRange(0, max(total, 1))
        self.progress_bar.setValue(current)
        self.progress_bar.setFormat(f"{current}/{total} 완료")
        self.progress_detail.setText(detail)

    def _worker_done(self, value: Any, done: Callable[[Any], None], worker: Worker) -> None:
        self.active_workers.discard(worker)
        self.elapsed_timer.stop()
        self._update_elapsed()
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(1)
        self.progress_bar.setFormat("완료")
        self.progress_title.setText(f"{self.operation_name} 완료")
        self.progress_detail.setText("작업이 정상적으로 끝났습니다.")
        self._set_busy(False, "완료")
        done(value)

    def _worker_failed(self, message: str, worker: Worker) -> None:
        self.active_workers.discard(worker)
        self.elapsed_timer.stop()
        self._update_elapsed()
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("실패")
        self.progress_title.setText(f"{self.operation_name} 실패")
        self.progress_detail.setText(message)
        self._set_busy(False, "오류")
        QMessageBox.critical(self, "처리 실패", message)

    def choose_audio(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(self, "음성 파일 선택", "", "음성 파일 (*.mp3 *.m4a *.wav *.mp4)")
        if not filename:
            return
        source = Path(filename)
        content = source.read_bytes()
        self.rid = recording_id(source.name, content)
        self.audio_path = save_upload(self.rid, source.name, content)
        self.duration = ffprobe_duration(self.audio_path)
        self.player.setSource(QUrl.fromLocalFile(str(self.audio_path)))
        self._restore_recording()

    def configure_api_key(self) -> None:
        key, accepted = QInputDialog.getText(
            self,
            "OpenAI API 키 설정",
            "OpenAI API 키를 입력하세요. 입력값은 이 PC의 .env 파일에 저장됩니다.",
            QLineEdit.EchoMode.Password,
        )
        if not accepted:
            return
        key = key.strip()
        if not key:
            QMessageBox.warning(self, "입력 확인", "API 키를 입력해 주세요.")
            return
        env_path = HOME / ".env"
        if not env_path.exists():
            env_path.touch()
        set_key(str(env_path), "OPENAI_API_KEY", key, quote_mode="never")
        os.environ["OPENAI_API_KEY"] = key
        self.settings = load_settings()
        self._refresh_state()
        QMessageBox.information(self, "저장 완료", "API 키를 저장했습니다. 이제 전사와 AI 후보 분석을 사용할 수 있습니다.")

    def choose_text(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(self, "시간 녹취록 선택", "", "텍스트 파일 (*.txt)")
        if not filename:
            return
        self.txt_path = Path(filename)
        if not self.rid:
            content = self.txt_path.read_bytes()
            self.rid = recording_id(self.txt_path.name, content)
        self._restore_recording()

    def _restore_recording(self) -> None:
        if not self.rid:
            return
        self.transcript = load_transcript(self.rid)
        self.candidates = load_candidates(self.rid) or []
        self._refresh_state()

    def _refresh_state(self) -> None:
        names = []
        if self.audio_path:
            names.append(self.audio_path.name)
        if self.txt_path:
            names.append(self.txt_path.name)
        duration = f" · {format_seconds(self.duration)}" if self.duration else ""
        self.source_label.setText((" + ".join(names) if names else "파일을 선택해 주세요.") + duration)
        self.api_label.setText("API 연결됨" if self.settings.openai_api_key else "API 키 없음")
        self.api_label.setStyleSheet("color: #196c4a;" if self.settings.openai_api_key else "color: #a44d18;")

        if self.transcript:
            self.transcript_view.setPlainText("\n".join(
                f"[{format_seconds(segment.start)}] {segment.text}" for segment in self.transcript.segments
            ))
        else:
            self.transcript_view.clear()
        self._populate_candidates()
        self.transcribe_button.setEnabled(bool(self.audio_path or self.txt_path))
        self.analyze_button.setEnabled(self.transcript is not None)
        self.save_button.setEnabled(bool(self.candidates))
        self.process_button.setEnabled(bool(self.candidates))
        self.preview_button.setEnabled(self.audio_path is not None and self.current_index >= 0)

    def run_transcription(self) -> None:
        if not self.rid:
            QMessageBox.information(self, "파일 필요", "음성 파일이나 시간 녹취록을 먼저 선택해 주세요.")
            return
        if self.txt_path:
            fn = lambda: parse_timed_text(self.txt_path.name, self.txt_path.read_text(encoding="utf-8-sig"))
            progress_aware = False
        elif self.audio_path and self.settings.openai_api_key:
            fn = lambda progress: transcribe_audio(
                self.audio_path,
                self.audio_path.name,
                self.settings.openai_api_key,
                self.settings.transcribe_model,
                progress,
            )
            progress_aware = True
        else:
            QMessageBox.warning(self, "API 키 필요", "음성 전사에는 EXE 옆 .env 파일의 OPENAI_API_KEY가 필요합니다.")
            return
        self._run_worker(
            fn,
            "음성 업로드 및 전사 처리 중...",
            self._transcription_done,
            progress_aware=progress_aware,
        )

    def _transcription_done(self, transcript: Transcript) -> None:
        if self.duration and transcript.duration and transcript.duration > self.duration + 60:
            QMessageBox.warning(self, "시간 확인", "전사 타임코드가 원본 길이를 크게 벗어납니다.")
            return
        self.transcript = transcript
        save_transcript(self.rid, transcript)
        self._refresh_state()
        self.tabs.setCurrentIndex(0)

    def run_analysis(self) -> None:
        if not self.transcript or not self.rid:
            return
        fn = lambda: analyze_candidates(self.transcript, self.settings.openai_api_key, self.settings.analysis_model)
        self._run_worker(fn, "전사문에서 후보 분석 중...", self._analysis_done)

    def _analysis_done(self, candidates: list[Candidate]) -> None:
        self.candidates = candidates
        save_candidates(self.rid, candidates)
        self._populate_candidates()
        self.tabs.setCurrentIndex(1)
        self.statusBar().showMessage(f"후보 {len(candidates)}개를 저장했습니다.", 5000)

    def _populate_candidates(self) -> None:
        self.candidate_list.blockSignals(True)
        self.candidate_list.clear()
        for candidate in self.candidates:
            status = "승인" if candidate.status == "approved" else "보류"
            summary = candidate.summary.replace("\n", " ").strip()
            if len(summary) > 55:
                summary = summary[:55] + "..."
            detail = f"\n{summary}" if summary else ""
            self.candidate_list.addItem(
                f"[{status}] {candidate.title}{detail}\n{format_seconds(candidate.start)} - {format_seconds(candidate.end)}"
            )
        self.candidate_list.blockSignals(False)
        self.current_index = -1
        if self.candidates:
            self.candidate_list.setCurrentRow(0)
        else:
            self._clear_editor()

    def _store_editor(self) -> None:
        if not (0 <= self.current_index < len(self.candidates)):
            return
        old = self.candidates[self.current_index]
        self.candidates[self.current_index] = Candidate(
            id=old.id,
            title=self.title_edit.text().strip() or old.title,
            summary=self.summary_edit.toPlainText().strip(),
            listener_question=self.question_edit.text().strip(),
            reason=self.reason_edit.toPlainText().strip(),
            start=self.start_edit.value(),
            end=self.end_edit.value(),
            transcript=self.candidate_transcript.toPlainText().strip(),
            usage_type=self.usage_edit.currentText(),
            review_notes=self.notes_edit.toPlainText().strip(),
            status=str(self.status_edit.currentData()),
        )

    def select_candidate(self, index: int) -> None:
        self._store_editor()
        self.current_index = index
        if not (0 <= index < len(self.candidates)):
            self._clear_editor()
            return
        candidate = self.candidates[index]
        self.title_edit.setText(candidate.title)
        self.summary_edit.setPlainText(candidate.summary)
        self.question_edit.setText(candidate.listener_question)
        self.reason_edit.setPlainText(candidate.reason)
        self.start_edit.setValue(candidate.start)
        self.end_edit.setValue(candidate.end)
        self.usage_edit.setCurrentText(candidate.usage_type)
        self.status_edit.setCurrentIndex(1 if candidate.status == "approved" else 0)
        self.notes_edit.setPlainText(candidate.review_notes)
        self.candidate_transcript.setPlainText(candidate.transcript)
        self.preview_button.setEnabled(self.audio_path is not None)

    def _clear_editor(self) -> None:
        for field in (self.title_edit, self.question_edit):
            field.clear()
        for field in (self.summary_edit, self.reason_edit, self.notes_edit, self.candidate_transcript):
            field.clear()
        self.preview_button.setEnabled(False)

    def save_candidate_changes(self) -> None:
        if not self.rid:
            return
        self._store_editor()
        save_candidates(self.rid, self.candidates)
        self._populate_candidates()
        self.statusBar().showMessage("후보를 저장했습니다.", 4000)

    def preview_candidate(self) -> None:
        if not self.audio_path or not (0 <= self.current_index < len(self.candidates)):
            return
        start = int(self.start_edit.value() * 1000)
        self.preview_end_ms = int(self.end_edit.value() * 1000)
        self.player.setPosition(start)
        self.player.play()

    def _stop_preview_at_end(self, position: int) -> None:
        if self.preview_end_ms is not None and position >= self.preview_end_ms:
            self.player.stop()
            self.preview_end_ms = None

    def process_approved(self) -> None:
        if not self.rid:
            return
        self._store_editor()
        save_candidates(self.rid, self.candidates)
        approved = [candidate for candidate in self.candidates if candidate.status == "approved"]
        if not approved:
            QMessageBox.information(self, "승인 후보 없음", "승인 상태인 후보가 없습니다.")
            return
        self._run_worker(
            lambda report: self._process_candidates(approved, report),
            "승인 후보 처리 중...",
            self._processing_done,
            progress_aware=True,
        )

    def _process_candidates(
        self,
        approved: list[Candidate],
        report: Callable[[int, int, str], None],
    ) -> list[str]:
        messages: list[str] = []
        rdir = recording_dir(self.rid)
        total = len(approved)
        for index, candidate in enumerate(approved, start=1):
            report(index - 1, total, f"{candidate.title}: 오디오와 메타데이터를 처리하고 있습니다.")
            if candidate.end <= candidate.start:
                messages.append(f"{candidate.title}: 시간 범위 오류")
                report(index, total, f"{candidate.title}: 시간 범위 오류")
                continue
            if self.duration and candidate.end > self.duration:
                messages.append(f"{candidate.title}: 원본 길이 초과")
                report(index, total, f"{candidate.title}: 원본 길이 초과")
                continue
            clip_audio = None
            if self.audio_path:
                clip_audio = rdir / "clips" / f"{clip_base_name(candidate)}.mp3"
                ok, message = cut_audio(self.audio_path, candidate.start, candidate.end, clip_audio)
                if not ok:
                    messages.append(f"{candidate.title}: {message}")
                    report(index, total, f"{candidate.title}: 처리 실패")
                    continue
            write_clip_artifacts(self.rid, candidate, clip_audio)
            inserted = upsert_approved_clip(
                self.rid, candidate, clip_audio, self.settings.openai_api_key, self.settings.embedding_model
            )
            messages.append(f"{candidate.title}: {'저장 완료' if inserted else '기존 결과 재사용'}")
            report(index, total, f"{candidate.title}: 완료")
        return messages

    def _processing_done(self, messages: list[str]) -> None:
        QMessageBox.information(self, "처리 결과", "\n".join(messages))

    def open_results(self) -> None:
        target = recording_dir(self.rid) if self.rid else HOME / "data"
        target.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(target)))


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Podcast Episode Tool")
    window = PodcastWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
