# Linux 运维实训演示项目

基于 Rocky Linux 9.8 的用户管理系统，用于练习 Nginx 反向代理、动静分离、Java 服务部署和 MySQL 运维。

## 技术栈

| 组件 | 版本 |
|------|------|
| Rocky Linux | 9.8 |
| Nginx | 1.30 |
| OpenJDK | 21 |
| Apache Maven | 3.9.16 |
| MySQL | 8.4 |
| Spring Boot | 3.3.x |

## 快速开始

### 1. 克隆项目

```bash
git clone <repo-url> /opt/ops-demo
cd /opt/ops-demo
```

### 2. 初始化数据库

```bash
mysql -u root -p < sql/init.sql
```

### 3. 构建项目

```bash
mvn clean package -DskipTests
```

### 4. 启动 Java 服务

```bash
java -jar target/demo-1.0.0.jar --spring.profiles.active=dev
```

### 5. 配置 Nginx

```bash
cp nginx/ops-demo.conf /etc/nginx/conf.d/
# 修改 server_name 和 root 路径
nginx -t && systemctl reload nginx
```

### 6. 验证

- 浏览器访问 `http://<服务器IP>/`
- API 测试: `curl http://localhost:8080/api/auth/login`

## 项目结构

```
java/
├── pom.xml                    # Maven 构建配置
├── src/main/java/com/ops/demo/
│   ├── DemoApplication.java   # Spring Boot 启动类
│   ├── config/                # 配置类（Security, Redis 预留）
│   ├── controller/            # REST 控制器
│   ├── model/                 # JPA 实体
│   ├── repository/            # 数据访问层
│   ├── service/               # 业务逻辑层
│   ├── dto/                   # 数据传输对象
│   └── security/              # JWT 认证过滤器
├── src/main/resources/
│   ├── application.yml        # 主配置
│   └── application-dev.yml    # 开发环境配置
├── static/                    # 静态资源（Nginx 直接 serve）
├── nginx/                     # Nginx 配置文件
├── sql/                       # 数据库初始化脚本
└── docs/                      # 项目文档
```

## API 端点

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | /api/auth/register | 用户注册 | 否 |
| POST | /api/auth/login | 用户登录 | 否 |
| GET | /api/users | 用户列表 | JWT |
| POST | /api/users | 创建用户 | JWT |
| PUT | /api/users/{id} | 更新用户 | JWT |
| DELETE | /api/users/{id} | 删除用户 | JWT |
| GET | /actuator/health | 健康检查 | 仅本地 |

## 运维实训演示要点

1. **Nginx 反向代理** — 观察 `/api/` 请求的 proxy_pass 转发
2. **动静分离** — `static/` 下文件由 Nginx 直接返回，API 由 Java 处理
3. **日志排查** — `/var/log/nginx/ops-demo-*.log` + Spring Boot 日志
4. **健康检查** — `curl localhost/actuator/health`
5. **数据库运维** — 连接池参数调优、慢查询分析
6. **JWT 排障** — Token 过期、签名验证失败场景

## Redis 扩展

项目已预留 Redis 代码结构，后续实训只需：

1. 取消 `application.yml` 中 Redis 配置的注释
2. 设置 `spring.data.redis.enabled: true`
3. 启动 Redis 服务
4. `RedisConfig` 自动加载
