# Win7 C 盘空间排查记录

记录时间：2026-08-05  
排查对象：远程 Win7 电脑 `XS0409`  
排查原则：之前仅执行只读查看命令，未做删除、移动、清理或配置修改。

## 远程登录方式

先登录跳板机：

```bash
ssh root@47.121.185.35
```

再从跳板机登录 Win7：

```bash
ssh 'bidcenter\xs0409@localhost' -p 3311 -i /root/.ssh/id_win7
```

也可以从本机直接通过嵌套 SSH 执行只读命令。

## 磁盘空间概况

最近一次查询结果：

| 盘符 | 总容量 | 已用 | 可用 |
|---|---:|---:|---:|
| `C:` | `119.24 GiB` | `116.84 GiB` | `2.40 GiB` |
| `D:` | `100.01 GiB` | `80.39 GiB` | `19.62 GiB` |
| `E:` | `200.01 GiB` | `31.23 GiB` | `168.78 GiB` |
| `F:` | `165.75 GiB` | `47.16 GiB` | `118.59 GiB` |

结论：`E:` 最宽裕，其次是 `F:`。如果迁移微信/企业微信数据，优先考虑 `E:`。

## C 盘主要占用

| 路径 | 大小 | 说明 |
|---|---:|---|
| `C:\Users\xs0409` | 约 `112 GiB` | 最大占用来源 |
| `C:\Users\xs0409\Documents\WeChat Files` | `45.21 GiB` | 旧版个人微信/双开遗留可能性高 |
| `C:\Users\xs0409\xwechat_files` | `38.45 GiB` | 当前个人微信存储位置 |
| `C:\Users\xs0409\Documents\WXWork` | `5.36 GiB` | 当前企业微信存储位置 |
| `C:\Users\xs0409\AppData` | 约 `22.44 GiB` | 应用数据 |
| `C:\ProgramData\Tencent\QQPinyin\users\public\dict` | 约 `14.23 GiB` | 腾讯拼音词库/数据异常偏大 |
| `C:\hiberfil.sys` | 约 `5.91 GiB` | 休眠文件 |
| `C:\Users\xs0409\AppData\Local\Temp` | 约 `3.24 GiB` | 临时目录 |
| `C:\1` | 约 `3.09 GiB` | 安装包等文件 |

页面文件不在 C 盘，当前为：

```text
D:\pagefile.sys
```

## 微信和企业微信目录

用户确认：

- 企业微信 App 当前显示存储位置：`C:\Users\xs0409\Documents\WXWork`
- 个人微信 App 当前显示存储位置：`C:\Users\xs0409\xwechat_files`
- 个人微信之前使用过电脑双开，升级后不能双开。

三个目录大小：

| 目录 | 大小 |
|---|---:|
| `C:\Users\xs0409\Documents\WeChat Files` | `45.21 GiB` |
| `C:\Users\xs0409\xwechat_files` | `38.45 GiB` |
| `C:\Users\xs0409\Documents\WXWork` | `5.36 GiB` |

### 账号目录

`C:\Users\xs0409\Documents\WeChat Files`：

```text
wxid_72t0d0jbnq5t22
wxid_kkt1v7j2sl3r22
wxid_pjz65xtjxqd112
wxid_zd3nrm1j4w5j22
```

`C:\Users\xs0409\xwechat_files`：

```text
wxid_72t0d0jbnq5t22_ea1d
wxid_pjz65xtjxqd112_37d1
```

`C:\Users\xs0409\Documents\WXWork`：

```text
1688850297679837
1688855031319247
2251801668800038
2251802526811609
```

企业微信目录不是 `wxid` 命名，而是数字 ID 目录。

### 重点账号对比

用户判断以下两个目录应该是同一账号在新旧微信目录里的名称：

- `C:\Users\xs0409\Documents\WeChat Files\wxid_72t0d0jbnq5t22`
- `C:\Users\xs0409\xwechat_files\wxid_72t0d0jbnq5t22_ea1d`

只读统计结果：

| 目录 | 大小 | 文件数 | 最后更新时间 |
|---|---:|---:|---|
| `C:\Users\xs0409\Documents\WeChat Files\wxid_72t0d0jbnq5t22` | `33.94 GiB` | `97,165` | `2026-07-31 08:30:21` |
| `C:\Users\xs0409\xwechat_files\wxid_72t0d0jbnq5t22_ea1d` | `29.59 GiB` | `53,224` | `2026-07-31 11:42:06` |

判断：

- `xwechat_files\wxid_72t0d0jbnq5t22_ea1d` 明显是当前活跃使用目录。
- `Documents\WeChat Files\wxid_72t0d0jbnq5t22` 更像旧版微信/双开遗留数据，但当天早上仍有少量 `.db-shm` 更新时间，清理前应谨慎确认。

## 可优化方向

1. 休眠文件  
   如果确认不需要休眠，可以在 Win7 管理员命令行执行：

   ```cmd
   powercfg /hibernate off
   ```

   或：

   ```cmd
   powercfg -h off
   ```

   成功后会自动删除 `C:\hiberfil.sys`，预计释放约 `5.9 GiB`。这会修改系统配置，之前没有执行。

2. 迁移当前个人微信数据  
   当前个人微信使用 `C:\Users\xs0409\xwechat_files`，建议通过微信 App 设置把存储位置迁到 `E:` 或 `F:`，不要直接手动移动或删除。

3. 迁移企业微信数据  
   当前企业微信使用 `C:\Users\xs0409\Documents\WXWork`，建议通过企业微信 App 设置迁移到 `E:` 或 `F:`。

4. 处理旧微信目录  
   `C:\Users\xs0409\Documents\WeChat Files` 占 `45.21 GiB`，很可能是旧版个人微信/双开遗留。建议先确认历史聊天记录和文件是否还需要，最好备份到 `E:` 或 `F:` 后再考虑清理。

5. 腾讯拼音数据  
   `C:\ProgramData\Tencent\QQPinyin\users\public\dict` 占约 `14.23 GiB`，异常偏大。建议通过腾讯拼音自带设置、修复工具或备份词库后重装来处理，不建议直接盲删。

6. 临时目录和安装包  
   `C:\Users\xs0409\AppData\Local\Temp` 约 `3.24 GiB`，`C:\1` 约 `3.09 GiB`。可作为次要清理目标，需确认无用后再处理。

## 下次继续时建议先做

1. 重新查询各盘可用空间，确认 C 盘是否已有变化。
2. 确认是否要执行 `powercfg /hibernate off`。
3. 如果要清理微信空间，先确认当前个人微信是否能正常迁移存储位置到 `E:`。
4. 对 `Documents\WeChat Files` 先备份或改名测试，不建议直接删除。
