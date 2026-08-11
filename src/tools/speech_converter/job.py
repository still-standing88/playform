from PySide6.QtCore import QThread, Signal


class SaveSpeechJob(QThread):
    """Runs SpeechEngine.save_to_file() on a worker thread.

    save_to_file() drives SAPI synchronously (no incremental progress to report), so this
    only surfaces a final result the same way tools.m4b_tools.audiobook_tools.job.SimpleM4BTask
    does for its single-outcome operations.
    """

    finished_job = Signal(bool, str)

    def __init__(self, engine, text: str, output_path: str, use_pitch_xml: bool, pitch_middle: int):
        super().__init__()
        self._engine = engine
        self._text = text
        self._output_path = output_path
        self._use_pitch_xml = use_pitch_xml
        self._pitch_middle = pitch_middle

    def run(self):
        try:
            result = self._engine.save_to_file(
                self._text, self._output_path, self._use_pitch_xml, self._pitch_middle
            )
            self.finished_job.emit(bool(result), "")
        except Exception as error:
            self.finished_job.emit(False, str(error))
