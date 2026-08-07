# VRS Retry 域名切换运维手册

本文记录 VRS retry 域名在伏羲 DNS 和 Skywalker 网关中的配置关系、操作步骤与核验结果。

最后核验时间：2026-08-04。

## 系统入口

- 伏羲 retry 域名列表：`http://dns.cloud.qiyi.domain/dns/service/index?name=retry-`
- Skywalker API 列表：`http://skywalker.cloud.qiyi.domain/apis/prod-advance`
- 伏羲使用文档：`https://iq.feishu.cn/wiki/TZGbwazLhik8UOkKNcJcPNaJnBm`
- 继承域名解绑章节：伏羲使用文档的 `2.2.1.3.1、继承域名解绑`

需要浏览器自动化时，执行：

```bash
~/shells/start-ai-chrome.sh
```

浏览器使用 remote debugging port `9222`。

## 网关域名映射

| 普通网关域名 | Retry 镜像网关域名 | 说明 |
| --- | --- | --- |
| `apigw-vrs.iqiyi.com` | `retry-apigw-vrs.iqiyi.com` | iqiyi.com 外网域名 |
| `apigw-vrs.qiyi.domain` | `retry-apigw-vrs.qiyi.domain` | qiyi.domain 内网域名 |
| `apigw-vrs.ptqy.gitv.tv` | `retry-apigw-vrs.ptqy.gitv.tv` | ptqy.gitv.tv 外网域名 |
| `apigw-v6-vrs.ptqy.gitv.tv` | `retry-apigw-v6-vrs.ptqy.gitv.tv` | ptqy.gitv.tv 双栈网关 |

## 当前 DNS 配置

| 伏羲 ID | Retry 域名 | 预期 CNAME | 区域说明 |
| --- | --- | --- | --- |
| `6558426` | `retry-pre-cache.video.ptqy.gitv.tv` | `retry-apigw-vrs.ptqy.gitv.tv` | 仅 `default` |
| `6558425` | `retry-pre-cache.video.iqiyi.com` | `retry-apigw-vrs.iqiyi.com` | 仅 `default` |
| `6558424` | `retry-pre-cache.video.qiyi.domain` | `retry-apigw-vrs.qiyi.domain` | 仅内网默认区域 |
| `6522740` | `retry-live.video.ptqy.gitv.tv` | `retry-apigw-vrs.ptqy.gitv.tv` | 仅 `default` |
| `6521051` | `retry-live.video.iqiyi.com` | `retry-apigw-vrs.iqiyi.com` | 仅 `default` |
| `6456594` | `retry-cache.video.qiyi.domain` | `retry-apigw-vrs.qiyi.domain` | 仅内网默认区域 |
| `6453490` | `retry-cache.video.ptqy.gitv.tv` | `retry-apigw-vrs.ptqy.gitv.tv` | `default` 已切换；另有两个特殊区域，见下文 |
| `6453489` | `retry-sdk-cache.video.ptqy.gitv.tv` | `retry-apigw-vrs.ptqy.gitv.tv` | 仅 `default` |
| `6442233` | `retry-cache.video.iqiyi.com` | `retry-apigw-vrs.iqiyi.com` | 仅 `default` |
| `6588175` | `retry-shop-live.video.iqiyi.com` | `retry-apigw-vrs.iqiyi.com` | 已解除继承，仅保留 `default` |
| `6596871` | `retry-shop-live.video.ptqy.gitv.tv` | `retry-apigw-vrs.ptqy.gitv.tv` | 已解除继承，仅保留 `default` |

### 特殊区域

`retry-cache.video.ptqy.gitv.tv` 除 `default` 外还有两个四川移动区域：

- `as-cn-cmn-xn-sc`：A 记录，保留原配置。
- `as-cn-cmn-xn-sc-iptv`：CNAME 仍为 `apigw-vrs.ptqy.gitv.tv`。伏羲页面明确禁止修改该区域，不能绕过平台限制。

## 继承域名解绑

以下两个域名最初继承父域名配置：

- `retry-shop-live.video.iqiyi.com` 继承 `live.video.iqiyi.com`
- `retry-shop-live.video.ptqy.gitv.tv` 继承 `live.video.ptqy.gitv.tv`

解绑流程：

1. 在“我的域名”中搜索 retry 域名。
2. 展开父域名下的“继承此域名的域名”。
3. 在目标子域名右侧选择“操作 → 归属变更”。
4. 在“继承域名”字段右侧点击清除按钮 `×`。
5. 保持项目、负责人、部门等其他信息不变，点击“保存”。
6. 等待列表刷新，确认子域名已经成为独立域名并获得自己的伏羲 ID。

伏羲文档说明：解绑后默认保留父域名当时的解析配置，后续修改不再影响父域名。解绑后应进入独立域名的配置页，删除不需要的继承区域。

本次两个 `retry-shop-live` 域名均要求只保留 `default`，其余区域全部删除。

## 伏羲 DNS 修改流程

1. 打开配置变更页：`/dns/set/index?id=<伏羲ID>&conf_type=NORMAL`。
2. 勾选需要修改的区域，点击“编辑选中”。
3. 弹窗中的记录类型可能默认显示为 A，即使原记录是 CNAME；必须先选择 `CNAME`，再填写目标域名。
4. 保存弹窗后，在列表中检查变更差异：
   - 修改行应显示新旧 CNAME。
   - 删除行应标记为删除状态。
   - 不应误改不在范围内的特殊区域。
5. 填写改动原因，例如：`retry域名切换至镜像网关`。
6. 点击页面底部“提交”。
7. 等待数秒后打开配置查看页：`/dns/service/manage?id=<伏羲ID>&conf_type=NORMAL`。
8. 核对域名、区域数量、记录类型和最终 CNAME，不能只依赖提交成功提示。

操作应逐个域名完成并验证后再处理下一个。所有变更通过页面表单完成，不直接调用后台接口执行。

## Skywalker 调度策略

下列 API 的服务配置调度策略均已核验为“就近”：

| API ID | 域名 | 最终调度策略 |
| --- | --- | --- |
| `42901` | `retry-pre-cache.video.ptqy.gitv.tv` | 就近 |
| `42902` | `retry-pre-cache.video.iqiyi.com` | 就近 |
| `42900` | `retry-pre-cache.video.qiyi.domain` | 就近 |
| `39446` | `retry-live.video.ptqy.gitv.tv` | 就近 |
| `39445` | `retry-live.video.iqiyi.com` | 就近 |
| `36552` | `retry-cache.video.qiyi.domain` | 就近 |
| `36569` | `retry-cache.video.ptqy.gitv.tv` | 就近 |
| `36570` | `retry-sdk-cache.video.ptqy.gitv.tv` | 就近 |
| `36571` | `retry-cache.video.iqiyi.com` | 就近 |
| `51565` | `retry-shop-live.video.iqiyi.com` | 就近 |
| `54014` | `retry-shop-live.video.ptqy.gitv.tv` | 就近 |

### Skywalker 修改流程

1. 在 API 列表中使用完整 retry 域名搜索。
2. 检查搜索结果中的域名，点击 API ID 进入详情页。
3. 点击右侧“直接修改线上 API 配置（旧模式）”。
4. 保持在“基础配置”页签。
5. 在“服务配置”区域点击第一个“编辑”按钮，不要误点“上游服务协议”的编辑按钮。
6. 在弹窗中将“调度策略”从“自定义”改为“就近”。
7. 点击“确认”。
8. 返回基础配置页，确认页面明确显示 `调度策略: 就近`。

搜索框按 Enter 偶尔不会触发查询，此时点击搜索框右侧的搜索按钮，并检查结果总数和完整域名，避免操作错误 API。

## 完成检查清单

- [ ] 域名与伏羲 ID 对应正确。
- [ ] CNAME 使用与域名后缀对应的 retry 网关。
- [ ] `retry-shop-live` 仅保留 `default`。
- [ ] 特殊或锁定区域没有被误删、误改。
- [ ] DNS 提交后从“配置查看”页重新核验。
- [ ] Skywalker 搜索结果的完整域名正确。
- [ ] 修改的是“服务配置”，不是“上游服务协议”。
- [ ] Skywalker 基础配置最终显示“调度策略：就近”。
