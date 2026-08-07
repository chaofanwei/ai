# Octopus 发布配置笔记

本文记录 `leke-feedback` 在 Octopus 中接入 QCD 构建和 QPaaS 线上部署的配置方法。内容来自 2026-08-04 对 `star-map` 线上流水线、QCD 流水线和 QPaaS 实际工作负载的页面核对。

## 已验证的资源

| 项目 | 值 |
| --- | --- |
| Octopus 应用 | `leke-feedback`（App ID `5484`） |
| 所属项目 | `VRS` |
| QCD 流水线 | `leke-feedback-online` |
| QCD 流水线 ID | `138401` |
| QCD 默认分支 | `master` |
| 镜像仓库 | `docker-registry.qiyi.virtual/video-play/leke-feedback-online` |
| QPaaS 应用 | `vrs-ops`（ID `15763`） |
| QPaaS 生产环境 | `leke-feedback-fronted` |
| 命名空间 | `qke-generic-vrs-ops` |
| 部署位置 | `cnhb4 / iqiyi-cnhb4-az1`（保定定兴） |

注意：现有环境名称确实拼写为 `fronted`，不是 `frontend`。QPaaS 工作负载 `leke-feedback-fronted` 实际使用的镜像仓库是 `leke-feedback-online`，两者名称不同但配置匹配。

## 整体发布流程

```text
填写 VERSION
    ↓
QCD 138401 构建并推送 leke-feedback-online:${VERSION}
    ↓
Octopus 手动确认部署
    ↓
QPaaS 升级 leke-feedback-fronted，IMG_TAG=${VERSION}
```

生产流水线建议使用“自动构建、手动部署”，避免镜像构建完成后未经确认直接更新线上环境。

## 新建 Octopus 应用

进入 `应用 → 新建应用`，填写：

- 应用名称：`leke-feedback`
- 关联项目：`VRS`
- 应用描述：例如 `leke-feedback 发布部署`

保存后进入该应用。

## 关联 QPaaS 环境

进入 `环境 → 新增 QPaaS 环境`，建议填写：

- 环境名称：`QPAAS`
- 环境级别：`PROD / 生产级`
- QPaaS 应用：`vrs-ops`
- 标签：可留空

这里关联的是整个 QPaaS 应用。具体的 `leke-feedback-fronted` 环境在流水线的“QPaaS 部署升级”任务中选择。

如果“QPaaS 应用”下拉框为空，依次检查：

1. Octopus 应用是否已关联 `VRS` 项目。
2. 当前账号是否有 QPaaS 应用 `vrs-ops` 的访问权限。
3. 点击下拉框旁的刷新按钮后重新打开下拉框。
4. 重新进入 Octopus 应用页面，确认项目权限变更已经生效。

不要因为下拉框为空而新建一个同名 QPaaS 应用；应先确认项目和权限。

## 新建线上流水线

进入 `流水线 → 新建新版流水线`：

- 流水线名称：`线上部署`
- 流水线级别：`PROD / 生产级`
- 关注人：至少选择发布负责人
- 通知方式：按团队需要配置

新增流水线全局变量：

| 字段 | 值 |
| --- | --- |
| 变量类型 | `STRING` |
| 变量名 | `VERSION` |
| 变量值 | 留空，由发布时填写 |
| 必填 | 建议勾选 |
| 变量描述 | `发布版本` |

建议的阶段图：

```text
开始 → build image → deploy fronted → 结束
```

### 阶段画布连线

新增阶段后，节点默认可能处于悬空状态：

1. 将鼠标移到源节点上，等待节点边缘出现连接点。
2. 从源节点右侧连接点按住鼠标，拖到目标节点左侧连接点后松开。
3. 如果源节点已经直接连接“结束”，先选中原连线，再点击画布上方的“删除”。
4. 完成新连线后可点击“自动布局”整理位置。

从节点主体拖动只会移动节点，必须从节点边缘的连接点开始拖动才能创建连线。

## `build image` 阶段

进入阶段的“任务设置”，配置一个 QCD 构建任务：

| 字段 | 值 |
| --- | --- |
| 任务名称 | `build&push image` |
| 任务类型 | `QCD 构建` |
| 自动/手动执行 | `自动` |
| 执行方式 | `即时` |
| 任务实际执行身份 | `默认（使用发布者身份）` |
| QCD 流水线 ID | `138401` |
| QCD 缺省构建分支 | `master` |

QCD 构建参数：

```text
IMAGE_NAME = ${VERSION}
```

此参数配置已经与 QCD `138401` 核对，填写正确。发布时如果输入：

```text
VERSION=202608041900
```

最终构建的镜像为：

```text
docker-registry.qiyi.virtual/video-play/leke-feedback-online:202608041900
```

可选的 QCD 构建描述：

```text
构建&发布镜像：docker-registry.qiyi.virtual/video-play/leke-feedback-online:${VERSION}
```

构建描述留空不影响任务执行。

## `deploy fronted` 阶段

进入阶段的“任务设置”，配置 QPaaS 部署任务：

| 字段 | 建议值 |
| --- | --- |
| 任务名称 | `deploy fronted` |
| 任务类型 | `QPaaS 部署 → QPaaS 部署升级` |
| 自动/手动执行 | `手动` |
| 执行方式 | `即时` |
| 环境来源 | 当前 Octopus 应用关联的环境 |
| 环境 | `QPAAS` |
| 集群（已部署） | `leke-feedback-fronted - qke-generic-vrs-ops` |
| 与 QPaaS 环境保持一致 | 关闭，与参考流水线一致 |

QPaaS 模板参数：

```text
IMG_TAG = ${VERSION}
```

`SERVICE_NAME`、`PROFILE`、`CONSUL_CLUSTER` 等参数已配置在 QPaaS 环境信息中，Octopus 流水线通常只覆盖本次发布的 `IMG_TAG`。

## 首次发布验证

1. 点击流水线“发布”，输入非空且唯一的 `VERSION`。
2. 等待 `build&push image` 构建成功。
3. 确认 QCD 已推送对应标签的镜像。
4. 手动执行 `deploy fronted`。
5. 在 QPaaS 工作负载中确认 Pod 已 Ready。
6. 核对实际镜像为：

```text
docker-registry.qiyi.virtual/video-play/leke-feedback-online:${VERSION}
```

若构建成功但部署未更新，优先检查部署任务是否选中了 `leke-feedback-fronted`，以及模板参数名是否为 `IMG_TAG`。
