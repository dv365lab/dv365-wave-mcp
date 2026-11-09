> **本文件由《芯片验证日记》整理分享，仅供学习交流使用。**
>
> - 公众号 / 视频号：**芯片验证日记**
> - 知识星球：**7833526** —— 一年 365 天答疑，为您的工作和学习保驾护航！
> - 已成功指导 **200+** 位芯片同行求职上岸、收获满意 Offer；提供**求职套餐 / 职业规划**服务，欢迎微信：DV365-DV_Daily。

---

# SHM 波形接入指南（Cadence Xcelium / SimVision）

[English version](SHM_GUIDE.en.md)

wave-mcp 只读 FST。SHM（Cadence SST2 数据库，`waves.shm/` 目录，内含
`waves.trn` 与 `waves.dsn`）走转换通道：`prepare_session`、`open_wave_view`、
`wave-view`、`wave-session --vcd` 都可以直接传 SHM，自动转成 FST 后再用，
查询工具零改动。

> 新跑的仿真，首选仍是 [Xcelium 直出 FST](XCELIUM_FST_GUIDE.md)（零转换）。
> 本通道面向已有的 SHM 波形，或不方便改仿真脚本的场景。
> Verisium Debug 的 VWDB 见 [VWDB_GUIDE.md](VWDB_GUIDE.md)；同时含 `.trn` 与 `*.vwdb`
> 的混合 `.shm` 目录按 SHM 读，只含 `*.vwdb` 的按 VWDB 读。

## 1. 转换原理

```
waves.shm  --simvisdbutil -vcd-->  临时 VCD  --vcd2fst-->  waves.fst
```

1. 用 Xcelium 自带的 `simvisdbutil` 把 SHM 导出为临时 VCD；
2. 用 GTKWave 的 `vcd2fst` 转成 FST（与 VCD 通道同一个转换器、同一套压缩档位）；
3. 临时 VCD 无论成功失败都会删除。

`simvisdbutil` 是读 SHM 唯一可靠的途径（格式不公开），wave-mcp 不附带也不重新实现它。
是否 checkout license 由 Cadence 版本与站点配置决定，wave-mcp 本身不涉及 license。

## 2. 需要什么

| 依赖 | 说明 |
| --- | --- |
| `simvisdbutil` | 随 Xcelium 安装（`<install>/tools/bin/simvisdbutil`）。查找顺序：`$SIMVISDBUTIL_BIN` → `PATH` → `$XCELIUM_HOME` / `$XLM_ROOT` / `$CDS_INST_DIR` 下的 `tools/bin` → `PATH` 上 `xrun` 所在目录 |
| `vcd2fst` | 与 VCD 通道相同，见 README 与 [DEPLOY_AIRGAP.md](DEPLOY_AIRGAP.md) |

MCP server 由 IDE 拉起，不经过项目的 `cshrc`。`simvisdbutil` 不在 `PATH` 上时，在 MCP
配置的 `env` 里加 `XCELIUM_HOME`（Xcelium 安装根目录）或 `SIMVISDBUTIL_BIN` 即可。

## 3. 用法

可以传 `.shm` 目录，也可以传里面的 `.trn` / `.dsn`，三者都指向同一个数据库、共用同一份 FST。
不以 `.shm` 结尾但含有 `*.trn` 的目录也会被识别为 SHM。

```python
prepare_session(wave_path="sim/waves.shm", filelist_path="rtl.f", top="tb")
open_wave_view(fst_paths=["sim/waves.shm"])
```

```bash
wave-view sim/waves.shm
wave-session --vcd sim/waves.shm --out sess/
```

**产物位置**：`sim/waves.shm` → `sim/waves.fst`（放在 `.shm` 目录旁边，不写进目录内部）。
规则与 VCD / FSDB 相同：旁边已有不比数据库旧的 FST 就直接复用；重新仿真后 `.trn` / `.dsn`
有变化则重新转换并覆盖；目录不可写或部分转换时改放 `~/.wave-mcp/cache/fst/`，返回里说明原因。

临时 VCD 默认写在 FST 所在目录（以 `.` 开头的隐藏文件），体积通常是 SHM 的数倍。
所在盘空间紧张时，用 `WAVE_MCP_SHM_TMPDIR` 指到大盘。

## 4. 大数据库：只转一部分

`convert_shm_to_fst` 工具（以及 `prepare_session` 的同名参数）支持只导出一部分：

```python
convert_shm_to_fst(shm_path="sim/waves.shm", scopes=["tb.u_dut.u_core"])
convert_shm_to_fst(shm_path="sim/waves.shm", signals_file="sigs.txt")
```

- `scopes`：**完整的层次路径**（不是子串，这一点与 FSDB 的 `scopes` 不同），每个 scope 连同其下
  所有层级一起导出（`simvisdbutil -scope <s> all`）。`/` 分隔符会自动换成 `.`。
- `signals_file`：每行一个完整信号路径，`#` 之后为注释（`simvisdbutil -signal`）。
- 名字不存在时 `simvisdbutil` 往往仍以 0 退出，wave-mcp 会识别它打印的 `*F,` / `*E,` 诊断并报错，
  不会产出一个缺信号的 FST。

部分转换的产物放在缓存目录，不占用完整波形的 `waves.fst` 文件名。

## 5. 排错

| 现象 | 处理 |
| --- | --- |
| `'simvisdbutil' not found` | 在 MCP `env` 里设 `XCELIUM_HOME` 或 `SIMVISDBUTIL_BIN`，或把 Xcelium 的 `tools/bin` 加入 `PATH` |
| `simvisdbutil SHM -> VCD export failed ... *F,MKEXPF: bad scope name` | `scopes` 写的是完整路径吗？用 SimVision 或 `simvisdbutil waves.shm -vcd -scope tb` 确认层次名 |
| `*F,BDSIGNM` | `signals_file` 里有信号不在数据库中 |
| 转换慢 / 磁盘被占满 | SHM 体积小但展开成 VCD 会膨胀；用 `scopes` / `signals_file` 缩小范围，或改为仿真时 [直出 FST](XCELIUM_FST_GUIDE.md) |
| 手动转换 | `simvisdbutil waves.shm -vcd -output waves.vcd -overwrite`，然后把 `.vcd` 传给 wave-mcp |
