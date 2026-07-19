# Linux 运维实训演示项目 — 设计规格

**日期：** 2026-07-19
**状态：** 已确认

## 概述

基于 Rocky Linux 9.8 的运维实训演示 Java 项目，核心是通过"用户管理系统"业务演示 Nginx 动静分离、反向代理、Java 服务部署、MySQL 运维等完整流程。

## 技术栈

| 组件 | 版本 | 用途 |
|------|------|------|
| Rocky Linux | 9.8 | 操作系统 |
| Nginx | 1.30 | 反向代理 + 静态资源服务 |
| OpenJDK | 21 | Java 运行环境 |
| Maven | 3.9.16 | 项目构建 |
| MySQL | 8.4 | 数据库 |
| Spring Boot | 3.x | Java 后端框架 |
| Spring Data JPA | — | ORM / 数据访问层 |
| JWT (jjwt) | — | 无状态认证 |

## 架构

```
浏览器
  │
  ▼
Nginx (:80)
  ├── /, *.html, /css/*, /js/*  → 静态文件直接返回
  ├── /api/*                     → proxy_pass http://127.0.0.1:8080
  └── /actuator/health           → 仅本地可访问
       │
       ▼
Spring Boot (:8080)
  ├── /api/auth/login, /register  (公开)
  ├── /api/users CRUD             (需 JWT)
  └── /actuator/health            (运维端点)
       │
       ▼
MySQL 8.4 (:3306)
  └── ops_demo.users
```

## 项目结构

```
java/
├── pom.xml
├── src/main/java/com/ops/demo/
│   ├── DemoApplication.java
│   ├── config/SecurityConfig.java
│   ├── controller/AuthController.java
│   ├── controller/UserController.java
│   ├── model/User.java
│   ├── repository/UserRepository.java
│   ├── service/UserService.java
│   ├── service/JwtService.java
│   ├── dto/LoginRequest.java
│   ├── dto/RegisterRequest.java
│   ├── dto/LoginResponse.java
│   └── security/JwtAuthFilter.java
├── src/main/resources/
│   ├── application.yml
│   └── application-dev.yml
├── static/          ← Nginx 直接 serve
│   ├── index.html
│   ├── login.html
│   ├── users.html
│   ├── css/style.css
│   └── js/{api,auth,users}.js
├── nginx/ops-demo.conf
├── sql/init.sql
└── docs/README.md
```

## 业务功能

1. **用户注册** — POST /api/auth/register {username, password, email}
2. **用户登录** — POST /api/auth/login {username, password} → {token, username}
3. **用户列表** — GET /api/users (需 JWT)
4. **创建用户** — POST /api/users (需 JWT)
5. **更新用户** — PUT /api/users/{id} (需 JWT)
6. **删除用户** — DELETE /api/users/{id} (需 JWT)

## 认证方案

- JWT Token 存储在浏览器 localStorage
- 前端每次请求通过 `Authorization: Bearer <token>` 携带
- Spring Security + OncePerRequestFilter 拦截 `/api/**`（除 `/api/auth/**`）验证 Token
- Nginx 不参与认证，纯透传

## Redis 预留

- `pom.xml` 包含 `spring-boot-starter-data-redis` 依赖
- `application.yml` 中 Redis 配置全部注释，标注 "Redis 扩展预留"
- `RedisConfig.java` 使用 `@ConditionalOnProperty(prefix = "spring.redis", name = "enabled", havingValue = "true")`，默认不加载
- 后续实训只需：取消注释、启动 Redis、设置 `spring.redis.enabled=true`

## 运维演示要点

| 技能点 | 演示方式 |
|--------|---------|
| Nginx 反向代理 | 配置 `/api/*` → proxy_pass |
| 动静分离 | 静态资源 Nginx 直接返回，API 转发 Java |
| Java 服务部署 | `mvn package` → `java -jar` 启动 |
| 健康检查 | /actuator/health + Nginx health check |
| 数据库运维 | MySQL 连接配置、连接池参数调优 |
| 日志排查 | Spring Boot 日志 + Nginx access/error log |
| JWT 排障 | Token 过期、签名验证失败等场景 |
