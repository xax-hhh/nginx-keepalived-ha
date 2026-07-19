# Linux 运维实训演示项目 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建基于 Spring Boot 3.x + JWT + MySQL 的用户管理系统，配合 Nginx 动静分离部署方案。

**Architecture:** Nginx 反向代理 + Spring Boot 后端 + MySQL。静态文件（HTML/CSS/JS）由 Nginx 直接 serve，`/api/**` 请求转发至 Java 服务。JWT 无状态认证，Spring Data JPA 数据访问。

**Tech Stack:** Java 21, Spring Boot 3.x, Spring Security, Spring Data JPA, jjwt, MySQL 8.4, Maven 3.9, Nginx 1.30

## Global Constraints

- Java 21 源码和目标版本
- Spring Boot 3.x（Java 17+ baseline 任一版本）
- 所有 API 返回 JSON，Content-Type: application/json
- JWT 密钥通过 application.yml 配置
- Redis 依赖已引入但默认禁用，配置全部注释
- 静态文件零构建依赖，Nginx 直接 serve
- 数据库名：`ops_demo`，默认端口 3306

---

### Task 1: Maven 项目骨架与依赖

**Files:**
- Create: `pom.xml`

**Produces:** Maven 项目定义，所有依赖声明完毕，`mvn validate` 可成功加载。

- [ ] **Step 1: 创建 pom.xml**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0
         https://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>

    <parent>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-parent</artifactId>
        <version>3.3.4</version>
        <relativePath/>
    </parent>

    <groupId>com.ops</groupId>
    <artifactId>demo</artifactId>
    <version>1.0.0</version>
    <name>linux-ops-demo</name>
    <description>Linux 运维实训演示项目 — Nginx + Spring Boot + MySQL</description>

    <properties>
        <java.version>21</java.version>
        <jjwt.version>0.12.6</jjwt.version>
    </properties>

    <dependencies>
        <!-- Spring Boot Web -->
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-web</artifactId>
        </dependency>

        <!-- Spring Boot Security -->
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-security</artifactId>
        </dependency>

        <!-- Spring Boot Data JPA -->
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-data-jpa</artifactId>
        </dependency>

        <!-- Spring Boot Validation -->
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-validation</artifactId>
        </dependency>

        <!-- Spring Boot Actuator -->
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-actuator</artifactId>
        </dependency>

        <!-- MySQL Connector -->
        <dependency>
            <groupId>com.mysql</groupId>
            <artifactId>mysql-connector-j</artifactId>
            <scope>runtime</scope>
        </dependency>

        <!-- JWT -->
        <dependency>
            <groupId>io.jsonwebtoken</groupId>
            <artifactId>jjwt-api</artifactId>
            <version>${jjwt.version}</version>
        </dependency>
        <dependency>
            <groupId>io.jsonwebtoken</groupId>
            <artifactId>jjwt-impl</artifactId>
            <version>${jjwt.version}</version>
            <scope>runtime</scope>
        </dependency>
        <dependency>
            <groupId>io.jsonwebtoken</groupId>
            <artifactId>jjwt-jackson</artifactId>
            <version>${jjwt.version}</version>
            <scope>runtime</scope>
        </dependency>

        <!-- Redis 扩展预留 -->
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-data-redis</artifactId>
            <optional>true</optional>
        </dependency>

        <!-- Test -->
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-test</artifactId>
            <scope>test</scope>
        </dependency>
        <dependency>
            <groupId>org.springframework.security</groupId>
            <artifactId>spring-security-test</artifactId>
            <scope>test</scope>
        </dependency>
    </dependencies>

    <build>
        <plugins>
            <plugin>
                <groupId>org.springframework.boot</groupId>
                <artifactId>spring-boot-maven-plugin</artifactId>
            </plugin>
        </plugins>
    </build>
</project>
```

- [ ] **Step 2: 验证 pom 结构**

```bash
mvn validate
```

Expected: BUILD SUCCESS

---

### Task 2: 应用入口与配置

**Files:**
- Create: `src/main/java/com/ops/demo/DemoApplication.java`
- Create: `src/main/resources/application.yml`
- Create: `src/main/resources/application-dev.yml`

**Produces:** Spring Boot 应用可以启动（尽管因无数据库连接而失败 — 这是预期的）。

- [ ] **Step 1: 创建 DemoApplication.java**

```java
package com.ops.demo;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class DemoApplication {

    public static void main(String[] args) {
        SpringApplication.run(DemoApplication.class, args);
    }
}
```

- [ ] **Step 2: 创建 application.yml**

```yaml
server:
  port: 8080

spring:
  application:
    name: linux-ops-demo
  datasource:
    url: jdbc:mysql://localhost:3306/ops_demo?useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=Asia/Shanghai&characterEncoding=utf8mb4
    username: root
    password: root
    driver-class-name: com.mysql.cj.jdbc.Driver
    hikari:
      minimum-idle: 5
      maximum-pool-size: 20
      idle-timeout: 300000
      max-lifetime: 1200000
      connection-timeout: 30000

  jpa:
    hibernate:
      ddl-auto: update
    show-sql: false
    open-in-view: false
    properties:
      hibernate:
        format_sql: true
        dialect: org.hibernate.dialect.MySQLDialect

# ──────────────────────────────────────────
# Redis 扩展预留（后续实训取消注释即可使用）
# ──────────────────────────────────────────
# spring.data.redis:
#   host: localhost
#   port: 6379
#   timeout: 3000ms
#   lettuce:
#     pool:
#       max-active: 8
#       max-idle: 8
#       min-idle: 0

jwt:
  secret: bXlTZWNyZXRLZXlGb3JKV1RTaWduaW5nRm9yT3BzVHJhaW5pbmdEZW1vUHJvamVjdA==
  expiration: 86400000  # 24 hours in milliseconds

logging:
  level:
    com.ops.demo: DEBUG
    org.springframework.security: DEBUG
```

- [ ] **Step 3: 创建 application-dev.yml**

```yaml
spring:
  datasource:
    url: jdbc:mysql://localhost:3306/ops_demo?useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=Asia/Shanghai&characterEncoding=utf8mb4

  jpa:
    show-sql: true

logging:
  level:
    com.ops.demo: TRACE
```

- [ ] **Step 4: 确认目录结构**

```bash
mkdir -p src/main/java/com/ops/demo/{config,controller,model,repository,service,dto,security}
mkdir -p src/main/resources
mkdir -p static/{css,js}
mkdir -p nginx sql docs
```

- [ ] **Step 5: 测试编译**

```bash
mvn compile
```

Expected: BUILD SUCCESS（编译通过，不要求数据库连接）

---

### Task 3: User JPA 实体

**Files:**
- Create: `src/main/java/com/ops/demo/model/User.java`

**Produces:** User 实体类，JPA 会据此自动建表 `users`。

- [ ] **Step 1: 创建 User.java**

```java
package com.ops.demo.model;

import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "users")
public class User {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, unique = true, length = 50)
    private String username;

    @Column(nullable = false)
    private String password;

    @Column(nullable = false, unique = true, length = 100)
    private String email;

    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;

    @Column(name = "updated_at")
    private LocalDateTime updatedAt;

    @PrePersist
    protected void onCreate() {
        createdAt = LocalDateTime.now();
        updatedAt = LocalDateTime.now();
    }

    @PreUpdate
    protected void onUpdate() {
        updatedAt = LocalDateTime.now();
    }

    public User() {}

    public User(String username, String password, String email) {
        this.username = username;
        this.password = password;
        this.email = email;
    }

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }

    public String getUsername() { return username; }
    public void setUsername(String username) { this.username = username; }

    public String getPassword() { return password; }
    public void setPassword(String password) { this.password = password; }

    public String getEmail() { return email; }
    public void setEmail(String email) { this.email = email; }

    public LocalDateTime getCreatedAt() { return createdAt; }
    public LocalDateTime getUpdatedAt() { return updatedAt; }
}
```

- [ ] **Step 2: 验证编译**

```bash
mvn compile
```

Expected: BUILD SUCCESS

---

### Task 4: User Repository

**Files:**
- Create: `src/main/java/com/ops/demo/repository/UserRepository.java`

**Produces:** JPA Repository 接口，提供数据访问能力。

- [ ] **Step 1: 创建 UserRepository.java**

```java
package com.ops.demo.repository;

import com.ops.demo.model.User;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public interface UserRepository extends JpaRepository<User, Long> {

    Optional<User> findByUsername(String username);

    boolean existsByUsername(String username);

    boolean existsByEmail(String email);
}
```

- [ ] **Step 2: 验证编译**

```bash
mvn compile
```

Expected: BUILD SUCCESS

---

### Task 5: DTO 类

**Files:**
- Create: `src/main/java/com/ops/demo/dto/LoginRequest.java`
- Create: `src/main/java/com/ops/demo/dto/RegisterRequest.java`
- Create: `src/main/java/com/ops/demo/dto/LoginResponse.java`

**Produces:** 数据传输对象，定义请求/响应结构。

- [ ] **Step 1: 创建 LoginRequest.java**

```java
package com.ops.demo.dto;

import jakarta.validation.constraints.NotBlank;

public class LoginRequest {

    @NotBlank(message = "用户名不能为空")
    private String username;

    @NotBlank(message = "密码不能为空")
    private String password;

    public String getUsername() { return username; }
    public void setUsername(String username) { this.username = username; }

    public String getPassword() { return password; }
    public void setPassword(String password) { this.password = password; }
}
```

- [ ] **Step 2: 创建 RegisterRequest.java**

```java
package com.ops.demo.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public class RegisterRequest {

    @NotBlank(message = "用户名不能为空")
    @Size(min = 3, max = 50, message = "用户名长度需在 3-50 之间")
    private String username;

    @NotBlank(message = "密码不能为空")
    @Size(min = 6, max = 100, message = "密码长度需在 6-100 之间")
    private String password;

    @NotBlank(message = "邮箱不能为空")
    @Email(message = "邮箱格式不正确")
    private String email;

    public String getUsername() { return username; }
    public void setUsername(String username) { this.username = username; }

    public String getPassword() { return password; }
    public void setPassword(String password) { this.password = password; }

    public String getEmail() { return email; }
    public void setEmail(String email) { this.email = email; }
}
```

- [ ] **Step 3: 创建 LoginResponse.java**

```java
package com.ops.demo.dto;

public class LoginResponse {

    private String token;
    private String username;

    public LoginResponse(String token, String username) {
        this.token = token;
        this.username = username;
    }

    public String getToken() { return token; }
    public void setToken(String token) { this.token = token; }

    public String getUsername() { return username; }
    public void setUsername(String username) { this.username = username; }
}
```

- [ ] **Step 4: 验证编译**

```bash
mvn compile
```

Expected: BUILD SUCCESS

---

### Task 6: JWT Service

**Files:**
- Create: `src/main/java/com/ops/demo/service/JwtService.java`

**Consumes:** `application.yml` 中的 `jwt.secret` 和 `jwt.expiration`

**Produces:** `JwtService.generateToken(String username): String`, `JwtService.extractUsername(String token): String`, `JwtService.isTokenValid(String token): boolean`

- [ ] **Step 1: 创建 JwtService.java**

```java
package com.ops.demo.service;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import javax.crypto.SecretKey;
import java.util.Base64;
import java.util.Date;
import java.util.function.Function;

@Service
public class JwtService {

    private final SecretKey signingKey;
    private final long expirationMs;

    public JwtService(
            @Value("${jwt.secret}") String secret,
            @Value("${jwt.expiration}") long expirationMs) {
        byte[] keyBytes = Base64.getDecoder().decode(secret);
        this.signingKey = Keys.hmacShaKeyFor(keyBytes);
        this.expirationMs = expirationMs;
    }

    public String generateToken(String username) {
        Date now = new Date();
        Date expiration = new Date(now.getTime() + expirationMs);

        return Jwts.builder()
                .subject(username)
                .issuedAt(now)
                .expiration(expiration)
                .signWith(signingKey)
                .compact();
    }

    public String extractUsername(String token) {
        return extractClaim(token, Claims::getSubject);
    }

    public boolean isTokenValid(String token) {
        try {
            extractAllClaims(token);
            return !isTokenExpired(token);
        } catch (Exception e) {
            return false;
        }
    }

    private boolean isTokenExpired(String token) {
        return extractExpiration(token).before(new Date());
    }

    private Date extractExpiration(String token) {
        return extractClaim(token, Claims::getExpiration);
    }

    private <T> T extractClaim(String token, Function<Claims, T> claimsResolver) {
        Claims claims = extractAllClaims(token);
        return claimsResolver.apply(claims);
    }

    private Claims extractAllClaims(String token) {
        return Jwts.parser()
                .verifyWith(signingKey)
                .build()
                .parseSignedClaims(token)
                .getPayload();
    }
}
```

- [ ] **Step 2: 验证编译**

```bash
mvn compile
```

Expected: BUILD SUCCESS

---

### Task 7: User Service

**Files:**
- Create: `src/main/java/com/ops/demo/service/UserService.java`

**Consumes:** `UserRepository`, `JwtService`

**Produces:** `UserService.register(RegisterRequest): User`, `UserService.authenticate(LoginRequest): LoginResponse`, `UserService.getAllUsers(): List<User>`, `UserService.createUser(RegisterRequest): User`, `UserService.updateUser(Long, RegisterRequest): User`, `UserService.deleteUser(Long): void`

- [ ] **Step 1: 创建 UserService.java**

```java
package com.ops.demo.service;

import com.ops.demo.dto.LoginRequest;
import com.ops.demo.dto.LoginResponse;
import com.ops.demo.dto.RegisterRequest;
import com.ops.demo.model.User;
import com.ops.demo.repository.UserRepository;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class UserService {

    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;
    private final JwtService jwtService;

    public UserService(UserRepository userRepository,
                       PasswordEncoder passwordEncoder,
                       JwtService jwtService) {
        this.userRepository = userRepository;
        this.passwordEncoder = passwordEncoder;
        this.jwtService = jwtService;
    }

    public User register(RegisterRequest request) {
        if (userRepository.existsByUsername(request.getUsername())) {
            throw new RuntimeException("用户名已存在");
        }
        if (userRepository.existsByEmail(request.getEmail())) {
            throw new RuntimeException("邮箱已被注册");
        }

        User user = new User(
                request.getUsername(),
                passwordEncoder.encode(request.getPassword()),
                request.getEmail()
        );
        return userRepository.save(user);
    }

    public LoginResponse authenticate(LoginRequest request) {
        User user = userRepository.findByUsername(request.getUsername())
                .orElseThrow(() -> new RuntimeException("用户名或密码错误"));

        if (!passwordEncoder.matches(request.getPassword(), user.getPassword())) {
            throw new RuntimeException("用户名或密码错误");
        }

        String token = jwtService.generateToken(user.getUsername());
        return new LoginResponse(token, user.getUsername());
    }

    public List<User> getAllUsers() {
        return userRepository.findAll();
    }

    public User createUser(RegisterRequest request) {
        return register(request);
    }

    public User updateUser(Long id, RegisterRequest request) {
        User user = userRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("用户不存在"));

        if (!user.getUsername().equals(request.getUsername())
                && userRepository.existsByUsername(request.getUsername())) {
            throw new RuntimeException("用户名已被占用");
        }
        if (!user.getEmail().equals(request.getEmail())
                && userRepository.existsByEmail(request.getEmail())) {
            throw new RuntimeException("邮箱已被占用");
        }

        user.setUsername(request.getUsername());
        user.setEmail(request.getEmail());
        if (request.getPassword() != null && !request.getPassword().isBlank()) {
            user.setPassword(passwordEncoder.encode(request.getPassword()));
        }
        return userRepository.save(user);
    }

    public void deleteUser(Long id) {
        if (!userRepository.existsById(id)) {
            throw new RuntimeException("用户不存在");
        }
        userRepository.deleteById(id);
    }
}
```

- [ ] **Step 2: 验证编译**

```bash
mvn compile
```

Expected: BUILD SUCCESS

---

### Task 8: JWT 认证过滤器

**Files:**
- Create: `src/main/java/com/ops/demo/security/JwtAuthFilter.java`

**Consumes:** `JwtService`, `UserRepository`

**Produces:** `JwtAuthFilter extends OncePerRequestFilter`

- [ ] **Step 1: 创建 JwtAuthFilter.java**

```java
package com.ops.demo.security;

import com.ops.demo.model.User;
import com.ops.demo.repository.UserRepository;
import com.ops.demo.service.JwtService;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.web.authentication.WebAuthenticationDetailsSource;
import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.Collections;
import java.util.Optional;

@Component
public class JwtAuthFilter extends OncePerRequestFilter {

    private final JwtService jwtService;
    private final UserRepository userRepository;

    public JwtAuthFilter(JwtService jwtService, UserRepository userRepository) {
        this.jwtService = jwtService;
        this.userRepository = userRepository;
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request,
                                    HttpServletResponse response,
                                    FilterChain filterChain)
            throws ServletException, IOException {

        String token = extractTokenFromHeader(request);

        if (token != null && jwtService.isTokenValid(token)) {
            String username = jwtService.extractUsername(token);
            Optional<User> userOpt = userRepository.findByUsername(username);

            if (userOpt.isPresent()) {
                UsernamePasswordAuthenticationToken authToken =
                        new UsernamePasswordAuthenticationToken(
                                userOpt.get(), null, Collections.emptyList());
                authToken.setDetails(
                        new WebAuthenticationDetailsSource().buildDetails(request));
                SecurityContextHolder.getContext().setAuthentication(authToken);
            }
        }

        filterChain.doFilter(request, response);
    }

    private String extractTokenFromHeader(HttpServletRequest request) {
        String bearerToken = request.getHeader("Authorization");
        if (StringUtils.hasText(bearerToken) && bearerToken.startsWith("Bearer ")) {
            return bearerToken.substring(7);
        }
        return null;
    }
}
```

- [ ] **Step 2: 验证编译**

```bash
mvn compile
```

Expected: BUILD SUCCESS

---

### Task 9: Security 配置

**Files:**
- Create: `src/main/java/com/ops/demo/config/SecurityConfig.java`
- Create: `src/main/java/com/ops/demo/config/RedisConfig.java`（预留）

**Consumes:** `JwtAuthFilter`

**Produces:** Spring Security 安全配置，`/api/auth/**` 公开，其他 `/api/**` 需认证。

- [ ] **Step 1: 创建 SecurityConfig.java**

```java
package com.ops.demo.config;

import com.ops.demo.security.JwtAuthFilter;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;

@Configuration
@EnableWebSecurity
public class SecurityConfig {

    private final JwtAuthFilter jwtAuthFilter;

    public SecurityConfig(JwtAuthFilter jwtAuthFilter) {
        this.jwtAuthFilter = jwtAuthFilter;
    }

    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        http
            .csrf(csrf -> csrf.disable())
            .sessionManagement(session ->
                session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/api/auth/**").permitAll()
                .requestMatchers("/api/**").authenticated()
                .requestMatchers("/actuator/health").permitAll()
                .anyRequest().permitAll()
            )
            .addFilterBefore(jwtAuthFilter, UsernamePasswordAuthenticationFilter.class);

        return http.build();
    }

    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }
}
```

- [ ] **Step 2: 创建 RedisConfig.java（预留）**

```java
package com.ops.demo.config;

import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.redis.connection.RedisConnectionFactory;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.serializer.StringRedisSerializer;

@Configuration
@ConditionalOnProperty(prefix = "spring.data.redis", name = "enabled", havingValue = "true")
public class RedisConfig {

    @Bean
    public RedisTemplate<String, Object> redisTemplate(
            RedisConnectionFactory connectionFactory) {
        RedisTemplate<String, Object> template = new RedisTemplate<>();
        template.setConnectionFactory(connectionFactory);
        template.setKeySerializer(new StringRedisSerializer());
        template.setValueSerializer(new StringRedisSerializer());
        template.setHashKeySerializer(new StringRedisSerializer());
        template.setHashValueSerializer(new StringRedisSerializer());
        return template;
    }
}
```

- [ ] **Step 3: 验证编译**

```bash
mvn compile
```

Expected: BUILD SUCCESS

---

### Task 10: Auth 控制器

**Files:**
- Create: `src/main/java/com/ops/demo/controller/AuthController.java`

**Consumes:** `UserService`

**Produces:** `POST /api/auth/register` (公开), `POST /api/auth/login` (公开)

- [ ] **Step 1: 创建 AuthController.java**

```java
package com.ops.demo.controller;

import com.ops.demo.dto.LoginRequest;
import com.ops.demo.dto.LoginResponse;
import com.ops.demo.dto.RegisterRequest;
import com.ops.demo.model.User;
import com.ops.demo.service.UserService;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/auth")
public class AuthController {

    private final UserService userService;

    public AuthController(UserService userService) {
        this.userService = userService;
    }

    @PostMapping("/register")
    public ResponseEntity<?> register(@Valid @RequestBody RegisterRequest request) {
        try {
            User user = userService.register(request);
            return ResponseEntity.status(HttpStatus.CREATED).body(Map.of(
                    "id", user.getId(),
                    "username", user.getUsername(),
                    "email", user.getEmail()
            ));
        } catch (RuntimeException e) {
            return ResponseEntity.badRequest().body(Map.of("error", e.getMessage()));
        }
    }

    @PostMapping("/login")
    public ResponseEntity<?> login(@Valid @RequestBody LoginRequest request) {
        try {
            LoginResponse response = userService.authenticate(request);
            return ResponseEntity.ok(response);
        } catch (RuntimeException e) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED)
                    .body(Map.of("error", e.getMessage()));
        }
    }
}
```

- [ ] **Step 2: 验证编译**

```bash
mvn compile
```

Expected: BUILD SUCCESS

---

### Task 11: User 控制器

**Files:**
- Create: `src/main/java/com/ops/demo/controller/UserController.java`

**Consumes:** `UserService`

**Produces:** `GET/POST /api/users`, `PUT/DELETE /api/users/{id}` (均需 JWT)

- [ ] **Step 1: 创建 UserController.java**

```java
package com.ops.demo.controller;

import com.ops.demo.dto.RegisterRequest;
import com.ops.demo.model.User;
import com.ops.demo.service.UserService;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/users")
public class UserController {

    private final UserService userService;

    public UserController(UserService userService) {
        this.userService = userService;
    }

    @GetMapping
    public ResponseEntity<List<Map<String, Object>>> getAllUsers() {
        List<Map<String, Object>> users = userService.getAllUsers().stream()
                .map(user -> Map.<String, Object>of(
                        "id", user.getId(),
                        "username", user.getUsername(),
                        "email", user.getEmail(),
                        "createdAt", user.getCreatedAt(),
                        "updatedAt", user.getUpdatedAt()
                ))
                .toList();
        return ResponseEntity.ok(users);
    }

    @PostMapping
    public ResponseEntity<?> createUser(@Valid @RequestBody RegisterRequest request) {
        try {
            User user = userService.createUser(request);
            return ResponseEntity.status(HttpStatus.CREATED).body(Map.of(
                    "id", user.getId(),
                    "username", user.getUsername(),
                    "email", user.getEmail()
            ));
        } catch (RuntimeException e) {
            return ResponseEntity.badRequest().body(Map.of("error", e.getMessage()));
        }
    }

    @PutMapping("/{id}")
    public ResponseEntity<?> updateUser(
            @PathVariable Long id,
            @Valid @RequestBody RegisterRequest request) {
        try {
            User user = userService.updateUser(id, request);
            return ResponseEntity.ok(Map.of(
                    "id", user.getId(),
                    "username", user.getUsername(),
                    "email", user.getEmail()
            ));
        } catch (RuntimeException e) {
            return ResponseEntity.badRequest().body(Map.of("error", e.getMessage()));
        }
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<?> deleteUser(@PathVariable Long id) {
        try {
            userService.deleteUser(id);
            return ResponseEntity.ok(Map.of("message", "用户已删除"));
        } catch (RuntimeException e) {
            return ResponseEntity.badRequest().body(Map.of("error", e.getMessage()));
        }
    }
}
```

- [ ] **Step 2: 验证编译**

```bash
mvn compile
```

Expected: BUILD SUCCESS

---

### Task 12: 静态前端页面

**Files:**
- Create: `static/login.html`
- Create: `static/index.html`
- Create: `static/users.html`
- Create: `static/css/style.css`
- Create: `static/js/api.js`
- Create: `static/js/auth.js`
- Create: `static/js/users.js`

**Produces:** 完整前端页面，可通过 Nginx 或 Spring Boot 静态资源直接访问。

- [ ] **Step 1: 创建 static/css/style.css**

```css
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto,
                 'Helvetica Neue', Arial, sans-serif;
    background: #f0f2f5;
    color: #333;
    min-height: 100vh;
}

/* ── Navbar ── */
.navbar {
    background: #1a1a2e;
    color: #fff;
    padding: 0 24px;
    height: 56px;
    display: flex;
    align-items: center;
    justify-content: space-between;
}

.navbar .brand {
    font-size: 18px;
    font-weight: 700;
}

.navbar .nav-links {
    display: flex;
    gap: 20px;
    align-items: center;
}

.navbar .nav-links a {
    color: #a0a0c0;
    text-decoration: none;
    font-size: 14px;
    transition: color 0.2s;
}

.navbar .nav-links a:hover,
.navbar .nav-links a.active {
    color: #fff;
}

.navbar .nav-links button {
    background: #e94560;
    color: #fff;
    border: none;
    padding: 6px 16px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 13px;
}

.navbar .nav-links button:hover {
    background: #d63851;
}

/* ── Container ── */
.container {
    max-width: 960px;
    margin: 32px auto;
    padding: 0 20px;
}

/* ── Card ── */
.card {
    background: #fff;
    border-radius: 8px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    padding: 32px;
    margin-bottom: 20px;
}

.card h2 {
    font-size: 20px;
    margin-bottom: 20px;
    color: #1a1a2e;
}

/* ── Form ── */
.form-group {
    margin-bottom: 16px;
}

.form-group label {
    display: block;
    font-size: 14px;
    font-weight: 500;
    margin-bottom: 6px;
    color: #555;
}

.form-group input {
    width: 100%;
    padding: 10px 12px;
    border: 1px solid #d9d9d9;
    border-radius: 6px;
    font-size: 14px;
    transition: border-color 0.2s;
}

.form-group input:focus {
    outline: none;
    border-color: #4a6cf7;
    box-shadow: 0 0 0 3px rgba(74, 108, 247, 0.1);
}

.btn {
    display: inline-block;
    padding: 10px 24px;
    border: none;
    border-radius: 6px;
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    transition: background 0.2s;
}

.btn-primary {
    background: #4a6cf7;
    color: #fff;
}

.btn-primary:hover {
    background: #3b5de7;
}

.btn-danger {
    background: #e94560;
    color: #fff;
}

.btn-danger:hover {
    background: #d63851;
}

.btn-secondary {
    background: #6c757d;
    color: #fff;
}

.btn-secondary:hover {
    background: #5a6268;
}

/* ── Message ── */
.message {
    padding: 10px 16px;
    border-radius: 6px;
    margin-bottom: 16px;
    font-size: 14px;
    display: none;
}

.message.error {
    background: #fff0f0;
    color: #c0392b;
    border: 1px solid #f5c6cb;
}

.message.success {
    background: #f0fff4;
    color: #27ae60;
    border: 1px solid #c3e6cb;
}

/* ── Auth pages ── */
.auth-container {
    max-width: 420px;
    margin: 80px auto;
    padding: 0 20px;
}

.auth-container .card h2 {
    text-align: center;
}

.auth-container .btn {
    width: 100%;
}

.auth-container .switch-link {
    text-align: center;
    margin-top: 12px;
    font-size: 14px;
    color: #888;
}

.auth-container .switch-link a {
    color: #4a6cf7;
    text-decoration: none;
    cursor: pointer;
}

/* ── Table ── */
.table {
    width: 100%;
    border-collapse: collapse;
}

.table th, .table td {
    padding: 12px 16px;
    text-align: left;
    border-bottom: 1px solid #eee;
    font-size: 14px;
}

.table th {
    background: #f8f9fa;
    font-weight: 600;
    color: #555;
}

.table tr:hover td {
    background: #f8f9ff;
}

.table .actions {
    display: flex;
    gap: 8px;
}

.table .btn {
    padding: 4px 12px;
    font-size: 12px;
}

/* ── Welcome ── */
.welcome {
    text-align: center;
    padding: 60px 0;
}

.welcome h1 {
    font-size: 28px;
    color: #1a1a2e;
    margin-bottom: 12px;
}

.welcome p {
    font-size: 16px;
    color: #888;
    margin-bottom: 24px;
}

.stats {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 16px;
    margin-top: 24px;
}

.stat-card {
    background: #fff;
    border-radius: 8px;
    padding: 24px;
    text-align: center;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}

.stat-card .number {
    font-size: 32px;
    font-weight: 700;
    color: #4a6cf7;
}

.stat-card .label {
    font-size: 14px;
    color: #888;
    margin-top: 4px;
}
```

- [ ] **Step 2: 创建 static/js/api.js**

```javascript
const API_BASE = '/api';

const api = {
    async request(url, options = {}) {
        const token = localStorage.getItem('token');
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers,
        };
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
        const response = await fetch(`${API_BASE}${url}`, {
            ...options,
            headers,
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || `HTTP ${response.status}`);
        }
        return data;
    },

    get(url) {
        return this.request(url, { method: 'GET' });
    },

    post(url, body) {
        return this.request(url, {
            method: 'POST',
            body: JSON.stringify(body),
        });
    },

    put(url, body) {
        return this.request(url, {
            method: 'PUT',
            body: JSON.stringify(body),
        });
    },

    delete(url) {
        return this.request(url, { method: 'DELETE' });
    },
};
```

- [ ] **Step 3: 创建 static/js/auth.js**

```javascript
document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('loginForm');
    const registerForm = document.getElementById('registerForm');
    const messageEl = document.getElementById('message');

    function showMessage(text, type) {
        if (!messageEl) return;
        messageEl.textContent = text;
        messageEl.className = `message ${type}`;
        messageEl.style.display = 'block';
    }

    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const username = document.getElementById('username').value.trim();
            const password = document.getElementById('password').value;
            try {
                const data = await api.post('/auth/login', { username, password });
                localStorage.setItem('token', data.token);
                localStorage.setItem('username', data.username);
                window.location.href = '/index.html';
            } catch (err) {
                showMessage(err.message, 'error');
            }
        });
    }

    if (registerForm) {
        registerForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const username = document.getElementById('username').value.trim();
            const email = document.getElementById('email').value.trim();
            const password = document.getElementById('password').value;
            try {
                await api.post('/auth/register', { username, email, password });
                showMessage('注册成功！即将跳转到登录页...', 'success');
                setTimeout(() => {
                    window.location.href = '/login.html';
                }, 1500);
            } catch (err) {
                showMessage(err.message, 'error');
            }
        });
    }
});
```

- [ ] **Step 4: 创建 static/js/users.js**

```javascript
document.addEventListener('DOMContentLoaded', () => {
    const tableBody = document.getElementById('userTableBody');
    const userForm = document.getElementById('userForm');
    const messageEl = document.getElementById('message');
    const formTitle = document.getElementById('formTitle');
    const userIdInput = document.getElementById('userId');
    const cancelEditBtn = document.getElementById('cancelEdit');
    const userCountEl = document.getElementById('userCount');

    function showMessage(text, type) {
        if (!messageEl) return;
        messageEl.textContent = text;
        messageEl.className = `message ${type}`;
        messageEl.style.display = 'block';
        setTimeout(() => { messageEl.style.display = 'none'; }, 3000);
    }

    async function loadUsers() {
        try {
            const users = await api.get('/users');
            if (tableBody) {
                tableBody.innerHTML = users.length === 0
                    ? '<tr><td colspan="5" style="text-align:center;color:#999;">暂无用户数据</td></tr>'
                    : users.map(u => `
                        <tr>
                            <td>${u.id}</td>
                            <td>${escapeHtml(u.username)}</td>
                            <td>${escapeHtml(u.email)}</td>
                            <td>${new Date(u.createdAt).toLocaleString('zh-CN')}</td>
                            <td>
                                <div class="actions">
                                    <button class="btn btn-primary" onclick="editUser(${u.id}, '${escapeHtml(u.username)}', '${escapeHtml(u.email)}')">编辑</button>
                                    <button class="btn btn-danger" onclick="deleteUser(${u.id})">删除</button>
                                </div>
                            </td>
                        </tr>
                    `).join('');
            }
            if (userCountEl) userCountEl.textContent = users.length;
        } catch (err) {
            showMessage('加载用户列表失败: ' + err.message, 'error');
        }
    }

    function escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    function resetForm() {
        userForm.reset();
        userIdInput.value = '';
        formTitle.textContent = '添加用户';
        cancelEditBtn.style.display = 'none';
    }

    window.editUser = async function(id, username, email) {
        document.getElementById('username').value = username;
        document.getElementById('email').value = email;
        document.getElementById('password').value = '';
        document.getElementById('password').placeholder = '留空则不修改密码';
        userIdInput.value = id;
        formTitle.textContent = '编辑用户';
        cancelEditBtn.style.display = 'inline-block';
        window.scrollTo({ top: 0, behavior: 'smooth' });
    };

    window.deleteUser = async function(id) {
        if (!confirm('确定要删除该用户吗？')) return;
        try {
            await api.delete(`/users/${id}`);
            showMessage('用户已删除', 'success');
            loadUsers();
        } catch (err) {
            showMessage('删除失败: ' + err.message, 'error');
        }
    };

    if (cancelEditBtn) {
        cancelEditBtn.addEventListener('click', resetForm);
    }

    if (userForm) {
        userForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const username = document.getElementById('username').value.trim();
            const email = document.getElementById('email').value.trim();
            const password = document.getElementById('password').value;
            const id = userIdInput.value;
            const body = { username, email, password };
            try {
                if (id) {
                    await api.put(`/users/${id}`, body);
                    showMessage('用户已更新', 'success');
                } else {
                    await api.post('/users', body);
                    showMessage('用户已创建', 'success');
                }
                resetForm();
                loadUsers();
            } catch (err) {
                showMessage('操作失败: ' + err.message, 'error');
            }
        });
    }

    loadUsers();
});
```

- [ ] **Step 5: 创建 static/login.html**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>登录 — Linux 运维实训平台</title>
    <link rel="stylesheet" href="/css/style.css">
</head>
<body>
    <div class="auth-container">
        <div class="card">
            <h2>🔐 用户登录</h2>
            <div id="message" class="message"></div>
            <form id="loginForm">
                <div class="form-group">
                    <label for="username">用户名</label>
                    <input type="text" id="username" placeholder="请输入用户名" required autocomplete="username">
                </div>
                <div class="form-group">
                    <label for="password">密码</label>
                    <input type="password" id="password" placeholder="请输入密码" required autocomplete="current-password">
                </div>
                <button type="submit" class="btn btn-primary">登 录</button>
            </form>
            <p class="switch-link">
                还没有账号？<a href="/register.html">立即注册</a>
            </p>
        </div>
    </div>
    <script src="/js/api.js"></script>
    <script src="/js/auth.js"></script>
</body>
</html>
```

- [ ] **Step 6: 创建 static/register.html**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>注册 — Linux 运维实训平台</title>
    <link rel="stylesheet" href="/css/style.css">
</head>
<body>
    <div class="auth-container">
        <div class="card">
            <h2>📝 用户注册</h2>
            <div id="message" class="message"></div>
            <form id="registerForm">
                <div class="form-group">
                    <label for="username">用户名</label>
                    <input type="text" id="username" placeholder="3-50 个字符" required autocomplete="username">
                </div>
                <div class="form-group">
                    <label for="email">邮箱</label>
                    <input type="email" id="email" placeholder="请输入邮箱地址" required autocomplete="email">
                </div>
                <div class="form-group">
                    <label for="password">密码</label>
                    <input type="password" id="password" placeholder="至少 6 个字符" required autocomplete="new-password">
                </div>
                <button type="submit" class="btn btn-primary">注 册</button>
            </form>
            <p class="switch-link">
                已有账号？<a href="/login.html">去登录</a>
            </p>
        </div>
    </div>
    <script src="/js/api.js"></script>
    <script src="/js/auth.js"></script>
</body>
</html>
```

- [ ] **Step 7: 创建 static/index.html**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>首页 — Linux 运维实训平台</title>
    <link rel="stylesheet" href="/css/style.css">
</head>
<body>
    <nav class="navbar">
        <span class="brand">🐧 Linux 运维实训平台</span>
        <div class="nav-links">
            <a href="/index.html" class="active">首页</a>
            <a href="/users.html">用户管理</a>
            <button id="logoutBtn">退出登录</button>
        </div>
    </nav>

    <div class="container">
        <div class="welcome">
            <h1>欢迎，<span id="displayName">---</span>！</h1>
            <p>这是一个 Linux 运维实训演示项目<br>
               用于练习 Nginx 反向代理、动静分离、Java 服务部署和 MySQL 运维</p>
        </div>

        <div class="stats">
            <div class="stat-card">
                <div class="number" id="userCount">0</div>
                <div class="label">系统用户数</div>
            </div>
            <div class="stat-card">
                <div class="number">Nginx 1.30</div>
                <div class="label">反向代理</div>
            </div>
            <div class="stat-card">
                <div class="number">Java 21</div>
                <div class="label">后端服务</div>
            </div>
            <div class="stat-card">
                <div class="number">MySQL 8.4</div>
                <div class="label">数据库</div>
            </div>
        </div>
    </div>

    <script src="/js/api.js"></script>
    <script>
        document.addEventListener('DOMContentLoaded', () => {
            const username = localStorage.getItem('username');
            const token = localStorage.getItem('token');
            if (!token) {
                window.location.href = '/login.html';
                return;
            }
            document.getElementById('displayName').textContent = username || '用户';

            document.getElementById('logoutBtn').addEventListener('click', () => {
                localStorage.removeItem('token');
                localStorage.removeItem('username');
                window.location.href = '/login.html';
            });

            api.get('/users').then(users => {
                document.getElementById('userCount').textContent = users.length;
            }).catch(() => {});
        });
    </script>
</body>
</html>
```

- [ ] **Step 8: 创建 static/users.html**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>用户管理 — Linux 运维实训平台</title>
    <link rel="stylesheet" href="/css/style.css">
</head>
<body>
    <nav class="navbar">
        <span class="brand">🐧 Linux 运维实训平台</span>
        <div class="nav-links">
            <a href="/index.html">首页</a>
            <a href="/users.html" class="active">用户管理</a>
            <button id="logoutBtn">退出登录</button>
        </div>
    </nav>

    <div class="container">
        <div class="card">
            <h2 id="formTitle">添加用户</h2>
            <div id="message" class="message"></div>
            <form id="userForm">
                <input type="hidden" id="userId">
                <div class="form-group">
                    <label for="username">用户名</label>
                    <input type="text" id="username" placeholder="请输入用户名" required>
                </div>
                <div class="form-group">
                    <label for="email">邮箱</label>
                    <input type="email" id="email" placeholder="请输入邮箱" required>
                </div>
                <div class="form-group">
                    <label for="password">密码</label>
                    <input type="password" id="password" placeholder="请输入密码（至少6位）" required>
                </div>
                <button type="submit" class="btn btn-primary">提 交</button>
                <button type="button" id="cancelEdit" class="btn btn-secondary" style="display:none;">取消编辑</button>
            </form>
        </div>

        <div class="card">
            <h2>用户列表 (<span id="userCount">0</span>)</h2>
            <table class="table">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>用户名</th>
                        <th>邮箱</th>
                        <th>创建时间</th>
                        <th>操作</th>
                    </tr>
                </thead>
                <tbody id="userTableBody"></tbody>
            </table>
        </div>
    </div>

    <script src="/js/api.js"></script>
    <script src="/js/users.js"></script>
    <script>
        document.addEventListener('DOMContentLoaded', () => {
            const token = localStorage.getItem('token');
            if (!token) {
                window.location.href = '/login.html';
                return;
            }
            document.getElementById('logoutBtn').addEventListener('click', () => {
                localStorage.removeItem('token');
                localStorage.removeItem('username');
                window.location.href = '/login.html';
            });
        });
    </script>
</body>
</html>
```

---

### Task 13: Nginx 配置

**Files:**
- Create: `nginx/ops-demo.conf`

**Produces:** Nginx 配置文件，定义动静分离规则。

- [ ] **Step 1: 创建 nginx/ops-demo.conf**

```nginx
# ──────────────────────────────────────────────
# Linux 运维实训项目 — Nginx 动静分离配置
# 部署路径：/etc/nginx/conf.d/ops-demo.conf
# ──────────────────────────────────────────────

upstream java_backend {
    server 127.0.0.1:8080 weight=1 max_fails=3 fail_timeout=30s;
    # 负载均衡预留节点：
    # server 127.0.0.1:8081 weight=1 max_fails=3 fail_timeout=30s;
}

server {
    listen 80;
    server_name _;  # 替换为实际域名或 IP

    charset utf-8;

    # ── 访问日志 ──
    access_log /var/log/nginx/ops-demo-access.log;
    error_log  /var/log/nginx/ops-demo-error.log;

    # ── 静态资源根目录 ──
    root /opt/ops-demo/static;
    index index.html;

    # ── 动静分离规则 ──
    # 1. API 请求 → 反向代理到 Java 后端
    location /api/ {
        proxy_pass http://java_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # 超时配置
        proxy_connect_timeout 10s;
        proxy_read_timeout 30s;
        proxy_send_timeout 30s;
    }

    # 2. Actuator 健康检查 — 仅允许本地访问
    location /actuator/health {
        allow 127.0.0.1;
        deny all;
        proxy_pass http://java_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # 3. 静态文件 — Nginx 直接 serve
    location / {
        try_files $uri $uri/ /index.html;
    }

    # 4. 静态资源缓存策略
    location ~* \.(css|js|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
        expires 7d;
        add_header Cache-Control "public, immutable";
    }

    # 5. 安全头
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # 6. 隐藏 Nginx 版本号
    server_tokens off;

    # 7. 请求体大小限制
    client_max_body_size 10m;
}
```

---

### Task 14: SQL 初始化脚本

**Files:**
- Create: `sql/init.sql`

**Produces:** 数据库初始化脚本，可直接在 MySQL 中执行。

- [ ] **Step 1: 创建 sql/init.sql**

```sql
-- ──────────────────────────────────────────────
-- Linux 运维实训项目 — 数据库初始化脚本
-- 执行方式: mysql -u root -p < init.sql
-- ──────────────────────────────────────────────

CREATE DATABASE IF NOT EXISTS ops_demo
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

USE ops_demo;

-- JPA ddl-auto: update 会自动建表，此脚本用于手动初始化场景
-- 如需手动建表，取消下方注释：

-- CREATE TABLE IF NOT EXISTS users (
--     id         BIGINT AUTO_INCREMENT PRIMARY KEY,
--     username   VARCHAR(50)  NOT NULL UNIQUE,
--     password   VARCHAR(255) NOT NULL,
--     email      VARCHAR(100) NOT NULL UNIQUE,
--     created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
--     updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
--     INDEX idx_username (username),
--     INDEX idx_email (email)
-- ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 插入测试数据
-- INSERT INTO users (username, password, email) VALUES
--     ('admin', '$2a$10$placeholder', 'admin@ops-demo.local'),
--     ('test',  '$2a$10$placeholder', 'test@ops-demo.local');
```

---

### Task 15: 项目文档 README

**Files:**
- Create: `docs/README.md`

**Produces:** 项目说明与运维部署指南。

- [ ] **Step 1: 创建 docs/README.md**

````markdown
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
````

---

### Task 16: 完整构建与验证

**Files:** 无新建

- [ ] **Step 1: 完整编译**

```bash
mvn clean compile
```

Expected: BUILD SUCCESS，所有 Java 文件编译通过。

- [ ] **Step 2: 打包构建**

```bash
mvn clean package -DskipTests
```

Expected: BUILD SUCCESS，`target/demo-1.0.0.jar` 生成成功。

- [ ] **Step 3: 验证 JAR 结构**

```bash
jar tf target/demo-1.0.0.jar | grep -E "(com/ops|application|static/)"
```

Expected: 列出项目类和资源文件。

- [ ] **Step 4: 确认最终文件结构**

```bash
find . -type f \( -name "*.java" -o -name "*.html" -o -name "*.css" -o -name "*.js" -o -name "*.yml" -o -name "*.xml" -o -name "*.conf" -o -name "*.sql" -o -name "*.md" \) | sort
```

Expected: 列出全部 20+ 个项目文件。
