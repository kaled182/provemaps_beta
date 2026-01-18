import logging
import os
import shutil
from pathlib import Path
from typing import Dict

from fastapi import FastAPI, HTTPException
from pydantic import AnyUrl, BaseModel, Field

from .process_manager import StreamProcessManager

logger = logging.getLogger("video_transmuxer")
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s %(name)s: %(message)s")

app = FastAPI(title="Video Transmuxer", version="1.0.0")
manager = StreamProcessManager()

DEFAULT_TARGET = os.environ.get("VIDEO_HLS_RTMP_URL", "rtmp://video-hls:1935/live")
HLS_STORAGE_PATH = Path(
    os.environ.get("VIDEO_HLS_STORAGE_PATH", "/var/www/hls")
)


class StreamRequest(BaseModel):
    stream_id: str = Field(..., min_length=3, max_length=64)
    source_url: AnyUrl
    stream_type: str = Field(default="rtmp")
    target_key: str = Field(..., min_length=1, max_length=64)

def _cleanup_stream_artifacts(stream_id: str) -> None:
    if not stream_id:
        return
    try:
        if not HLS_STORAGE_PATH.exists():
            return
    except Exception:
        return

    patterns = (
        f"{stream_id}.m3u8",
        f"{stream_id}_*.m3u8",
        f"{stream_id}_*.ts",
        f"{stream_id}-*.ts",
        f"{stream_id}*.tmp",
    )

    removed = 0
    for pattern in patterns:
        for artifact in HLS_STORAGE_PATH.glob(pattern):
            try:
                artifact.unlink()
                removed += 1
            except FileNotFoundError:
                continue
            except Exception as exc:  # pragma: no cover - defensive cleanup
                logger.debug(
                    "Falha ao remover artefato HLS %s: %s", artifact, exc
                )

    nested_dir = HLS_STORAGE_PATH / stream_id
    if nested_dir.is_dir():
        try:
            shutil.rmtree(nested_dir, ignore_errors=True)
            removed += 1
        except Exception as exc:  # pragma: no cover - defensive cleanup
            logger.debug("Falha ao remover diretório HLS %s: %s", nested_dir, exc)

    if removed:
        logger.info("Artefatos HLS limpos para %s (%s arquivos)", stream_id, removed)


def _build_ffmpeg_command(payload: StreamRequest) -> list[str]:
    target_base = DEFAULT_TARGET.rstrip("/")
    target_url = f"{target_base}/{payload.target_key}"

    source_url = str(payload.source_url)

    cmd = [
        "ffmpeg",
        "-loglevel", "warning",
        "-hide_banner",
        "-nostdin",
        # Gera PTS quando faltarem nos pacotes de entrada (ajuda a manter fluxo contínuo)
        "-fflags", "+genpts",
        # Leitura em tempo-real, evita sobrecarregar buffers quando fonte é ao vivo
        "-re",
    ]
    stream_type = payload.stream_type.lower().strip()
    if stream_type == "rtsp":
        cmd.extend(["-rtsp_transport", "tcp"])
    # Entrada
    cmd.extend(["-i", source_url])

    # Saída de vídeo: reencode para garantir keyframes previsíveis e baixa latência
    # Força keyframe ~ a cada 3s (alinha com hls_fragment=3s do nginx-rtmp)
    cmd.extend([
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-tune", "zerolatency",
        # Evita detecção de cena que altera keyint
        "-sc_threshold", "0",
        # Força keyframes por tempo (independente do fps)
        "-force_key_frames", "expr:gte(t,n_forced*3)",
    ])

    # Áudio
    cmd.extend([
        "-c:a", "aac",
        "-ar", "44100",
        "-b:a", "128k",
    ])

    # Saída para RTMP (FLV)
    cmd.extend(["-f", "flv", target_url])
    return cmd


@app.get("/healthz")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/streams")
def list_streams() -> Dict[str, Dict[str, object]]:
    return manager.list()


@app.post("/streams")
def start_stream(payload: StreamRequest) -> Dict[str, object]:
    try:
        command = _build_ffmpeg_command(payload)
        _cleanup_stream_artifacts(payload.stream_id)
        manager.start(payload.stream_id, command)
    except FileNotFoundError as exc:
        logger.error("ffmpeg not available: %s", exc)
        raise HTTPException(status_code=500, detail="ffmpeg executável não encontrado.")
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Erro ao iniciar stream %s", payload.stream_id)
        raise HTTPException(status_code=500, detail=str(exc))

    logger.info(
        "Stream %s iniciado, origem=%s destino=%s",
        payload.stream_id,
        payload.source_url,
        payload.target_key,
    )
    return {"success": True, "stream_id": payload.stream_id}


@app.delete("/streams/{stream_id}")
def stop_stream(stream_id: str) -> Dict[str, object]:
    stopped = manager.stop(stream_id)
    if not stopped:
        raise HTTPException(status_code=404, detail="Stream não encontrado.")
    _cleanup_stream_artifacts(stream_id)
    logger.info("Stream %s encerrado", stream_id)
    return {"success": True, "stream_id": stream_id}


@app.get("/streams/{stream_id}")
def stream_status(stream_id: str) -> Dict[str, object]:
    running = manager.is_running(stream_id)
    return {"stream_id": stream_id, "running": running}
