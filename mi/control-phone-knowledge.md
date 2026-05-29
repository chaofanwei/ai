# 手机控制知识：截屏、OCR 定位、点击和滑动

本文记录在当前工作目录中控制 Android 手机的常用方法。设备分辨率按现有脚本经验为 `1080x2340`，adb 路径为：

```bash
/Users/weichaofan/Library/Android/sdk/platform-tools/adb
```

本机 Python 路径：

```bash
/Users/weichaofan/miniconda3/envs/py3.11/bin/python
```

如果手机黑屏或锁屏，可以先运行：

```bash
./unlock.sh
```

## 1. adb 基础操作

点击指定坐标：

```bash
/Users/weichaofan/Library/Android/sdk/platform-tools/adb shell input tap 540 1200
```

滑动：

```bash
/Users/weichaofan/Library/Android/sdk/platform-tools/adb shell input swipe 540 1700 540 850 650
```

参数含义：`x1 y1 x2 y2 duration_ms`。例如上面的命令表示从屏幕下方向上滑，持续 `650ms`。

常见方向：

```bash
# 向上翻页：手指从下往上划
adb shell input swipe 540 1700 540 850 650

# 向下翻页：手指从上往下划
adb shell input swipe 540 850 540 1700 650

# 横向左滑
adb shell input swipe 820 330 180 330 700
```

启动 App：

```bash
adb shell monkey -p com.slwy.shanglvwuyou -c android.intent.category.LAUNCHER 1
```

停止 App：

```bash
adb shell am force-stop com.slwy.shanglvwuyou
```

## 2. 截屏

推荐用 `exec-out screencap -p`，可以直接把 PNG 写到本机文件：

```bash
/Users/weichaofan/Library/Android/sdk/platform-tools/adb exec-out screencap -p > screen.png
```

Python 写法：

```python
from pathlib import Path
import subprocess

ADB = "/Users/weichaofan/Library/Android/sdk/platform-tools/adb"

def screencap(path: str = "screen.png") -> Path:
    proc = subprocess.run(
        [ADB, "exec-out", "screencap", "-p"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=12,
        check=True,
    )
    output = Path(path)
    output.write_bytes(proc.stdout)
    return output
```

## 3. 用 uiautomator 识别控件文字位置

如果目标文字是原生控件文本，优先使用 `uiautomator dump`，比 OCR 更快、更稳定。

导出当前 UI XML：

```bash
adb shell uiautomator dump /sdcard/window.xml
adb exec-out cat /sdcard/window.xml > window.xml
```

XML 中常见字段：

- `text`：控件显示文字
- `bounds`：控件矩形，例如 `[338,1649][786,1745]`
- `clickable`：控件是否可点击
- `class`：控件类型

根据 `bounds` 算中心点：

```python
import re
import subprocess
import xml.etree.ElementTree as ET
from dataclasses import dataclass

ADB = "/Users/weichaofan/Library/Android/sdk/platform-tools/adb"

@dataclass(frozen=True)
class UINode:
    text: str
    bounds: str
    clickable: bool

    @property
    def nums(self) -> tuple[int, int, int, int] | None:
        values = tuple(map(int, re.findall(r"\d+", self.bounds or "")))
        return values if len(values) == 4 else None

    @property
    def center(self) -> tuple[int, int]:
        x1, y1, x2, y2 = self.nums
        return (x1 + x2) // 2, (y1 + y2) // 2

    @property
    def visible(self) -> bool:
        x1, y1, x2, y2 = self.nums
        return x2 > x1 and y2 > y1 and y2 > 245 and y1 < 2135

def dump_nodes() -> list[UINode]:
    subprocess.run([ADB, "shell", "uiautomator", "dump", "/sdcard/window.xml"], check=True, timeout=8)
    proc = subprocess.run([ADB, "exec-out", "cat", "/sdcard/window.xml"], stdout=subprocess.PIPE, check=True, timeout=8)
    root = ET.fromstring(proc.stdout)
    nodes = []
    for node in root.iter("node"):
        nodes.append(
            UINode(
                text=node.attrib.get("text", ""),
                bounds=node.attrib.get("bounds", ""),
                clickable=node.attrib.get("clickable", "false") == "true",
            )
        )
    return nodes

def tap(x: int, y: int) -> None:
    subprocess.run([ADB, "shell", "input", "tap", str(x), str(y)], check=True, timeout=4)

def tap_text(text: str) -> bool:
    for node in dump_nodes():
        if node.visible and node.text == text:
            x, y = node.center
            tap(x, y)
            return True
    return False
```

使用示例：

```python
tap_text("贵宾服务")
tap_text("立即购买")
```

等待某个文字出现：

```python
import time

def wait_for_text(candidates: list[str], timeout_s: int = 10) -> list[UINode]:
    deadline = time.time() + timeout_s
    last_nodes = []
    while time.time() < deadline:
        try:
            last_nodes = dump_nodes()
        except Exception:
            time.sleep(0.5)
            continue
        if any(candidate in node.text for candidate in candidates for node in last_nodes if node.visible):
            return last_nodes
        time.sleep(0.5)
    return last_nodes
```

## 4. 用 OCR 识别截图文字位置

如果目标文字不是原生控件，或者 `uiautomator dump` 里没有该文字，可以用截图加 OCR。

当前脚本里使用的是 `PaddleOCR`，核心流程：

1. `adb exec-out screencap -p` 截屏到本机。
2. 可选：裁剪目标区域，减少 OCR 干扰并提升速度。
3. 调用 PaddleOCR。
4. 把 OCR 返回的文字框转为 `(x1, y1, x2, y2)`。
5. 找到目标文字后点击中心点。

示例代码：

```python
from dataclasses import dataclass
from pathlib import Path
import os
import re
import subprocess
from PIL import Image
from paddleocr import PaddleOCR

ADB = "/Users/weichaofan/Library/Android/sdk/platform-tools/adb"
SCREENSHOT_PATH = Path("/private/tmp/phone_screen.png")
OCR_CROP_PATH = Path("/private/tmp/phone_ocr_crop.png")
OCR_CROP_BOX = (0, 300, 1080, 2135)

@dataclass(frozen=True)
class OCRTextBox:
    text: str
    box: tuple[int, int, int, int]
    score: float

    @property
    def center(self) -> tuple[int, int]:
        x1, y1, x2, y2 = self.box
        return (x1 + x2) // 2, (y1 + y2) // 2

    @property
    def visible(self) -> bool:
        x1, y1, x2, y2 = self.box
        return x2 > x1 and y2 > y1 and y2 > 245 and y1 < 2135

    def translated(self, dx: int, dy: int) -> "OCRTextBox":
        x1, y1, x2, y2 = self.box
        return OCRTextBox(self.text, (x1 + dx, y1 + dy, x2 + dx, y2 + dy), self.score)

def screencap(path: Path = SCREENSHOT_PATH) -> Path:
    proc = subprocess.run([ADB, "exec-out", "screencap", "-p"], stdout=subprocess.PIPE, check=True, timeout=12)
    path.write_bytes(proc.stdout)
    return path

def bounds_from_ocr_box(raw_box: object) -> tuple[int, int, int, int]:
    if hasattr(raw_box, "tolist"):
        raw_box = raw_box.tolist()

    if isinstance(raw_box, (list, tuple)) and len(raw_box) == 4:
        try:
            x1, y1, x2, y2 = [int(round(float(value))) for value in raw_box]
            return x1, y1, x2, y2
        except (TypeError, ValueError):
            pass

    points = list(raw_box)
    xs = [int(round(float(point[0]))) for point in points]
    ys = [int(round(float(point[1]))) for point in points]
    return min(xs), min(ys), max(xs), max(ys)

def parse_paddleocr_result(result: object) -> list[OCRTextBox]:
    pages = result if isinstance(result, list) else [result]
    boxes = []
    for page in pages:
        if isinstance(page, dict):
            texts = page.get("rec_texts", [])
            raw_boxes = page.get("rec_boxes") or page.get("rec_polys", [])
            scores = page.get("rec_scores", [])
            for index, text in enumerate(texts):
                if index >= len(raw_boxes):
                    continue
                score = float(scores[index]) if index < len(scores) else 0.0
                boxes.append(OCRTextBox(str(text), bounds_from_ocr_box(raw_boxes[index]), score))
            continue

        # PaddleOCR 2.x: [[box, (text, score)], ...]
        for item in page or []:
            text_info = item[1]
            text = str(text_info[0])
            score = float(text_info[1]) if len(text_info) > 1 else 0.0
            boxes.append(OCRTextBox(text, bounds_from_ocr_box(item[0]), score))
    return boxes

def ocr_screen() -> list[OCRTextBox]:
    os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
    image_path = screencap()

    crop_x1, crop_y1, crop_x2, crop_y2 = OCR_CROP_BOX
    with Image.open(image_path) as image:
        image.crop(OCR_CROP_BOX).save(OCR_CROP_PATH)

    ocr = PaddleOCR(
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
    )
    if hasattr(ocr, "predict"):
        result = ocr.predict(str(OCR_CROP_PATH))
    else:
        result = ocr.ocr(str(OCR_CROP_PATH), cls=False)

    return [box.translated(crop_x1, crop_y1) for box in parse_paddleocr_result(result)]

def tap(x: int, y: int) -> None:
    subprocess.run([ADB, "shell", "input", "tap", str(x), str(y)], check=True, timeout=4)

def tap_ocr_text(target: str, min_score: float = 0.5) -> bool:
    for box in ocr_screen():
        if box.visible and box.score >= min_score and target in box.text:
            x, y = box.center
            tap(x, y)
            return True
    return False
```

使用示例：

```python
tap_ocr_text("9986")
tap_ocr_text("贵宾VIP卡")
```

如果要识别金额，可以先只保留数字，避免 `￥9986`、`9986元`、`9,986` 这类格式差异：

```python
def ocr_digits(text: str) -> str:
    return re.sub(r"\D+", "", text)

def find_price_point(price: int) -> tuple[int, int] | None:
    target = str(price)
    for box in ocr_screen():
        if box.visible and box.score >= 0.5 and ocr_digits(box.text) == target:
            return box.center
    return None
```

## 5. 点击 OCR 识别到的文字附近

有些页面点击文字中心不一定触发，需要点击文字所在卡片或按钮的其它位置。做法是先通过 OCR 找到文字，再按固定偏移点击。

```python
point = find_price_point(9986)
if point is not None:
    x, y = point
    tap(x, y)

    # 如果实际可点击区域在价格文字右侧或下方，可以加偏移。
    # tap(x + 300, y)
    # tap(x, y + 120)
```

偏移值需要结合当前页面布局调整。建议第一次先打印识别结果：

```python
for box in ocr_screen():
    if box.visible and box.score >= 0.5:
        print(box.text, box.box, box.center, box.score)
```

## 6. 滑动寻找目标文字

当目标文字不在当前屏幕时，可以循环执行“识别 -> 找不到就滑动”：

```python
def swipe(x1: int, y1: int, x2: int, y2: int, duration_ms: int = 600) -> None:
    subprocess.run(
        [ADB, "shell", "input", "swipe", str(x1), str(y1), str(x2), str(y2), str(duration_ms)],
        check=True,
        timeout=6,
    )

def tap_ocr_text_with_scroll(target: str, attempts: int = 6) -> bool:
    for _ in range(attempts):
        if tap_ocr_text(target):
            return True
        swipe(540, 1700, 540, 850, 650)
    return False
```

如果目标可能在上方，则反向滑动：

```python
swipe(540, 850, 540, 1700, 650)
```

## 7. 实战建议

- 优先用 `uiautomator dump` 找文字和 `bounds`；找不到再用 OCR。
- OCR 前裁剪区域可以明显减少误识别，例如只识别列表左侧价格区域：`OCR_CROP_BOX = (0, 300, 450, 2050)`。
- 点击前最好过滤可见区域：顶部状态栏和底部导航栏附近容易误点，现有脚本一般用 `y > 245` 且 `y < 2135`。
- OCR 结果要设置置信度阈值，建议 `score >= 0.5`。
- 每次点击或滑动后加短暂等待，例如 `time.sleep(0.8)`，避免页面还没刷新就继续识别。
- 对长流程建议保留 dry-run 模式：先打印将要点击的坐标，再加 `--execute` 真正执行。
- 若设备锁屏或黑屏，先运行 `./unlock.sh`，不要直接点击。
