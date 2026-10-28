"""
转录数据解析器模块

负责解析来自不同ASR（自动语音识别）服务商的JSON输出格式。
支持 ElevenLabs、Whisper、Deepgram、AssemblyAI、Gemini Transcribe 等多种数据源。
提供统一的接口将不同格式的转录数据转换为内部标准格式。

作者: fuxiaomoke
版本: 0.2.2.0
"""

from typing import List, Optional, Literal
import re
import traceback
# Corrected import: removed 'src.' prefix, or use relative if preferred for sibling modules
from core.data_models import TimestampedWord, ParsedTranscription
# from .data_models import TimestampedWord, ParsedTranscription # Alternative using relative import


class TranscriptionParser:
    """解析来自不同ASR服务商的JSON输出。"""
    def __init__(self, signals_forwarder=None):
        self._signals = signals_forwarder # 用于日志输出的信号转发器

    def log(self, message):
        """记录日志消息。"""
        if self._signals and hasattr(self._signals, 'log_message') and hasattr(self._signals.log_message, 'emit'):
            self._signals.log_message.emit(f"[Parser] {message}")
        else:
            print(f"[Parser] {message}") # 如果没有信号转发器，则打印到控制台

    @staticmethod
    def is_gemini_transcribe(data) -> bool:
        """是否为 Gemini Transcribe 导出的 JSON（顶层 app 字段带 Gemini，且有 words 列表）。"""
        return (isinstance(data, dict) and "gemini" in str(data.get("app", "")).lower()
                and isinstance(data.get("words"), list))

    def parse(self, data: dict, source_format: Literal["elevenlabs", "whisper", "deepgram", "assemblyai", "soniox", "elevenlabs_api", "gemini"]) -> Optional[ParsedTranscription]:
        """
        解析JSON数据。
        :param data: 包含ASR结果的字典。
        :param source_format: JSON的来源格式。
        :return: 解析后的转录数据对象，或在失败时返回None。
        """
        # Gemini 的 JSON 和 ElevenLabs 长得很像，选错格式也能“解析成功”，但日文会被空格拆开、语言码也识别不了，
        # 所以只要认出是 Gemini Transcribe 的输出，就按 Gemini 格式解析
        if source_format != "gemini" and self.is_gemini_transcribe(data):
            self.log(f"检测到 Gemini Transcribe 输出（当前选择的是 {source_format}），自动改用 Gemini 格式解析。")
            source_format = "gemini"
        self.log(f"开始解析 {source_format.capitalize()} JSON...")
        result: Optional[ParsedTranscription] = None
        try:
            if source_format == "gemini": result = self._parse_gemini(data)
            elif source_format == "elevenlabs": result = self._parse_elevenlabs(data)
            elif source_format == "elevenlabs_api": result = self._parse_elevenlabs_api(data)
            elif source_format == "soniox": result = self._parse_soniox(data)
            elif source_format == "whisper": result = self._parse_whisper(data)
            elif source_format == "deepgram": result = self._parse_deepgram(data)
            elif source_format == "assemblyai": result = self._parse_assemblyai(data)
            else:
                self.log(f"错误: 不支持的 JSON 格式源 '{source_format}'")
                return None

            if result:
                self.log(f"{source_format.capitalize()} JSON 解析完成，得到 {len(result.words)} 个词。总文本长度: {len(result.full_text or '')} 字符。")
            else:
                self.log(f"{source_format.capitalize()} JSON 解析未能返回有效结果。")
            return result
        except Exception as e:
            self.log(f"解析 {source_format.capitalize()} JSON 时出错: {e}")
            self.log(traceback.format_exc())
            return None

    def _parse_elevenlabs(self, data: dict) -> Optional[ParsedTranscription]:
        """解析 ElevenLabs 格式的JSON。"""
        parsed_words: List[TimestampedWord] = []
        for word_info in data.get("words", []):
            text = word_info.get("text", word_info.get("word")) # 兼容 'text' 和 'word' 字段
            start = word_info.get("start")
            end = word_info.get("end")
            speaker = word_info.get("speaker_id", word_info.get("speaker")) # 兼容 'speaker_id' 和 'speaker'
            if text is not None and start is not None and end is not None:
                try:
                    parsed_words.append(TimestampedWord(str(text), float(start), float(end), str(speaker) if speaker else None))
                except ValueError:
                    self.log(f"警告: 跳过 ElevenLabs 词条，时间戳格式无效: {word_info}")
            else:
                self.log(f"警告: 跳过不完整的 ElevenLabs 词条: {word_info}")
        full_text = data.get("text", "") # 获取完整文本
        if not full_text and parsed_words:
            full_text = " ".join(word.text for word in parsed_words) # 如果没有完整文本，则从词语拼接
        language = data.get("language_code", data.get("language")) # 获取语言代码
        return ParsedTranscription(words=parsed_words, full_text=full_text, language_code=language)

    def _parse_whisper(self, data: dict) -> Optional[ParsedTranscription]:
        """解析 Whisper (OpenAI) 格式的JSON。"""
        parsed_words: List[TimestampedWord] = []
        whisper_words_list: list = []
        # Whisper 的词列表可能在顶层 "words" 或嵌套在 "segments" 下
        if "words" in data and isinstance(data["words"], list):
            whisper_words_list = data["words"]
        elif "segments" in data and isinstance(data["segments"], list):
            for segment in data.get("segments", []):
                if "words" in segment and isinstance(segment["words"], list):
                    whisper_words_list.extend(segment["words"])

        if not whisper_words_list: # 如果没有词列表，尝试获取仅有的完整文本
            full_text_only = data.get("text")
            if full_text_only:
                return ParsedTranscription(words=[], full_text=full_text_only, language_code=data.get("language"))
            self.log("错误: Whisper JSON 既无有效词列表也无顶层文本。")
            return None

        for word_info in whisper_words_list:
            text = word_info.get("word", word_info.get("text")) # 兼容 'word' 和 'text'
            start = word_info.get("start")
            end = word_info.get("end")
            if text is not None and start is not None and end is not None:
                try:
                    parsed_words.append(TimestampedWord(str(text), float(start), float(end)))
                except ValueError:
                    self.log(f"警告: 跳过 Whisper 词条，时间戳格式无效: {word_info}")
            else:
                self.log(f"警告: 跳过不完整的 Whisper 词条: {word_info}")
        full_text = data.get("text", "")
        if not full_text and parsed_words:
            full_text = " ".join(word.text for word in parsed_words)
        language = data.get("language")
        return ParsedTranscription(words=parsed_words, full_text=full_text, language_code=language)

    def _parse_deepgram(self, data: dict) -> Optional[ParsedTranscription]:
        """解析 Deepgram 格式的JSON。"""
        try:
            # 检查 Deepgram JSON 的预期结构
            if not (data.get("results") and data["results"].get("channels") and isinstance(data["results"]["channels"], list) and
                    len(data["results"]["channels"]) > 0 and data["results"]["channels"][0].get("alternatives") and
                    isinstance(data["results"]["channels"][0]["alternatives"], list) and len(data["results"]["channels"][0]["alternatives"]) > 0):
                self.log("错误: Deepgram JSON 结构不符合预期。")
                return None

            alternative = data["results"]["channels"][0]["alternatives"][0] # 通常取第一个 alternative
            if "words" not in alternative or not isinstance(alternative["words"], list): # 如果没有词列表
                full_text_only = alternative.get("transcript", "") # 尝试获取 "transcript"
                if full_text_only:
                    return ParsedTranscription(words=[], full_text=full_text_only, language_code=data["results"]["channels"][0].get("detected_language"))
                self.log("错误: Deepgram JSON 既无词列表也无 transcript。")
                return None

            parsed_words: List[TimestampedWord] = []
            for word_info in alternative.get("words", []):
                text = word_info.get("word", word_info.get("punctuated_word")) # 优先使用 "punctuated_word"
                start = word_info.get("start")
                end = word_info.get("end")
                speaker = word_info.get("speaker")
                if text is not None and start is not None and end is not None:
                    try:
                        parsed_words.append(TimestampedWord(str(text), float(start), float(end), str(speaker) if speaker else None))
                    except ValueError:
                        self.log(f"警告: 跳过 Deepgram 词条，时间戳格式无效: {word_info}")
                else:
                    self.log(f"警告: 跳过不完整的 Deepgram 词条: {word_info}")
            full_text = alternative.get("transcript", "")
            if not full_text and parsed_words:
                full_text = " ".join(word.text for word in parsed_words)
            language = data["results"]["channels"][0].get("detected_language")
            return ParsedTranscription(words=parsed_words, full_text=full_text, language_code=language)
        except (KeyError, IndexError) as e:
            self.log(f"错误: 解析 Deepgram JSON 时键或索引错误: {e}")
            return None

    def _parse_assemblyai(self, data: dict) -> Optional[ParsedTranscription]:
        """解析 AssemblyAI 格式的JSON。"""
        parsed_words: List[TimestampedWord] = []
        assemblyai_words_list: list = []
        # AssemblyAI 的词列表可能在顶层 "words" 或嵌套在 "utterances" 下
        if "words" in data and isinstance(data["words"], list):
            assemblyai_words_list = data["words"]
        elif "utterances" in data and isinstance(data["utterances"], list):
            for utterance in data["utterances"]:
                if "words" in utterance and isinstance(utterance["words"], list):
                    assemblyai_words_list.extend(utterance["words"])

        if not assemblyai_words_list:
            full_text_only = data.get("text")
            if full_text_only:
                return ParsedTranscription(words=[], full_text=full_text_only, language_code=data.get("language_code"))
            self.log("错误: AssemblyAI JSON 既无有效词列表也无顶层文本。")
            return None

        for word_info in assemblyai_words_list:
            text = word_info.get("text")
            start_ms = word_info.get("start")
            end_ms = word_info.get("end")
            speaker = word_info.get("speaker")
            # AssemblyAI 时间戳以毫秒为单位，需要转换
            if text is not None and start_ms is not None and end_ms is not None:
                try:
                    parsed_words.append(TimestampedWord(str(text), float(start_ms)/1000.0, float(end_ms)/1000.0, str(speaker) if speaker else None))
                except ValueError:
                    self.log(f"警告: 跳过 AssemblyAI 词条，时间戳或ID格式无效: {word_info}")
            else:
                self.log(f"警告: 跳过不完整的 AssemblyAI 词条: {word_info}")
        full_text = data.get("text", "")
        if not full_text and parsed_words:
            full_text = " ".join(word.text for word in parsed_words)
        language = data.get("language_code")
        return ParsedTranscription(words=parsed_words, full_text=full_text, language_code=language)

    def _parse_soniox(self, data: dict) -> Optional[ParsedTranscription]:
        """解析 Soniox 格式的JSON。"""
        parsed_words: List[TimestampedWord] = []
        try:
            # [修复] 更宽容的解析逻辑：如果tokens不存在，不要直接返回None
            tokens = data.get("tokens", [])
            
            if not tokens:
                # 打印当前JSON的所有顶级键，方便调试
                keys = list(data.keys())
                self.log(f"警告: Soniox JSON 中没有找到 'tokens' 列表。可用键: {keys}")
                
                # 如果没有tokens但状态是completed，可能是空转录
                if data.get("status") == "completed":
                    self.log("提示: 任务状态为 completed 但无 tokens，将视为空转录处理。")
                    return ParsedTranscription(words=[], full_text="", language_code=None)
                
                return None

            for token in tokens:
                text = token.get("text", "")
                start_ms = token.get("start_ms")
                end_ms = token.get("end_ms")
                speaker = token.get("speaker")
                confidence = token.get("confidence")
                is_final = token.get("is_final", False)

                # 只处理最终的tokens，避免重复 (Soniox实时流可能有非最终token，文件转录通常都是最终)
                # 但为了保险，如果有is_final字段且为False，则跳过
                if "is_final" in token and not is_final:
                    continue

                if text and start_ms is not None and end_ms is not None:
                    try:
                        # Soniox 时间戳为毫秒，需要转换为秒
                        start_time = float(start_ms) / 1000.0
                        end_time = float(end_ms) / 1000.0

                        parsed_words.append(TimestampedWord(
                            text=str(text),
                            start_time=start_time,
                            end_time=end_time,
                            speaker_id=str(speaker) if speaker else None,
                            confidence=float(confidence) if confidence is not None else 1.0
                        ))
                    except ValueError as e:
                        self.log(f"警告: 跳过 Soniox token，时间戳格式无效: {token}")
                else:
                    # 没有时间戳的token（如翻译token）可能用于其他用途，这里跳过
                    pass

            # 构建完整文本
            full_text = data.get("text", "")
            if not full_text and parsed_words:
                full_text = " ".join(word.text for word in parsed_words)

            # 尝试从token中检测主要语言
            language = None
            if tokens:
                # 找到第一个有语言标记的token
                for token in tokens:
                    if "language" in token:
                        language = token["language"]
                        break

            self.log(f"Soniox 解析完成: {len(parsed_words)} 个词，语言: {language or '未知'}")

            # 提取 soniox_metadata（如果存在）
            soniox_metadata = data.get("soniox_metadata")

            return ParsedTranscription(words=parsed_words, full_text=full_text, language_code=language, soniox_metadata=soniox_metadata)

        except (KeyError, IndexError, TypeError) as e:
            self.log(f"错误: 解析 Soniox JSON 时出现异常: {e}")
            traceback.print_exc()
            return None

    @staticmethod
    def _join_words(parts: List[str]) -> str:
        """把词拼回整段：拉丁字母/数字之间补空格，中日韩直接相连（不会把日文拆成「起き ちゃっ た」）。"""
        def latin(ch: str) -> bool:
            return bool(ch) and ch.isascii() and ch.isalnum()
        out = ""
        for p in parts:
            if not p:
                continue
            if not out:
                out = p.lstrip()
            elif p[:1].isspace() or out[-1:].isspace():
                out += p
            elif latin(out[-1]) and latin(p[0]):
                out += " " + p
            else:
                out += p
        return re.sub(r"\s+", " ", out).strip()

    @staticmethod
    def _normalize_language(code) -> Optional[str]:
        """BCP-47 → 下游能识别的短码：ja-JP → ja，ko-KR → ko，en-US → en；中文保留 zh-xx（下游按 zh 前缀判断）。"""
        if not code:
            return None
        code = str(code).strip().replace("_", "-").lower()
        if code.startswith("zh"):
            return code
        return code.split("-")[0] or None

    def _parse_gemini(self, data: dict) -> Optional[ParsedTranscription]:
        """解析 Gemini Transcribe 导出的 JSON。

        结构：顶层 words[]（text / start / end / speaker / chunk，时间单位秒），
        另有句级 segments[]、language（如 "ja-JP"）、speakers、failures（转录失败的分块）。
        断句交给 LLM，所以这里只取逐词时间戳；segments 仅在没有 words 时兜底。"""
        parsed_words: List[TimestampedWord] = []
        skipped = 0
        for word_info in data.get("words", []) or []:
            if not isinstance(word_info, dict):
                skipped += 1
                continue
            text = word_info.get("text", word_info.get("word"))
            start, end = word_info.get("start"), word_info.get("end")
            speaker = word_info.get("speaker", word_info.get("speaker_id"))
            if text is None or not str(text).strip() or start is None or end is None:
                skipped += 1
                continue
            try:
                s, e = float(start), float(end)
            except (TypeError, ValueError):
                skipped += 1
                continue
            # Gemini 的时间戳是 0.1 秒精度，偶尔有 end == start 甚至略早的情况，这里保证不倒挂
            parsed_words.append(TimestampedWord(str(text), s, max(s, e), str(speaker) if speaker is not None else None))
        if skipped:
            self.log(f"警告: 跳过 {skipped} 个不完整的 Gemini 词条。")

        if not parsed_words:
            # 没有逐词时间戳时，退而用句级 segments（每句当作一个“词”，仍可生成字幕，只是切分粒度粗）
            for seg in data.get("segments", []) or []:
                try:
                    text = str(seg.get("text", "")).strip()
                    if text:
                        s = float(seg["start"]); e = float(seg["end"])
                        parsed_words.append(TimestampedWord(text, s, max(s, e)))
                except (KeyError, TypeError, ValueError):
                    continue
            if parsed_words:
                self.log("警告: Gemini JSON 没有逐词时间戳，改用句级 segments，字幕时间精度会降低。")
            else:
                self.log("错误: Gemini JSON 中既没有 words 也没有可用的 segments。")
                return None

        parsed_words.sort(key=lambda w: w.start_time)
        failures = data.get("failures") or []
        if failures:
            self.log(f"警告: Gemini 转录有 {len(failures)} 个分块失败，对应时间段可能没有字幕: {failures}")

        full_text = data.get("text") or self._join_words([w.text for w in parsed_words])
        language = self._normalize_language(data.get("language") or data.get("language_code"))
        speakers = {w.speaker_id for w in parsed_words if w.speaker_id}
        self.log(f"Gemini 解析完成: {len(parsed_words)} 个词，语言: {language or '未知'}，"
                 f"说话人: {len(speakers) or 1}，模型: {data.get('model', '未知')}")
        return ParsedTranscription(words=parsed_words, full_text=full_text, language_code=language)

    def _parse_elevenlabs_api(self, data: dict) -> Optional[ParsedTranscription]:
        """解析 ElevenLabs 官方API 格式的JSON。"""
        parsed_words: List[TimestampedWord] = []
        try:
            # ElevenLabs API 的格式与Web版基本相同，都在 words 数组中
            words = data.get("words", [])
            if not words:
                self.log("错误: ElevenLabs API JSON 中没有找到 words 数组")
                return None

            for word_info in words:
                # 支持不同的字段名
                text = word_info.get("text") or word_info.get("word", "")
                start_time = word_info.get("start")
                end_time = word_info.get("end")
                speaker_id = word_info.get("speaker_id") or word_info.get("speaker")
                word_type = word_info.get("type", "")

                if text and start_time is not None and end_time is not None:
                    try:
                        # 过滤掉音频事件，或者保留它们用于后续处理
                        if word_type == "audio_event":
                            # 保留音频事件，但不作为词处理
                            pass

                        parsed_words.append(TimestampedWord(
                            text=str(text),
                            start_time=float(start_time),
                            end_time=float(end_time),
                            speaker_id=str(speaker_id) if speaker_id else None
                        ))
                    except ValueError as e:
                        self.log(f"警告: 跳过 ElevenLabs API 词条，时间戳格式无效: {word_info}")

            # 构建完整文本
            full_text = data.get("text", "")
            if not full_text and parsed_words:
                # 只包含非音频事件的词来构建文本
                text_words = [w for w in parsed_words if not w.text.startswith("(") or not w.text.endswith(")")]
                full_text = " ".join(word.text for word in text_words)

            # 尝试获取语言代码
            language = data.get("language_code")

            self.log(f"ElevenLabs API 解析完成: {len(parsed_words)} 个词，语言: {language or '未知'}")
            return ParsedTranscription(words=parsed_words, full_text=full_text, language_code=language)

        except (KeyError, IndexError, TypeError) as e:
            self.log(f"错误: 解析 ElevenLabs API JSON 时出现异常: {e}")
            traceback.print_exc()
            return None