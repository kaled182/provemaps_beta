import logging
import threading
import time
import subprocess
from typing import Dict, Optional

logger = logging.getLogger("video_transmuxer")


class StreamProcessManager:
    """Keeps track of ffmpeg processes that restream sources into RTMP."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._processes: Dict[str, Dict[str, object]] = {}

    def _cleanup_finished(self) -> None:
        to_remove = []
        for stream_id, info in self._processes.items():
            process = info.get("process")
            if isinstance(process, subprocess.Popen) and process.poll() is not None:
                # Log stderr when process terminates unexpectedly
                stderr_data = process.stderr.read() if process.stderr else b""
                if stderr_data:
                    logger.warning(
                        "Stream %s terminou com erros:\n%s",
                        stream_id,
                        stderr_data.decode("utf-8", errors="replace")[:500]
                    )
                to_remove.append(stream_id)
        for stream_id in to_remove:
            self._processes.pop(stream_id, None)

    def start(self, stream_id: str, command: list[str]) -> None:
        # Ensure any previous process is stopped before acquiring the lock
        self.stop(stream_id)

        with self._lock:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self._processes[stream_id] = {
                "process": process,
                "command": command,
                "started_at": time.time(),
            }

    def stop(self, stream_id: str) -> bool:
        with self._lock:
            info = self._processes.get(stream_id)
            if not info:
                return False
            process: Optional[subprocess.Popen] = info.get("process")  # type: ignore[assignment]
            if isinstance(process, subprocess.Popen) and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    process.kill()
            self._processes.pop(stream_id, None)
            return True

    def list(self) -> Dict[str, Dict[str, object]]:
        with self._lock:
            self._cleanup_finished()
            result: Dict[str, Dict[str, object]] = {}
            for stream_id, info in self._processes.items():
                process: Optional[subprocess.Popen] = info.get("process")  # type: ignore[assignment]
                result[stream_id] = {
                    "command": info.get("command"),
                    "started_at": info.get("started_at"),
                    "running": bool(
                        isinstance(process, subprocess.Popen) and process.poll() is None
                    ),
                }
            return result

    def is_running(self, stream_id: str) -> bool:
        with self._lock:
            info = self._processes.get(stream_id)
            if not info:
                return False
            process: Optional[subprocess.Popen] = info.get("process")  # type: ignore[assignment]
            return bool(isinstance(process, subprocess.Popen) and process.poll() is None)
