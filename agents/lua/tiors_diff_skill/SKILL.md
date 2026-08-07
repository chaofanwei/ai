---
name: tiors-diff-skill
description: Analyze Dash selected-rate inconsistencies across qpaas profiles such as bddx-qpaas and prerelease-qpaas. Use when the user provides a /dash request, access log, or says two environments selected different bid/vid/code/ff. Follow the replay-compare-root-cause workflow for Lua/OpenResty Dash debugging.
---

# TIORS/Dash 选流差异分析

## 触发场景

当用户提供 `/dash` 请求、access log，或描述“两个环境选中的码流不一致”时，先按本 skill 处理。目标是实际回放请求、对比两个环境的候选码流和选中结果，然后给出可验证的原因。

## 标准流程

1. 确认是否重建环境。
   - 如果本会话首次调试请求，先询问是否重新构建 `nginx-dev`，提示当前环境可能是历史调试遗留。
   - 用户未指定时，默认沿用当前项目常用参数：`./build-nginx-dev.sh zyx master bddx-qpaas master`。
   - 用户明确说“不重建”时，直接使用现有 `nginx-dev`。

2. 回放请求。
   - 将线上 URL 改成本地形式：`curl -H "Host: cache.video.iqiyi.com" "http://localhost:8080/dash?..."`
   - 如果请求里没有 `pck` 但返回类似鉴权缺失，补一个任意 `pck` header 或参数。
   - `vf` 签名错误、`tm` 超时不是本类问题重点；必要时只做临时本地旁路，验证完必须还原。

3. 分别验证两个 profile。
   - 先跑 `bddx-qpaas`，记录选中码流与同 bid 候选。
   - 再切 `conf/lua/profile` 为 `prerelease-qpaas`，重启 OpenResty 后回放同一请求。
   - profile 可能在 worker 初始化时缓存；仅 `HUP` 不一定生效，必要时停止 master 后重新启动。

4. 记录最小对比字段。
   - 响应：`code`、`data.st`、`ctl.cost`、`video_count`。
   - 选中码流：`bid`、`vid`、`code`、`ff`、`dr`、`drmType`、`fr`、`br`、`duration`。
   - 同 `bid` 候选顺序，尤其关注同优先级候选的相对顺序。
   - access log 中的 `porsche_detail`：`rate_code`、`rate_ff`、`v:` 字段。

5. 对比并定位原因。
   - 先判断是否“候选集合不同”：某一路在一个环境被过滤、另一个环境保留。
   - 如果候选集合相同，再判断是否“候选顺序不同”：同优先级候选都保留，但最终选中 `selected[1]`。
   - 输出原因时要说明具体规则或代码位置，而不是只说“环境数据不同”。

6. 收尾。
   - 移除所有临时 mock、旁路、调试日志代码。
   - 恢复用户期望的 `profile`。
   - 本会话启动过 OpenResty 时，结束前必须执行 `./stop-openresty.sh`；如果脚本卡住，再手动终止本次 master/worker。

## 常用解析命令

回放后用 Python 提取选中码流和同 bid 候选：

```bash
curl -sS -m 60 -H 'Host: cache.video.iqiyi.com' "http://localhost:8080/dash?..." \
  | /home/fan/miniconda3/envs/py310/bin/python -c '
import sys,json
data=json.load(sys.stdin)
d=data.get("data") or data
print("code", data.get("code"), "data_st", d.get("st"))
print("ctl", d.get("ctl") or {})
videos=((d.get("program") or {}).get("video") or [])
print("video_count", len(videos))
for i,v in enumerate(videos):
    if v.get("_selected") or str(v.get("bid")) == "860":
        print(i, "SEL" if v.get("_selected") else "---",
              "bid", v.get("bid"), "vid", v.get("vid"),
              "code", v.get("code"), "ff", v.get("ff"),
              "dr", v.get("dr"), "drmType", v.get("drmType"),
              "fr", v.get("fr"), "br", v.get("br"),
              "duration", v.get("duration"))
'
```

按实际请求把 `bid` 条件改成目标 bid，例如 `800`、`860`。

## 关键代码路径

- profile 决定 fshark/Couchbase 数据源：`nginx-dev/play-nginx/conf/lua/p911/http/fshark.lua`
- qpaas 数据源配置：`nginx-dev/play-nginx/conf/lua/p911/conf/vp_conf_qpaas.lua`
- 选流主逻辑：`nginx-dev/play-nginx/conf/lua/p911/select/video_selection.lua`
- group 去重逻辑：`nginx-dev/play-nginx/conf/lua/p911/rules/video/group_filter.lua`
- 黑白名单配置逻辑：`nginx-dev/play-nginx/html/4s-data/group_7.json` 的 `black_white_list_config`
- 清晰度与 pano 过滤：`nginx-dev/play-nginx/conf/lua/p911/rules/filter/clarity.lua`

## 重点经验

### 同优先级顺序依赖

`video_selection.lua` 的默认优先级先按 `DOLBY_VISION`、`HDR10`、`AV1`、`H265` 等条件找候选。命中某一级后会直接返回该级的全部候选；如果仍有多路，最后使用 `selected[1]._selected = true`。

因此只要两环境 fshark 返回数组顺序不同，就可能选出不同 `vid`，即使过滤后的集合和属性完全一致。

常见例子：

- `HDR10` 只匹配 `{ dr = 2 }`，不会在同为 HDR10 时继续按 `code=5(AV1)`、`code=1(H265)` 打破平局。
- `DOLBY_VISION` 只匹配 `{ dr = 1 }`，不会在同为 Dolby Vision 时继续按 `ff=fmp4/265ts`、`code` 或 `drmType` 打破平局。

### 请求 vid 不一定参与选流

URL 带 `vid` 不代表一定按该 vid 起播。`get_selectable_rates_by_vid_or_vvid()` 只有 `ps=1` 或 `tvvid` 时才会按 vid 收敛；普通 `ps=0` 请求仍按 `bid`、`np`、`prio` 等规则选择。

### pano 参数不一定是核心

`pano264`、`pano265` 主要限制特定 pano 类型下的最高 bid，不负责同 bid 候选的 ff/code 二级排序。遇到 pano 请求仍要先看是否进入 VR/pano 规则，再判断它是否真的改变候选集合。

### 不能回放到选流时如何处理

如果某个 profile 本地返回：

- `st=800` 且 `ctl.boss_ts_fail=true`：说明被 boss_ts 检查提前拦截。
- `st=803` 且日志出现 `fshark`、`couchbase`、`/vp`、`/vpr` 错误：说明元数据未取到，不能据此判断选流。

这种情况下可以临时 mock boss 或旁路非核心校验，但如果 fshark 数据源本身不可达，只能基于可回放环境结果、用户提供的线上 access log、代码逻辑做结论，并明确说明验证边界。

## 输出模板

```markdown
结论：两个环境选中不同的直接原因是 <候选集合不同/同优先级候选顺序不同>。

验证结果：
- `<profile A>`：选中 `bid=... vid=... code=... ff=... dr=... drmType=...`
- `<profile B>`：选中 `bid=... vid=... code=... ff=... dr=... drmType=...`

关键差异：
- <列出同 bid 候选顺序或被过滤规则>

代码原因：
- <具体文件/函数>
- <为什么现有逻辑会选 selected[1] 或被某规则过滤>

验证边界：
- <是否有本地无法连 fshark/boss 等限制>
- <是否使用过临时 mock/旁路，是否已还原>
```
