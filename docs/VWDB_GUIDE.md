> **本文件由《芯片验证日记》整理分享，仅供学习交流使用。**
>
> - 公众号 / 视频号：**芯片验证日记**
> - 知识星球：**7833526** —— 一年 365 天答疑，为您的工作和学习保驾护航！
> - 已成功指导 **200+** 位芯片同行求职上岸、收获满意 Offer；提供**求职套餐 / 职业规划**服务，欢迎微信：DV365-DV_Daily。

---

# VWDB 波形接入指南（Cadence Verisium Debug）

[English version](VWDB_GUIDE.en.md)

wave-mcp 只读 FST。VWDB（Verisium Waveform Database，`*.vwdb` 目录，内含
`vwdb_info.json`、`dsn_*`、`trn_*`）走转换通道：`prepare_session`、`open_wave_view`、
`wave-view`、`wave-session --vcd` 都可以直接传 VWDB，自动转成 FST 后再用，
查询工具零改动。

> 新跑的仿真，首选仍是 [Xcelium 直出 FST](XCELIUM_FST_GUIDE.md)（零转换）。
> 本通道面向已有的 VWDB 波形，例如为 Verisium Debug 跑出来的回归波形。

## 1. 转换原理

```
waves.vwdb  --vwdb2vcd -64 -db ... -o-->  临时 VCD  --vcd2fst-->  waves.fst
```

1. 用 Cadence 自带的 `vwdb2vcd` 把 VWDB 导出为临时 VCD；
2. 用 GTKWave 的 `vcd2fst` 转成 FST（与 VCD 通道同一个转换器、同一套压缩档位）；
3. 临时 VCD 以及 `vwdb2vcd` 在工作目录里留下的 `vwdb2vcd.log`、崩溃转储等，无论成功失败都会删除。

`vwdb2vcd` 是读 VWDB 唯一可靠的途径（格式不公开），wave-mcp 不附带也不重新实现它。
是否 checkout license 由 Cadence 版本与站点配置决定，wave-mcp 本身不涉及 license。

## 2. 需要什么

| 依赖 | 说明 |
| --- | --- |
| `vwdb2vcd` | 随 Xcelium 与 Verisium Debug 安装（`<install>/tools/bin/vwdb2vcd`）。查找顺序：`$VWDB2VCD_BIN` → `PATH` → `$XCELIUM_HOME` / `$XLM_ROOT` / `$CDS_INST_DIR` / `$VERISIUM_DEBUG_HOME` 等目录下的 `tools/bin` → `PATH` 上 `xrun` 所在目录 |
| `vcd2fst` | 与 VCD 通道相同，见 README 与 [DEPLOY_AIRGAP.md](DEPLOY_AIRGAP.md) |

MCP server 由 IDE 拉起，不经过项目的 `cshrc`。`vwdb2vcd` 不在 `PATH` 上时，在 MCP
配置的 `env` 里加 `XCELIUM_HOME`（Xcelium 安装根目录）或 `VWDB2VCD_BIN` 即可。

## 3. 能传哪些路径

| 传入 | 识别为 |
| --- | --- |
| `run/waves.vwdb`（目录） | 该 VWDB |
| VWDB 目录里的任意路径（`vwdb_info.json`、`trn_0_0/...`） | 所在的 VWDB |
| 不以 `.vwdb` 结尾但含 `vwdb_info.json` 的目录 | 该 VWDB |
| 只含一个 `*.vwdb`、没有 `.trn` 的 `.shm` 目录（只写 VWDB 的 dump） | 里面那个 VWDB |
| 同时含 `.trn` 和 `*.vwdb` 的 `.shm` 目录（SHM/VWDB 混合 dump） | **SHM**；要读 VWDB 就直接传里面的 `*.vwdb` |

```python
prepare_session(wave_path="sim/waves.shm/waves_ida.vwdb", filelist_path="rtl.f", top="tb")
open_wave_view(fst_paths=["sim/waves.vwdb"])
```

```bash
wave-view sim/waves.vwdb
wave-session --vcd sim/waves.vwdb --out sess/
```

**产物位置**：`sim/waves.vwdb` → `sim/waves.fst`。VWDB 位于 `.shm` 目录内时
（Xcelium 默认写成 `waves.shm/waves_ida.vwdb`），FST 放在 `.shm` 目录**旁边**：
`sim/waves_ida.fst`，不写进仿真器的目录。复用、过期重转、目录不可写或部分转换时改放缓存，
规则与 VCD / FSDB / SHM 相同。VWDB 的版本按其下所有数据文件计算（`.temp` 等隐藏的临时项除外），
重新仿真后会自动重新转换。

临时 VCD 默认写在 FST 所在目录（以 `.` 开头的隐藏项），体积通常是 VWDB 的数倍。
所在盘空间紧张时，用 `WAVE_MCP_SHM_TMPDIR` 指到大盘（SHM 与 VWDB 共用这个变量）。

## 4. 大数据库：只转一部分

`convert_vwdb_to_fst` 工具（以及 `prepare_session` 的同名参数）支持只导出一部分：

```python
convert_vwdb_to_fst(vwdb_path="sim/waves.vwdb", scopes=["tb.u_dut.u_core"])
convert_vwdb_to_fst(vwdb_path="sim/waves.vwdb", signals_file="sigs.txt")
```

- `scopes`：**完整的层次路径**（不是子串，这一点与 FSDB 的 `scopes` 不同），每个 scope 连同其下
  所有层级一起导出（`vwdb2vcd -scope`）。`/` 分隔符会自动换成 `.`。
- `signals_file`：每行一个完整信号路径。`vwdb2vcd` 自己的列表文件不认注释，wave-mcp 会先去掉
  `#` 之后的内容和空行再交给它（`-signalListFile`）。
- `vwdb2vcd` 遇到不存在的信号或 scope 时仍以 0 退出，只在日志里记一笔。wave-mcp 会读它的日志，
  并检查导出的 VCD 是否一个信号都没有，两种情况都报错，不会产出一个缺信号的 FST。

部分转换的产物放在缓存目录，不占用完整波形的 FST 文件名。

## 5. 怎样得到 VWDB

不需要为 wave-mcp 专门产生 VWDB；已有的直接用即可。作为参考，在 Xcelium 26.03 上设置
`CDNS_ENABLE_SHM2VWDB=1` 后，`$shm_open` / `$shm_probe` 的 dump 会写成
`waves.shm/waves_ida.vwdb`（SHM/VWDB 混合模式下 `.shm` 目录里同时有 `.trn` 与 `.vwdb`）。

## 6. 排错

| 现象 | 处理 |
| --- | --- |
| `'vwdb2vcd' not found` | 在 MCP `env` 里设 `XCELIUM_HOME` 或 `VWDB2VCD_BIN`，或把 Xcelium / Verisium Debug 的 `tools/bin` 加入 `PATH` |
| `export failed (rc=0): the export selected no signals` | `scopes` 写的是完整路径吗？`vwdb2vcd -64 -db waves.vwdb -o x.vcd -scope tb` 看一下层次名 |
| `Signal "..." not found in database` | `signals_file` 里有信号不在数据库中 |
| `... holds several VWDB databases` | `.shm` 目录里有多个 `*.vwdb`，直接传要读的那个 |
| 转换慢 / 磁盘被占满 | 展开成 VCD 会膨胀；用 `scopes` / `signals_file` 缩小范围，或改为仿真时 [直出 FST](XCELIUM_FST_GUIDE.md) |
| 手动转换 | `vwdb2vcd -64 -db waves.vwdb -o waves.vcd`，然后把 `.vcd` 传给 wave-mcp |
