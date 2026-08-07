# Win7 远程访问记录（XS0409）

记录时间：2026-08-07  
机器：`XS0409.bidcenter.cn`（Win7 Professional，域 `bidcenter.cn` / `BIDCENTER`）

## 连接拓扑

```text
本机 Linux
  → SSH 跳板机 root@47.121.185.35
    → 反向隧道 localhost:3311 → Win7:2222（OpenSSH）
      → Win7 本机服务（sshd:2222、RDP:3389）
```

Win7 OpenSSH 路径：`E:\OpenSSH-Win64\`  
跳板机密钥：`/root/.ssh/id_win7`（本机副本：`jie/id_win7`）

---

## 一、SSH 命令行登录

### 经跳板机

```bash
ssh root@47.121.185.35
ssh 'bidcenter\xs0409@localhost' -p 3311 -i /root/.ssh/id_win7
```

### 本机一条命令（嵌套 SSH）

```bash
ssh -J root@47.121.185.35 -p 3311 -i /path/to/id_win7 'bidcenter\xs0409@localhost'
```

### 账号说明

| 账号 | 用途 | SSH 方式 |
|---|---|---|
| `BIDCENTER\xs0409` | 日常运维 | 公钥（`C:\Users\xs0409\.ssh\authorized_keys`） |
| `BIDCENTER\a` | 管理员域账号 | 需单独配置公钥，或临时开密码登录 |

**sshd 认证（2026-08-07 调整后）：**

- `PubkeyAuthentication yes`
- `PasswordAuthentication yes`（临时，用完建议改回 `no`）
- `AllowUsers bidcenter\xs0409 bidcenter\a`
- 配置备份：`E:\OpenSSH-Win64\sshd_config.bak_20260807_1603`

**注意：** sshd 未安装为 Windows 服务，由 `start_autossh.bat` 启动；账号 `a` 用密码登录时若出现 `CreateProcessAsUserW error:1314`，需运行 `install-sshd.ps1` 并以 SYSTEM 服务方式启动。

---

## 二、RDP 图形远程（已验证可用）

### 前置条件

Win7 远程桌面需同时满足：

1. **服务已开**：`fDenyTSConnections=0`，`TermService` 运行，3389 监听
2. **NLA 已开**：`UserAuthentication=1`（客户端须用 NLA/TLS，勿选 Legacy RDP）
3. **账号有远程桌面权限**：必须在 **Remote Desktop Users** 组，或属于本地 **Administrators**

若权限不足，客户端报错：

```text
ERRINFO_SERVER_INSUFFICIENT_PRIVILEGES (0x00000009)
The user cannot connect to the server due to insufficient access privileges.
```

Remmina 表现为：输密码点 OK 后无报错，直接回到登录框。

**授权方法（Win7 本机管理员 CMD）：**

```cmd
net localgroup "Remote Desktop Users" bidcenter\xs0409 /add
net localgroup "Remote Desktop Users" bidcenter\a /add
```

打开方式：开始菜单 → 搜索 `cmd` → 右键 **以管理员身份运行**。  
本地管理员可试：`.\admin`、`.\00admin` 或域账号 `BIDCENTER\00admin`。

2026-08-07 排查时 **Remote Desktop Users 组为空**，`xs0409` 和 `a` 均不在本地 Administrators，导致 RDP 失败；加组后恢复正常。

### 方式 A：本机 SSH 隧道 + xfreerdp（推荐，已验证）

**终端 1：建立隧道（保持不关）**

```bash
cd /path/to/jie   # id_win7 所在目录
ssh -L 13389:127.0.0.1:3389 \
  -J root@47.121.185.35 \
  -p 3311 -i id_win7 \
  'bidcenter\xs0409@localhost'
```

含义：本机 `127.0.0.1:13389` → 跳板机 → Win7 `127.0.0.1:3389`。

**终端 2：连接桌面**

```bash
xfreerdp /v:127.0.0.1:13389 /u:BIDCENTER\\xs0409 /sec:nla /cert:ignore
```

按提示输入 Windows 密码即可。

**依赖：** 本机需安装 `freerdp2-x11`：

```bash
sudo apt install freerdp2-x11
```

### 方式 B：Remmina 图形客户端

1. 先建好上述 SSH 隧道
2. 新建 RDP 连接：
   - 服务器：`127.0.0.1:13389`
   - **用户名：** `xs0409`（不要写 `BIDCENTER\xs0409`）
   - **域：** `BIDCENTER` 或 `bidcenter.cn`
   - 安全协议：**NLA** 或 **TLS**
3. 启动：`remmina`

### 方式 C：隧道开在跳板机（可选）

在跳板机 `47.121.185.35` 上：

```bash
ssh -f -N -L 0.0.0.0:13389:127.0.0.1:3389 \
  -p 3311 -i /root/.ssh/id_win7 \
  'bidcenter\xs0409@localhost'
```

本机 RDP 连：`47.121.185.35:13389`（13389 暴露在公网，安全性低于方式 A）。

---

## 三、账号与权限参考

### 本地 Administrators 组成员（2026-08-07）

- `00admin`
- `admin`
- `BIDCENTER\Domain Admins`

`BIDCENTER\a` 是域账号，**不在**上述本地管理员列表；是否域管需域控确认。

  a   bjbidcenter123.com
  xs0409   Ab98765432100.

### 域控

- 主机名：`SERVER200` / `server200.bidcenter.cn`
- IP：`192.168.1.200`
- Win7 上 `ping` / `nltest /dsgetdc` 正常

### RDP 登录名写法

| 写法 | 适用场景 |
|---|---|
| xfreerdp：`/u:BIDCENTER\\xs0409` | 命令行 |
| Remmina：用户名 `xs0409`，域 `BIDCENTER` | 图形界面 |
| WMIC：`/user:BIDCENTER\a` | 远程提权（须 `/node:127.0.0.1`） |

---

## 四、常见问题

| 现象 | 原因 | 处理 |
|---|---|---|
| xfreerdp `INSUFFICIENT_PRIVILEGES` | 账号无 RDP 权限 | 管理员 CMD 加入 Remote Desktop Users |
| Remmina 反复要密码 | 同上或用户名/域格式错误 | 加组；用户名与域分开填 |
| SSH `Permission denied (publickey)` | 无公钥或密码登录关闭 | 给对应用户配 `authorized_keys` 或临时开密码 |
| WMIC 本地报 `User credentials cannot be used for local connections` | WMIC 本机限制 | 加 `/node:127.0.0.1`；或改用本机管理员 CMD |
| `start_autossh.bat` 失败 | C 盘满、多 sshd 实例、2222 未监听 | 保 C 盘空间；清理多余 sshd；见 device_control 日志 |

---

## 五、相关路径

| 路径 | 说明 |
|---|---|
| `E:\OpenSSH-Win64\sshd_config` | SSH 服务配置 |
| `E:\OpenSSH-Win64\start_autossh.bat` | 启动 sshd + 反向隧道 |
| `E:\OpenSSH-Win64\sshd.log` | sshd 日志 |
| `E:\soft\pc_device_control\device_control.log` | 远程命令执行日志 |
| `jie/win7_disk_space_notes.md` | C 盘空间排查记录 |

---

## 六、安全提醒

- 管理员密码勿在聊天/工单中明文传递
- `PasswordAuthentication yes` 为临时方案，稳定后建议改回 `no`
- 优先使用本机 `-L 13389` 隧道，避免在跳板机公网暴露 RDP 端口
