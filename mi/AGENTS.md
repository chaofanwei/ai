## 环境

- 本机python位置： ./miniconda3/envs/py3.11/bin/ 下面，里面有python和pip命令
- pip已安装了 pyautogui
- 差客切换账号脚本还需要 uiautomator2：`pip install uiautomator2`
- 若手机屏幕处于黑屏或者lock状态，可以通过脚本`unlock.sh`解锁手机


## adb和scrcpy命令 （只是我记录的备忘信息，你可以忽略）

- 息屏后点亮屏幕：adb shell su -c 'svc power stayon true'  或者 adb shell su -c 'input keyevent 26'
- 亮屏后滑动到手势解锁界面：adb shell su -c 'input swipe 500 1800 500 300'
- 支持鼠标点击： 开启 USB调试（安全设置）
- 分辨率: Physical size: 1080x2340

## 技能或知识点

- `unlock.sh` 用于解锁当前手机，即从锁屏/黑屏 状态进入到主屏幕
- `chake_refund.py` 用于打开差客app，并申请退款订单
- `chake-refund.sh` 依次为两个账号批量申请退款（退款 -> 切换 -> 退款 -> 切回）
- `chake_buy_vip.py` 用于打开差客app，并购买指定金额的贵宾VIP卡
- `chake-switch-account.py` 用于在差客 App 的两个测试账号之间自动切换
- `alipay_hotel_orders.py` 用于打开支付宝账单，按截止日期 OCR 解析“酒店订单”，进入详情页提取付款银行卡尾号和订单金额
- `meituan_scan_pay.py` 用于打开美团，选择收藏相册里的二维码图片并发起扫码支付
- `unionpay_scan_pay.py` 用于打开云闪付，选择相册第二行指定二维码照片，输入金额并发起支付
- 上面脚本执行时间可能都比较长，10分钟内算正常，即不要强行停止
- 可以自主调用当前文件夹下面的所有shell, python脚本，无需询问

## 差客脚本使用说明

### `chake-switch-account.py` 切换登录账号

- 用途：在差客/差旅无忧 App 的两个测试账号之间自动切换。脚本会先进入「我的」页面，读取「您好，\<姓名\>」判断当前账号，退出登录后再登录另一个账号。

```bash
# 切换账号（从当前账号切到另一个）
/Users/weichaofan/miniconda3/envs/py3.11/bin/python chake-switch-account.py --execute
```

详细流程见 `notes/差客-切换账号.md`。

**依赖：**

- 需要安装 `uiautomator2`：`/Users/weichaofan/miniconda3/envs/py3.11/bin/pip install uiautomator2`
- 首次连接手机时会自动部署 ATX agent

**注意事项：**

- 密码通过 uiautomator2 写剪贴板 + 粘贴输入，不要用 `adb input text`（会把字母变成大写）
- 多次登录失败可能出现图片验证码，脚本会报错并停止，需人工处理一次后再跑

### `chake_refund.py` 自动申请退款

- 用途：打开差客/差旅无忧 App，进入“我的” -> “贵宾VIP卡订单列表”，批量处理可申请退款的订单。

```bash
/Users/weichaofan/miniconda3/envs/py3.11/bin/python chake_refund.py --execute
```

### `chake-refund.sh` 两个账号依次退款

- 用途：先对当前登录账号跑退款，再切换账号、对另一账号退款，最后切回原账号。微信通知会带各自账号名。

```bash
./chake-refund.sh --execute
```

### `chake_buy_vip.py` 购买贵宾 VIP 卡

- 用途：打开差客 App，进入“贵宾服务”，按目标金额选择最接近的贵宾 VIP 卡价格和数量组合，并进入购买流程。第一个参数就是表示本次要购买的金额

```bash
/Users/weichaofan/miniconda3/envs/py3.11/bin/python chake_buy_vip.py 40000 --execute
```

## 支付宝脚本使用说明

### `alipay_hotel_orders_all.py` 识别支付宝里面的酒店订单的付款银行卡信息到远程账本里面。

- 用途：把3个支付宝帐号里面的酒店订单的银行卡信息同步到远程账本。

```bash
/Users/weichaofan/miniconda3/envs/py3.11/bin/python alipay_hotel_orders_all.py --execute
```

## 美团脚本使用说明

### `meituan_scan_pay.py` 美团扫码支付

- 用途：打开美团app，进行扫码支付，可以指定支付多少元和第几个商户。

```bash
/Users/weichaofan/miniconda3/envs/py3.11/bin/python -u meituan_scan_pay.py 60 1 --execute
```

## 云闪付脚本使用说明

### `unionpay_scan_pay.py` 云闪付相册二维码支付

- 用途：打开云闪付，点击「扫一扫」->「相册」，选择第二行第 1/2/3 张二维码照片，输入指定金额并点击确认支付。脚本会等待支付成功页；支付认证阶段需要人工或系统自动完成。其中只有第1张支持100到200之间的金额，其他两张都要小于100元。

```bash
/Users/weichaofan/miniconda3/envs/py3.11/bin/python -u unionpay_scan_pay.py 159 1 --execute
```

详细流程见 `notes/云闪付支付.md`。
