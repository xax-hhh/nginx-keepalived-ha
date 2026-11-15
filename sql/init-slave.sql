-- ──────────────────────────────────────────────
-- Linux 运维实训项目 — MySQL Slave 初始化脚本
-- 执行目标：MySQL Slave（192.168.10.125）
-- 执行方式：mysql -u root -p < init-slave.sql
--
-- 【改】SOURCE_HOST / SOURCE_USER / SOURCE_PASSWORD
--       以及 SOURCE_LOG_FILE / SOURCE_LOG_POS
--       （后两个来自 Master 上 SHOW BINARY LOG STATUS 的输出）
-- ──────────────────────────────────────────────

-- 0. 前置检查：确保 Slave 的 my.cnf 包含主从复制参数
--    /etc/my.cnf.d/mysql-server.cnf 应包含：
--      [mysqld]
--      server-id        = 2              # 必须与 Master(1) 不同
--      relay-log        = relay-bin      # 中继日志
--      read_only        = ON             # 全局只读
--      super_read_only  = ON             # 禁止 SUPER 用户写入（更安全）
--    修改后需重启: sudo systemctl restart mysqld

-- 1. 创建业务库（Schema 同步，数据由复制自动同步）
CREATE DATABASE IF NOT EXISTS ops_demo
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

-- 2. 配置复制源（MySQL 8.4 推荐语法）
--    【改】替换为 Master 上 SHOW BINARY LOG STATUS 的实际值
CHANGE REPLICATION SOURCE TO
    SOURCE_HOST             = '192.168.10.122',
    SOURCE_PORT             = 3306,
    SOURCE_USER             = 'repl',
    SOURCE_PASSWORD         = 'ReplPass@2024',
    SOURCE_LOG_FILE         = 'binlog.000009',   -- 【改】来自 SHOW BINARY LOG STATUS
    SOURCE_LOG_POS          = 158,                   -- 【改】来自 SHOW BINARY LOG STATUS
    SOURCE_CONNECT_RETRY    = 60,
    SOURCE_HEARTBEAT_PERIOD = 30,
    GET_SOURCE_PUBLIC_KEY   = 1;       -- MySQL 8.4 caching_sha2_password 需要 RSA 公钥

-- 兼容旧版 MySQL 8.0 语法（MySQL 8.4+ 已移除以下命令，请使用上面的新语法）:
-- CHANGE MASTER TO
--     MASTER_HOST             = '192.168.10.122',
--     MASTER_PORT             = 3306,
--     MASTER_USER             = 'repl',
--     MASTER_PASSWORD         = 'ReplPass@2024',
--     MASTER_LOG_FILE         = 'mysql-bin.000001',
--     MASTER_LOG_POS          = 157,
--     MASTER_CONNECT_RETRY    = 60,
--     MASTER_HEARTBEAT_PERIOD = 30;

-- 3. 启动复制线程
START REPLICA;

-- 4. 查看复制状态（应看到 Replica_IO_Running: Yes, Replica_SQL_Running: Yes）
SHOW REPLICA STATUS\G

-- 兼容旧版: START SLAVE; SHOW SLAVE STATUS\G

-- 5. 设置只读（Slave 不接收直接写入）
--    ★ 推荐在 my.cnf 中持久化（重启不丢失）：
--      read_only        = ON   → 对非 SUPER 用户生效
--      super_read_only  = ON   → 对 SUPER 用户（root）也生效
--    以下 SET GLOBAL 为运行时即时生效（重启后恢复为 my.cnf 中的值）
SET GLOBAL read_only = ON;
SET GLOBAL super_read_only = ON;

-- 6. ★ 防火墙提醒 ★
--    Slave 需要放行 App 服务器（读写分离读操作）：
--    sudo firewall-cmd --permanent --add-rich-rule='rule family="ipv4" source address="192.168.10.121" port protocol="tcp" port="3306" accept'
--    sudo firewall-cmd --permanent --add-rich-rule='rule family="ipv4" source address="192.168.10.124" port protocol="tcp" port="3306" accept'
--    sudo firewall-cmd --reload
