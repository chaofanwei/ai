# VIDEODEV-5853 国际站互动鉴权时播放判断基于地区判断播控

## 基本信息

- PMS: http://pms.qiyi.domain/browse/VIDEODEV-5853
- 分支: fan_5853_inter_auth_region_playcontrol
- 修改时间: 2026-07-03
- Codex session: 019f2261-1681-7f50-af48-f47f73c667d3

## 背景

互动视频鉴权当前触发条件是互动视频内容，并且当前平台 `control.platform[pf].common.a == 2`。
该判断只看播控默认状态，没有结合地区播控。默认下线但当前地区明确上线时，仍会进入互动鉴权。

## 改动

在 `p911/rules/pre/ovi.lua` 的互动鉴权入口增加地区播控上线判断：

- 保留原有互动内容判断：`data.p.ovi.enable == 1` 或 `data.content.contentType == 27`。
- 保留原有默认播控判断：`control.platform[pf].common.a == 2`。
- 新增当前地区判断：按 `city/province/country/continent/area` 顺序检查当前请求命中的地区配置。
- 如果当前地区 `a == 1` 或 `a == 4`，认为地区已上线，不进入互动鉴权。
- 如果当前地区没有明确上线配置，保持原逻辑，继续进入互动鉴权。

## 测试

- `busted spec/p911/rules/pre/ovi_spec.lua`：5 successes。
- `git diff --check`：通过。

## 提交

- commit: `c9cf5479c`
- message: `国际站互动鉴权时播放判断基于地区判断播控 http://pms.qiyi.domain/browse/VIDEODEV-5853`
- 远端分支: `origin/fan_5853_inter_auth_region_playcontrol`
