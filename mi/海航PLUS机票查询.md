# 海航PLUS机票查询流程

## 前置准备

- 确保手机已解锁（如未解锁，运行 `./unlock.sh`）
- 确保已安装 `paddleocr`（用于OCR识别）
- ADB路径：`/Users/weichaofan/Library/Android/sdk/platform-tools/adb`

## 完整查询流程

### 1. 打开海南航空APP

```bash
/Users/weichaofan/Library/Android/sdk/platform-tools/adb shell monkey -p com.rytong.hnair -c android.intent.category.LAUNCHER 1
```

### 2. 进入海航PLUS权益卡页面

在APP首页找到并点击"海航PLUS权益卡"入口（大约在屏幕下方位置）

### 3. 选择出发地

- 点击"选择出发地"
- 在搜索框输入出发城市（如"北京首都"）
- 点击对应城市选项

### 4. 选择目的地

- 点击"选择目的地"
- 在搜索框输入目的地城市（如"乌鲁木齐"或"三亚"）
- 点击对应城市选项

### 5. 选择日期

- 点击日期区域
- 向上/向下滑动日历找到目标日期（如6月19日）
- 点击目标日期

### 6. 搜索机票

- 点击"搜索预订"按钮

### 7. 查看航班价格

- 查看搜索结果中的航班列表
- **注意**：真正的航班信息左边有起飞/到达时间，右边有价格
- 页面上方的"￥199起>"通常是广告，不是具体航班价格
- 如需要看更多航班，可向上滑动页面

## 常用ADB命令参考

```bash
# 截屏
/Users/weichaofan/Library/Android/sdk/platform-tools/adb exec-out screencap -p > screen.png

# 点击坐标 x,y
/Users/weichaofan/Library/Android/sdk/platform-tools/adb shell input tap x y

# 滑动（从x1,y1 到 x2,y2，持续时间毫秒）
/Users/weichaofan/Library/Android/sdk/platform-tools/adb shell input swipe x1 y1 x2 y2 duration

# 返回键
/Users/weichaofan/Library/Android/sdk/platform-tools/adb shell input keyevent KEYCODE_BACK
```

## OCR识别页面内容

当前目录已有 `ocr_page.py` 可用于识别屏幕内容：

```python
from paddleocr import PaddleOCR
from PIL import Image

image_path = 'screen.png'
img = Image.open(image_path)

ocr = PaddleOCR(use_textline_orientation=False, use_doc_orientation_classify=False, use_doc_unwarping=False)
result = ocr.predict(image_path)

for page in result:
    if page:
        for text, box, score in zip(page['rec_texts'], page['rec_polys'], page['rec_scores']):
            print(f"文本: {text}, 置信度: {score:.3f}, 位置: {box}")
```

## 示例查询：北京首都到三亚 6月19号 199的票

下次如果需要查询，可以直接告诉我：
"帮我查询下海航PLUS卡里面有没有北京首都到三亚 6月19号 的199的票"

我会按照上述流程帮你操作。

---

## 流程优化建议

### 之前流程中的慢的环节

#### 1. OCR模型重复加载 ⭐⭐⭐⭐⭐
**问题**：每次运行 `ocr_page.py` 都会重新加载PaddleOCR模型，非常耗时
**优化方案**：参考 `chake_buy_vip.py` 的做法，使用全局变量缓存OCR引擎

```python
_OCR_ENGINE = None

def get_ocr_engine():
    global _OCR_ENGINE
    if _OCR_ENGINE is None:
        import os
        os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
        from paddleocr import PaddleOCR
        _OCR_ENGINE = PaddleOCR(
            use_textline_orientation=False,
            use_doc_orientation_classify=False,
            use_doc_unwarping=False
        )
    return _OCR_ENGINE
```

#### 2. 没有优先用uiautomator ⭐⭐⭐⭐
**问题**：一上来就用OCR，其实uiautomator更快更准确
**优化方案**：先用uiautomator dump，找不到再用OCR

```python
def dump_nodes(adb):
    adb.shell(["uiautomator", "dump", "/sdcard/window.xml"])
    result = adb.run(["exec-out", "cat", "/sdcard/window.xml"])
    # 解析XML...
```

#### 3. 滑动操作比较盲目 ⭐⭐⭐
**问题**：随便滑动，不知道该滑多少
**优化方案**：先看页面内容，再决定滑动方向和距离

#### 4. 截屏再读取文件 ⭐⭐
**问题**：截屏写到文件，再用PIL读，多了一步IO
**优化方案**：可以直接用内存（不过为了调试方便，保留截屏也可以）

### 优化后的查询流程

#### 快速检查清单

1. **先用uiautomator看页面结构** - 快速确认是否在正确页面
2. **OCR引擎只加载一次** - 重复利用，避免重复初始化
3. **OCR前可以裁剪区域** - 只识别需要的部分，提高准确率和速度

#### 参考chake_buy_vip.py的优化技巧

```python
# 裁剪区域只看航班列表
OCR_CROP_BOX = (0, 300, 1080, 2050)

# 只识别数字，去除干扰
def ocr_digits(text):
    return re.sub(r"\D+", "", text)

# 先检查是否有目标价格
def has_target_price(boxes, target):
    target_str = str(target)
    for box in boxes:
        if box.visible and box.score >= 0.5 and ocr_digits(box.text) == target_str:
            return True, box.center
    return False, None
```

#### 下次查询的简化指令

你可以直接说：
"帮我查询海航PLUS：北京首都→三亚，6月19日，找199的票"

我会按照优化后的流程快速执行：
1. 解锁→打开APP→进入PLUS页面
2. 快速选择出发地、目的地、日期
3. 搜索后优先用uiautomator，必要时用OCR
4. 直接告诉你有没有199的票，以及对应的航班时间
