package com.ops.demo.config;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;

/**
 * 在每次响应头中注入 X-Java-Server，用于识别是哪台 Java 后端处理了请求。
 * 值从外部 application.yml 的 app.server-id 读取，两台服务器配不同值即可区分。
 */
@Component
public class ServerIdentityFilter extends OncePerRequestFilter {

    private final String serverId;

    public ServerIdentityFilter(@Value("${app.server-id:unknown}") String serverId) {
        this.serverId = serverId;
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request,
                                    HttpServletResponse response,
                                    FilterChain filterChain)
            throws ServletException, IOException {
        response.addHeader("X-Java-Server", serverId);
        filterChain.doFilter(request, response);
    }
}
