# Book Translation Pipeline

**语言：中文 | [English](README.en.md)**

面向整本书翻译、审校与 EPUB 交付的 Codex 技能。支持文本 PDF、扫描 PDF 与 EPUB，强调可恢复处理、段落重建、注释和索引完整性、中文出版校对以及可审计的本地模型工作流。

也支持对已有电子书独立执行**校对、分级目录生成/修复、格式重排**，无需重跑翻译。使用方法与边界见 [电子书整理流程](references/ebook-maintenance.md)。例如：“校对这本 EPUB，修复目录并统一正文和脚注排版。”

## 安装

建议使用 Python 3.12。文本 PDF 检查使用 `pypdf`；扫描 PDF 使用 `pypdfium2`、Pillow 和本地 RapidOCR。翻译服务使用项目自行配置的 Ollama 兼容 `/api/chat` 接口；本仓库不下载模型。图表重绘需要本机中文字体，或在视觉配置中指定 `font` 与 `font_bold`。

在 PowerShell 中安装依赖，并将仓库复制到 Codex 技能目录：

```powershell
git clone https://github.com/x5711813-cpu/book-translation-pipeline.git
cd book-translation-pipeline
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$skillDir = "$env:USERPROFILE\.codex\skills\book-translation-pipeline"
New-Item -ItemType Directory -Force $skillDir | Out-Null
Copy-Item -Force SKILL.md $skillDir
Copy-Item -Recurse -Force agents,assets,references,scripts $skillDir
```

安装后可继续使用克隆目录中的 `.venv` 运行脚本。重新启动或刷新 Codex 后，可显式调用 `$book-translation-pipeline`；符合描述的整书翻译任务也可自动触发。

在 macOS/Linux 上以 `python3.12 -m venv .venv` 创建环境，并用 `.venv/bin/python` 运行下面的命令。脚本处理的输入书籍应有合法使用权；本仓库不包含书籍内容。

## 最小使用示例

对已有 EPUB 做只读结构检查，不需要翻译模型：

```powershell
.\.venv\Scripts\python.exe scripts/ebook_tool.py audit --help
.\.venv\Scripts\python.exe scripts/ebook_tool.py audit "C:\books\input.epub" --output "C:\books\audit.json"
```

翻译 PDF 时，先初始化并检查来源，再编辑项目中的 `project.json` 配置章节和本地模型。扫描页才运行 OCR，随后重建语义块、解决边界、批准源版本、试译与审校，最后构建及审计。每一步的参数可用相应脚本的 `--help` 查看；完整顺序见 [翻译流程](references/workflow.md)，章节字段见 [数据契约](references/schemas.md#sections)。

```powershell
.\.venv\Scripts\python.exe scripts/init_project.py "C:\books\project" --source "C:\books\input.pdf" --title "示例书名" --model "your-local-model"
.\.venv\Scripts\python.exe scripts/inspect_source.py "C:\books\project"
.\.venv\Scripts\python.exe scripts/ocr_pdf.py "C:\books\project"
.\.venv\Scripts\python.exe scripts/build_blocks.py "C:\books\project"
.\.venv\Scripts\python.exe scripts/resolve_boundaries.py "C:\books\project" --dry-run
.\.venv\Scripts\python.exe scripts/approve_source.py "C:\books\project"
.\.venv\Scripts\python.exe scripts/translate_blocks.py "C:\books\project" --pilot
.\.venv\Scripts\python.exe scripts/build_epub.py "C:\books\project"
.\.venv\Scripts\python.exe scripts/audit_project.py "C:\books\project"
```

如果 `--dry-run` 列出待处理边界，先按 [人工或模型判定说明](references/workflow.md#3-reconstruct-the-source-book) 解决，再重建并批准源版本。`build_epub.py` 检查源批准状态、译文状态与缓存元数据；它生成的构建记录只表示文件已构建，最终交付还需 `audit_project.py` 和人工内容、版式检查。已有 EPUB 的独立整理见 [电子书整理流程](references/ebook-maintenance.md)。

## 仓库内容

- `SKILL.md`：技能入口、路由和不可破坏的工作约束。
- `scripts/`：初始化、源文件检查、OCR、语义块重建、翻译/审校、图表处理、EPUB 构建与质量审计程序。
- `references/`：工作流、数据契约、OCR、EPUB、中文出版校对和质量门槛。
- `assets/`：项目与 EPUB 样式模板。
- `agents/openai.yaml`：Codex 界面元数据。
- `CHANGELOG.md`：面向使用者的版本变化。
- `docs/iteration-history.md`：从真实项目中提炼出的设计演进及取舍。
- `docs/reuse-inventory.md`：可复用程序清单、输入输出和适用边界。

本仓库不包含原始 PDF、译文、模型缓存、项目报告或针对某一本书的硬编码修复规则。

## 验证

```powershell
python scripts/test_audit_manuscript.py
python scripts/test_ebook_tool.py
python scripts/test_translation_contracts.py
python scripts/test_pipeline_repairs.py
python scripts/audit_manuscript.py --help
python path\to\skill-creator\scripts\quick_validate.py .
```

`audit_manuscript.py` 默认只让高置信度错误阻断交付；使用 `--strict` 时，警告与风格候选也会产生非零退出码。候选项必须联系上下文研判，不能为了清零报告而机械改写正文。

本仓库按 [MIT 许可证](LICENSE) 开源。OCR 缓存依赖来源、页码、参数、脚本版本和输出文件哈希。复杂公式、多栏、注释、图表与视觉排版仍需人工检查；自动测试与基础 EPUB 审计不能代替逐页出版验收。

## 设计来源

中文校对检查器的分级诊断、Markdown 受保护区域、严格模式和回归测试思路，概念上参考了 MIT 许可的 [Tech-Doc-Style-Chinese](https://github.com/Fenng/tech-doc-style-chinese)。技术文档特有的引号与中西文空格规则没有直接移植；本技能采用中文译著的出版体例。
