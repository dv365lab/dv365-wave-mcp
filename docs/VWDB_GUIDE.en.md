> **本文件由《芯片验证日记》整理分享，仅供学习交流使用。**
>
> - 公众号 / 视频号：**芯片验证日记**
> - 知识星球：**7833526** —— 一年 365 天答疑，为您的工作和学习保驾护航！
> - 已成功指导 **200+** 位芯片同行求职上岸、收获满意 Offer；提供**求职套餐 / 职业规划**服务，欢迎微信：DV365-DV_Daily。

---

# VWDB Waveform Guide (Cadence Verisium Debug)

[中文版](VWDB_GUIDE.md)

wave-mcp reads FST only. VWDB (Verisium Waveform Database: a `*.vwdb` directory holding
`vwdb_info.json`, `dsn_*` and `trn_*`) goes through a conversion path: `prepare_session`,
`open_wave_view`, `wave-view` and `wave-session --vcd` all accept a VWDB directly, convert it to
FST, and carry on. The query tools work unchanged.

> For new simulations, [dumping FST straight from Xcelium](XCELIUM_FST_GUIDE.md) is still the
> first choice (zero conversion). This path is for VWDB waveforms you already have, such as
> regression runs recorded for Verisium Debug.

## 1. How the conversion works

```
waves.vwdb  --vwdb2vcd -64 -db ... -o-->  temporary VCD  --vcd2fst-->  waves.fst
```

1. Cadence's own `vwdb2vcd` exports the VWDB to a temporary VCD;
2. GTKWave's `vcd2fst` converts it to FST (the same converter and compression levels as the VCD
   path);
3. the temporary VCD, along with the `vwdb2vcd.log`, crash dumps and other files `vwdb2vcd`
   leaves in its working directory, is deleted whether the conversion succeeds or fails.

`vwdb2vcd` is the only reliable way to read VWDB (the format is not published); wave-mcp neither
ships nor reimplements it. Whether it checks out a license depends on your Cadence version and
site configuration; wave-mcp itself involves no license.

## 2. Requirements

| Dependency | Notes |
| --- | --- |
| `vwdb2vcd` | Installed with Xcelium and Verisium Debug (`<install>/tools/bin/vwdb2vcd`). Search order: `$VWDB2VCD_BIN` → `PATH` → `tools/bin` under `$XCELIUM_HOME` / `$XLM_ROOT` / `$CDS_INST_DIR` / `$VERISIUM_DEBUG_HOME` and similar → the directory of `xrun` on `PATH` |
| `vcd2fst` | Same as the VCD path, see the README and [DEPLOY_AIRGAP.md](DEPLOY_AIRGAP.md) |

The MCP server is launched by the IDE and does not go through your project's `cshrc`. When
`vwdb2vcd` is not on `PATH`, add `XCELIUM_HOME` (the Xcelium installation root) or
`VWDB2VCD_BIN` to the `env` block of the MCP configuration.

## 3. Which paths you can pass

| You pass | Read as |
| --- | --- |
| `run/waves.vwdb` (directory) | that VWDB |
| Any path inside a VWDB directory (`vwdb_info.json`, `trn_0_0/...`) | the enclosing VWDB |
| A directory not ending in `.vwdb` that contains `vwdb_info.json` | that VWDB |
| A `.shm` directory holding a single `*.vwdb` and no `.trn` (VWDB-only dumping) | the VWDB inside it |
| A `.shm` directory holding both `.trn` and `*.vwdb` (hybrid SHM/VWDB dumping) | **SHM**; to read the VWDB, pass the `*.vwdb` inside it |

```python
prepare_session(wave_path="sim/waves.shm/waves_ida.vwdb", filelist_path="rtl.f", top="tb")
open_wave_view(fst_paths=["sim/waves.vwdb"])
```

```bash
wave-view sim/waves.vwdb
wave-session --vcd sim/waves.vwdb --out sess/
```

**Where the FST goes**: `sim/waves.vwdb` → `sim/waves.fst`. When the VWDB sits inside a `.shm`
directory (Xcelium writes `waves.shm/waves_ida.vwdb` by default), the FST goes **beside** the
`.shm` directory: `sim/waves_ida.fst`, never into the simulator's directory. Reuse, reconversion
when stale, and the cache fallback for unwritable directories or partial conversions follow the
same rules as VCD / FSDB / SHM. A VWDB is versioned over all its data files (hidden scratch
entries such as `.temp` excluded), so it is converted again after a re-simulation.

The temporary VCD is written next to the FST by default (a hidden name starting with `.`) and is
usually several times the size of the VWDB. If that disk is short of space, point
`WAVE_MCP_SHM_TMPDIR` at a larger one (SHM and VWDB share this variable).

## 4. Large databases: convert only part of them

The `convert_vwdb_to_fst` tool (and the parameters of the same name on `prepare_session`) can
export only part of a database:

```python
convert_vwdb_to_fst(vwdb_path="sim/waves.vwdb", scopes=["tb.u_dut.u_core"])
convert_vwdb_to_fst(vwdb_path="sim/waves.vwdb", signals_file="sigs.txt")
```

- `scopes`: **exact hierarchical paths** (not substrings, unlike `scopes` for FSDB). Each scope
  is exported together with every level below it (`vwdb2vcd -scope`). `/` separators are turned
  into `.` automatically.
- `signals_file`: one full signal path per line. `vwdb2vcd`'s own list file accepts no comments,
  so wave-mcp strips everything after `#` and blank lines before handing it over
  (`-signalListFile`).
- `vwdb2vcd` still exits 0 when a signal or scope does not exist and only notes it in its log.
  wave-mcp reads that log and also checks whether the exported VCD declares any signal at all;
  either case is reported as an error instead of producing an FST with missing signals.

A partial conversion is stored in the cache directory and never takes the FST name reserved for
the full waveform.

## 5. Getting a VWDB

You do not need to produce a VWDB for wave-mcp; use the ones you already have. For reference, on
Xcelium 26.03, setting `CDNS_ENABLE_SHM2VWDB=1` makes a `$shm_open` / `$shm_probe` dump write
`waves.shm/waves_ida.vwdb` (in this hybrid SHM/VWDB mode the `.shm` directory holds both `.trn`
and `.vwdb`).

## 6. Troubleshooting

| Symptom | What to do |
| --- | --- |
| `'vwdb2vcd' not found` | Set `XCELIUM_HOME` or `VWDB2VCD_BIN` in the MCP `env`, or add the `tools/bin` of Xcelium / Verisium Debug to `PATH` |
| `export failed (rc=0): the export selected no signals` | Is each scope a full path? Check the hierarchy names with `vwdb2vcd -64 -db waves.vwdb -o x.vcd -scope tb` |
| `Signal "..." not found in database` | A signal in `signals_file` is not in the database |
| `... holds several VWDB databases` | The `.shm` directory contains several `*.vwdb`; pass the one you want |
| Slow conversion / disk fills up | The database expands as VCD; narrow it with `scopes` / `signals_file`, or [dump FST directly](XCELIUM_FST_GUIDE.md) during simulation |
| Converting by hand | `vwdb2vcd -64 -db waves.vwdb -o waves.vcd`, then pass the `.vcd` to wave-mcp |
