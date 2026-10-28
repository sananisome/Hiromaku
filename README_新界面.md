# 治幕 新界面 · v7（唯一有效说明，取代之前所有 README）

> 解压前请先**删掉之前解压出来的 v1–v6 目录**。本包是完整交付：改动过的 14 个文件全在 `src/` 下（`ui/`、`ui/controllers/`、`core/`），没有别的地方还藏着新版本。

## 安装

**首选：直接覆盖。** 把包里的 `src/` 整个合并进项目的 `src/`，同名覆盖即可（只含改动过的 14 个文件）。
文件统一是 LF 行尾；项目的 `.gitattributes` 是 `* text=auto`，git 会自动处理，不会出现整文件 diff。

**可选：打补丁**（想逐行审改动时用）。`新界面-v7.patch` 是相对于你发我的那份源码（已含 v3）生成的纯 LF 补丁：

| 你的工作区行尾 | 命令 |
|---|---|
| LF | `git apply 新界面-v7.patch` 或 `patch -p1 < 新界面-v7.patch` |
| CRLF | `git apply --ignore-whitespace 新界面-v7.patch`（GNU `patch` 在 CRLF 文件上会失败） |

`src/main.py` 不用动（你那份已经有新旧界面切换和 GBK 保护）。切回旧界面：`set HEAL_JIMAKU_LEGACY_UI=1`。

## 文件清单

| 文件 | 作用 |
|---|---|
| `modern_main_window.py` | 新主窗口（继承原 `HealJimakuApp`，搬运原装控件 + 失败回退） |
| `subtitle_preview.py` / `subtitle_data.py` | 右侧放映区与预览用的 JSON / SRT 解析 |
| `theme_modern.py` | 新主题：主窗口 QSS + 给其它窗口换皮的调色板和同签名构建函数 |
| `theme.py` | 原主题，新增 30 个令牌（值与原字面量逐字相同）和 4 个函数 |
| 5 个对话框 + `main_window.py` | 字面量 → 令牌、字体 → `theme` 函数；背景设置修了红框；主窗口格式列表加 Gemini |
| `core/transcription_parser.py` | 新增 Gemini 解析与自动识别 |
| `conversion_worker.py` / `controllers/conversion_controller.py` | 识别到 Gemini 时纠正格式；文档字符串补 gemini |

## v7 改动：支持 Gemini Transcribe 输出的 JSON

**已经装过 v6 的话**，覆盖这 6 个文件即可（或 `git apply v6到v7增量.patch`）：
`core/transcription_parser.py`、`ui/conversion_worker.py`、`ui/controllers/conversion_controller.py`、
`ui/main_window.py`、`ui/modern_main_window.py`、`ui/subtitle_data.py`

- 格式列表新增 **Gemini**（主窗口格式标签里会多出一个）
- 新解析器 `_parse_gemini()`：读顶层 `words[]` 的逐词时间戳和说话人；没有 `words` 时退而用句级 `segments[]`
- 全文拼接按语种处理：日文 / 中文直接相连，拉丁字母之间才补空格（如果当成 ElevenLabs 解析，日文会被拼成「起き ちゃっ た」再交给 LLM 断句）
- 语言码 `ja-JP` → `ja`、`ko-KR` → `ko`、`en-US` → `en`，这样下游能选中对应语言的断句提示词（原来 `ja-JP` 认不出，会退回自动检测）
- `failures` 非空时在日志里提示哪些分块转录失败、对应时段可能缺字幕
- **选错格式也没关系**：识别到顶层 `"app": "Gemini Transcribe"` 时自动按 Gemini 解析，后续 SRT 处理也按 Gemini 走（基础处理 Mode A，不套 ElevenLabs 专用的时间修正）；新界面里选中或拖入这种 JSON，格式标签会自动切到 Gemini
- 用你发的样例实测：221 个词全部读到，语言识别为 `ja`，全文 443 字、无多余空格；预览区能正常播放原始碎片

## v6 改动：云端转录对话框支持拖拽选择音频

**已经装过 v5 的话，只需覆盖 `src/ui/cloud_transcription_dialog.py` 这一个文件**（或 `git apply v5到v6增量.patch`）。

- 音视频文件可以直接拖进**整个对话框**（不必瞄准输入框），松手即选中；拖动时「音频文件」分组显示虚线高亮，输入框提示「松手即可添加 N 个文件」
- 一次拖多个 → 自动进入批量模式；拖**文件夹** → 取文件夹第一层里的全部音视频（按文件名排序）
- 与「浏览」按钮共用同一段逻辑（新抽出 `_apply_selected_audio_files()`），批量模式下禁用台本导入等联动和以前一致
- 拖进来的东西里有不支持的格式会跳过并提示；全都不支持则不接收（光标显示禁止）
- 剧情设定、专有名词这些文本框本来就接受拖放：拖**音视频**到上面时由对话框接管，拖**普通文字**进去仍是原来的插入行为
- 支持格式与主窗口拖拽一致：mp3 wav flac m4a ogg opus aac webm mp4 mov；「浏览」的文件过滤器也补上了 opus / webm / mp4 / mov（原来漏了，主窗口拖视频进来能用，自己浏览却选不到）

## v5 改动（对应 v4 审查）

| 条目 | 处理 |
|---|---|
| I1 补丁行尾混杂 | 改成纯 LF 重新生成；在 LF 树上 `patch -p1` / `git apply`、在 CRLF 树上 `git apply --ignore-whitespace` 都实测通过 |
| I2 交付目录是旧版本 | 本包一次交付全部 11 个文件，README 合并成这一份 |
| I3 背景设置「图片丢失红框」从不显示 | 判断挪进 `_update_custom_ui_state()`：自定义图片模式下路径不存在就显示红框，悬停提示缺失路径；重新选图后恢复正常 |
| I4 「断句模型」卡片档案名被压成 "De…" | 档案名按内容定宽、不再压缩；模型名按剩余宽度中间省略（悬停看全名），空余交给末尾 stretch |
| I5 台本编辑弹窗变大 | 不是样式造成的：这个弹窗按**父窗口的 90%** 定尺寸。864×648 = 960×720 的 90%，1152×738 = 1280×820 的 90%，正好是旧 / 新主窗口的尺寸，说明测试脚本里拿主窗口当了父窗口。程序里只有两处会打开它，父窗口都是云端转录对话框，尺寸来自固定的 `DIALOG_SIZES`，两套主题下一样。所以没改代码；从云端转录对话框里打开时尺寸如果还不一样，再告诉我 |
| O1 全局字体 | 有意为之：只在新界面路径设置一次应用字体，让没指定字体的控件统一 |
| O2 换主题不可撤销 | 当前不需要：进程内不会从新界面切回旧界面。将来要做运行时切换主题时再补 |

## 还需要真机看的

- Gemini：选 Gemini 格式转换一次；再故意选 ElevenLabs 转换同一个文件，日志里应出现「自动改为 'gemini'」，结果一致

- 云端转录：拖单个文件、多个文件、文件夹、混入不支持的文件；拖到剧情设定文本框上；拖普通文字到文本框

- 背景设置：选「自定义图片作为固定背景」，填一个不存在的路径，重开对话框，应看到红框
- 主窗口「断句模型」卡片：档案名完整显示；很长的模型名中间省略
- 真实显示器上的字体和 DPI（offscreen 下字体全走 fallback）
- OCR 进行中按钮、台本导入「锁定」态、拖拽投递和批量的完整链路
