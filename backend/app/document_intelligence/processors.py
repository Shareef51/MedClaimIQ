from __future__ import annotations

import hashlib
import json
import math
import subprocess
import tempfile
from pathlib import Path
from typing import Protocol

from app.domain.document_intelligence import CitationAnchor, ExtractionBundle, ExtractionUnit, ExtractionUnitType
from app.document_intelligence.visual_descriptors import sanitize_visual_descriptor


class ProcessorUnavailable(RuntimeError): pass
class UnsupportedMedia(RuntimeError): pass


class MediaProcessor(Protocol):
    def parse(self, path: Path, *, evidence_id: str, media_type: str) -> ExtractionBundle: ...


class PdfProcessor:
    """Layout-aware PDF processor. Uses PyMuPDF when installed; falls back only for tests/dev text fixtures."""
    def parse(self, path: Path, *, evidence_id: str, media_type: str) -> ExtractionBundle:
        try:
            import fitz  # type: ignore
        except ImportError as exc:
            raise ProcessorUnavailable("PyMuPDF is required for PDF extraction") from exc
        units = []
        with fitz.open(path) as doc:
            for page_index, page in enumerate(doc):
                blocks = page.get_text("blocks")
                for block_index, block in enumerate(blocks):
                    text = str(block[4]).strip()
                    if not text: continue
                    units.append(ExtractionUnit(ExtractionUnitType.TEXT, len(units), text, {}, 0.99,
                        CitationAnchor(evidence_id=evidence_id, page_number=page_index + 1, bbox=(float(block[0]), float(block[1]), float(block[2]), float(block[3])), source_locator={"block": block_index})))
                tables = page.find_tables() if hasattr(page, "find_tables") else None
                if tables:
                    for table_index, table in enumerate(tables.tables):
                        rows = table.extract()
                        units.append(ExtractionUnit(ExtractionUnitType.TABLE, len(units), None, {"rows": rows}, 0.95,
                            CitationAnchor(evidence_id=evidence_id, page_number=page_index + 1, source_locator={"table": table_index})))
        return ExtractionBundle("pymupdf", getattr(fitz, "VersionBind", "unknown"), media_type, tuple(units))


class DoclingPdfProcessor:
    def parse(self, path: Path, *, evidence_id: str, media_type: str) -> ExtractionBundle:
        try:
            from docling.document_converter import DocumentConverter  # type: ignore
        except ImportError as exc:
            raise ProcessorUnavailable("Docling is not installed") from exc
        result = DocumentConverter().convert(str(path))
        text = result.document.export_to_markdown()
        unit = ExtractionUnit(ExtractionUnitType.TEXT, 0, text, {"format": "markdown"}, 0.96,
                              CitationAnchor(evidence_id=evidence_id, source_locator={"parser": "docling"}))
        return ExtractionBundle("docling", "runtime", media_type, (unit,))


class ImageOcrProcessor:
    def __init__(self, visual_descriptor=None): self.visual_descriptor=visual_descriptor
    def parse(self, path: Path, *, evidence_id: str, media_type: str) -> ExtractionBundle:
        try:
            from PIL import Image  # type: ignore
            import pytesseract  # type: ignore
        except ImportError as exc:
            raise ProcessorUnavailable("Pillow and pytesseract are required for OCR") from exc
        image = Image.open(path)
        data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
        units=[]
        ocr_words=[]
        for i, raw in enumerate(data.get("text", [])):
            text = str(raw).strip()
            if not text: continue
            ocr_words.append(text)
            conf_raw = data.get("conf", ["0"])[i]
            try: conf=max(0.0, min(1.0, float(conf_raw)/100.0))
            except Exception: conf=0.0
            x,y,w,h = (int(data[k][i]) for k in ("left","top","width","height"))
            units.append(ExtractionUnit(ExtractionUnitType.TEXT, len(units), text, {}, conf,
                CitationAnchor(evidence_id=evidence_id, page_number=1, bbox=(x,y,x+w,y+h), source_locator={"ocr_word": i,"kind":"image_ocr"})))
        image_sha=hashlib.sha256(path.read_bytes()).hexdigest()
        visual=sanitize_visual_descriptor(self.visual_descriptor.describe(path,media_type=media_type)) if self.visual_descriptor is not None else {}
        visual_text=str(visual.get("description") or "")
        image_text=" ".join(x for x in (" ".join(ocr_words)[:10000],visual_text) if x).strip() or None
        units.append(ExtractionUnit(ExtractionUnitType.IMAGE, len(units), image_text,
            {"width": image.width, "height": image.height, "image_sha256": image_sha, "descriptor_source": "approved_vision_adapter" if visual else "ocr_layout", "visual": visual},
            max([u.confidence for u in units], default=1.0),
            CitationAnchor(evidence_id=evidence_id, page_number=1, source_locator={"kind":"image","image_sha256":image_sha})))
        return ExtractionBundle("tesseract", str(pytesseract.get_tesseract_version()), media_type, tuple(units), metadata={"width": image.width, "height": image.height, "image_sha256": image_sha})


class FasterWhisperTranscriber:
    """Optional local transcription adapter. Model loading is lazy and worker-local."""
    def __init__(self, model_name: str = "small", device: str = "cpu", compute_type: str = "int8"):
        self.model_name=model_name; self.device=device; self.compute_type=compute_type; self._model=None
    def __call__(self, path: Path) -> list[dict[str, object]]:
        try:
            from faster_whisper import WhisperModel  # type: ignore
        except ImportError as exc:
            raise ProcessorUnavailable("faster-whisper is not installed") from exc
        if self._model is None:
            self._model=WhisperModel(self.model_name,device=self.device,compute_type=self.compute_type)
        segments,_=self._model.transcribe(str(path),vad_filter=True)
        result=[]
        for seg in segments:
            confidence=max(0.0,min(1.0,math.exp(float(getattr(seg,"avg_logprob",-0.2)))))
            result.append({"text":str(seg.text).strip(),"start_ms":int(seg.start*1000),"end_ms":int(seg.end*1000),"confidence":confidence,"speaker":None})
        return result


class FfmpegVideoAnalyzer:
    """Extracts audio plus deterministic keyframe samples using FFmpeg, then transcribes audio."""
    def __init__(self, transcriber=None, keyframe_interval_seconds: int = 15, frame_descriptor=None):
        self.transcriber=transcriber or FasterWhisperTranscriber(); self.keyframe_interval_seconds=keyframe_interval_seconds; self.frame_descriptor=frame_descriptor
    def __call__(self, path: Path) -> dict[str, object]:
        with tempfile.TemporaryDirectory(prefix="medclaimiq-video-") as tmp:
            tmp_path=Path(tmp); audio=tmp_path/"audio.wav"; frames=tmp_path/"frames"; frames.mkdir()
            audio_cmd=["ffmpeg","-hide_banner","-loglevel","error","-y","-i",str(path),"-vn","-ac","1","-ar","16000",str(audio)]
            frame_cmd=["ffmpeg","-hide_banner","-loglevel","error","-y","-i",str(path),"-vf",f"fps=1/{self.keyframe_interval_seconds}",str(frames/"frame-%06d.jpg")]
            for cmd in (audio_cmd,frame_cmd):
                completed=subprocess.run(cmd,capture_output=True,text=True,check=False)
                if completed.returncode != 0:
                    raise ProcessorUnavailable(f"ffmpeg failed: {completed.stderr[-300:]}")
            segments=self.transcriber(audio) if audio.exists() else []
            keyframes=[]
            for index, frame in enumerate(sorted(frames.glob("frame-*.jpg"))):
                raw=frame.read_bytes(); visual=sanitize_visual_descriptor(self.frame_descriptor.describe(frame,media_type="image/jpeg")) if self.frame_descriptor is not None else {}
                keyframes.append({"timestamp_ms":index*self.keyframe_interval_seconds*1000,"frame_index":index,"frame_sha256":hashlib.sha256(raw).hexdigest(),"byte_size":len(raw),"confidence":1.0,"text":visual.get("description") or None,"visual_descriptor":visual})
            return {"segments":segments,"keyframes":keyframes,"keyframe_interval_seconds":self.keyframe_interval_seconds}


class AudioProcessor:
    """Provider-neutral transcription adapter contract. A configured transcriber is injected in production."""
    def __init__(self, transcriber=None): self.transcriber = transcriber or FasterWhisperTranscriber()
    def parse(self, path: Path, *, evidence_id: str, media_type: str) -> ExtractionBundle:
        if self.transcriber is None: raise ProcessorUnavailable("audio transcriber is not configured")
        segments = self.transcriber(path)
        units=[]
        for segment in segments:
            units.append(ExtractionUnit(ExtractionUnitType.AUDIO_SEGMENT, len(units), segment["text"], {"speaker": segment.get("speaker")}, float(segment.get("confidence", .9)),
                CitationAnchor(evidence_id=evidence_id, start_ms=int(segment["start_ms"]), end_ms=int(segment["end_ms"]), source_locator={"segment": len(units)})))
        return ExtractionBundle("configured-transcriber", "runtime", media_type, tuple(units))


class VideoProcessor:
    """Combines transcript segments and keyframes supplied by an isolated FFmpeg-capable adapter."""
    def __init__(self, analyzer=None): self.analyzer=analyzer or FfmpegVideoAnalyzer()
    def parse(self, path: Path, *, evidence_id: str, media_type: str) -> ExtractionBundle:
        if self.analyzer is None: raise ProcessorUnavailable("video analyzer is not configured")
        result=self.analyzer(path); units=[]
        for seg in result.get("segments", []):
            units.append(ExtractionUnit(ExtractionUnitType.AUDIO_SEGMENT, len(units), seg["text"], {}, float(seg.get("confidence",.9)), CitationAnchor(evidence_id=evidence_id,start_ms=int(seg["start_ms"]),end_ms=int(seg["end_ms"]))))
        for frame in result.get("keyframes", []):
            frame_index=int(frame.get("frame_index", len(units)))
            frame_sha=str(frame.get("frame_sha256") or "") or None
            units.append(ExtractionUnit(ExtractionUnitType.VIDEO_KEYFRAME, len(units), frame.get("text"), {"frame_sha256":frame_sha,"byte_size":frame.get("byte_size"),"visual_descriptor":frame.get("visual_descriptor")}, float(frame.get("confidence",.9)), CitationAnchor(evidence_id=evidence_id,start_ms=int(frame["timestamp_ms"]),end_ms=int(frame["timestamp_ms"]),frame_index=frame_index,frame_sha256=frame_sha,source_locator={"kind":"keyframe","frame_index":frame_index,"frame_sha256":frame_sha})))
        return ExtractionBundle("configured-video-analyzer", "runtime", media_type, tuple(units))


class StructuredTextProcessor:
    def parse(self, path: Path, *, evidence_id: str, media_type: str) -> ExtractionBundle:
        text=path.read_text(encoding="utf-8", errors="replace")
        structured={}
        if media_type == "application/json":
            structured={"json": json.loads(text)}; text=None
        return ExtractionBundle("structured-text", "1", media_type, (ExtractionUnit(ExtractionUnitType.TEXT if text else ExtractionUnitType.METADATA,0,text,structured,1.0,CitationAnchor(evidence_id=evidence_id)),))


class ProcessorRouter:
    def __init__(self, *, pdf=None, image=None, audio=None, video=None, structured=None):
        self.pdf=pdf or PdfProcessor(); self.image=image or ImageOcrProcessor(); self.audio=audio or AudioProcessor(); self.video=video or VideoProcessor(); self.structured=structured or StructuredTextProcessor()
    def select(self, media_type: str) -> MediaProcessor:
        if media_type == "application/pdf": return self.pdf
        if media_type.startswith("image/"): return self.image
        if media_type.startswith("audio/"): return self.audio
        if media_type.startswith("video/"): return self.video
        if media_type in {"application/json","text/csv","text/plain"}: return self.structured
        raise UnsupportedMedia(media_type)
