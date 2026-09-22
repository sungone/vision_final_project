package com.vision.inspection.entity;
import com.vision.inspection.dto.*;
import java.time.Instant;
import java.util.UUID;
public record Inspection(UUID id,Instant inspectionTime,String status,String originalImagePath,
    String processedImagePath,String originalContentType,String modelVersion,RuleSettings ruleSnapshot,
    InspectionDecision decision,Metadata metadata,String imageSha256) {
    public record Metadata(String equipmentId,String productCode,String lotNumber,String operatorId) {
        public Metadata {
            for (String value : new String[]{equipmentId,productCode,lotNumber,operatorId})
                if(value!=null && value.length()>100) throw new IllegalArgumentException("Metadata exceeds 100 characters");
        }
    }
}
