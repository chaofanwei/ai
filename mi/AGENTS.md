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

