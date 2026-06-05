# VIDEODEV-5820 点播和直播：qsm域名的upstream优化

## 背景

- PMS: http://pms.qiyi.domain/browse/VIDEODEV-5820
- 需求：nginx-conf 中 qsm 域名 upstream 的 server 关闭被动健康检查。

## 改动

- 分支：fan_5820_qsm_upstream_max_fails
- 修改 `~/lua/projects/live-luna/nginx-config/nginx1/conf/upstreams/upstream.common.live.video.qiyi.com.conf`
- 给 qsm 域名 upstream 的 server 配置增加 `max_fails=0`：
  - `bvd-live-pre.qsm.qiyi.middle`
  - `bvd-live-bdxs.qsm.qiyi.middle`
  - `bvd-live-intel-huawei.qsm.qiyi.middle`
  - `bvd-live-ali-sg.qsm.qiyi.middle`
  - `bvd-live-use-ali.qsm.qiyi.middle`
  - `bvd-live-bddx.qsm.qiyi.middle`
  - `bvd-live-whlkg.qsm.qiyi.middle`
  - `drm-live.qsm.qiyi.middle`
  - `intl-drm-live.qsm.qiyi.middle`
  - `vip-auth.qsm.qiyi.middle`

## 修改时间

- 2026-06-01 16:49:16 CST

## Codex Session

- 当前对话未提供可读取的 session id。
