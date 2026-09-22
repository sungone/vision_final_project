package com.vision.inspection.dto;
import com.vision.inspection.entity.Inspection;
import java.time.Instant;
import java.util.*;
public record InspectionResponse(UUID inspectionId,Instant inspectionTime,String overallResult,
    InspectionDecision.ComponentCheck componentCheck,InspectionDecision.OrderCheck orderCheck,
    InspectionDecision.FasteningCheck fasteningCheck,InspectionDecision.Measurements measurements,
    List<String> defectCodes,Images images,String modelVersion,String ruleVersion,RuleSettings ruleSnapshot,
    Inspection.Metadata metadata,String imageSha256,List<VisionResult.Detection> detections) {
    public record Images(String originalUrl,String processedUrl) {}
    public static InspectionResponse from(Inspection i,List<VisionResult.Detection> detections) {
        var d=i.decision(); String base="/api/inspections/"+i.id()+"/images/";
        return new InspectionResponse(i.id(),i.inspectionTime(),d.overallResult(),d.componentCheck(),d.orderCheck(),d.fasteningCheck(),d.measurements(),
            d.defectCodes(),new Images(base+"original",base+"processed"),i.modelVersion(),i.ruleSnapshot().ruleVersion(),i.ruleSnapshot(),i.metadata(),i.imageSha256(),detections);
    }
}
