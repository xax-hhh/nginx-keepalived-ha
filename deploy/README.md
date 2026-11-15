# Linux 运维实训项目 — 部署指南

> **目标系统**：Rocky Linux 9.x × 7 台
> **前提**：所有服务器已安装 Rocky Linux 9.x，`192.168.10.0/24` 内网互通，SSH 可用

---

## 一、架构拓扑

### 1.1 基础架构（5 服务器）

```
                      客户端
                        │
                        ▼
           ┌─────────────────────────┐
           │   Nginx (反向代理)        │
           │   192.168.10.120         │
           │   端口 80                │
           └────────────┬────────────┘
                        │ proxy_pass
                        ▼
           ┌─────────────────────────┐
           │   Java (Spring Boot)    │
           │   192.168.10.121         │
           │   端口 8080              │
           └────────────┬────────────┘
                        │ JDBC :3307
                        ▼
           ┌─────────────────────────┐
           │ ShardingSphere-Proxy     │
           │   192.168.10.126         │
           │   端口 3307              │
           └────────┬───────┬────────┘
                    │ 写     │ 读
                    ▼        ▼
      ┌──────────────────┐  ┌──────────────────┐
      │ MySQL Master 8.4 │  │ MySQL Slave 8.4  │
      │ 192.168.10.122   │  │ 192.168.10.125   │
      │ 端口 3306         │  │ 端口 3306         │
      └──────────────────┘  └──────────────────┘
                    │ 异步复制 (binlog)
                    └─────────▶──────────┘
```

### 1.2 高可用架构（7 服务器）

```
                      客户端
                        │
                        ▼
                   VIP (虚拟IP)
                192.168.1.200 (漂移)
                        │
           ┌────────────┴────────────┐
           │                         │
           ▼                         ▼
 ┌──────────────────┐     ┌──────────────────┐
 │  Nginx-1 (MASTER) │     │  Nginx-2 (BACKUP) │
 │  192.168.10.120   │     │  192.168.10.123   │
 │  Keepalived       │     │  Keepalived       │
 │  优先级 120        │     │  优先级 100        │
 └────────┬──────────┘     └────────┬──────────┘
           │                         │
           └───────────┬─────────────┘
                       │ proxy_pass (ip_hash)
                       ▼
           ┌─────────────────────────┐
           │   Nginx upstream 负载均衡  │
           └────────┬───────┬────────┘
                    │       │
           ┌────────┴─┐  ┌──┴──────────┐
           ▼           ▼  ▼              ▼
 ┌──────────────────┐  ┌──────────────────┐
 │  App-1           │  │  App-2           │
 │  192.168.10.121  │  │  192.168.10.124  │
 │  端口 8080        │  │  端口 8080        │
 └────────┬─────────┘  └────────┬─────────┘
           │                     │
           └──────────┬──────────┘
                      │ 直连 Proxy :3307
           ┌──────────┴──────────┐
           │ 写                   │ 读
           ▼                      ▼
 ┌──────────────────┐  ┌──────────────────┐
 │ MySQL Master 8.4 │  │ MySQL Slave 8.4  │
 │ 192.168.10.122   │  │ 192.168.10.125   │
 │ 读写              │  │ 只读 (read_only)  │
 └──────────────────┘  └──────────────────┘
           │ 异步复制 (binlog)
           └─────────▶──────────┘
```

---

## 二、服务器规划 & 网卡信息

### 2.1 IP 分配

| 角色 | 主机名 | IP（内网） | 网卡 | 外部/管理 IP | 端口 |
|------|--------|-----------|------|-------------|------|
| **Nginx-1** | nginx-1 | `192.168.10.120` | ens224 | 192.168.17.120 (ens160) | 80 |
| **Nginx-2** | nginx-2 | `192.168.10.123` | ens224 | 192.168.17.124 (ens160) | 80 |
| **App-1** | app-1 | `192.168.10.121` | ens160 | — | 8080 |
| **App-2** | app-2 | `192.168.10.124` | ens160 | — | 8080 |
| **ShardingSphere-Proxy** | proxy-1 | `192.168.10.126` | ens160 | — | 3307 |
| **MySQL-Master** | MySQL-Master | `192.168.10.122` | ens160 | — | 3306 |
| **MySQL-Slave** | MySQL-Slave | `192.168.10.125` | ens160 | — | 3306 |
| **VIP** | — | `192.168.1.200` | — | — | 80 |

> **网卡说明**：Nginx 服务器有双网卡 — ens160（外网，桥接模式，承载 VIP）和 ens224（内网 192.168.10.x）。App 和 MySQL 只有 ens160 接内网。

### 2.2 部署前检查

在每台服务器上确认 IP 和内网互通：

```bash
# 查看 IP
ip a | grep -E "inet 192\.168"

# 内网互通测试（从任意一台）
for ip in 120 121 122 123 124 125 126; do
    ping -c 1 -W 1 192.168.10.$ip > /dev/null 2>&1 && echo "192.168.10.$ip ✅" || echo "192.168.10.$ip ❌"
done
```

---

## 三、本地构建（Windows 开发机）

### 3.1 Maven 阿里云镜像（国内加速）

```bash
# 首次使用：复制阿里云 settings 到 Maven 配置目录
copy deploy\settings-aliyun.xml %USERPROFILE%\.m2\settings.xml
```

> 项目的 `pom.xml` 已内置阿里云仓库配置，此步骤可选但推荐。

### 3.2 构建 JAR

```bash
cd java/
mvn clean package -DskipTests

# 产物：target/demo-1.0.0.jar（约 64 MB）
```

### 3.3 上传到服务器

```bash
# JAR → App 服务器（两台都要传）
scp target/demo-1.0.0.jar root@192.168.10.121:/opt/ops-demo/app.jar
scp target/demo-1.0.0.jar root@192.168.10.124:/opt/ops-demo/app.jar

# 静态文件 → Nginx 服务器（两台都要传）
scp -r static/* root@192.168.10.120:/opt/ops-demo/static/
scp -r static/* root@192.168.10.123:/opt/ops-demo/static/

# Nginx 配置 → 两台 Nginx
scp nginx/ops-demo.conf root@192.168.10.120:/etc/nginx/conf.d/ops-demo.conf
scp nginx/ops-demo.conf root@192.168.10.123:/etc/nginx/conf.d/ops-demo.conf

# Keepalived 配置
scp nginx/keepalived-master.conf root@192.168.10.120:/etc/keepalived/keepalived.conf
scp nginx/keepalived-backup.conf root@192.168.10.123:/etc/keepalived/keepalived.conf

# SQL 脚本 → Master 和 Slave
scp sql/init-master.sql root@192.168.10.122:/tmp/
scp sql/init-slave.sql root@192.168.10.125:/tmp/
```

---

## 四、MySQL Master 层部署（192.168.10.122）

### 4.1 安装 MySQL 8.4

```bash
sudo dnf install -y https://dev.mysql.com/get/mysql84-community-release-el9-1.noarch.rpm
sudo dnf install -y mysql-community-server
```

### 4.2 配置 my.cnf（含主从复制参数）

```bash
sudo tee -a /etc/my.cnf.d/mysql-server.cnf >> /dev/null << 'EOF'

[mysqld]
bind-address    = 0.0.0.0
character-set-server = utf8mb4
collation-server     = utf8mb4_unicode_ci

# ===== 主从复制 — Master 配置 =====
server-id        = 1              # 唯一 ID，Master 固定为 1
log-bin          = mysql-bin      # 开启二进制日志（必须）
binlog_format    = ROW            # 行级复制（推荐）
expire_logs_days = 7             # binlog 保留 7 天
EOF
```

### 4.3 启动并初始化

```bash
sudo systemctl enable --now mysqld

# 获取临时密码
sudo grep 'temporary password' /var/log/mysqld.log

# 登录
mysql -u root -p
```

进入 MySQL 后执行：

```sql
ALTER USER 'root'@'localhost' IDENTIFIED BY 'RootPass@2024';

CREATE DATABASE IF NOT EXISTS ops_demo
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

-- 业务用户（两台 App 都要连）
CREATE USER IF NOT EXISTS 'ops_user'@'192.168.10.121' IDENTIFIED BY 'OpsUser@2024';
GRANT ALL PRIVILEGES ON ops_demo.* TO 'ops_user'@'192.168.10.121';

CREATE USER IF NOT EXISTS 'ops_user'@'192.168.10.124' IDENTIFIED BY 'OpsUser@2024';
GRANT ALL PRIVILEGES ON ops_demo.* TO 'ops_user'@'192.168.10.124';

-- ShardingSphere-Proxy 连接
CREATE USER IF NOT EXISTS 'ops_user'@'192.168.10.126' IDENTIFIED BY 'OpsUser@2024';
GRANT ALL PRIVILEGES ON ops_demo.* TO 'ops_user'@'192.168.10.126';

FLUSH PRIVILEGES;

-- 验证
SELECT User, Host FROM mysql.user WHERE User = 'ops_user';
```

> 或直接执行 `mysql -u root -p < /tmp/init-master.sql`

### 4.4 创建复制用户并记录 binlog 位置

```sql
-- 创建复制用户（供 Slave 连接）
CREATE USER IF NOT EXISTS 'repl'@'192.168.10.125' IDENTIFIED BY 'ReplPass@2024';
GRANT REPLICATION SLAVE, REPLICATION CLIENT ON *.* TO 'repl'@'192.168.10.125';
FLUSH PRIVILEGES;

-- ★ 记录以下输出，Slave 配置时需要
-- MySQL 8.4+ 使用 SHOW BINARY LOG STATUS（旧名 SHOW MASTER STATUS 已移除）
SHOW BINARY LOG STATUS\G
-- 输出示例:
-- File: mysql-bin.000001
-- Position: 157
-- → 记下这两个值！
```

### 4.5 防火墙

```bash
# App 服务器访问
sudo firewall-cmd --permanent --add-rich-rule='rule family="ipv4" source address="192.168.10.121" port protocol="tcp" port="3306" accept'
sudo firewall-cmd --permanent --add-rich-rule='rule family="ipv4" source address="192.168.10.124" port protocol="tcp" port="3306" accept'

# Slave 服务器访问（主从复制需要）
sudo firewall-cmd --permanent --add-rich-rule='rule family="ipv4" source address="192.168.10.125" port protocol="tcp" port="3306" accept'

sudo firewall-cmd --reload

# 验证
sudo firewall-cmd --list-rich-rules
```

### 4.6 验证数据库连通（从 App 服务器测试）

```bash
# 方式一：安装 mysql 客户端测试（在 app-1 上）
sudo dnf install -y mysql
mysql -h 192.168.10.122 -u ops_user -p -e "SHOW DATABASES;"

# 方式二：nc 测端口（无需装客户端）
nc -zv 192.168.10.122 3306
# 期望: Connected to 192.168.10.122 port 3306 [tcp/mysql] succeeded!

# 方式三：启动 Java 应用后看健康检查
curl http://127.0.0.1:8080/actuator/health
# 返回 {"status":"UP"} = 数据库连接正常
```

---

## 五、MySQL Slave 层部署 & 主从复制（192.168.10.125）

### 5.1 安装 MySQL 8.4

```bash
sudo dnf install -y https://dev.mysql.com/get/mysql84-community-release-el9-1.noarch.rpm
sudo dnf install -y mysql-community-server
```

### 5.2 配置 my.cnf

```bash
sudo tee -a /etc/my.cnf.d/mysql-server.cnf >> /dev/null << 'EOF'

[mysqld]
bind-address    = 0.0.0.0
character-set-server = utf8mb4
collation-server     = utf8mb4_unicode_ci

# ===== 主从复制 — Slave 配置 =====
server-id        = 2              # 唯一 ID，不能和 Master 重复
relay-log        = relay-bin      # 中继日志
read_only        = ON             # 从库只读（对非 SUPER 用户生效）
super_read_only  = ON             # 对 SUPER 用户（root）也生效
EOF
```

### 5.3 启动并初始化

```bash
sudo systemctl enable --now mysqld

# 获取临时密码
sudo grep 'temporary password' /var/log/mysqld.log

# 登录改密码
mysql -u root -p
```

```sql
ALTER USER 'root'@'localhost' IDENTIFIED BY 'RootPass@2024';
```

### 5.4 配置复制源并启动

**关键**：先修改 `/tmp/init-slave.sql` 中的 binlog 位置，填入 Master 上 `SHOW BINARY LOG STATUS` 的实际值：

```bash
# 编辑 init-slave.sql
vi /tmp/init-slave.sql
```

修改这两行：

```sql
MASTER_LOG_FILE = 'mysql-bin.000001',   -- ← 改成 Master 的实际 File 值
MASTER_LOG_POS  = 157,                   -- ← 改成 Master 的实际 Position 值
```

然后执行：

```bash
mysql -u root -p < /tmp/init-slave.sql
```

或者登录后逐条执行：

```sql
-- 1. 创建业务库（Schema 同步，数据由复制自动同步）
CREATE DATABASE IF NOT EXISTS ops_demo
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

-- 2. 配置复制源
CHANGE MASTER TO
    MASTER_HOST             = '192.168.10.122',
    MASTER_PORT             = 3306,
    MASTER_USER             = 'repl',
    MASTER_PASSWORD         = 'ReplPass@2024',
    MASTER_LOG_FILE         = 'mysql-bin.000001',
    MASTER_LOG_POS          = 157,
    MASTER_CONNECT_RETRY    = 60,
    MASTER_HEARTBEAT_PERIOD = 30;

-- 3. 启动复制线程
START SLAVE;

-- 4. 设置只读（对非 SUPER 用户生效）
SET GLOBAL read_only = ON;
```

### 5.5 验证复制状态

```sql
-- MySQL 8.4+ 使用 SHOW REPLICA STATUS（旧名 SHOW SLAVE STATUS 已移除）
SHOW REPLICA STATUS\G
```

**关键字段必须都是 Yes**：

```
Replica_IO_Running: Yes     ← I/O 线程（从 Source 拉取 binlog）
Replica_SQL_Running: Yes    ← SQL 线程（执行 binlog 中的语句）
Seconds_Behind_Source: 0    ← 复制延迟（0 = 实时同步）
```

### 5.6 防火墙

```bash
# 读写分离场景下，App 服务器需要连 Slave 进行读操作
sudo firewall-cmd --permanent --add-rich-rule='rule family="ipv4" source address="192.168.10.121" port protocol="tcp" port="3306" accept'
sudo firewall-cmd --permanent --add-rich-rule='rule family="ipv4" source address="192.168.10.124" port protocol="tcp" port="3306" accept'
sudo firewall-cmd --reload

# 验证
sudo firewall-cmd --list-rich-rules
```

### 5.7 功能验证：Master 写入 → Slave 同步

在 Master（.122）上：

```sql
USE ops_demo;
CREATE TABLE test_repl (id INT PRIMARY KEY, msg VARCHAR(50));
INSERT INTO test_repl VALUES (1, 'hello replication!');
```

在 Slave（.125）上：

```sql
USE ops_demo;
SELECT * FROM test_repl;   -- 应该能看到 id=1 这条数据！
```

清理（在 Master 上）：

```sql
DROP TABLE test_repl;      -- Slave 自动同步删除
```

---

## 六、Java 应用层部署（192.168.10.121 & 192.168.10.124）

> 两台 App 服务器步骤完全一致，以 App-1（.121）为例。

### 6.1 安装 Java 21

```bash
# JDK 安装路径：/usr/local/jdk-21.0.11
# 如未安装，下载解压后配置环境变量：
#   export JAVA_HOME=/usr/local/jdk-21.0.11
#   export PATH=$JAVA_HOME/bin:$PATH
java -version
# 期望: openjdk version "21.0.11"
```

### 6.2 创建目录和外部配置

```bash
sudo mkdir -p /opt/ops-demo/logs

# 外部 Spring Boot 配置（覆盖 server-id 和数据源连接信息）
sudo tee /opt/ops-demo/application.yml > /dev/null << 'EOF'
app:
  server-id: app-1
spring:
  datasource:
    url: jdbc:mysql://192.168.10.126:3307/ops_demo?useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=Asia/Shanghai&characterEncoding=UTF-8
    username: root
    password: proxy123
    driver-class-name: com.mysql.cj.jdbc.Driver
EOF
```

> **App-2（.124）**：`server-id: app-1` 改为 `server-id: app-2`，其他内容完全一致。

### 6.3 确认 JAR 已上传

```bash
ls -l /opt/ops-demo/app.jar
# 应该看到约 64MB 的 JAR 文件
```

### 6.4 创建 systemd 服务

**App-1（192.168.10.121）**：

```bash
sudo tee /etc/systemd/system/ops-demo.service > /dev/null << 'EOF'
[Unit]
Description=Linux Ops Demo - Spring Boot Backend
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/ops-demo
Environment=SERVER_ID=app-1
ExecStart=/usr/local/jdk-21.0.11/bin/java -jar /opt/ops-demo/app.jar \
    --spring.config.additional-location=file:/opt/ops-demo/application.yml
Restart=on-failure
RestartSec=10
StandardOutput=append:/opt/ops-demo/logs/app.log
StandardError=append:/opt/ops-demo/logs/app-error.log
ExecStop=/bin/kill -15 $MAINPID
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now ops-demo
```

> **App-2（192.168.10.124）**：systemd 服务内容同上，只需把 `Environment=SERVER_ID=app-1` 改为 `Environment=SERVER_ID=app-2`。

### 6.5 检查启动状态

```bash
sudo systemctl status ops-demo

# 实时看日志，看到 "Tomcat started on port 8080" 后 Ctrl+C
sudo journalctl -u ops-demo -f

# 健康检查
curl http://127.0.0.1:8080/actuator/health
# 期望: {"status":"UP"}
```

### 6.6 防火墙

```bash
# 只允许两台 Nginx 访问 8080
sudo firewall-cmd --permanent --add-rich-rule='rule family="ipv4" source address="192.168.10.120" port protocol="tcp" port="8080" accept'
sudo firewall-cmd --permanent --add-rich-rule='rule family="ipv4" source address="192.168.10.123" port protocol="tcp" port="8080" accept'
sudo firewall-cmd --reload
```

---

## 七、ShardingSphere-Proxy 读写分离（192.168.10.126）

> Proxy 作为独立进程运行，App 连接 Proxy（像连接普通 MySQL），由 Proxy 内部做读写分离路由。

### 7.1 安装 Java 21

```bash
# 从 app-1 复制 JDK
scp -r root@192.168.10.121:/usr/local/jdk-21.0.11 /usr/local/
echo 'export JAVA_HOME=/usr/local/jdk-21.0.11' > /etc/profile.d/java.sh
echo 'export PATH=$JAVA_HOME/bin:$PATH' >> /etc/profile.d/java.sh
source /etc/profile.d/java.sh
java -version
```

### 7.2 下载并安装 ShardingSphere-Proxy

```bash
cd /opt
wget https://dlcdn.apache.org/shardingsphere/5.5.3/apache-shardingsphere-5.5.3-shardingsphere-proxy-bin.tar.gz
tar -xzf apache-shardingsphere-5.5.3-shardingsphere-proxy-bin.tar.gz
mv apache-shardingsphere-5.5.3-shardingsphere-proxy-bin shardingsphere-proxy
cd shardingsphere-proxy

# 下载 MySQL 驱动
wget https://repo1.maven.org/maven2/com/mysql/mysql-connector-j/8.3.0/mysql-connector-j-8.3.0.jar -P lib/

# 删除不需要的驱动（避免依赖错误）
rm -f lib/*hive* lib/*zookeeper* lib/*seata* 2>/dev/null
```

### 7.3 配置 Proxy

```bash
# global.yaml — 权限和端口
cat > conf/global.yaml << 'EOF'
mode:
  type: Standalone
  repository:
    type: Memory

authority:
  users:
    - user: root@%
      password: proxy123
  privilege:
    type: ALL_PERMITTED

props:
  proxy-default-port: 3307
  sql-show: false
EOF

# database-readwrite-splitting.yaml — 读写分离规则
cat > conf/database-readwrite-splitting.yaml << 'EOF'
databaseName: ops_demo

dataSources:
  master:
    url: jdbc:mysql://192.168.10.122:3306/ops_demo?useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=Asia/Shanghai
    username: ops_user
    password: OpsUser@2024
    connectionTimeoutMilliseconds: 30000
    idleTimeoutMilliseconds: 60000
    maxLifetimeMilliseconds: 1800000
    maxPoolSize: 20
    minPoolSize: 5
  slave:
    url: jdbc:mysql://192.168.10.125:3306/ops_demo?useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=Asia/Shanghai
    username: ops_user
    password: OpsUser@2024
    connectionTimeoutMilliseconds: 30000
    idleTimeoutMilliseconds: 60000
    maxLifetimeMilliseconds: 1800000
    maxPoolSize: 20
    minPoolSize: 5

rules:
  - !SINGLE
    tables:
      - "*.*"
    defaultDataSource: readwrite_ds
  - !READWRITE_SPLITTING
    dataSourceGroups:
      readwrite_ds:
        writeDataSourceName: master
        readDataSourceNames:
          - slave
        transactionalReadQueryStrategy: PRIMARY
        loadBalancerName: round_robin
    loadBalancers:
      round_robin:
        type: ROUND_ROBIN
EOF
```

### 7.4 MySQL 授权 Proxy

```bash
# Master (.122) 和 Slave (.125) 上都要执行
mysql -u root -p << 'SQL'
CREATE USER IF NOT EXISTS 'ops_user'@'192.168.10.126' IDENTIFIED BY 'OpsUser@2024';
GRANT ALL PRIVILEGES ON ops_demo.* TO 'ops_user'@'192.168.10.126';
FLUSH PRIVILEGES;
SQL

# Slave 执行前需临时关闭只读：
# SET GLOBAL super_read_only = OFF;
# SET GLOBAL read_only = OFF;
# ... 执行完再改回 ON
```

### 7.5 创建 systemd 服务

```bash
cat > /etc/systemd/system/shardingsphere-proxy.service << 'EOF'
[Unit]
Description=ShardingSphere-Proxy
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/shardingsphere-proxy
ExecStart=/usr/local/jdk-21.0.11/bin/java -cp "/opt/shardingsphere-proxy/conf:/opt/shardingsphere-proxy/lib/*:/opt/shardingsphere-proxy/ext-lib/*" org.apache.shardingsphere.proxy.Bootstrap -1 /opt/shardingsphere-proxy/conf 0.0.0.0
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now shardingsphere-proxy
```

### 7.6 防火墙

```bash
# 只允许两台 App 访问
firewall-cmd --permanent --add-rich-rule='rule family="ipv4" source address="192.168.10.121" port protocol="tcp" port="3307" accept'
firewall-cmd --permanent --add-rich-rule='rule family="ipv4" source address="192.168.10.124" port protocol="tcp" port="3307" accept'
firewall-cmd --reload
```

### 7.7 验证

```bash
# 从 app-1 测试 Proxy 连通性和读写分离
mysql -h 192.168.10.126 -P 3307 -u root -pproxy123 -e "USE ops_demo; SELECT * FROM users;"
# 期望：返回 user 表数据
```

---

## 八、Nginx 接入层部署（192.168.10.120 & 192.168.10.123）

### 8.1 安装 Nginx

```bash
sudo dnf install -y nginx
```

### 8.2 创建目录结构

```bash
sudo mkdir -p /opt/ops-demo/static
```

确认静态文件已上传：

```bash
ls /opt/ops-demo/static/
# 应该看到: index.html  login.html  register.html  users.html  css/  js/
```

设置权限（Nginx worker 只需要读权限）：

```bash
sudo chown -R root:root /opt/ops-demo/static/
sudo find /opt/ops-demo/static/ -type d -exec chmod 755 {} \;
sudo find /opt/ops-demo/static/ -type f -exec chmod 644 {} \;
```

| 命令 | 效果 |
|------|------|
| `chown root:root` | 所有者归 root，Nginx 进程（nginx 用户）无法修改文件 |
| 目录 `755` | `rwxr-xr-x` — 其他人可读可进入 |
| 文件 `644` | `rw-r--r--` — 其他人只读 |

### 8.3 部署 Nginx 配置

配置文件：参见 [nginx/ops-demo.conf](../nginx/ops-demo.conf)

```bash
# 确认配置已上传
ls -l /etc/nginx/conf.d/ops-demo.conf

# 移除默认欢迎页（避免端口冲突）
sudo rm -f /etc/nginx/conf.d/default.conf 2>/dev/null
sudo rm -f /etc/nginx/nginx.conf 2>/dev/null

# 测试配置语法
sudo nginx -t
# 期望: syntax is ok / test is successful

# 启动
sudo systemctl enable --now nginx
```

### 8.4 配置要点说明

`nginx/ops-demo.conf` 的核心功能：

| 路径 | 处理方式 |
|------|---------|
| `/nginx-health` | Nginx 自身健康检查（供 Keepalived 检测） |
| `/api/**` | 反向代理到 Java upstream（ip_hash 会话亲和） |
| `/actuator/health` | 仅允许内网 IP 访问 |
| `/` | 静态文件，SPA fallback 到 index.html |
| `*.css/js/图片` | 7 天浏览器缓存 |

### 8.5 SELinux 配置

```bash
# 允许 Nginx 发起反向代理网络连接
sudo setsebool -P httpd_can_network_connect 1

# 设置静态文件上下文
sudo chcon -R -t httpd_sys_content_t /opt/ops-demo/static

# 如仍有权限问题，查看审计日志
# sudo ausearch -m avc -ts recent | audit2allow -a
```

### 8.6 防火墙

```bash
sudo firewall-cmd --permanent --add-port=80/tcp
sudo firewall-cmd --reload
```

### 8.7 验证

```bash
# 本机测试
curl http://127.0.0.1/nginx-health     # 期望: OK
curl http://127.0.0.1/                  # 期望: 登录页面 HTML

# 从其他内网机器测试
curl http://192.168.10.120/nginx-health
curl http://192.168.10.123/nginx-health
```

---

## 九、Keepalived 高可用（两台 Nginx 之间）

### 9.1 安装

```bash
# 两台 Nginx 都装
sudo dnf install -y keepalived
```

### 9.2 部署配置

| 服务器 | 配置文件 | 说明 |
|--------|---------|------|
| Nginx-1 (.120) | [nginx/keepalived-master.conf](../nginx/keepalived-master.conf) | 优先级 120，MASTER |
| Nginx-2 (.123) | [nginx/keepalived-backup.conf](../nginx/keepalived-backup.conf) | 优先级 100，BACKUP |

关键参数：
- **网卡**：`ens160`（外网桥接网卡）
- **VIP**：`192.168.1.200`
- **virtual_router_id**：51（两台必须一致）
- **健康检测**：每 2 秒 curl `/nginx-health`，连续 3 次失败触发 VIP 漂移

```bash
# 上传配置后
# 先启动 BACKUP（Nginx-2），再启动 MASTER（Nginx-1）
# Nginx-2:
sudo systemctl enable --now keepalived

# Nginx-1:
sudo systemctl enable --now keepalived
```

### 9.3 验证 VIP

```bash
# Nginx-1 上应能看到 VIP
ip a | grep 192.168.1.200
# 期望: inet 192.168.1.200/24 ... ens160:vip

# Nginx-2 上不应看到 VIP（仅 MASTER 持有）
ssh root@192.168.10.123 "ip a | grep 192.168.1.200"
# 期望: 无输出

# 通过 VIP 访问
curl http://192.168.1.200/nginx-health  # 期望: OK
curl http://192.168.1.200/              # 期望: 登录页面
```

### 9.4 VRRP 防火墙

```bash
# 两台 Nginx 都执行
sudo firewall-cmd --permanent --add-rich-rule='rule protocol value="vrrp" accept'
sudo firewall-cmd --reload
```

### 9.5 故障切换测试

```bash
# 1. 确认 VIP 在 Nginx-1 上
ssh root@192.168.10.120 "ip a | grep 192.168.1.200"

# 2. 停掉 Nginx-1 的 Nginx
ssh root@192.168.10.120 "sudo systemctl stop nginx"

# 3. 等 5-10 秒，VIP 应漂移到 Nginx-2
ssh root@192.168.10.123 "ip a | grep 192.168.1.200"
# 期望: 能看到 VIP

# 4. 通过 VIP 仍能正常访问
curl http://192.168.1.200/nginx-health  # 期望: OK

# 5. 恢复 Nginx-1
ssh root@192.168.10.120 "sudo systemctl start nginx"
# VIP 自动回到 Nginx-1（优先级更高）
```

---

## 十、双 Java 负载均衡

两台 Nginx 的 upstream 配置完全相同（参见 [nginx/ops-demo.conf](../nginx/ops-demo.conf)）：

```nginx
upstream java_backend {
    ip_hash;   # 会话亲和：同一客户端 IP 始终到同一后端
    server 192.168.10.121:8080 max_fails=3 fail_timeout=30s;
    server 192.168.10.124:8080 max_fails=3 fail_timeout=30s;
    keepalive 32;
}
```

> **为什么用 ip_hash？** 项目未引入 Redis，不用 ip_hash 会导致登录状态在 Java-1 和 Java-2 之间丢失。

同步文件时两台都要更新：

```bash
# 静态文件 → 两台 Nginx
scp -r static/* root@192.168.10.120:/opt/ops-demo/static/
scp -r static/* root@192.168.10.123:/opt/ops-demo/static/

# JAR → 两台 App（上传后需重启）
scp target/demo-1.0.0.jar root@192.168.10.121:/opt/ops-demo/app.jar
ssh root@192.168.10.121 "sudo systemctl restart ops-demo"
scp target/demo-1.0.0.jar root@192.168.10.124:/opt/ops-demo/app.jar
ssh root@192.168.10.124 "sudo systemctl restart ops-demo"
```

---

## 十一、读写分离架构

### 11.1 工作原理

Java 应用通过 JDBC 连接 ShardingSphere-Proxy（192.168.10.126:3307），Proxy 作为独立的数据库中间件，自动将读写请求路由到不同 MySQL 实例：

| SQL 类型 | 路由目标 | 说明 |
|---------|---------|------|
| INSERT / UPDATE / DELETE | **Master** (.122) | 所有写入走主库 |
| SELECT | **Slave** (.125) | 查询走从库，轮询负载均衡 |
| SELECT（事务内） | **Master** (.122) | 避免主从延迟读到旧数据 |
| DDL（CREATE/ALTER） | **Master** (.122) | 表结构变更走主库 |

> Proxy 使用 `!SINGLE` 规则（`*.*`）自动发现数据库中的单表，无需手动声明表名。

### 11.2 验证读写分离

```bash
# 在 Proxy 日志中观察 SQL 路由（需先开启 sql-show: true 并重启）
tail -f /opt/shardingsphere-proxy/logs/stdout.log | grep -E "Actual SQL|Logic SQL"

# 写操作 → 应显示路由到 master
# Logic SQL: INSERT INTO users ...
# Actual SQL: master ::: INSERT INTO users ...

# 读操作 → 应显示路由到 slave
# Logic SQL: SELECT ... FROM users
# Actual SQL: slave ::: SELECT ... FROM users
```

### 11.3 浏览器 F12 观察服务器标识

部署完成后，打开浏览器 `F12` → **Network** 标签，刷新页面或触发 API 请求，在响应头中可以看到：

| 响应头 | 含义 | 示例值 |
|--------|------|--------|
| `X-Nginx-Server` | 当前处理请求的 Nginx 服务器（自动取主机名） | `nginx-1` 或 `nginx-2` |
| `X-Java-Server` | 当前处理 API 请求的 Java 后端（systemd 中配置） | `app-1` 或 `app-2` |

> **注意**：`X-Java-Server` 只在 `/api/` 请求的响应中出现（经过 Java 后端处理），静态文件请求只有 `X-Nginx-Server`。

**运维实训观察点：**

1. **正常情况** — 同一客户端所有请求看到同一台 Java（ip_hash 会话亲和）
2. **Nginx 故障切换** — 停掉 Nginx-1 的 Nginx 后，`X-Nginx-Server` 变为 `nginx-2`
3. **Java 故障** — 停掉 App-1 后，Nginx 自动把新请求发到 App-2

---

## 十二、完整验证清单

### 12.1 基础连通性

```bash
# 所有服务器互通
for ip in 120 121 122 123 124 125 126; do
    ping -c 1 -W 1 192.168.10.$ip > /dev/null 2>&1 && echo "192.168.10.$ip ✅" || echo "192.168.10.$ip ❌"
done

# 两台 Java 都健康
curl http://192.168.10.121:8080/actuator/health
curl http://192.168.10.124:8080/actuator/health

# 两台 Nginx 都正常
curl http://192.168.10.120/nginx-health
curl http://192.168.10.123/nginx-health

# VIP 可访问
curl http://192.168.1.200/nginx-health
```

### 12.2 数据库层验证

```bash
# Master（.122）
mysql -u root -p -e "SHOW DATABASES;"
mysql -u root -p -e "SELECT User, Host FROM mysql.user WHERE User='ops_user';"
mysql -u root -p -e "SHOW BINARY LOG STATUS\G"

# Slave（.125）
mysql -u root -p -e "SHOW REPLICA STATUS\G" | grep -E "Running|Behind"
# 期望: Replica_IO_Running: Yes / Replica_SQL_Running: Yes / Seconds_Behind_Source: 0

# 数据同步验证
mysql -h 192.168.10.122 -u ops_user -p -e "SELECT COUNT(*) FROM ops_demo.users;"
mysql -h 192.168.10.125 -u ops_user -p -e "SELECT COUNT(*) FROM ops_demo.users;"
# 两个 count 应该一致
```

### 12.3 端到端测试（通过 VIP）

```bash
# 注册
curl -X POST http://192.168.1.200/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"123456","email":"admin@test.local"}'

# 登录
TOKEN=$(curl -s -X POST http://192.168.1.200/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"123456"}' | grep -o '"token":"[^"]*"' | cut -d'"' -f4)

# 访问受保护接口
curl http://192.168.1.200/api/users -H "Authorization: Bearer $TOKEN"

# 浏览器访问 http://192.168.1.200/ — 应看到登录页面，能注册、登录、管理用户
```

### 12.4 各层验证

```bash
# MySQL 层
ssh root@192.168.10.122 "mysql -u root -p -e 'SHOW BINARY LOG STATUS\G'"
ssh root@192.168.10.125 "mysql -u root -p -e 'SHOW REPLICA STATUS\G' | grep Running"

# Java 层（在 .121 和 .124 上）
sudo systemctl status ops-demo
curl http://127.0.0.1:8080/actuator/health

# Nginx 层（在 .120 和 .123 上）
sudo systemctl status nginx
curl http://127.0.0.1/nginx-health
```

---

## 十三、故障排查

| 现象 | 检查方向 |
|------|---------|
| Nginx 502 Bad Gateway | Java 服务是否启动？`sudo systemctl status ops-demo`；防火墙是否拦截？ |
| Nginx 静态文件 403 | `sudo chcon -R -t httpd_sys_content_t /opt/ops-demo/static` |
| 注册/登录报错 | Java 日志 `sudo journalctl -u ops-demo -f` |
| `ERROR 2003: No route to host` | MySQL 防火墙未放行：① `sudo systemctl status mysqld` ② `sudo ss -tlnp \| grep 3306` ③ 检查 rich-rule |
| 数据库连接失败 | `nc -zv 192.168.10.122 3306` 测端口 |
| 无法访问 80 端口 | `sudo firewall-cmd --list-ports` |
| Java 启动后立即退出 | `sudo journalctl -u ops-demo -n 50`；常见：数据库连不上、端口被占用 |
| Slave 读操作报错 | `SHOW REPLICA STATUS\G` 确认 IO/SQL 都是 Yes；检查 Slave 防火墙 |
| 主从复制中断 | `SHOW REPLICA STATUS\G` 查看 `Last_Error`；常见：主键冲突、SQL 语法不兼容 |
| 主从数据不一致 | `CHECKSUM TABLE ops_demo.users` 分别在 Master 和 Slave 执行对比 |
| `curl 外部IP:8080` 不通但 `127.0.0.1:8080` 正常 | **防火墙限制** — 8080 端口只对 Nginx 服务器白名单放行 |
| `/actuator/health` curl 卡住不动 | ① 先确认 8080 在监听 `ss -tlnp \| grep 8080` ② 看应用日志是否 `Tomcat started` |
| VIP 不漂移 | ① virtual_router_id 和 auth_pass 是否一致？② VRRP 防火墙规则？③ interface 网卡名是否正确？ |
| VIP 两台都持有（脑裂） | ① 两台 Nginx 间网络是否互通？② VRRP 多播（224.0.0.18）是否被防火墙屏蔽？ |
| Keepalived 无法启动 | `sudo journalctl -u keepalived -n 20`；常见：配置文件语法、网卡名不对 |
| 登录后掉线 | 检查 upstream 是否配了 `ip_hash`；轮询会导致请求随机到另一台 Java，Session 丢失 |
| SELinux 权限问题 | `sudo ausearch -m avc -ts recent \| audit2allow -a` |

---

## 十四、服务器文件路径汇总

| 服务器 | 文件 | 路径 |
|--------|------|------|
| **Nginx-1 (.120)** | Nginx 配置 | `/etc/nginx/conf.d/ops-demo.conf` |
| | Keepalived 配置 | `/etc/keepalived/keepalived.conf` |
| | 静态文件 | `/opt/ops-demo/static/` |
| **Nginx-2 (.123)** | Nginx 配置 | `/etc/nginx/conf.d/ops-demo.conf`（同 Nginx-1） |
| | Keepalived 配置 | `/etc/keepalived/keepalived.conf` |
| | 静态文件 | `/opt/ops-demo/static/`（同 Nginx-1） |
| **App-1 (.121)** | JAR | `/opt/ops-demo/app.jar` |
| | 外部配置 | `/opt/ops-demo/application.yml` |
| | 应用日志 | `/opt/ops-demo/logs/` |
| | systemd | `/etc/systemd/system/ops-demo.service` |
| **App-2 (.124)** | 同上 | 同 App-1 |
| **Proxy-1 (.126)** | 全局配置 | `/opt/shardingsphere-proxy/conf/global.yaml` |
| | 读写分离 | `/opt/shardingsphere-proxy/conf/database-readwrite-splitting.yaml` |
| | systemd | `/etc/systemd/system/shardingsphere-proxy.service` |
| **MySQL-Master (.122)** | MySQL 配置 | `/etc/my.cnf.d/mysql-server.cnf` |
| **MySQL-Slave (.125)** | MySQL 配置 | `/etc/my.cnf.d/mysql-server.cnf` |

---

## 十五、项目文件清单

```
java/
├── pom.xml
├── src/main/java/com/ops/demo/    # Spring Boot 后端
├── src/main/resources/
│   ├── application.yml            # 主配置（数据源、JPA、JWT）
│   └── application-dev.yml        # 开发环境覆写
├── static/                        # 前端（Nginx 直接 serve）
│   ├── index.html
│   ├── login.html
│   ├── register.html
│   ├── users.html
│   ├── css/style.css
│   └── js/
│       ├── api.js                 # HTTP 请求封装
│       ├── auth.js                # 登录/注册逻辑
│       └── users.js               # 用户管理逻辑
├── nginx/
│   ├── ops-demo.conf              # Nginx 配置（双 upstream + ip_hash）
│   ├── keepalived-master.conf     # Keepalived MASTER（Nginx-1）
│   └── keepalived-backup.conf     # Keepalived BACKUP（Nginx-2）
├── sql/
│   ├── init.sql                   # 单机数据库初始化
│   ├── init-master.sql            # MySQL 主库初始化（主从复制用）
│   └── init-slave.sql             # MySQL 从库初始化（主从复制用）
├── deploy/
│   ├── README.md                  # ★ 本文件
│   └── settings-aliyun.xml        # Maven 阿里云镜像配置
├── stress_test.py                 # 压力测试脚本（攀升 + 极限模式）
└── docs/
    └── README.md                  # 项目概述
```
