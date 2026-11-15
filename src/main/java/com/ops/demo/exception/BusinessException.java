package com.ops.demo.exception;

/**
 * 业务异常，用于区分业务错误和系统错误。
 * <p>
 * GlobalExceptionHandler 根据此类返回不同 HTTP 状态码：
 * <ul>
 *   <li>业务错误 → 4xx（展示给用户）</li>
 *   <li>系统异常 → 5xx（不暴露内部细节）</li>
 * </ul>
 */
public class BusinessException extends RuntimeException {

    /**
     * 建议的 HTTP 状态码，默认 400 Bad Request。
     */
    private final int httpStatus;

    public BusinessException(String message) {
        super(message);
        this.httpStatus = 400;
    }

    public BusinessException(String message, int httpStatus) {
        super(message);
        this.httpStatus = httpStatus;
    }

    public int getHttpStatus() {
        return httpStatus;
    }
}
