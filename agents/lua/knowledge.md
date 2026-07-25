# Dash 调试知识库

## 清晰度 bid 对照

- 100: 极速
- 200: 240P
- 300: 360P/480P
- 500: 720P
- 600: 1080P
- 800: 4K
- 860: 4K HDR

## drmType 对照

- 1: NONE_DRM（非 DRM）
- 3: INTER_TRUST_DRM
- 5: IQIYI_CHINA_DRM
- 7: WIDEVINE_DRM
- 8: PLAYREADY_DRM
- 9: FAIRPLAY

## 本地环境常见问题

- `nginx-dev/play-nginx` 需先执行 `./build-nginx-dev.sh`
- macOS 需安装 `pcre2`、`lua-zlib`（luarocks 安装到 OpenResty LuaJIT）
- 缺 zlib 会导致 `core.rule_process` 加载失败，dash 返回 st=1500

## 查视频原始码流

可直接调 fshark VP 接口查元数据（不经过 dash 过滤）：

```bash
curl "http://fshark.video.qiyi.smart/vp?tvId={tvid}&tm=$(date +%s000)"
```

返回 `program.video` 数组，按 `drmType==1` 过滤后取最大 `bid` 即为非 DRM 最高清晰度。

## 下载非 DRM 1080P 到本地（调试流程）

1. mock `boss.lua` 的 `proxy_boss` 跳过鉴权
2. 在 `m3u8.lua` 中强制选中 `bid=600 && drmType=1` 最高 `vsize` 码流并写 m3u8 到 `logs/download_1080.m3u8`
3. ffmpeg 合并：

```bash
ffmpeg -protocol_whitelist "file,http,https,tcp,tls,crypto" \
  -i nginx-dev/play-nginx/logs/download_1080.m3u8 \
  -c copy -bsf:a aac_adtstoasc downloads/3929509678409800_1080p.mp4
```

本地 `init.lua` 的 luarocks cpath 需为 `.../?.so` 格式，否则 zlib 加载失败。
