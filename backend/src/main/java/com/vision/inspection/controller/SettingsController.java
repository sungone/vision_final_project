package com.vision.inspection.controller;
import com.vision.inspection.dto.RuleSettings;
import com.vision.inspection.service.SettingsService;
import org.springframework.web.bind.annotation.*;
@RestController
@RequestMapping("/api/settings/inspection-rules")
public class SettingsController {
    private final SettingsService service;
    public SettingsController(SettingsService service) { this.service=service; }
    @GetMapping public RuleSettings get() { return service.get(); }
    @PutMapping public RuleSettings update(@RequestBody RuleSettings settings,@RequestHeader(value="X-Settings-Key",required=false) String key) { return service.update(settings,key); }
}
