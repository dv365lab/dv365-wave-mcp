> **本文件由《芯片验证日记》整理分享，仅供学习交流使用。**
>
> - 公众号 / 视频号：**芯片验证日记**
> - 知识星球：**7833526** —— 一年 365 天答疑，为您的工作和学习保驾护航！
> - 已成功指导 **200+** 位芯片同行求职上岸、收获满意 Offer；提供**求职套餐 / 职业规划**服务，欢迎微信：DV365-DV_Daily。

---

# 将 wave-mcp 作为 Agent Skill 使用

同一份 `wave-mcp` 技能支持 Claude Code、Codex，以及支持 [Agent Skills 标准](https://agentskills.io/specification) 且能执行本地命令的其他 agent。技能通过项目原有 CLI 调用分析能力，无需先注册 MCP；已有 MCP 连接也可以直接使用。

## 打包

在本仓库运行（只需要 Python 3.10+ 和 Git，不需要安装波形分析依赖）：

```bash
python deploy/build_skill.py
```

生成：

```text
dist/skills/wave-mcp-<项目版本>.zip
dist/skills/wave-mcp-<项目版本>.skill
```

两者内容相同，均为 ZIP。优先使用 `.zip` 解压安装；只有明确接受 `.skill` 的工具才使用该扩展名，不代表所有 agent 都能直接导入 `.skill`。

压缩包只有一个顶层目录：

```text
wave-mcp/
  .gitignore
  SKILL.md
  LICENSE
  agents/openai.yaml
  scripts/setup_runtime.py
  scripts/wave.py
  references/setup.md
  references/workflows.md
  assets/wave-mcp-source.zip
```

源码快照来自当前工作区中 Git 已跟踪的项目源码、部署脚本、文档和许可文件，保留本仓库的 SHM/VWDB 支持。已跟踪文件的未提交修改也会包含；新增项目源文件应先纳入 Git 跟踪。包内不含虚拟环境、仿真波形、测试产物、商业库或本地构建的二进制，也不依赖原仓库的绝对路径。

## 安装到 agent

将压缩包中的整个 `wave-mcp/` 目录放到目标技能目录，保持目录名与 `SKILL.md` 中的 `name` 一致：

| Agent | 当前项目使用 | 所有项目使用 | 显式调用 |
| --- | --- | --- | --- |
| Claude Code | `.claude/skills/wave-mcp/` | `~/.claude/skills/wave-mcp/` | `/wave-mcp` |
| Codex | `.agents/skills/wave-mcp/` | `~/.agents/skills/wave-mcp/` | `$wave-mcp` |
| 其他 Agent Skills 兼容 agent | 按该工具文档配置技能目录 | 按该工具文档配置 | 按该工具的技能调用方式 |

以上目录与调用方式参考 [Claude Code 官方文档](https://code.claude.com/docs/en/skills) 和 [Codex 官方文档](https://learn.chatgpt.com/docs/build-skills)。旧版或定制 Codex 可能使用 `~/.codex/skills/`，以当前客户端实际扫描的目录为准，不要在多个目录重复安装同名技能。

例如 Linux/macOS 下，将生成的 ZIP 解压到个人技能目录：

```bash
# Claude Code
mkdir -p ~/.claude/skills
unzip dist/skills/wave-mcp-1.1.1.zip -d ~/.claude/skills

# Codex
mkdir -p ~/.agents/skills
unzip dist/skills/wave-mcp-1.1.1.zip -d ~/.agents/skills
```

文件名中的版本号以实际产物为准。已有同名安装时先检查其内容，避免覆盖本地定制。Windows 也可以用解压工具将 `wave-mcp` 文件夹放到用户主目录下相应位置。

## 安装运行环境

推荐在 **Linux x86_64、glibc >= 2.28、Python 3.10–3.13** 环境运行。在放置好技能目录后，以实际路径执行：

```bash
python /absolute/path/to/wave-mcp/scripts/setup_runtime.py
python /absolute/path/to/wave-mcp/scripts/wave.py query --list
```

安装脚本在技能目录建立独立 `.venv`，从包内源码安装，再检查工具发现。Python 依赖通常需要联网下载。该包是**包含源码的技能包**，不等同于携带 Python、依赖 wheel 和转换器的完全离线包。已有离线 bundle 或其他已安装环境时，可将 `WAVE_MCP_PYTHON` 设为该环境 Python 的绝对路径，并保留已有库路径等环境设置，无需再运行安装脚本。

Windows/macOS 上 `pylibfst` 可能需要 CMake、C/C++ 编译器和 zlib 才能源码安装。技能格式跨 agent 通用，不代表底层原生依赖在每个平台都开箱即用；缺少构建环境时可使用已部署好的 Linux/WSL 环境。转换和查看器的额外依赖见技能内的 [setup.md](../skills/wave-mcp/references/setup.md)，完全离线部署见 [DEPLOY_AIRGAP.md](DEPLOY_AIRGAP.md)。

若直接使用仓库里的 `skills/wave-mcp/`，安装脚本会找到本仓库作为源码。若只复制该子目录到别处，需要 `--source /path/to/dv365-wave-mcp` 指定源码；分发 ZIP 自带快照，无此要求。

## 使用示例

Claude Code：

```text
/wave-mcp 分析 sim/waves.shm，顶层 tb，filelist 是 rtl.f。
请定位 tb.u_dut.result 在 250ns 变成 X 的原因，并给出波形和源码证据。
```

Codex：

```text
$wave-mcp 对比 sim/pass.fst 和 sim/fail.fst，只检查 tb.u_dut，按 tb.clk 对齐，定位首次分歧。
```

无波形的 RTL 分析：

```text
使用 wave-mcp 分析 rtl.f，顶层 uart_top，找出 uart_top.u_tx.tx_serial 的驱动和两层扇入。
```

安装技能不会自动修改 MCP 配置。大量查询、交互式查看器适合持久 MCP 服务，具体配置见技能内的 `references/setup.md`。普通 CLI 查询每次是新进程，应保存返回的 `session_path`，在后续命令传入 `--session`。

## 维护与验证

技能说明和脚本的唯一维护位置是 `skills/wave-mcp/`；重新运行打包脚本更新分发物，无需复制项目源码到技能目录。

```bash
python -m unittest discover -s tests/skills -v
python deploy/build_skill.py
```

独立测试覆盖压缩包结构与源码完整性、解压后搬迁、私有环境安装命令、CLI 参数/工作目录/退出码透传和缺依赖提示。它们不依赖 `pylibfst`，也不能替代受支持环境中的真实波形回归。解压出的 `assets/wave-mcp-source.zip` 可单独通过 pip 构建安装，用于进一步验证交付快照。
