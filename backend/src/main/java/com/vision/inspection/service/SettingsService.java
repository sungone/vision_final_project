package com.vision.inspection.service;
import com.vision.inspection.dto.RuleSettings;
import com.vision.inspection.exception.ApiException;
import com.vision.inspection.repository.SettingsRepository;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
@Service
public class SettingsService {
    private final SettingsRepository repository; private final String key;
    public SettingsService(SettingsRepository repository,@Value("${inspection.settings-api-key:}") String key) { this.repository=repository; this.key=key; }
    public RuleSettings get() { return repository.get(); }
    public RuleSettings update(RuleSettings settings,String suppliedKey) {
        if(key.isBlank()) throw new ApiException(503,"SETTINGS_READ_ONLY","설정 변경용 API 키가 구성되지 않았습니다.");
        if(suppliedKey==null || !MessageDigest.isEqual(key.getBytes(StandardCharsets.UTF_8),suppliedKey.getBytes(StandardCharsets.UTF_8)))
            throw new ApiException(403,"FORBIDDEN","설정 변경 권한이 없습니다.");
        try { return repository.update(settings); }
        catch(IllegalArgumentException e) { throw new ApiException(400,"INVALID_RULE_SETTING","검사 설정값이 올바르지 않습니다."); }
    }
}
