from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from desktop_app import PodcastWindow


class DesktopProgressTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_progress_aware_worker_updates_panel(self) -> None:
        window = PodcastWindow()
        completed: list[list[str]] = []

        def work(report):
            report(1, 2, "첫 후보 완료")
            report(2, 2, "두 번째 후보 완료")
            return ["ok"]

        def done(value):
            completed.append(value)
            self.app.quit()

        window._run_worker(work, "테스트 처리 중...", done, progress_aware=True)
        QTimer.singleShot(3000, self.app.quit)
        self.app.exec()

        self.assertEqual(completed, [["ok"]])
        self.assertFalse(window.progress_panel.isHidden())
        self.assertEqual(window.progress_bar.format(), "완료")
        window.close()


if __name__ == "__main__":
    unittest.main()
