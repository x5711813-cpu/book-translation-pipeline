# Book Translation Pipeline

面向整本书翻译、审校与 EPUB 交付的 Codex 技能。支持文本 PDF、扫描 PDF 与 EPUB，强调可恢复处理、段落重建、注释和索引完整性、中文出版校对以及可审计的本地模型工作流。

## 安装

将本仓库复制到 Codex 技能目录：

```powershell
Copy-Item -Recurse -Force book-translation-pipeline "$env:USERPROFILE\.codex\skills\book-translation-pipeline"
```

重新启动或刷新 Codex 后，可显式调用 `$book-translation-pipeline`；符合描述的整书翻译任务也可自动触发。

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
python scripts/audit_manuscript.py --help
python path\to\skill-creator\scripts\quick_validate.py .
```

`audit_manuscript.py` 默认只让高置信度错误阻断交付；使用 `--strict` 时，警告与风格候选也会产生非零退出码。候选项必须联系上下文研判，不能为了清零报告而机械改写正文。

## 设计来源

中文校对检查器的分级诊断、Markdown 受保护区域、严格模式和回归测试思路，概念上参考了 MIT 许可的 [Tech-Doc-Style-Chinese](https://github.com/Fenng/tech-doc-style-chinese)。技术文档特有的引号与中西文空格规则没有直接移植；本技能采用中文译著的出版体例。

