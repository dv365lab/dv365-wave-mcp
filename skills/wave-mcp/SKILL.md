---
name: wave-mcp
description: Analyze RTL waveforms (FST, VCD, FSDB, Cadence SHM/VWDB) and SystemVerilog designs with wave-mcp. Use for signal queries, driver/fan-in analysis, X propagation, pass/fail waveform comparison, and RTL debugging (波形分析、X态溯源、驱动追踪). Requires existing RTL or simulation output; does not run a simulator.
license: Apache-2.0; bundled third-party source retains its original notices.
metadata:
  runtime: "Shell and Python 3.10+; Linux x86_64 recommended. Install Python dependencies online or reuse an existing wave-mcp runtime. MCP is optional."
---

> **本文件由《芯片验证日记》整理分享，仅供学习交流使用。**
>
> - 公众号 / 视频号：**芯片验证日记**
> - 知识星球：**7833526** —— 一年 365 天答疑，为您的工作和学习保驾护航！
> - 已成功指导 **200+** 位芯片同行求职上岸、收获满意 Offer；提供**求职套餐 / 职业规划**服务，欢迎微信：DV365-DV_Daily。

---


# wave-mcp

Investigate existing simulation output or a SystemVerilog design using the project's actual query results. Reply in the user's language.

## Runtime and entry point

Resolve this skill's directory from the location of this `SKILL.md`; all helper paths are relative to that directory. Keep the working directory at the user's RTL project so filelist paths and environment variables retain their meaning.

- Prefer an already connected wave-mcp MCP server for repeated queries and viewer use. Its tool names may have a host-specific prefix.
- Otherwise use `python "/absolute/path/to/wave-mcp/scripts/wave.py" query ...`. This launcher selects the skill's `.venv`; `WAVE_MCP_PYTHON` can select an existing runtime by absolute Python path.
- If no runtime exists, read [references/setup.md](references/setup.md) and run `python "/absolute/path/to/wave-mcp/scripts/setup_runtime.py"`. The distribution contains this repository's source snapshot; do not replace it with a potentially different PyPI release.
- Discover the installed interface with `query --list` and `query TOOL --help`. Use `--json` for structured replies. Parameter flags use the exact Python names, including underscores (`--wave_path`, `--filelist_path`).

## Select the analysis

Find the requested waveform, top instance/module, RTL filelist, and failure time or symptom in the user's project and build logs. Reuse the simulation's include directories and defines. Ask for missing inputs when they affect the answer; do not invent paths, top names, signal names, or compile options.

| Available inputs | Entry tool |
| --- | --- |
| Waveform, optionally RTL | `prepare_session(wave_path=..., top=..., filelist_path=...)` |
| RTL only | `open_static_session(top=..., filelist_path=...)` |
| Existing session directory or manifest | `open_session(session_path=...)` (MCP), or CLI `--session DIR` |
| Two or more FST waveforms | `diff_waveforms(fst_paths=[...], scope=..., signals=..., clock=...)` |

Omit optional arguments that are unknown. `prepare_session` converts VCD/FSDB/SHM/VWDB to FST as needed; see [references/setup.md](references/setup.md) for format-specific executables. Static analysis needs no waveform but still uses the project's installed dependencies. Simulation itself stays in the user's existing workflow.

## Session handling

Check the entry reply's status and session summary, including available netlist health and consistency warnings. Report partial or unavailable netlist coverage before relying on a driver or trace result. Preserve `session_path` for subsequent work.

- **MCP:** use the returned `session_id` on subsequent session-based tools, particularly when several sessions are open. Query defaults and viewer state persist within that server process.
- **CLI:** each invocation is a new process. Pass `--session <returned session_path>` on each subsequent query and give paths/time bounds explicitly. A prior CLI `session_id` or `query_defaults_set` does not carry over. Check the JSON body for `status: error`, `error`, or unavailable capabilities even if the process exits zero.

Example CLI sequence (replace paths and top with discovered inputs):

```bash
python "/absolute/path/to/wave-mcp/scripts/wave.py" query prepare_session \
  --wave_path sim/waves.shm --filelist_path rtl.f --top tb --json
# Read session_path from the response and use that exact directory below.
python "/absolute/path/to/wave-mcp/scripts/wave.py" query list_signals \
  --session "/returned/session/path" --path tb.u_dut --limit 100 --json
python "/absolute/path/to/wave-mcp/scripts/wave.py" query signal_values \
  --session "/returned/session/path" --paths tb.u_dut.valid,tb.u_dut.ready \
  --start 100ns --end 200ns --limit 200 --json
```

## Investigate with bounded queries

Start with `find_instances`, `scope_info`, `list_signals`, and `signal_info` to confirm hierarchy and names. Batch related signals in `signal_values`; start with a narrow failure window and explicit units (`100ns`, `250ps`). If the reply is sampled or limited, narrow the window or raise the relevant limit before making a completeness claim.

Choose tools by the question:

| Question | Tools |
| --- | --- |
| Who drives this signal, and where? | `signal_drivers`, `signal_connectivity`, `signal_fanin`, `signal_loads` |
| Which assignment was active at the failure? | `active_drivers`, then `driver_contributors` if needed |
| Why does this value occur? | `trace_value` and surrounding `signal_values` |
| Where did X originate? | `trace_x`, verify candidate roots with `signal_values` and RTL |
| Which signals stopped changing? | `signal_activity`, then inspect the relevant clock/reset/enable |
| Where do pass and fail diverge? | `diff_waveforms`, then inspect the earliest divergent signals |

Read [references/workflows.md](references/workflows.md) for static-analysis and comparison examples, conversion scoping, and persistent viewer usage. Consult `query TOOL --help` or the connected tool schema for advanced arguments rather than guessing.

`trace_x` is approximate; a driver relationship alone does not prove a runtime cause. Cross-check values, guards, reset/clock behavior, and source locations. Do not interpret an absent or undumped signal as a constant zero.

## Deliver the evidence

State the finding with signal paths, time and units, observed values, and relevant source file/line when available. Distinguish observed facts from causal hypotheses, and identify missing evidence or coverage. Suggest the smallest next check or fix supported by the results; edit RTL only when the user's request authorizes it.

Conversions write reusable FST files beside the original inputs when possible; scoped conversions and unwritable directories use a cache. Keep generated sessions and conversions out of commits. For a browser view, use the persistent MCP server or foreground `wave-view`, then give the user the live URL; a one-shot CLI query cannot keep its viewer alive.
