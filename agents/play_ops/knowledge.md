# play_ops 运维知识

## dash 服务

- dash 服务的 nginx-conf 更新使用 `starmap` 分支的 `nginx_deploy/deploy_nginx_conf.sh` 脚本。
- dash qpaas 的 `porsche_zone` 限流在 `nginx_deploy/deploy_nginx_conf.sh` 的 k8s 构建阶段调整，目标文件是运行时克隆的 `play-nginx/conf/vh.cache.video.qiyi.com.conf`。
- dash nginx-conf k8s 包的 profile 映射：国内主站使用 `*_upsync` 包；国际新加坡使用 `xjp`；国际北美使用 `use`。

## live 服务

- live 服务的 nginx-conf 更新使用 `starmap` 分支的 `live_nginx_conf/deploy_nginx_conf.sh` 脚本。
- live 的 nginx-conf 配置仓库是 `ssh://git@gitlab.qiyi.domain:10022/live-video-play/nginx-config.git`。
- live qpaas 的 `live_zone` 限流在 `live_nginx_conf/deploy_nginx_conf.sh` 的 k8s 构建阶段调整，目标文件是 `nginx1/conf/vh/*/vh.live.video.qiyi.com.conf` 里的 `limit_req_zone LIVE zone=live_zone`。
- live 国际站 profile 映射：新加坡使用 `ali-sg` 和 `intel-huawei`；北美使用 `use_ali`。
