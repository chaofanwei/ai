# PX4 300mm 小型开发无人机组装方案

> 目标：组装一台 **小尺寸、支持 PX4/Pixhawk、适合学习与开发、方便后续扩展 ROS2 / MAVLink / 视觉算法** 的四旋翼无人机。

---

## 1. 项目定位

这台无人机不是以 FPV 穿越、竞速为主要目标，而是作为一个 **小型 PX4 开发平台**。

主要用途：

- 学习 PX4 固件
- 使用 QGroundControl 调参
- 学习 MAVLink 通信
- GPS 定点与自动航线
- 自动起飞 / 降落
- 后续接入 ROS2 / MAVROS
- 后续接入树莓派 / Jetson
- 后续尝试视觉识别、目标跟踪、SLAM 等

设计原则：

- 尺寸尽量小
- 不使用 450 / 500mm 这类大型教学机架
- 比传统 250mm FPV 机架多留一些开发空间
- 优先选择 PX4 官方生态成熟的硬件

---

## 2. 推荐整体方案

推荐基础配置：

```text
300mm 左右碳纤机架
+
Holybro Pixhawk 6C Mini
+
Holybro M10 GPS
+
Holybro PM06 V2 Micro 电源模块
+
2207 1700~1900KV 电机 × 4
+
35A 左右 4 合 1 ESC
+
6 寸桨
+
4S 2200mAh 电池
+
ELRS 遥控系统
+
Holybro SiK MAVLink 数传
```

整体定位：

> 比 QAV250 稍大，但仍然属于小型无人机，同时为 GPS、Pixhawk、数传和后续伴随计算机留出更多空间。

---

# 3. 淘宝购买清单

## 3.1 机架

### 推荐规格

- 轴距：280~310mm
- 推荐目标：约 300mm
- X 型四轴
- 碳纤维
- 最好支持 6 寸桨
- 中部空间不要过窄
- 最好有上下双层板
- 中央最好能提供约 `70 × 50mm` 左右的平整安装空间

### 淘宝搜索关键词

```text
300mm 四轴 碳纤 机架 6寸
280mm 四轴机架
300mm 四轴机架 Pixhawk
6寸 长航时 四轴 机架
```

### 预算

```text
¥80 ~ ¥200
```

### 注意

不要优先选择那种纯 FPV 竞速机架：

- 中间非常窄
- 只为 20×20 / 30×30 飞塔设计
- 没地方安装 Pixhawk / GPS / 电源模块 / 数传

购买前最好向卖家确认：

```text
1. 实际轴距多少？
2. 最大支持几寸桨？
3. 中间安装区域尺寸多少？
4. 是否方便安装 Pixhawk？
```

---

# 3.2 飞控

## Holybro Pixhawk 6C Mini

这是本方案核心。

### 推荐原因

- PX4 官方支持
- 体积比普通 Pixhawk 小
- H7 系列 MCU
- 接口完整
- 支持 GPS / TELEM / CAN / I2C / RC
- 后续接 ROS2 / MAVLink / RTK / 激光雷达都方便

### 淘宝搜索关键词

```text
Holybro Pixhawk 6C Mini
Pixhawk 6C Mini 原装 Holybro
```

### 预算

```text
¥900 ~ ¥1300
```

### 注意

淘宝同时会有：

```text
Pixhawk 6C
Pixhawk 6C Mini
```

本方案建议：

```text
Pixhawk 6C Mini
```

购买前问卖家：

```text
是否原装 Holybro？
包含哪些线材？
是否包含电源模块？
```

如果套装已经带 PM06 V2 Micro，就不需要重复购买。

---

# 3.3 GPS

## Holybro M10 GPS + Compass

推荐 M10，不建议现在再买老 M8N。

### 淘宝搜索关键词

```text
Holybro M10 GPS Pixhawk
Holybro M10 GPS Compass
```

### 预算

```text
¥300 ~ ¥450
```

### 推荐原因

- 与 Pixhawk / PX4 生态匹配
- 集成 GPS + 罗盘
- 接插件规范
- 比淘宝几十元的裸 M10 小板更适合开发机

---

# 3.4 电源模块

## Holybro PM06 V2 Micro

作用：

- 给 Pixhawk 稳定供电
- 测量电池电压
- 测量电流
- 为 PX4 提供电池状态信息

### 淘宝搜索关键词

```text
Holybro PM06 V2 Micro
Pixhawk PM06 电源模块
```

### 预算

```text
¥150 ~ ¥250
```

注意：

如果 Pixhawk 套装已经包含，则无需单独购买。

---

# 3.5 电机

## 推荐规格

```text
2207
1700 ~ 1900KV
4S
```

推荐目标：

```text
2207 1800KV 左右
```

可参考：

```text
EMAX ECO II 2207 1700KV
朗宇 / SunnySky 同规格型号
其它 2207 1700~1900KV 电机
```

### 淘宝搜索关键词

```text
2207 1700KV 4S 电机
2207 1800KV 电机
EMAX ECO II 2207 1700KV
```

### 数量

```text
4 个
```

最好可以买 5 个：

```text
4 使用 + 1 备用
```

### 预算

```text
¥200 ~ ¥350 / 4个
```

### 为什么不选择高 KV

本机目标是：

```text
稳定
效率
PX4 调参
GPS 飞行
开发测试
```

不是追求穿越机的极端爆发力，所以没有必要上 2300~2600KV。

---

# 3.6 ESC

## 推荐

```text
35A 左右
4 合 1 ESC
3~6S
支持 DShot
BLHeli_S / BLHeli_32
```

### 淘宝搜索关键词

```text
35A 4合1 ESC BLHeli 3-6S
40A 4合1 ESC DShot
```

### 预算

```text
¥150 ~ ¥250
```

### 重要

购买前确认 ESC 有：

```text
M1
M2
M3
M4
```

独立电机信号输入焊盘。

Pixhawk 的 MAIN OUT 需要分别连接：

```text
MAIN OUT 1 -> ESC M1
MAIN OUT 2 -> ESC M2
MAIN OUT 3 -> ESC M3
MAIN OUT 4 -> ESC M4
```

如果第一次组机，觉得 4 合 1 ESC 接线麻烦，也可以使用：

```text
4 个独立 30~35A ESC
```

优点：

- 逻辑更直观
- 每个电机一路 ESC

缺点：

- 线更多
- 整机不够整洁

---

# 3.7 螺旋桨

## 推荐

如果最终机架确认支持 6 寸：

```text
6×3
6×4
6030
6040
```

两叶、三叶都可以尝试。

开发机优先考虑：

```text
低负载
效率
稳定
```

### 淘宝搜索关键词

```text
6040 6寸 桨
6030 6寸 桨
6寸 无人机 螺旋桨
```

### 建议数量

至少：

```text
2~3 套
```

因为新手调试很容易损坏桨。

### 预算

```text
¥30 ~ ¥60
```

---

# 3.8 电池

## 推荐规格

```text
4S
2200mAh
45C ~ 75C
XT60
```

### 淘宝搜索关键词

```text
4S 2200mAh 航模 锂电池 XT60
4S 2200 45C 航模电池
```

### 推荐数量

```text
2 块
```

一块飞，一块充。

### 预算

```text
¥150 ~ ¥250 / 块
```

暂时不建议直接上：

```text
4S 4000mAh
4S 5000mAh
```

原因：

- 300mm 机架会变重
- 动态响应变差
- 对第一阶段学习没有必要

---

# 3.9 遥控器

## 推荐

RadioMaster Pocket ELRS 2.4GHz

### 淘宝搜索关键词

```text
RadioMaster Pocket ELRS
RadioMaster Pocket 2.4G ELRS
```

### 预算

```text
¥400 ~ ¥500
```

优点：

- 便宜
- 小巧
- ELRS 生态成熟
- 后续换无人机也可以继续用

---

# 3.10 ELRS 接收机

## 推荐

```text
RadioMaster RP1
或
RadioMaster RP3
```

### 淘宝搜索关键词

```text
RadioMaster RP1 ELRS 2.4G
RadioMaster RP3 ELRS
```

### 预算

```text
¥100 ~ ¥150
```

用途：

```text
遥控器
   ↓ ELRS
接收机
   ↓
Pixhawk
```

注意：

遥控链路和 MAVLink 数传不是一回事。

---

# 3.11 MAVLink 数传

## 推荐

Holybro SiK Telemetry Radio

根据所在地区和合法频段选择对应版本。

### 淘宝搜索关键词

```text
Holybro SiK 数传 Pixhawk
Holybro MAVLink 数传
Pixhawk Telemetry Radio
```

### 预算

```text
¥250 ~ ¥400
```

结构：

```text
Linux 笔记本
   ↓ USB
地面端 SiK
   ↓ 无线
机载 SiK
   ↓ TELEM
Pixhawk
```

这样 Linux Mint 上运行 QGroundControl，就能实时看到：

- GPS
- 姿态
- 高度
- 电池
- 飞行模式
- 参数
- MAVLink 数据
- 航点任务

---

# 3.12 GPS 支架

### 推荐

```text
折叠 GPS 支架
或
碳杆 GPS 支架
```

### 淘宝搜索关键词

```text
Pixhawk GPS 折叠支架
无人机 GPS 碳杆
```

### 预算

```text
¥20 ~ ¥40
```

作用：

让 GPS / Compass 离：

- 电源线
- ESC
- 电机

稍远一些，减少磁场干扰。

---

# 3.13 蜂鸣器

### 淘宝搜索关键词

```text
Pixhawk 蜂鸣器
5V 有源蜂鸣器 无人机
```

### 预算

```text
¥10 ~ ¥30
```

---

# 3.14 飞控减震

### 淘宝搜索关键词

```text
Pixhawk 飞控 减震
Pixhawk 减震胶
飞控 3M 减震胶
```

### 预算

```text
¥10 ~ ¥30
```

---

# 3.15 XT60 / 线材 / 小配件

建议准备：

```text
XT60 公母头
14AWG / 16AWG 硅胶线
热缩管
扎带
双面胶
3M 胶
螺丝
铜柱
焊锡
备用插头
```

### 淘宝搜索关键词

```text
XT60 硅胶线 航模
航模 热缩管
无人机 扎带
```

### 预算

```text
约 ¥30 ~ ¥100
```

---

# 4. 推荐结构

整体连接关系：

```text
                  M10 GPS
                     │
                     │
              Pixhawk 6C Mini
             /       |        \
            /        |         \
        ELRS       SiK数传     PM06
          │           │          │
          │           │          │
   RadioMaster     Linux        4S
      Pocket       Laptop      2200mAh
                      │
               QGroundControl
                      │
                      │
              Pixhawk MAIN OUT
                │ │ │ │
                1 2 3 4
                │ │ │ │
              4-in-1 ESC
                │ │ │ │
               M1 M2 M3 M4
```

---

# 5. 推荐预算

| 部件 | 预算 |
|---|---:|
| Pixhawk 6C Mini | ¥900~1300 |
| M10 GPS | ¥300~450 |
| PM06 V2 Micro | ¥150~250 |
| 300mm 机架 | ¥80~200 |
| 4× 电机 | ¥200~350 |
| 4 合 1 ESC | ¥150~250 |
| 螺旋桨 | ¥30~60 |
| 2× 4S 电池 | ¥300~500 |
| RadioMaster Pocket + ELRS RX | ¥500~650 |
| Holybro SiK 数传 | ¥250~400 |
| 线材 / 支架 / 小配件 | ¥100 左右 |

预计总预算：

```text
约 ¥2960 ~ ¥4510
```

如果已经有：

- 遥控器
- 电池
- 充电器

则可以明显降低预算。

---

# 6. 购买顺序

## 第一阶段：先确定机架

不要一次全部下单。

首先购买或至少确定：

```text
300mm 左右机架
```

确认：

```text
轴距
最大桨尺寸
中间安装空间
电池安装方式
Pixhawk 安装空间
```

---

## 第二阶段：确定动力系统

根据机架允许的最大桨尺寸，再确定：

```text
电机
+
螺旋桨
+
ESC
+
电池
```

当前预设：

```text
6寸桨
+
2207 1700~1900KV
+
35A ESC
+
4S 2200mAh
```

但最终应以实际机架为准。

---

## 第三阶段：购买 PX4 核心

```text
Pixhawk 6C Mini
M10 GPS
PM06
```

---

## 第四阶段：购买遥控和数传

```text
RadioMaster Pocket ELRS
RP1 / RP3
Holybro SiK
```

---

# 7. 第一阶段不要买的东西

暂时不要加：

```text
Jetson
Raspberry Pi
激光雷达
光流
FPV 图传
FPV 摄像头
RTK
云台
航拍相机
```

第一阶段先把：

```text
PX4
+
QGroundControl
+
GPS
+
MAVLink
+
ELRS
+
自动航点
```

全部跑通。

---

# 8. 第一阶段学习目标

建议按照下面顺序学习。

## Stage 1：基础飞控

```text
刷 PX4
↓
QGroundControl
↓
传感器校准
↓
遥控器校准
↓
电机方向检查
↓
飞行模式
↓
手动起飞
```

---

## Stage 2：GPS

```text
GPS 定位
↓
Position 模式
↓
定点悬停
↓
Return To Launch
↓
自动起降
```

---

## Stage 3：Mission

```text
QGroundControl
↓
规划 Waypoint
↓
上传 Mission
↓
自动飞行
↓
自动返航
```

---

## Stage 4：MAVLink

Linux 电脑：

```text
Python
↓
MAVSDK / pymavlink
↓
MAVLink
↓
Pixhawk
```

可以实现：

- Python 获取 GPS
- 获取姿态
- 获取电池
- ARM / DISARM
- 自动起飞
- 飞到指定坐标
- 自动降落

---

# 9. 后续 ROS2 路线

第二阶段可以加入：

```text
Raspberry Pi 5
+
ROS2
+
PX4
```

结构：

```text
              Raspberry Pi
                   │
                  ROS2
                   │
              MAVLink / uXRCE
                   │
             Pixhawk 6C Mini
```

用途：

- ROS2 控制无人机
- Offboard 模式
- 路径规划
- 外部定位
- 自动任务

---

# 10. 后续 AI / 视觉路线

再往后可以升级为：

```text
Jetson Orin Nano
+
相机
+
ROS2
+
PX4
```

实现：

- YOLO 目标识别
- 目标跟踪
- 视觉定位
- SLAM
- 自动避障
- AI 自主飞行

到这个阶段，如果 300mm 平台载重开始吃紧，再考虑升级：

```text
350mm
450mm
Holybro X500 V2
```

而不是一开始就买大型平台。

---

# 11. 为什么选择 300mm，而不是 250mm

250mm 的优势：

- 配件非常多
- 5 寸 FPV 生态成熟
- 小巧
- 便宜

但对于 PX4：

```text
Pixhawk
GPS
Power Module
ELRS RX
SiK
Raspberry Pi
Camera
```

会显得比较拥挤。

300mm 多出的几十毫米，对开发平台非常有价值：

- Pixhawk 更容易布置
- GPS 更容易远离干扰
- 电池空间更充足
- 数传更容易安装
- 后续还能放 Raspberry Pi
- 仍然保持比较小的体积

因此本项目选择：

> **约 300mm 是“小型 PX4 开发机”的折中甜点尺寸。**

---

# 12. Holybro QAV250 作为参考

Holybro 官方 QAV250 PX4 套件可作为本机设计参考。

典型结构：

```text
Pixhawk 6C Mini
+
M10 GPS
+
PM06 V2 Micro
+
2207 电机
+
5寸桨
+
ESC
+
数传
```

本项目可以理解为：

> 在 QAV250 思路基础上稍微放大到约 300mm，为学习、开发和扩展增加空间。

---

# 13. 最终目标配置

```text
机架：
280~310mm，目标约 300mm

飞控：
Holybro Pixhawk 6C Mini

GPS：
Holybro M10 GPS + Compass

电源：
Holybro PM06 V2 Micro

电机：
2207 1700~1900KV × 4

ESC：
35A 4-in-1

桨：
6 寸

电池：
4S 2200mAh × 2

遥控：
RadioMaster Pocket ELRS

接收机：
RP1 / RP3 ELRS

数传：
Holybro SiK Telemetry

地面站：
Linux Mint + QGroundControl
```

---

# 14. 当前最重要的下一步

**先确定机架。**

看到淘宝候选机架后，记录：

```text
商品链接：
轴距：
最大桨尺寸：
中部板尺寸：
重量：
售价：
```

然后再根据实际机架确认：

```text
电机 KV
+
桨尺寸
+
ESC 电流
+
电池容量
```

这样可以避免配件买回来互相不匹配。

---

## TODO

- [ ] 选定 280~310mm 机架
- [ ] 确认最大支持桨尺寸
- [ ] 确认中部 Pixhawk 安装空间
- [ ] 确定电机型号
- [ ] 确定 ESC
- [ ] 确定螺旋桨
- [ ] 购买 Pixhawk 6C Mini
- [ ] 购买 M10 GPS
- [ ] 购买 PM06
- [ ] 购买 RadioMaster Pocket ELRS
- [ ] 购买 RP1 / RP3
- [ ] 购买 SiK 数传
- [ ] 完成焊接
- [ ] 安装 PX4
- [ ] 完成 QGroundControl 校准
- [ ] 首次无桨电机测试
- [ ] 首次悬停
- [ ] GPS Position 模式测试
- [ ] RTL 测试
- [ ] Mission 自动航点测试
- [ ] MAVLink / Python 开发
- [ ] ROS2 开发

