> **本文件由《芯片验证日记》整理分享，仅供学习交流使用。**
>
> - 公众号 / 视频号：**芯片验证日记**
> - 知识星球：**7833526** —— 一年 365 天答疑，为您的工作和学习保驾护航！
> - 已成功指导 **200+** 位芯片同行求职上岸、收获满意 Offer；提供**求职套餐 / 职业规划**服务，欢迎微信：DV365-DV_Daily。

---

# SHM Waveform Guide (Cadence Xcelium / SimVision)

[中文版](SHM_GUIDE.md)

wave-mcp reads FST only. SHM (a Cadence SST2 database: a `waves.shm/` directory holding
`waves.trn` and `waves.dsn`) goes through a conversion path: `prepare_session`,
`open_wave_view`, `wave-view` and `wave-session --vcd` all accept an SHM directly, convert it to
FST, and carry on. The query tools work unchanged.

> For new simulations, [dumping FST straight from Xcelium](XCELIUM_FST_GUIDE.md) is still the
> first choice (zero conversion). This path is for SHM waveforms you already have, or for flows
> where changing the simulation scripts is inconvenient.
> For Verisium Debug's VWDB see [VWDB_GUIDE.en.md](VWDB_GUIDE.en.md). A hybrid `.shm` directory
> holding both `.trn` and `*.vwdb` is read as SHM; one holding only `*.vwdb` is read as VWDB.

## 1. How the conversion works

```
waves.shm  --simvisdbutil -vcd-->  temporary VCD  --vcd2fst-->  waves.fst
```

1. Xcelium's own `simvisdbutil` exports the SHM to a temporary VCD;
2. GTKWave's `vcd2fst` converts it to FST (the same converter and compression levels as the VCD
   path);
3. the temporary VCD is deleted whether the conversion succeeds or fails.

`simvisdbutil` is the only reliable way to read SHM (the format is not published); wave-mcp
neither ships nor reimplements it. Whether it checks out a license depends on your Cadence
version and site configuration; wave-mcp itself involves no license.

## 2. Requirements

| Dependency | Notes |
| --- | --- |
| `simvisdbutil` | Installed with Xcelium (`<install>/tools/bin/simvisdbutil`). Search order: `$SIMVISDBUTIL_BIN` → `PATH` → `tools/bin` under `$XCELIUM_HOME` / `$XLM_ROOT` / `$CDS_INST_DIR` → the directory of `xrun` on `PATH` |
| `vcd2fst` | Same as the VCD path, see the README and [DEPLOY_AIRGAP.md](DEPLOY_AIRGAP.md) |

The MCP server is launched by the IDE and does not go through your project's `cshrc`. When
`simvisdbutil` is not on `PATH`, add `XCELIUM_HOME` (the Xcelium installation root) or
`SIMVISDBUTIL_BIN` to the `env` block of the MCP configuration.

## 3. Usage

Pass the `.shm` directory or the `.trn` / `.dsn` inside it: all three name the same database and
share one FST. A directory that does not end in `.shm` but contains a `*.trn` file is recognised
as SHM too.

```python
prepare_session(wave_path="sim/waves.shm", filelist_path="rtl.f", top="tb")
open_wave_view(fst_paths=["sim/waves.shm"])
```

```bash
wave-view sim/waves.shm
wave-session --vcd sim/waves.shm --out sess/
```

**Where the FST goes**: `sim/waves.shm` → `sim/waves.fst` (next to the `.shm` directory, never
inside it). The rules are the same as for VCD / FSDB: an FST already there that is not older than
the database is reused; after a re-simulation changes the `.trn` / `.dsn` it is converted again
and overwritten; when the directory is not writable, or the conversion is partial, the FST goes
to `~/.wave-mcp/cache/fst/` and the reply says why.

The temporary VCD is written next to the FST by default (a hidden name starting with `.`) and is
usually several times the size of the SHM. If that disk is short of space, point
`WAVE_MCP_SHM_TMPDIR` at a larger one.

## 4. Large databases: convert only part of them

The `convert_shm_to_fst` tool (and the parameters of the same name on `prepare_session`) can
export only part of a database:

```python
convert_shm_to_fst(shm_path="sim/waves.shm", scopes=["tb.u_dut.u_core"])
convert_shm_to_fst(shm_path="sim/waves.shm", signals_file="sigs.txt")
```

- `scopes`: **exact hierarchical paths** (not substrings, unlike `scopes` for FSDB). Each scope
  is exported together with every level below it (`simvisdbutil -scope <s> all`). `/`
  separators are turned into `.` automatically.
- `signals_file`: one full signal path per line; anything after `#` is a comment
  (`simvisdbutil -signal`).
- `simvisdbutil` often still exits 0 when a name does not exist. wave-mcp recognises the `*F,` /
  `*E,` diagnostics it prints and reports an error instead of producing an FST with missing
  signals.

A partial conversion is stored in the cache directory and never takes the `waves.fst` name
reserved for the full waveform.

## 5. Troubleshooting

| Symptom | What to do |
| --- | --- |
| `'simvisdbutil' not found` | Set `XCELIUM_HOME` or `SIMVISDBUTIL_BIN` in the MCP `env`, or add Xcelium's `tools/bin` to `PATH` |
| `simvisdbutil SHM -> VCD export failed ... *F,MKEXPF: bad scope name` | Is each scope a full path? Check the hierarchy names in SimVision or with `simvisdbutil waves.shm -vcd -scope tb` |
| `*F,BDSIGNM` | A signal in `signals_file` is not in the database |
| Slow conversion / disk fills up | SHM is compact but expands as VCD; narrow it with `scopes` / `signals_file`, or [dump FST directly](XCELIUM_FST_GUIDE.md) during simulation |
| Converting by hand | `simvisdbutil waves.shm -vcd -output waves.vcd -overwrite`, then pass the `.vcd` to wave-mcp |
