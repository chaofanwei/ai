# 差客(chake) 对账接口 Wiki

记录每次购买流水，支持退款状态跟踪（申请 → 到帐）。

- **服务地址**：`http://myroute.cn`
- **管理页面**：<http://myroute.cn/chake/page>
- **支持账号**：`wei`、`chang`（其他值会被拒绝）

---

## 一、快速开始

### 1. 浏览器使用

直接打开 <http://myroute.cn/chake/page>：

1. 顶部下拉框选择账号（`wei` / `chang`）
2. 表格展示该账号的全部购买记录，**按购买时间倒序**，每页 20 条
3. 点击"申请退款"把这条记录的"已申请退款"置为是
4. 点击"已到帐"把这条记录的"退款已到帐"置为是
5. 已置过的状态按钮会自动变灰禁用

### 2. 用 API 新增一条记录

```bash
curl -X POST http://myroute.cn/chake/add \
  -H 'Content-Type: application/json' \
  -d '{
    "account_name": "wei",
    "purchase_time": "2026-06-01 10:00:00",
    "purchase_amount": 199
  }'
```

返回：

```json
{ "code": 0, "id": 42 }
```

拿到 `id` 后，后续可用 `/chake/update` 修改任意字段。

---

## 二、统一返回格式

所有 JSON 接口返回结构一致：

```json
{ "code": 0, "msg": "可选错误描述", "其它业务字段": "..." }
```

- `code = 0`：成功
- `code != 0`：失败，看 `msg`

常见错误 `msg`：

| msg | 含义 |
|---|---|
| `account_name required` | 没传账号 |
| `unknown account_name` | 账号不在 `wei` / `chang` 中 |
| `account_name, purchase_time, purchase_amount are required` | 新增时三个必填没传齐 |
| `invalid purchase_time, expect YYYY-MM-DD HH:MM:SS` | 时间格式不对 |
| `purchase_amount must be integer` | 金额不是整数 |
| `id required` / `id must be integer` | 更新没传 id 或 id 不是数字 |
| `no updatable field` | 更新时没传任何可改字段 |

---

## 三、接口列表

### 3.1 GET `/chake/list` —— 分页查询

**Query 参数**

| 参数 | 必填 | 默认 | 说明 |
|---|---|---|---|
| `account_name` | 是 | - | `wei` 或 `chang` |
| `page` | 否 | 1 | 页码，从 1 开始 |
| `page_size` | 否 | 20 | 每页条数，最大 100 |

**请求**

```bash
curl 'http://myroute.cn/chake/list?account_name=wei&page=1&page_size=20'
```

**响应**

```json
{
  "code": 0,
  "total": 37,
  "page": 1,
  "page_size": 20,
  "items": [
    {
      "id": 12,
      "account_name": "wei",
      "purchase_time": "2026-06-01 10:00:00",
      "purchase_amount": 199,
      "payment_card_bank": "招商",
      "payment_card_last_digits": "1234",
      "refund_applied": 1,
      "refund_received": 0,
      "create_time": "2026-06-01 10:00:05",
      "update_time": "2026-06-01 10:30:00"
    }
  ]
}
```

排序固定为 `purchase_time DESC, id DESC`。

---

### 3.2 POST `/chake/add` —— 新增记录

**Header**：`Content-Type: application/json`

**Body 字段**

| 字段 | 必填 | 类型 | 说明 |
|---|---|---|---|
| `account_name` | 是 | string | `wei` 或 `chang` |
| `purchase_time` | 是 | string | 时间，支持三种格式：`YYYY-MM-DD HH:MM:SS` / `YYYY-MM-DD HH:MM` / `YYYY-MM-DD` |
| `purchase_amount` | 是 | int | 购买金额（整数，单位元） |
| `payment_card_bank` | 否 | string | 支付卡银行，如 `招商` |
| `payment_card_last_digits` | 否 | string | 卡尾号，建议传字符串以保留前导 0，如 `"0123"` |
| `refund_applied` | 否 | 0/1/bool | 是否已申请退款，默认 0 |
| `refund_received` | 否 | 0/1/bool | 退款是否已到帐，默认 0 |

**请求**

```bash
curl -X POST http://myroute.cn/chake/add \
  -H 'Content-Type: application/json' \
  -d '{
    "account_name": "wei",
    "purchase_time": "2026-06-01 10:00:00",
    "purchase_amount": 199,
    "payment_card_bank": "招商",
    "payment_card_last_digits": "1234"
  }'
```

**响应**

```json
{ "code": 0, "id": 42 }
```

---

### 3.3 POST `/chake/update` —— 按 ID 更新字段

按 `id` 修改任意字段子集，未传的字段保持不变。

**Header**：`Content-Type: application/json`

**Body 字段**

| 字段 | 必填 | 说明 |
|---|---|---|
| `id` | 是 | 记录 ID（来自 `/chake/add` 返回，或 `/chake/list` 中的 `id`） |
| 任意可改字段 | 否 | 见下方白名单 |

**可改字段白名单**

```
account_name
purchase_time
purchase_amount
payment_card_bank
payment_card_last_digits
refund_applied
refund_received
```

白名单之外的字段会被静默忽略（不会报错）。

**示例 1：标记已申请退款**

```bash
curl -X POST http://myroute.cn/chake/update \
  -H 'Content-Type: application/json' \
  -d '{"id": 42, "refund_applied": 1}'
```

**示例 2：一次更新多个字段（补登卡信息 + 标记到帐）**

```bash
curl -X POST http://myroute.cn/chake/update \
  -H 'Content-Type: application/json' \
  -d '{
    "id": 42,
    "payment_card_bank": "工行",
    "payment_card_last_digits": "5678",
    "refund_received": 1
  }'
```

**示例 3：回滚状态**（误点了"已到帐"想撤销）

```bash
curl -X POST http://myroute.cn/chake/update \
  -H 'Content-Type: application/json' \
  -d '{"id": 42, "refund_received": 0}'
```

**响应**

```json
{ "code": 0, "updated": 1 }
```

`updated` 是 MySQL 影响行数：

- `1`：成功更新
- `0`：`id` 不存在，或新值跟原值完全一致（MySQL 视为未变化）

---

### 3.4 GET `/chake/page` —— 管理页面

返回 HTML 页面，浏览器直接访问即可，不需要任何参数。

---

## 四、字段一览

| 字段 | 类型 | 示例 | 说明 |
|---|---|---|---|
| `id` | int | `42` | 主键，自增 |
| `account_name` | string | `"wei"` | 账号，仅 `wei` / `chang` |
| `purchase_time` | string | `"2026-06-01 10:00:00"` | 购买时间 |
| `purchase_amount` | int | `199` | 金额，整数元 |
| `payment_card_bank` | string / null | `"招商"` | 支付卡银行 |
| `payment_card_last_digits` | string / null | `"1234"` | 卡尾号 |
| `refund_applied` | 0/1 | `1` | 是否已申请退款 |
| `refund_received` | 0/1 | `0` | 退款是否已到帐 |
| `create_time` | string | `"2026-06-01 10:00:05"` | 创建时间，自动 |
| `update_time` | string | `"2026-06-01 10:30:00"` | 最近一次更新时间，自动 |

---

## 五、典型对账流程

1. 下单后调用 `/chake/add` 落库 → 拿到 `id`
2. 申请退款时调用 `/chake/update`，置 `refund_applied=1`
3. 收到退款到帐通知后调用 `/chake/update`，置 `refund_received=1`
4. 任何时候可在浏览器打开 `/chake/page` 选账号查看状态；或调 `/chake/list` 拉数据自行展示

---

## 六、FAQ

**Q：账号能加吗？比如新增一个 `zhang`？**
A：联系开发改一行配置即可。当前服务端有账号白名单，前端下拉也会同步刷新。

**Q：金额可以是小数（如 `19.9`）吗？**
A：不行。`purchase_amount` 必须是整数（单位元）。如果以后要支持分，需要后端改成"以分为单位"重新发布。

**Q：卡尾号传数字会不会丢前导 0？**
A：传字符串 `"0123"` 是安全的；如果传数字 `123` 会按 `"123"` 入库。建议统一传字符串。

**Q：时间能不能传时间戳？**
A：暂不支持。请用 `"YYYY-MM-DD HH:MM:SS"` 格式（`HH:MM` 或 纯日期 `YYYY-MM-DD` 也可以，会自动补 0）。

**Q：分页拉到底之后 `next` 还能点吗？**
A：页面会在最后一页自动禁用"下一页"按钮。如果你是直接调 API，自行用 `total / page_size` 判断即可。

**Q：怎么删除一条记录？**
A：目前未提供删除接口。如确需删除请直连数据库处理，或联系开发新增 `/chake/delete`。
