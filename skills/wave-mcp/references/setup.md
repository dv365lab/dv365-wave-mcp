> **本文件由《芯片验证日记》整理分享，仅供学习交流使用。**
>
> - 公众号 / 视频号：**芯片验证日记**
> - 知识星球：**7833526** —— 一年 365 天答疑，为您的工作和学习保驾护航！
> - 已成功指导 **200+** 位芯片同行求职上岸、收获满意 Offer；提供**求职套餐 / 职业规划**服务，欢迎微信：DV365-DV_Daily。

---

# Runtime setup and agent integration

## Install the runtime

Use Python 3.10+; the project has tested 3.10–3.13. Linux x86_64 with glibc >= 2.28 is the recommended runtime. This skill does not supply Python, native wheels, conversion executables, commercial EDA tools, or viewer binaries.

After installing the complete skill folder, run with the desired Python interpreter:

```bash
python "/absolute/path/to/wave-mcp/scripts/setup_runtime.py"
python "/absolute/path/to/wave-mcp/scripts/wave.py" query --list
```

`setup_runtime.py` creates `.venv` inside the skill, installs the bundled source snapshot with pip, and checks tool discovery. It does not activate the environment, install a global package, or change agent configuration. Running it again installs the current source again. Network access is normally needed for Python dependencies and build requirements; pip's standard index and offline environment settings apply.

In the source repository, the helper uses the enclosing checkout if there is no bundled source. If only the skill subdirectory was copied from GitHub, supply the source explicitly:

```bash
python "/absolute/path/to/wave-mcp/scripts/setup_runtime.py" \
  --source "/absolute/path/to/dv365-wave-mcp"
```

To reuse an installed environment or the project's Linux offline bundle, set `WAVE_MCP_PYTHON` to the **absolute Python executable with wave-mcp installed**; this skips the skill's `.venv` and needs no setup run. For an offline bundle, preserve any PATH/library environment established by its installer or wrapper. This skill package is a source distribution, not the full offline runtime described in the project's [air-gap deployment guide](https://github.com/dv365lab/dv365-wave-mcp/blob/main/docs/DEPLOY_AIRGAP.md).

On Windows/macOS, `pylibfst` may need a source build with CMake, a compatible C/C++ compiler and zlib. A dependency installation failure is not a successful setup. Prefer a supported Linux environment (including WSL with an installed Linux distribution or an existing Linux host) if the required native toolchain is unavailable. Do not silently remove dependencies or install another release to hide the failure. Simulation files and converter executables must be accessible to the environment actually running wave-mcp.

## Waveform conversion requirements

| Input | Extra local dependency |
| --- | --- |
| FST | None beyond the Python runtime dependencies |
| VCD | GTKWave's `vcd2fst` on PATH or configured through the project's converter settings |
| FSDB | Local Verdi FsdbReader runtime, compiler/build tools for the source-only `fsdb2fst` helper; use the repository's FSDB guide |
| SHM directory, `.trn`, `.dsn` | Xcelium `simvisdbutil` plus `vcd2fst` |
| VWDB directory | Cadence `vwdb2vcd` plus `vcd2fst` |

For Cadence, set `XCELIUM_HOME` (or the existing installation environment). Explicit executable overrides are `SIMVISDBUTIL_BIN` and `VWDB2VCD_BIN`. Optional `WAVE_MCP_SHM_TMPDIR` selects temporary VCD storage; the exported VCD can be much larger than the original database. Do not claim that proprietary formats work without their vendor tools.

The packaged source includes `docs/FSDB_GUIDE.md`, `docs/SHM_GUIDE.md`, `docs/VWDB_GUIDE.md`, and `docs/SELF_BUILD.md`. Open the relevant file from the source checkout, or extract it from `assets/wave-mcp-source.zip` when needed. Those files document converter/build environment variables and viewer asset preparation.

## Optional MCP connection

The CLI works without an MCP connection. Prefer a persistent MCP process for many queries against a large design and for the browser viewer. With the skill's installed environment, configure the agent to start its Python directly:

```json
{
  "mcpServers": {
    "wave-mcp": {
      "command": "/absolute/path/to/wave-mcp/.venv/bin/python",
      "args": ["-m", "wave_mcp.server"]
    }
  }
}
```

For Windows use the absolute `.venv/Scripts/python.exe` path. For an existing runtime use that runtime's Python path and required environment. This stdio server can start without a session; create one with `prepare_session` or `open_static_session`.

Claude Code uses `.mcp.json` for project configuration. Codex uses TOML in its configuration:

```toml
[mcp_servers.wave-mcp]
command = "/absolute/path/to/wave-mcp/.venv/bin/python"
args = ["-m", "wave_mcp.server"]
```

Use absolute input paths with MCP, since the host's server working directory may differ from the RTL project. Preserve unrelated configuration. Registering a skill alone does not register its optional MCP server.
