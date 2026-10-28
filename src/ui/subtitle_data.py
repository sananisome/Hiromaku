"""
subtitle_data.py —— 预览区用的轻量数据层（纯 Python，不依赖 Qt）

只服务于新界面的「放映区」预览，不参与真正的转换流程：
- 从各家 ASR 的 JSON 里尽量抽出逐词时间戳（ElevenLabs / Soniox / Whisper / Deepgram / AssemblyAI）
- 解析导出的 SRT
解析失败一律返回空列表，绝不抛异常影响主流程。
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any, Iterable, List, Optional, Sequence


@dataclass
class Span:
    text: str
    s: float
    e: float


# ---------------------------------------------------------------- 工具
def _num(v: Any) -> Optional[float]:
    if isinstance(v, bool):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _is_latin(ch: str) -> bool:
    return bool(ch) and ch.isascii() and ch.isalnum()


def smart_join(parts: Iterable[str]) -> str:
    """把词拼回一行：拉丁词之间补空格，CJK 直接相连。"""
    out = ""
    for p in parts:
        if not p:
            continue
        if not out:
            out = p.lstrip()
            continue
        if p[:1].isspace() or out[-1:].isspace():
            out += p
        elif _is_latin(out[-1]) and _is_latin(p[0]):
            out += " " + p
        else:
            out += p
    return re.sub(r"\s+", " ", out).strip()


def _from_items(items: Sequence[Any], text_keys: Sequence[str], s_key: str, e_key: str, scale: float) -> List[Span]:
    out: List[Span] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        if it.get("type") in ("spacing", "audio_event"):
            continue
        text = None
        for k in text_keys:
            v = it.get(k)
            if isinstance(v, str):
                text = v
                break
        if text is None or not text.strip():
            continue
        s, e = _num(it.get(s_key)), _num(it.get(e_key))
        if s is None or e is None:
            continue
        out.append(Span(text, s * scale, max(s, e) * scale))
    return out


def _clean(words: List[Span]) -> List[Span]:
    words = [w for w in words if not (w.text.startswith("<") and w.text.endswith(">"))]
    words.sort(key=lambda w: w.s)
    return words


def _merge_soniox(tokens: List[Span]) -> List[Span]:
    """Soniox 给的是子词 token：没有前导空格的拉丁 token 并回上一个词。"""
    merged: List[Span] = []
    for t in tokens:
        if merged and not t.text[:1].isspace() and _is_latin(merged[-1].text[-1:]) and _is_latin(t.text[:1]):
            m = merged[-1]
            merged[-1] = Span(m.text + t.text, m.s, t.e)
        else:
            merged.append(t)
    return merged


# ---------------------------------------------------------------- JSON
def extract_words(data: Any, _depth: int = 0) -> List[Span]:
    if _depth > 3:
        return []
    if isinstance(data, list):
        if data and isinstance(data[0], dict) and any(k in data[0] for k in ("words", "segments", "tokens", "results")):
            res: List[Span] = []
            for d in data:
                res += extract_words(d, _depth + 1)
            return _clean(res)
        data = {"words": data}
    if not isinstance(data, dict):
        return []

    # Soniox
    tokens = data.get("tokens")
    if isinstance(tokens, list) and tokens:
        toks = [t for t in tokens if not (isinstance(t, dict) and t.get("translation_status") == "translation")]
        w = _from_items(toks, ("text",), "start_ms", "end_ms", 0.001)
        if w:
            return _clean(_merge_soniox(w))

    # Deepgram
    res = data.get("results")
    if isinstance(res, dict):
        try:
            items = res["channels"][0]["alternatives"][0]["words"]
        except (KeyError, IndexError, TypeError):
            items = None
        if isinstance(items, list):
            w = _from_items(items, ("punctuated_word", "word", "text"), "start", "end", 1.0)
            if w:
                return _clean(w)

    # Whisper（segments[].words[]）
    segs = data.get("segments")
    if isinstance(segs, list):
        items = []
        for sg in segs:
            if isinstance(sg, dict) and isinstance(sg.get("words"), list):
                items += sg["words"]
        if items:
            w = _from_items(items, ("word", "text"), "start", "end", 1.0)
            if w:
                return _clean(w)

    # ElevenLabs / AssemblyAI（words[]，AssemblyAI 是毫秒整数）
    words = data.get("words")
    if isinstance(words, list) and words:
        dicts = [it for it in words if isinstance(it, dict)]
        starts = [it.get("start") for it in dicts if it.get("start") is not None]
        scale = 1.0
        if starts and all(isinstance(x, int) and not isinstance(x, bool) for x in starts):
            ends = [_num(it.get("end")) for it in dicts]
            ends = [x for x in ends if x is not None]
            if ends and max(ends) > 1000:
                scale = 0.001
        w = _from_items(dicts, ("text", "word", "punctuated_word"), "start", "end", scale)
        if w:
            return _clean(w)

    # 只有句级 segments 的 Whisper
    if isinstance(segs, list):
        w = _from_items(segs, ("text",), "start", "end", 1.0)
        if w:
            return _clean(w)

    # 常见的外层包装
    for k in ("transcription", "transcript", "result", "data", "response", "output"):
        v = data.get(k)
        if isinstance(v, (dict, list)):
            w = extract_words(v, _depth + 1)
            if w:
                return w
    return []


def load_words_from_json(path: str, max_bytes: int = 80 * 1024 * 1024) -> List[Span]:
    try:
        if not path or not os.path.isfile(path) or os.path.getsize(path) > max_bytes:
            return []
        with open(path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
        return extract_words(data)
    except Exception:
        return []


def sniff_json_source(path: str) -> Optional[str]:
    """只读文件开头 4KB，识别少数能确定来源的 JSON。目前只认 Gemini Transcribe（顶层 "app" 字段）。"""
    try:
        with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
            head = f.read(4096)
    except OSError:
        return None
    if re.search(r'"app"\s*:\s*"[^"]*gemini', head, re.IGNORECASE):
        return "gemini"
    return None


def build_raw_lines(words: Sequence[Span], window: float = 2.6) -> List[Span]:
    """模拟「没断句」的原始效果：按固定时长硬切，常常切在句子中间。"""
    lines: List[Span] = []
    buf: List[Span] = []
    for w in words:
        if buf and w.s - buf[0].s >= window:
            lines.append(Span(smart_join(x.text for x in buf), buf[0].s, buf[-1].e))
            buf = []
        buf.append(w)
    if buf:
        lines.append(Span(smart_join(x.text for x in buf), buf[0].s, buf[-1].e))
    return lines


# ---------------------------------------------------------------- SRT
_TC = re.compile(
    r"(\d+):(\d{1,2}):(\d{1,2})[,.](\d{1,3})\s*-->\s*(\d+):(\d{1,2}):(\d{1,2})[,.](\d{1,3})"
)


def _tc(h: str, m: str, s: str, ms: str) -> float:
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms.ljust(3, "0")) / 1000.0


def parse_srt(text: str) -> List[Span]:
    cues: List[Span] = []
    for block in re.split(r"\r?\n\s*\r?\n", text.strip()):
        lines = block.splitlines()
        for i, line in enumerate(lines):
            m = _TC.search(line)
            if not m:
                continue
            body = "\n".join(x.strip() for x in lines[i + 1:] if x.strip())
            body = re.sub(r"<[^>]+>|\{\\[^}]*\}", "", body)
            if body:
                g = m.groups()
                cues.append(Span(body, _tc(*g[:4]), _tc(*g[4:])))
            break
    cues.sort(key=lambda c: c.s)
    return cues


def load_srt(path: str) -> List[Span]:
    for enc in ("utf-8-sig", "utf-16", "gbk"):
        try:
            with open(path, "r", encoding=enc) as f:
                return parse_srt(f.read())
        except (UnicodeError, OSError):
            continue
    return []


def fmt_tc(sec: float) -> str:
    total_ms = int(max(0.0, sec) * 1000 + 0.5)   # 先整体四舍五入再拆分：1.9999 → 2.000，0.0005 → 0.001
    total_s, ms = divmod(total_ms, 1000)
    h, rem = divmod(total_s, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def fmt_short(sec: float) -> str:
    sec = max(0, int(round(sec)))
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"
