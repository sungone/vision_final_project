package com.vision.inspection.exception;
import java.time.Instant;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.dao.DataAccessException;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MaxUploadSizeExceededException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.web.multipart.support.MissingServletRequestPartException;
import org.springframework.web.bind.MissingServletRequestParameterException;
@RestControllerAdvice
public class ErrorHandler {
    private static final Logger log=LoggerFactory.getLogger(ErrorHandler.class);
    public record ErrorResponse(Instant timestamp,int status,String code,String message) {}
    @ExceptionHandler(ApiException.class)
    ResponseEntity<ErrorResponse> api(ApiException e) { return response(e.status(),e.code(),e.getMessage()); }
    @ExceptionHandler(MaxUploadSizeExceededException.class)
    ResponseEntity<ErrorResponse> tooLarge(Exception e) { return response(413,"IMAGE_TOO_LARGE","이미지 용량 제한을 초과했습니다."); }
    @ExceptionHandler({MethodArgumentNotValidException.class,MethodArgumentTypeMismatchException.class,
        MissingServletRequestPartException.class,MissingServletRequestParameterException.class,IllegalArgumentException.class})
    ResponseEntity<ErrorResponse> invalid(Exception e) { return response(400,"INVALID_REQUEST","요청 값 또는 이미지 파일을 확인하세요."); }
    @ExceptionHandler(HttpMessageNotReadableException.class)
    ResponseEntity<ErrorResponse> invalidJson(Exception e) { return response(400,"INVALID_RULE_SETTING","설정 JSON 형식 또는 값이 올바르지 않습니다."); }
    @ExceptionHandler(DataAccessException.class)
    ResponseEntity<ErrorResponse> database(Exception e) { log.error("Database operation failed",e); return response(503,"DATABASE_ERROR","검사 데이터 저장소를 사용할 수 없습니다."); }
    @ExceptionHandler(Exception.class)
    ResponseEntity<ErrorResponse> unexpected(Exception e) { log.error("Unexpected API failure",e); return response(500,"INTERNAL_ERROR","요청 처리에 실패했습니다."); }
    private ResponseEntity<ErrorResponse> response(int status,String code,String message) {
        return ResponseEntity.status(status).body(new ErrorResponse(Instant.now(),status,code,message));
    }
}
