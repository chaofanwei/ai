# 月神 src/key 映射下线运维记录

## 通用执行方法

1. 每次操作前，在 `luna-platform` 执行 `git pull --ff-only`。
2. 通过跳板机 `ssh root@10.63.5.53 -p 443` 访问线上 MySQL。
3. 线上库连接信息以 `luna-platform/docs/online.conf` 为准，不在本文记录密码，也不要把密码放入命令行参数。
4. 删除前必须按最终确认的条件查询每组数量和总数；数量不符时停止。
5. 使用 `mysqldump` 导出目标记录，参数至少包括：
   - `--single-transaction --skip-lock-tables --skip-add-locks`
   - `--no-create-info --skip-triggers`
   - `--complete-insert --skip-extended-insert`
   - 用 `--where` 限定与删除完全相同的条件
6. 校验备份中 `INSERT` 条数和各 src 范围数量，确认不存在 `DROP`、`CREATE`、`TRUNCATE`、`DELETE` 或 `UPDATE`。
7. 删除时开启事务，先通过 `SELECT COUNT(*) ... FOR UPDATE` 锁定目标；只有数量等于确认值时才允许 `DELETE`。检查 `ROW_COUNT()` 和剩余数量后提交。
8. 提交后必须使用新的数据库连接，分别复查每个 src 条件。
9. 回滚前先确认目标 ID 不存在，避免主键冲突；确认后再执行对应回滚 SQL，并核对恢复数量。

注意：跳板机当前的旧版 `mysqldump` 不支持 `--connect-timeout` 参数。

## 2026-08-05 / VIDEODEV-5892

- 需求：废弃 src 下线
- 表：`videocloud_luna.sailor_moon_src_key_online`
- 删除条件：
  - `src LIKE '02023161010011%'`：107 条
  - `src LIKE '04022002131000000000%'`：13 条
  - `src LIKE '04025032682100000000%'`：4 条
- 删除总数：124 条
- 回滚文件：`rollback_20260805_VIDEODEV-5892.sql`
- 回滚文件 SHA-256：`5c0b1b3390e7db0bbd823b81498ad04a2aa14d3f616fda234b40c522323f2858`
- 事务结果：锁定 124 条，删除 124 条，提交前剩余 0 条
- 独立复查：三个前缀均为 0 条
- 代码状态：操作前已执行 `git pull --ff-only`，结果为 Already up to date；未修改月神源码
