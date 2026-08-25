# 可复用程序清单

## 项目与源文件

| 程序 | 用途 | 主要产物 |
| --- | --- | --- |
| `scripts/init_project.py` | 从模板初始化独立项目目录 | `project.json` 与工作目录 |
| `scripts/inspect_source.py` | 判断 PDF/EPUB 的文字层、页面和图像特征 | 源文件检查报告 |
| `scripts/extract_epub_blocks.py` | 从 EPUB 提取结构化文本块 | 块级 JSONL |

## OCR、段落与版面

| 程序 | 用途 | 主要产物 |
| --- | --- | --- |
| `scripts/ocr_pdf.py` | 对扫描页执行本地 OCR 并保留置信度 | 页级 OCR 数据 |
| `scripts/build_blocks.py` | 跨页重建稳定语义块 | 带来源和哈希的块记录 |
| `scripts/resolve_boundaries.py` | 裁决不确定的段落边界 | 可审计的边界决定 |
| `scripts/extract_visuals.py` | 按配置提取图表区域 | 图像与清单 |
| `scripts/render_visuals.py` | 本地化并重绘数据型图表 | 中文图表资源 |

## 翻译与构建

| 程序 | 用途 | 主要产物 |
| --- | --- | --- |
| `scripts/translate_blocks.py` | 调用本地 OpenAI 兼容模型进行可恢复翻译和审校 | 翻译 JSONL 与状态记录 |
| `scripts/build_epub.py` | 用已批准块和模板构建 EPUB | 可重复构建的 EPUB |
| `scripts/common.py` | 共享 JSON、哈希和路径辅助函数 | 供其他程序导入 |

## 审计

| 程序 | 用途 | 主要产物 |
| --- | --- | --- |
| `scripts/audit_manuscript.py` | 检查 Markdown 正文、注释、数字、标点、引号和外文残留候选 | 分级 JSON 报告 |
| `scripts/audit_project.py` | 检查项目状态、块完整性和 EPUB 不变量 | 项目质量报告 |
| `scripts/test_audit_manuscript.py` | 防止校对规则升级造成回归 | 单元测试结果 |

## 复用边界

- 所有程序先运行 `--help`，再根据项目配置调用。
- 输入输出契约见 `references/schemas.md`；不要依赖某一本书的目录名。
- 需要本地模型的程序应记录模型标识、提示词哈希、内容哈希和失败状态。
- 项目目录中的一次性修复脚本只有在移除固定路径、固定书名和个案规则，并补充测试后，才可提升到本清单。

