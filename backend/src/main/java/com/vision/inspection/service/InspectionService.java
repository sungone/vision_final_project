package com.vision.inspection.service;
import com.vision.inspection.dto.*;
import com.vision.inspection.entity.Inspection;
import com.vision.inspection.exception.ApiException;
import com.vision.inspection.repository.*;
import com.vision.inspection.rule.InspectionRuleEngine;
import com.vision.inspection.storage.*;
import com.vision.inspection.vision.VisionService;
import java.security.MessageDigest;
import java.time.*;
import java.time.format.DateTimeFormatter;
import java.util.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;
@Service
public class InspectionService {
    private static final Logger log=LoggerFactory.getLogger(InspectionService.class);
    private final InspectionRepository repository;
    private final SettingsRepository settings;
    private final ImageStorageService storage;
    private final ImageValidator validator;
    private final VisionService vision;
    private final InspectionRuleEngine rules;
    private final ProcessedImageRenderer renderer;
    private final HistoryService history;
    public InspectionService(InspectionRepository repository,SettingsRepository settings,ImageStorageService storage,
        ImageValidator validator,VisionService vision,InspectionRuleEngine rules,ProcessedImageRenderer renderer,HistoryService history) {
        this.repository=repository; this.settings=settings; this.storage=storage; this.validator=validator;
        this.vision=vision; this.rules=rules; this.renderer=renderer; this.history=history;
    }
    public InspectionResponse inspect(MultipartFile file,Inspection.Metadata metadata) {
        var image=validator.validate(file);
        var snapshot=settings.get();
        UUID id=UUID.randomUUID(); Instant time=Instant.now();
        String prefix="inspections/"+DateTimeFormatter.ofPattern("uuuu/MM/dd").withZone(ZoneOffset.UTC).format(time)+"/"+id;
        String original=prefix+"/original."+image.extension(), processed=prefix+"/processed.jpg";
        var inspection=new Inspection(id,time,"PROCESSING",original,processed,image.contentType(),null,snapshot,null,metadata,sha256(image.bytes()));
        // Reserve first so even a process crash has a durable identifier for reconciliation.
        repository.reserve(inspection);
        try {
            storage.save(original,image.bytes());
            var recognized=vision.predict(image.bytes(),"original."+image.extension(),image.contentType());
            if(recognized.width()!=image.image().getWidth() || recognized.height()!=image.image().getHeight())
                throw new ApiException(502,"VISION_INFERENCE_FAILED","Vision 이미지 좌표 크기가 일치하지 않습니다.");
            var decision=rules.evaluate(recognized,snapshot);
            storage.save(processed,renderer.render(image.image(),recognized,decision));
            repository.complete(id,recognized,decision);
        } catch(RuntimeException e) {
            // Never delete files when DB commit outcome is unknown. Re-check durable state first.
            try {
                var saved=repository.find(id);
                if(saved.isPresent() && saved.get().status().equals("COMPLETED")) return history.detail(id);
                if(repository.fail(id,e instanceof ApiException a?a.code():"INSPECTION_FAILED")) storage.deleteInspection(prefix);
            } catch(RuntimeException cleanup) { log.error("Inspection {} needs reconciliation; images retained if cleanup failed",id,cleanup); }
            throw e;
        }
        return history.detail(id);
    }
    private String sha256(byte[] bytes) {
        try { return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes)); }
        catch(java.security.NoSuchAlgorithmException e) { throw new IllegalStateException(e); }
    }
}
