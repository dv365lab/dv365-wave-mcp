> **本文件由《芯片验证日记》整理分享，仅供学习交流使用。**
>
> - 公众号 / 视频号：**芯片验证日记**
> - 知识星球：**7833526** —— 一年 365 天答疑，为您的工作和学习保驾护航！
> - 已成功指导 **200+** 位芯片同行求职上岸、收获满意 Offer；提供**求职套餐 / 职业规划**服务，欢迎微信：DV365-DV_Daily。

---

# Focused analysis workflows

The examples use the installed `wave-mcp` CLI for brevity. They are equivalent to `python "/absolute/path/to/skill/scripts/wave.py" ...`. Names, scope paths, and time windows are examples; discover the actual inputs first. JSON arguments below use POSIX shell quoting. In other shells, preserve JSON as one argument, or use the individual flags from `query TOOL --help`.

## Static RTL analysis

```bash
wave-mcp query open_static_session --top uart_top --filelist_path rtl.f --json
# Replace SESSION with the response's session_path in all following commands.
wave-mcp query find_instances --session SESSION --under uart_top --max_depth 2 --json
wave-mcp query signal_drivers --session SESSION --path uart_top.u_tx.tx_serial --json
wave-mcp query signal_fanin --session SESSION --path uart_top.u_tx.tx_serial --max_depth 2 --json
```

Inspect include paths, macro defines and netlist health if the design elaborates partially. Missing UVM packages or a failing top may reduce coverage. Do not use waveform-dependent tools in a static-only session. Once simulation output is available, call `prepare_session` with the same RTL configuration; automatic session locations allow netlist reuse.

## X or wrong-value investigation

1. Use `signal_values` around the observed failure to confirm the first visible bad value; narrow sampled output until the relevant transitions have full resolution.
2. Use `signal_drivers` for source locations and guards, then `active_drivers` at the same time.
3. Use `trace_x` for X propagation or `trace_value` for a wrong value. Query the candidate root and its clock, reset, inputs and enables around the failure.
4. Read the cited RTL statement before assigning causality. Distinguish missing dump data, undriven nets, reset initialization and propagation. A 2-state simulation cannot prove X propagation.

```bash
wave-mcp query trace_x --session SESSION --path tb.u_dut.result --time 250ns --max_depth 6 --json
wave-mcp query active_drivers --session SESSION --path tb.u_dut.result --time 250ns --json
```

## Pass/fail comparison

`diff_waveforms` accepts **FST paths**, not arbitrary source formats. Run `prepare_session` or the relevant conversion tool first for VCD/FSDB/SHM/VWDB, then use the actual converted FST path returned in the session/conversion reply. Do not assume its location when caching or scoped conversion is involved.

```bash
wave-mcp query diff_waveforms --json --json-args \
  '{"fst_paths":["/sim/pass.fst","/sim/fail.fst"],"scope":"tb.u_dut","clock":"tb.clk"}'
```

Use `scope` or selected `signals` to bound the comparison. Choose `clock` when edge-aligned comparison matches the question; omit it if transient differences matter. Check overlap, signal matching and alignment warnings before reporting a first divergence. Follow up with value and driver queries in separate sessions for the two runs as needed.

## Large proprietary databases

Narrow conversion with `scopes` or `signals_file` when the symptom identifies a subdesign. These arguments apply to FSDB/SHM/VWDB. FSDB scopes use substring matching; SHM/VWDB scopes are exact hierarchy paths and include descendants. Slash separators normalize to dots for Cadence scopes. A `.shm` containing both `.trn` and VWDB is treated as SHM; pass the inner `.vwdb` explicitly to analyze VWDB.

```bash
wave-mcp query prepare_session --json --json-args \
  '{"wave_path":"/sim/waves.shm","top":"tb","filelist_path":"/rtl/rtl.f","scopes":["tb.u_dut"]}'
```

A scoped waveform does not establish values for signals outside the converted set. Report that coverage limit. Conversion errors for missing signals/scopes must be resolved before analysis.

## Persistent browser viewer

Viewer assets are optional and must be prepared locally using the source's `docs/SELF_BUILD.md`; the skill does not ship them. Use `open_wave_view`, `update_wave_view` and `get_view_state` **through a persistent MCP server**. In a one-shot `query open_wave_view` process, cleanup closes the server when the command exits.

Example MCP arguments:

```json
{
  "fst_paths": ["/sim/fail.fst"],
  "signals": [{"path": "tb.u_dut.result", "group": "Suspects"}],
  "cursor": {"time": "250", "unit": "ns"},
  "viewport": {"from": "200", "to": "300", "unit": "ns"},
  "annotation": {"markdown": "Observed X on result at 250 ns; check the driver and reset."}
}
```

Viewer time fields are objects, unlike the string times in analysis tools. Use ASCII group names because the waveform canvas font has no CJK glyphs; annotations support the user's language. Confirm `page_ready` and the applied revision through `get_view_state` before claiming that the browser received the requested state. Return the live URL and any warnings.

Without MCP, run the installed `wave-view` command in a terminal that stays open:

```bash
wave-view /sim/fail.fst
```

Use the skill's `.venv/bin/wave-view` (Windows: `.venv/Scripts/wave-view.exe`) or the selected existing runtime's executable. Stop it when the user finishes. A remote URL may need the user's existing port-forwarding workflow.
