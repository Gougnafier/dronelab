"""Recherche YouTube et transcription, gratuites et locales.

- recherche : yt-dlp (« ytsearch »), sans clé d'API ;
- transcription : sous-titres existants (youtube-transcript-api), sinon audio téléchargé par yt-dlp et
  transcrit localement par faster-whisper (GPU si disponible, sinon CPU).
Les transcriptions sont gardées dans runs/<produit>/research/youtube/ (hors Git) pour citer des extraits
avec leur horodatage ; elles ne sont pas redistribuées.
"""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

WHISPER_MODEL = os.environ.get("DRONE_AGENT_WHISPER_MODEL", "small")
MAX_WHISPER_DURATION_S = 15 * 60  # transcription sur CPU : ~1,2 fois la durée de la vidéo


def video_id(ref: str) -> str:
    match = re.search(r"(?:v=|youtu\.be/|shorts/)([A-Za-z0-9_-]{11})", ref)
    if match:
        return match.group(1)
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", ref):
        return ref
    raise ValueError(f"identifiant ou URL YouTube invalide : {ref}")


def search(query: str, max_results: int = 8) -> list[dict]:
    import yt_dlp

    opts = {"quiet": True, "no_warnings": True, "skip_download": True, "extract_flat": True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(f"ytsearch{max(1, min(int(max_results), 20))}:{query}", download=False)
    out = []
    for e in info.get("entries") or []:
        out.append({"id": e.get("id"), "title": e.get("title"), "channel": e.get("channel") or e.get("uploader"),
                    "duration_s": e.get("duration"), "views": e.get("view_count"),
                    "url": f"https://www.youtube.com/watch?v={e.get('id')}"})
    return out


def _format(segments: list[dict]) -> str:
    return "\n".join(f"[{int(s['start']) // 60:02d}:{int(s['start']) % 60:02d}] {s['text'].strip()}" for s in segments)


def _captions(vid: str) -> list[dict] | None:
    from youtube_transcript_api import YouTubeTranscriptApi

    api = YouTubeTranscriptApi()
    try:
        fetched = api.fetch(vid, languages=["fr", "en", "en-US", "en-GB"])
    except Exception:
        try:  # toute langue disponible, y compris générée automatiquement
            listing = api.list(vid)
            transcript = next(iter(listing))
            fetched = transcript.fetch()
        except Exception:
            return None
    return [{"start": float(s.start), "text": s.text} for s in fetched]


def _whisper(vid: str, folder: Path) -> tuple[list[dict], dict]:
    import yt_dlp
    from faster_whisper import WhisperModel

    audio_dir = folder / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    opts = {"quiet": True, "no_warnings": True, "format": "bestaudio[ext=m4a]/bestaudio",
            "outtmpl": str(audio_dir / "%(id)s.%(ext)s")}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(f"https://www.youtube.com/watch?v={vid}", download=False)
        if (info.get("duration") or 0) > MAX_WHISPER_DURATION_S:
            raise ValueError(f"vidéo de {info['duration'] // 60} min sans sous-titres : trop longue pour la transcription locale")
        ydl.download([f"https://www.youtube.com/watch?v={vid}"])
    audio = next(audio_dir.glob(f"{vid}.*"))
    last_error = None
    # CPU par défaut : sur cette machine, l'initialisation CUDA de ctranslate2 reste bloquée (cartes Pascal/Volta).
    # DRONE_AGENT_WHISPER_DEVICE=cuda pour essayer le GPU ailleurs.
    candidates = [("cpu", 0, "int8")]
    if os.environ.get("DRONE_AGENT_WHISPER_DEVICE") == "cuda":
        candidates.insert(0, ("cuda", int(os.environ.get("DRONE_AGENT_WHISPER_GPU", "0")), "int8_float32"))
    for device, index, ctype in candidates:
        try:
            model = WhisperModel(WHISPER_MODEL, device=device, device_index=index, compute_type=ctype,
                                 cpu_threads=min(8, os.cpu_count() or 4))
            segments, meta = model.transcribe(str(audio), vad_filter=True)
            task = "transcribe"
            if meta.language not in ("fr", "en"):  # autre langue : traduction en anglais par Whisper
                segments, meta = model.transcribe(str(audio), vad_filter=True, task="translate")
                task = "translate"
            segs = [{"start": float(s.start), "text": s.text} for s in segments]
            audio.unlink(missing_ok=True)
            return segs, {"engine": f"faster-whisper {WHISPER_MODEL} ({device})", "language": meta.language,
                          "task": task}
        except Exception as exc:
            last_error = exc
    raise RuntimeError(f"transcription locale impossible : {last_error}")


def transcript(ref: str, root: Path, start_s: float = 0.0, max_chars: int = 12000) -> dict:
    vid = video_id(ref)
    folder = root / "research" / "youtube"
    folder.mkdir(parents=True, exist_ok=True)
    cache = folder / f"{vid}.json"
    if cache.exists():
        data = json.loads(cache.read_text(encoding="utf-8"))
    else:
        t0 = time.monotonic()
        segments = _captions(vid)
        source = {"engine": "sous-titres YouTube"}
        if segments is None:
            segments, source = _whisper(vid, folder)
        data = {"id": vid, "url": f"https://www.youtube.com/watch?v={vid}", "source": source, "segments": segments,
                "seconds": round(time.monotonic() - t0, 1)}
        cache.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    segments = [s for s in data["segments"] if s["start"] >= start_s]
    text, used, next_start = "", 0, None
    for s in segments:
        line = f"[{int(s['start']) // 60:02d}:{int(s['start']) % 60:02d}] {s['text'].strip()}\n"
        if used + len(line) > max_chars:
            next_start = s["start"]
            break
        text += line
        used += len(line)
    last = data["segments"][-1]["start"] if data["segments"] else 0
    return {"ok": True, "id": vid, "url": data["url"], "source": data["source"], "duration_s": round(last),
            "start_s": start_s, "next_start_s": next_start, "text": text,
            "note": "citer les extraits avec l'URL et l'horodatage (&t=<secondes>s)"}
