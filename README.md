# Linux 运维实训演示项目

基于 Rocky Linux 9.x 的用户管理系统，7 台服务器实现高可用架构：双 Nginx + Keepalived + 双 App + ShardingSphere-Proxy 读写分离 + MySQL 主从复制。

## 高可用架构

```
                     客户端
                        │
                       VIP
                  192.168.1.200
                        │
           ┌────────────┴────────────┐
           │                         │
    Nginx-1 (.120)  MASTER     Nginx-2 (.123)  BACKUP
    Keepalived 优先级 120       Keepalived 优先级 100
           │                         │
           └───────────┬─────────────┘
                       │ proxy_pass (ip_hash)
           ┌───────────┴───────────┐
           │                       │
      App-1 (.121)            App-2 (.124)
           │                       │
           └───────────┬───────────┘
                       │ JDBC :3307
                       ▼
              ShardingSphere-Proxy
                 proxy-1 (.126)
                  ┌────┴────┐
                  │ 写       │ 读
                  ▼          ▼
          MySQL Master   MySQL Slave
            (.122)         (.125)
              │── binlog ──→│
```

## 服务器规划

| 角色 | 主机名 | IP | 端口 |
|------|--------|-----|------|
| Nginx-1（MASTER） | nginx-1 | 192.168.10.120 | 80 |
| Nginx-2（BACKUP） | nginx-2 | 192.168.10.123 | 80 |
| App-1 | app-1 | 192.168.10.121 | 8080 |
| App-2 | app-2 | 192.168.10.124 | 8080 |
| ShardingSphere-Proxy | proxy-1 | 192.168.10.126 | 3307 |
| MySQL Master | MySQL-Master | 192.168.10.122 | 3306 |
| MySQL Slave | MySQL-Slave | 192.168.10.125 | 3306 |
| VIP | — | 192.168.1.200 | 80 |

## 技术栈

| 组件 | 版本 | 用途 |
|------|------|------|
| Rocky Linux | 9.x | 操作系统 |
| Nginx | 1.x | 反向代理 + 静态文件 |
| Keepalived | 2.x | VIP 高可用漂移 |
| OpenJDK | 21 | Java 运行时 |
| Spring Boot | 3.3.4 | 应用框架 |
| **ShardingSphere-Proxy** | **5.5.3** | **读写分离（独立进程）** |
| MySQL | 8.4 | 数据存储（主从复制） |

## 快速开始

### 1. 初始化数据库

```bash
# Master
mysql -u root -p < sql/init-master.sql
# Slave
mysql -u root -p < sql/init-slave.sql
```

### 2. 构建项目

```bash
mvn clean package -DskipTests
```

### 3. 启动 Java 服务

```bash
java -jar target/demo-1.0.0.jar --spring.profiles.active=dev
```

### 4. 配置 Nginx

```bash
cp nginx/ops-demo.conf /etc/nginx/conf.d/
nginx -t && systemctl reload nginx
```

### 5. 启动 ShardingSphere-Proxy

```bash
cd /opt/shardingsphere-proxy
bin/start.sh
mysql -h 127.0.0.1 -P 3307 -u root -pproxy123 -e "SELECT 1"
```

### 6. 验证

- 浏览器访问 `http://<服务器IP>/`
- 健康检查: `curl http://localhost:8080/actuator/health`

> 完整部署流程参见 [deploy/README.md](../deploy/README.md)

## 项目结构

```
java/
├── pom.xml                        # Maven 构建配置
├── src/main/java/com/ops/demo/
│   ├── DemoApplication.java       # Spring Boot 启动类
│   ├── config/                    # Security、Redis、ServerIdentity 配置
│   ├── controller/                # REST 控制器（Auth、User）
│   ├── model/                     # JPA 实体（User）
│   ├── repository/                # 数据访问层
│   ├── service/                   # 业务逻辑 + JWT
│   ├── dto/                       # 请求/响应 DTO
│   ├── exception/                 # 全局异常处理
│   └── security/                  # JWT 认证过滤器
├── src/main/resources/
│   ├── application.yml            # 主配置（JWT、数据源直连 Proxy）
│   └── application-dev.yml        # 开发环境覆写
├── static/                        # 前端静态文件（Nginx 直接 serve）
├── nginx/                         # Nginx + Keepalived 配置
├── sql/                           # 数据库初始化脚本（主从）
├── deploy/                        # 部署指南 + Maven 镜像配置
├── stress_test.py                 # 压力测试（攀升找极限 + 极限模式）
└── docs/                          # 项目文档
```

## API 端点

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/api/auth/register` | 用户注册 | 否 |
| POST | `/api/auth/login` | 用户登录 | 否 |
| GET | `/api/users` | 用户列表 | JWT |
| POST | `/api/users` | 创建用户 | JWT |
| PUT | `/api/users/{id}` | 更新用户 | JWT |
| DELETE | `/api/users/{id}` | 删除用户 | JWT |
| GET | `/actuator/health` | 健康检查 | 仅内网 |

## 运维实训要点

1. **Nginx 反向代理** — 观察 `/api/` 请求的 proxy_pass 转发，ip_hash 会话保持
2. **动静分离** — `static/` 下文件由 Nginx 直接返回，API 由 Java 处理
3. **高可用故障切换** — 停 Nginx-1，观察 VIP 自动漂移到 Nginx-2
4. **负载均衡** — 停 App-1，观察请求自动切到 App-2
5. **读写分离** — ShardingSphere-Proxy 自动将 SELECT 路由到 Slave，INSERT/UPDATE/DELETE 路由到 Master
6. **服务器身份识别** — 响应头 `X-Nginx-Server` 和 `X-Java-Server` 标识当前处理节点
7. **数据库运维** — MySQL 主从复制状态监控、复制延迟检查
8. **JWT 排障** — Token 过期、签名验证失败场景

## 性能基线

| 指标 | 值 |
|------|-----|
| 全链路 QPS（VIP） | 181（150 并发，0 失败） |
| 单节点 QPS 极限 | 36（2 核 VM CPU 满载） |
| 双节点 600 并发 | 99.9% 成功率（2/2000 超时） |
| Nginx / Proxy / MySQL | 远未饱和 |

> 压力测试脚本：`python stress_test.py --brutal -c 300 -n 1000`

## Redis 扩展

项目已预留 Redis 结构，后续实训只需：

1. 取消 `application.yml` 中 Redis 配置段的注释
2. 取消 `spring.autoconfigure.exclude` 中 Redis 的两行
3. 启动 Redis 服务 — `RedisConfig` 自动加载
