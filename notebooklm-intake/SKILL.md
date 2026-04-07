---
name: notebooklm-intake
description: 将本地资料上传、导入并同步到云端 NotebookLM 项目。用于当用户说“上传到 NotebookLM”“导入 NotebookLM”“把资料发到云端”“新建 NotebookLM 项目并入库资料”“把本地文件同步到 NotebookLM”等场景时触发。默认把这类请求理解为入库/上传，而不是生成输出；适用于扫描 knowledge/notebooklm/inbox 中新增的链接、PDF、音视频、文档、表格等资料，自动创建同名项目、上传 source，并写入本地 metadata。
---

# NotebookLM 入库

使用脚本优先，不要在对话里手动拼流程。

## 固定目录

脚本会自动检测 `.openclaw` 根目录，无需手动配置。以下为相对结构：

- 输入目录：`{.openclaw根}/knowledge/notebooklm/inbox`
- 项目目录：`{.openclaw根}/knowledge/notebooklm/projects`
- 输出目录：`{.openclaw根}/knowledge/notebook`
- 状态索引：`{.openclaw根}/knowledge/notebooklm/registry.json`

## 执行原则

1. 默认把“上传 / 导入 / 入库 / 同步到 NotebookLM”理解为**把本地资料送到云端**，优先走本 skill。
2. 不要把“生成 / 制作 / 产出 / 导出 / 输出某个 NotebookLM 项目内容”误判成 intake；这类请求默认应走 `notebooklm-output`。
3. 先运行脚本扫描 inbox 新文件。
4. 为每个新文件生成本地项目 metadata。
5. 当前阶段如果尚未完成真实云端接入，允许先写本地占位状态，但必须明确告诉用户“脚本骨架已完成，云端上传待接通”。
6. 不要假装已经上传成功；只有脚本返回成功且 metadata 明确记录 notebook_id/source_id 时，才能说已入库云端。

## 标准命令

> 脚本路径相对于本 SKILL.md 所在目录。执行时请用本 skill 目录下的实际绝对路径。

```powershell
python "{本skill目录}/scripts/intake.py"
```

如需指定单个文件，可用：

```powershell
python "{本skill目录}/scripts/intake.py" --path "<文件或目录>"
```

## 输出要求

简洁汇报：
- 新识别了哪些文件
- 哪些已写入 metadata
- 哪些已真正上传云端 / 哪些仍是待接通状态
- 对应项目目录在哪里
