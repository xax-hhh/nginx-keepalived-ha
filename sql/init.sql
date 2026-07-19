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
