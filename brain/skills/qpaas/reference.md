# QPaas 模版更新参考

## 常用应用

| 应用 | appId | 说明 |
|---|---|---|
| vrs-dash-qpaas | `4454` | dash 主站 |
| vrs-live-nginx | `4091` | 直播前端 |
| vrs-ops | `15763` | 运维侧 dash 相关环境 |

## dash（4454）已更新模版（20260722）

| 新模版 | 来源模版 | 环境 |
|---|---|---|
| `inter-prerelease20260722` | `inter-prerelease` | inter-prerelease |
| `AZ-20260722` | `AZ-20251022` | DEFAULT-AZ, test |
| `dash-grey-20260722-2` | `dash-grey-20250721-2` | grey-AZ |
| `inter-qlb-service20260722` | `inter-qlb-service` | inter, inter-audio |
| `inter-qlb-service-grey-v320260722` | `inter-qlb-service-grey-v3` | inter-grey, inter-grey-audio |
| `OTT-ZA-20260722` | `OTT-ZA-20250806` | OTT-AZ, OTT-AZ-INTER |
| `dash_pre20260722` | `dash_pre` | pre, pre-last |
| `AZ-20260722-prerelease-qlbservice` | `AZ-2025-prerelease-qlbservice` | prerelease-AZ |
| `UNIT2-AZ20260722` | `UNIT2-AZ 2025-07-31 16:17:12` | UNIT2-AZ |
| `INTER20260722` | `INTER 2025-07-31 17:14:24` | UNIT2-INTER |

## live（4091）已更新模版（20260722）

| 新模版 | 来源模版 | 环境 |
|---|---|---|
| `live-default-az20260722` | `live-default-az` | DEFAULT-AZ, SHOP-AZ, test |
| `live-grey-az20260722` | `live-grey-az` | grey-AZ, inter, inter-grey |
| `live-pre20260722` | `live-pre` | pre, pre-last, prerelease-AZ |
| `inter-prerelease20260722` | `inter-prerelease20260624` | inter-prerelease |
| `live-hk-20260722` | `live-hk-20250327` | UNIT2-INTER |

## vrs-ops（15763）已更新模版（20260722）

| 新模版 | 来源模版 | 环境 |
|---|---|---|
| `dash_legao_yulan20260722` | `dash_legao_yulan` | dash_legao_yulan |
| `dash-qcp-v320260722` | `dash-qcp-v3` | dash-qcp |
| `dash-test20260722` | `dash-test` | dash-test |

## 精确匹配代码片段

### 导入下拉（创建模版）

```javascript
const items = [...document.querySelectorAll('.el-select-dropdown__item span, .el-select-dropdown__item')];
const target = items.find(el => {
  const t = el.textContent.trim();
  return t === importFrom || t.startsWith(importFrom + '（');
});
if (target) target.click();
```

### 环境绑定下拉

```javascript
const items = [...document.querySelectorAll('.el-select-dropdown__item')];
const target = items.find(el => {
  const t = el.textContent.trim();
  return t === template || t.startsWith(template + '（');
});
if (target) target.click();
```

### 插入 fastjson（Ace 编辑器）

```javascript
const ed = window.ace.edit(document.querySelector('.ace_editor'));
const needle = '            - "-Dspring.profiles.active=${PROFILE_AGENT}"\n            - "-jar"';
const replacement = '            - "-Dspring.profiles.active=${PROFILE_AGENT}"\n            - "-Dfastjson.parser.safeMode=true"\n            - "-jar"';
if (!ed.getValue().includes('-Dfastjson.parser.safeMode=true') && ed.getValue().includes(needle)) {
  ed.setValue(ed.getValue().replace(needle, replacement), -1);
}
```

## 错误模版重建步骤

1. 将绑定环境 **改回** 旧模版并保存
2. 删除错误新模版（未部署时才可删）
3. 从正确来源 **精确导入** 重建
4. 加 fastjson → 确定发版
5. 环境改绑新模版
6. **版本对比** 验收（1 行差异）

## URL 快捷路径

| 操作 | URL |
|---|---|
| 环境详情 | `#/app/appDetail/{appId}/PROD_{envName}` |
| 创建模版 | `#/app/appDetail/{appId}/version/createVersion?verType=deploy` |
| 模版列表 | `#/app/appDetail/{appId}/version?vTab=done&tab=version` |
