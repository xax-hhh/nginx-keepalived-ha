-- ──────────────────────────────────────────────
-- Linux 运维实训项目 — MySQL Master 初始化脚本
-- 执行目标：MySQL Master（192.168.10.122）
-- 执行方式：mysql -u root -p < init-master.sql
-- 【改】Slave IP 和复制用户密码
-- ──────────────────────────────────────────────

-- 0. 前置检查：确保 Master 的 my.cnf 包含主从复制参数
--    /etc/my.cnf.d/mysql-server.cnf 应包含：
--      [mysqld]
--      server-id        = 1              # Master 固定为 1
--      log-bin          = mysql-bin      # 开启二进制日志（必须）
--      binlog_format    = ROW            # 行级复制（推荐）
--      expire_logs_days = 7             # binlog 自动清理
--    修改后需重启: sudo systemctl restart mysqld

-- 1. 创建业务库
CREATE DATABASE IF NOT EXISTS ops_demo
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

-- 2. 创建远程业务用户
--    （供 App 服务器连接，两台 App 分别授权）
CREATE USER IF NOT EXISTS 'ops_user'@'192.168.10.121' IDENTIFIED BY 'OpsUser@2024';
CREATE USER IF NOT EXISTS 'ops_user'@'192.168.10.124' IDENTIFIED BY 'OpsUser@2024';
GRANT ALL PRIVILEGES ON ops_demo.* TO 'ops_user'@'192.168.10.121';
GRANT ALL PRIVILEGES ON ops_demo.* TO 'ops_user'@'192.168.10.124';

-- 3. 创建复制用户（供 Slave 连接）
CREATE USER IF NOT EXISTS 'repl'@'192.168.10.125' IDENTIFIED BY 'ReplPass@2024';
GRANT REPLICATION SLAVE, REPLICATION CLIENT ON *.* TO 'repl'@'192.168.10.125';

FLUSH PRIVILEGES;

-- 4. 确认 binlog 状态（执行后记录 File 和 Position）
--    MySQL 8.4+ 使用 SHOW BINARY LOG STATUS（旧名 SHOW MASTER STATUS 已移除）
SHOW BINARY LOG STATUS\G

-- 输出示例:
-- File: mysql-bin.000001
-- Position: 157
-- → 在 Slave 上执行 CHANGE REPLICATION SOURCE TO 时需要用到这两个值

-- 5. 查看 Master 状态
SELECT User, Host FROM mysql.user WHERE User IN ('ops_user', 'repl');

-- 6. ★ 防火墙提醒 ★
--    Master 需要放行 Slave IP（192.168.10.125）的 3306 端口：
--    sudo firewall-cmd --permanent --add-rich-rule='rule family="ipv4" source address="192.168.10.125" port protocol="tcp" port="3306" accept'
--    sudo firewall-cmd --reload

-- 7. （可选）在 Slave 上测试复制用户连通性：
--    mysql -h 192.168.10.122 -u repl -p'ReplPass@2024' -e "SHOW BINARY LOG STATUS\G"
