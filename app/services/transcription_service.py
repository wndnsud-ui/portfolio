from app.services.integration_context import integration_value
import asyncio
import os
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

import httpx

from app.core.config import settings
from app.core.exceptions import AppError


class TranscriptionService:
    endpoint = "https://api.openai.com/v1/audio/transcriptions"
    supported_extensions = {".flac", ".mp3", ".mp4", ".mpeg", ".mpga", ".m4a", ".ogg", ".wav", ".webm"}
    openai_file_limit = 25 * 1024 * 1024
    max_file_size = 250 * 1024 * 1024
    chunk_duration_seconds = 300

    @staticmethod
    def _ffmpeg_executable() -> str:
        if settings.ffmpeg_path:
            configured = Path(settings.ffmpeg_path).expanduser()
            if configured.is_file():
                return str(configured)
            raise AppError("FFMPEG_NOT_FOUND", "설정된 FFMPEG_PATH에서 실행 파일을 찾지 못했습니다.", 500)
        discovered = shutil.which("ffmpeg")
        if discovered:
            return discovered
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            package_root = Path(local_app_data) / "Microsoft" / "WinGet" / "Packages"
            matches = sorted(package_root.glob("Gyan.FFmpeg_*/*/bin/ffmpeg.exe"), reverse=True)
            if matches:
                return str(matches[0])
        raise AppError("FFMPEG_NOT_FOUND", "서버에 FFmpeg가 설치되지 않았습니다.", 500)

    @staticmethod
    def _timestamp(seconds: float) -> str:
        total = max(0, round(seconds))
        return f"{total // 3600:02d}:{total % 3600 // 60:02d}:{total % 60:02d}"

    async def _request(
        self, client: httpx.AsyncClient, filename: str, content: bytes, content_type: str,
        chunk_index: int, chunk_count: int,
    ) -> str:
        response = await client.post(
            self.endpoint,
            headers={"Authorization": f"Bearer {integration_value('openai_api_key')}"},
            data={
                "model": settings.diarization_model,
                "response_format": "diarized_json",
                "chunking_strategy": "auto",
            },
            files={"file": (filename, content, content_type)},
        )
        if response.is_error:
            try:
                detail = response.json().get("error", {}).get("message")
            except ValueError:
                detail = None
            raise AppError("TRANSCRIPTION_ERROR", detail or "음성 전사 요청에 실패했습니다.", 502)
        body = response.json()
        segments = body.get("segments", [])
        if not segments:
            return body.get("text", "").strip()
        speaker_numbers: dict[str, int] = {}
        lines = [f"## 음성 구간 {chunk_index}/{chunk_count}"]
        offset = (chunk_index - 1) * self.chunk_duration_seconds
        for segment in segments:
            text = str(segment.get("text", "")).strip()
            if not text:
                continue
            speaker = str(segment.get("speaker", "unknown"))
            number = speaker_numbers.setdefault(speaker, len(speaker_numbers) + 1)
            start = self._timestamp(offset + float(segment.get("start", 0)))
            end = self._timestamp(offset + float(segment.get("end", 0)))
            lines.append(f"**화자 {number} (구간 {chunk_index})** `{start}-{end}`  \n{text}")
        return "\n\n".join(lines)

    async def _split_audio(self, filename: str, content: bytes) -> list[tuple[str, bytes]]:
        extension = Path(filename).suffix.lower()
        with TemporaryDirectory(prefix="decisionflow-audio-") as directory:
            source = Path(directory) / f"source{extension}"
            output_pattern = Path(directory) / "chunk-%03d.mp3"
            source.write_bytes(content)
            process = await asyncio.create_subprocess_exec(
                self._ffmpeg_executable(), "-hide_banner", "-loglevel", "error", "-i", str(source),
                "-vn", "-ac", "1", "-ar", "16000", "-b:a", "32k",
                "-f", "segment", "-segment_time", str(self.chunk_duration_seconds), "-reset_timestamps", "1",
                str(output_pattern), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await process.communicate()
            if process.returncode != 0:
                detail = stderr.decode("utf-8", errors="replace").strip()
                raise AppError("AUDIO_PROCESSING_ERROR", detail[-500:] or "음성 파일을 분할하지 못했습니다.", 422)
            chunks = [(path.name, path.read_bytes()) for path in sorted(Path(directory).glob("chunk-*.mp3"))]
            if not chunks:
                raise AppError("AUDIO_PROCESSING_ERROR", "음성 파일에서 처리할 구간을 찾지 못했습니다.", 422)
            return chunks

    async def transcribe(self, filename: str, content: bytes, content_type: str | None, on_chunk=None) -> str:
        if not integration_value('openai_api_key'):
            raise AppError("OPENAI_API_KEY_MISSING", "OPENAI_API_KEY가 설정되지 않았습니다.", 503)

        extension = Path(filename).suffix.lower()
        if extension not in self.supported_extensions:
            supported = ", ".join(sorted(self.supported_extensions))
            raise AppError("UNSUPPORTED_AUDIO_FORMAT", f"지원 형식: {supported}", 415)
        if not content:
            raise AppError("EMPTY_AUDIO_FILE", "비어 있는 음성 파일입니다.")
        if len(content) > self.max_file_size:
            raise AppError("AUDIO_FILE_TOO_LARGE", "음성 파일은 최대 250MB까지 업로드할 수 있습니다.", 413)

        try:
            async with httpx.AsyncClient(timeout=180) as client:
                # Compressed files can be small while still containing hours of audio,
                # so normalize every upload into context-safe chunks.
                chunks = await self._split_audio(filename, content)
                semaphore = asyncio.Semaphore(max(1, settings.transcription_concurrency))

                async def transcribe_chunk(index: int, chunk_name: str, chunk_content: bytes) -> str:
                    try:
                        async with semaphore:
                            text = await self._request(
                                client, chunk_name, chunk_content, "audio/mpeg", index, len(chunks)
                            )
                            if on_chunk:
                                on_chunk(index, len(chunks), text)
                            return text
                    except AppError as exc:
                        raise AppError(
                            exc.code,
                            f"{index}/{len(chunks)}번째 음성 구간 전사 실패: {exc.message}",
                            exc.status_code,
                        ) from exc

                texts = await asyncio.gather(*(
                    transcribe_chunk(index, chunk_name, chunk_content)
                    for index, (chunk_name, chunk_content) in enumerate(chunks, start=1)
                ))
        except httpx.RequestError as exc:
            raise AppError("TRANSCRIPTION_CONNECTION_ERROR", "OpenAI 전사 서버에 연결하지 못했습니다.", 502) from exc
        except FileNotFoundError as exc:
            raise AppError("AUDIO_PROCESSING_ERROR", "서버에 FFmpeg가 설치되지 않았습니다.", 500) from exc

        text = "\n\n".join(item for item in texts if item).strip()
        if not text:
            raise AppError("EMPTY_TRANSCRIPTION", "음성에서 텍스트를 추출하지 못했습니다.", 422)
        return text


transcription_service = TranscriptionService()
