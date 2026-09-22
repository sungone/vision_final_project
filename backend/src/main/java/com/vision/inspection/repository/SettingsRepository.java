package com.vision.inspection.repository;
import com.vision.inspection.dto.RuleSettings;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;
@Repository
public class SettingsRepository {
    private final JdbcTemplate jdbc; private final JsonCodec json;
    public SettingsRepository(JdbcTemplate jdbc,JsonCodec json) { this.jdbc=jdbc; this.json=json; }
    public RuleSettings get() { return json.read(jdbc.queryForObject("SELECT settings FROM inspection_rule_settings WHERE id=1",String.class),RuleSettings.class); }
    public RuleSettings update(RuleSettings settings) {
        // The evaluator version describes deployed code, not a client-controlled label.
        if(!"geometry-v1".equals(settings.ruleVersion())) throw new IllegalArgumentException("Unsupported ruleVersion");
        jdbc.update("UPDATE inspection_rule_settings SET settings=CAST(? AS jsonb),revision=revision+1,updated_at=now() WHERE id=1",json.write(settings));
        return settings;
    }
}
