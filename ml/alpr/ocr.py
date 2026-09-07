"""License-plate OCR with PaddleOCR 2.x/3.x and EasyOCR fallback."""

import inspect
import re
from dataclasses import dataclass
from enum import Enum

import cv2
import numpy as np
from loguru import logger

try:
    from paddleocr import PaddleOCR
except ImportError:
    PaddleOCR = None

try:
    import easyocr
except ImportError:
    easyocr = None


class OCREngine(Enum):
    PADDLEOCR = "paddleocr"
    EASYOCR = "easyocr"


@dataclass
class OCRResult:
    text: str
    raw_text: str
    confidence: float
    char_details: list[dict]
    engine_used: str
    is_valid_format: bool


class PlateFormat:
    PATTERNS = [
        r"^[A-Z]{1,2}\s?[0-9]{1,4}\s?[A-Z]{1,3}$",
        r"^[A-Z]{1,2}\s?[0-9]{1,4}$",
    ]
    CHAR_CORRECTIONS = {"O": "0", "I": "1", "S": "5", "B": "8", "Z": "2", "G": "6"}


class PlateOCR:
    def __init__(self, engine: str = "paddleocr", lang: str = "en",
                 confidence_threshold: float = 0.5, enable_postprocessing: bool = True):
        self.engine_type = OCREngine(engine)
        self.confidence_threshold = confidence_threshold
        self.enable_postprocessing = enable_postprocessing
        self.ocr_engine = self._init_engine(lang)
        logger.info(f"PlateOCR siap | engine={self.engine_type.value} | conf={confidence_threshold}")

    def _init_engine(self, lang: str):
        if self.engine_type == OCREngine.PADDLEOCR:
            if PaddleOCR is None:
                if easyocr is None:
                    raise ImportError("PaddleOCR/EasyOCR tidak terinstall")
                logger.warning("PaddleOCR tidak tersedia, fallback ke EasyOCR")
                self.engine_type = OCREngine.EASYOCR
                return self._init_easyocr(lang)

            # PaddleOCR 2.x uses the legacy constructor; PaddleOCR 3.x uses
            # the newer pipeline flags. Try legacy first for compatibility with
            # the project's existing environments, then fall back to 3.x API.
            try:
                return PaddleOCR(
                    use_angle_cls=False,
                    lang=lang,
                    show_log=False,
                    use_gpu=False,
                    det_db_box_thresh=0.3,
                    rec_batch_num=1,
                )
            except (TypeError, ValueError):
                kwargs = {
                    "use_doc_orientation_classify": False,
                    "use_doc_unwarping": False,
                    "use_textline_orientation": False,
                }
                # Keep only arguments supported by the installed constructor.
                try:
                    params = inspect.signature(PaddleOCR).parameters
                    kwargs = {k: v for k, v in kwargs.items() if k in params}
                    if "lang" in params:
                        kwargs["lang"] = lang
                    return PaddleOCR(**kwargs)
                except Exception as exc:
                    logger.exception(f"Gagal inisialisasi PaddleOCR: {exc}")
                    if easyocr is None:
                        raise
                    self.engine_type = OCREngine.EASYOCR
                    return self._init_easyocr(lang)

        if self.engine_type == OCREngine.EASYOCR:
            return self._init_easyocr(lang)
        raise ValueError(f"Engine tidak dikenal: {self.engine_type}")

    def _init_easyocr(self, lang: str):
        if easyocr is None:
            raise ImportError("EasyOCR tidak terinstall. Jalankan: pip install easyocr")
        return easyocr.Reader([lang], gpu=False)

    def read(self, image: np.ndarray) -> OCRResult:
        if image is None or image.size == 0:
            return OCRResult("", "", 0.0, [], self.engine_type.value, False)
        try:
            if self.engine_type == OCREngine.PADDLEOCR:
                raw_result = self._read_paddleocr(image)
            else:
                raw_result = self._read_easyocr(image)
            raw_text, confidence, details = self._parse_ocr_result(raw_result)
            text = self._postprocess(raw_text) if self.enable_postprocessing else raw_text
            return OCRResult(text, raw_text, confidence, details,
                             self.engine_type.value, self._validate_plate_format(text))
        except Exception as exc:
            # OCR failure must never crash the gate loop.
            logger.exception(f"OCR error: {exc}")
            return OCRResult("", "", 0.0, [], self.engine_type.value, False)

    def _read_paddleocr(self, image: np.ndarray):
        try:
            h, w = image.shape[:2]
            if w < 300:
                scale = 300 / max(w, 1)
                image = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
            if hasattr(self.ocr_engine, "predict"):
                return list(self.ocr_engine.predict(image))
            return self.ocr_engine.ocr(image, cls=False)
        except Exception as exc:
            logger.error(f"PaddleOCR error: {exc}")
            return []

    def _read_easyocr(self, image: np.ndarray):
        try:
            return self.ocr_engine.readtext(image)
        except Exception as exc:
            logger.error(f"EasyOCR error: {exc}")
            return []

    @staticmethod
    def _result_to_dict(item):
        if isinstance(item, dict):
            return item.get("res", item)
        try:
            value = item.json
            if callable(value):
                value = value()
            if isinstance(value, str):
                import json
                value = json.loads(value)
            if isinstance(value, dict):
                return value.get("res", value)
        except Exception:
            pass
        return None

    def _parse_ocr_result(self, result):
        if not result:
            return "", 0.0, []
        texts, confidences, details = [], [], []

        # PaddleOCR 3.x structured result: rec_texts / rec_scores / rec_polys.
        for item in result if isinstance(result, list) else [result]:
            data = self._result_to_dict(item)
            if data and "rec_texts" in data:
                rec_texts = data.get("rec_texts") or []
                rec_scores = data.get("rec_scores") or []
                rec_boxes = data.get("rec_boxes", data.get("rec_polys", [])) or []
                for i, text in enumerate(rec_texts):
                    conf = float(rec_scores[i]) if i < len(rec_scores) else 0.0
                    texts.append(str(text))
                    confidences.append(conf)
                    details.append({"text": str(text), "confidence": conf,
                                    "bbox": rec_boxes[i] if i < len(rec_boxes) else None})
                continue

            # PaddleOCR 2.x: [[bbox, (text, confidence)], ...]
            if isinstance(item, list):
                for detection in item:
                    if not isinstance(detection, (list, tuple)) or len(detection) < 2:
                        continue
                    bbox, text_conf = detection[0], detection[1]
                    if isinstance(text_conf, (list, tuple)) and len(text_conf) >= 2:
                        text, conf = str(text_conf[0]), float(text_conf[1])
                    else:
                        text, conf = str(text_conf), 1.0
                    texts.append(text)
                    confidences.append(conf)
                    details.append({"text": text, "confidence": conf, "bbox": bbox})

        # EasyOCR: [(bbox, text, confidence), ...]
        if not texts and isinstance(result, list):
            for detection in result:
                if isinstance(detection, (list, tuple)) and len(detection) >= 3:
                    bbox, text, conf = detection[:3]
                    texts.append(str(text))
                    confidences.append(float(conf))
                    details.append({"text": str(text), "confidence": float(conf), "bbox": bbox})

        avg = sum(confidences) / len(confidences) if confidences else 0.0
        return " ".join(texts), avg, details

    def _postprocess(self, text: str) -> str:
        text = str(text).upper()
        text = re.sub(r"\d{2}[.\-]\d{2}", " ", text)
        text = re.sub(r"[^A-Z0-9\s]", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            return ""

        parts = text.split()
        # If OCR already separated the plate, correct characters by semantic
        # position: prefix letters, number digits, suffix letters.
        if len(parts) >= 2:
            prefix = "".join(PlateFormat.CHAR_CORRECTIONS.get(c, c) if c.isdigit() else c
                              for c in parts[0])
            number = "".join(PlateFormat.CHAR_CORRECTIONS.get(c, c) if c.isalpha() else c
                              for c in parts[1])
            suffix = "".join(c if c.isalpha() else PlateFormat.CHAR_CORRECTIONS.get(c, c)
                              for c in "".join(parts[2:]))
            if prefix and number:
                return f"{prefix} {number}" + (f" {suffix}" if suffix else "")

        raw = text.replace(" ", "")
        match = re.search(r"([A-Z]{1,2})(\d{1,4})([A-Z]{1,3})", raw)
        if match:
            return " ".join(match.groups())
        match = re.search(r"([A-Z]{1,2})(\d{1,4})", raw)
        if match:
            return f"{match.group(1)} {match.group(2)}"
        return text

    @staticmethod
    def _validate_plate_format(text: str) -> bool:
        text = re.sub(r"\s+", " ", text).strip()
        return any(re.fullmatch(pattern, text) for pattern in PlateFormat.PATTERNS)
