package com.vision.inspection.rule;

import com.vision.inspection.dto.InspectionDecision.ComponentCheck;
import com.vision.inspection.dto.RuleSettings;
import com.vision.inspection.dto.VisionResult;
import com.vision.inspection.dto.VisionResult.Detection;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

public final class ComponentRule {
    static final List<String> REQUIRED = List.of("bolt", "washer", "nut");

    private final PostProcessor postProcessor;

    public ComponentRule(PostProcessor postProcessor) {
        this.postProcessor = postProcessor;
    }

    public Evaluation evaluate(VisionResult visionResult, RuleSettings settings) {
        Map<String, Detection> selected = new LinkedHashMap<>();
        Map<String, Double> confidences = new LinkedHashMap<>();
        Set<String> defects = new LinkedHashSet<>();
        List<String> details = new ArrayList<>();
        Map<String, Boolean> detected = new LinkedHashMap<>();

        for (String component : REQUIRED) {
            List<Detection> raw = visionResult.detections().stream()
                    .filter(detection -> component.equals(detection.className()))
                    .toList();
            raw.stream().map(Detection::confidence).max(Double::compareTo)
                    .ifPresent(value -> confidences.put(component, value));
            List<Detection> qualified = raw.stream()
                    .filter(detection -> detection.confidence() >= settings.confidenceThreshold())
                    .toList();
            detected.put(component, !qualified.isEmpty());

            if (qualified.isEmpty()) {
                defects.add("COMPONENT_MISSING");
                if (raw.isEmpty()) {
                    details.add(component + " missing");
                } else {
                    defects.add("LOW_CONFIDENCE");
                    details.add(component + " below confidence threshold");
                }
            } else if (qualified.size() > 1) {
                defects.add("DUPLICATE_COMPONENT");
                details.add(component + " has " + qualified.size() + " qualified detections");
            } else if (!postProcessor.hasUsableMask(qualified.get(0))) {
                defects.add("INVALID_SEGMENTATION");
                details.add(component + " has no usable segmentation mask");
            } else {
                selected.put(component, qualified.get(0));
            }
        }

        boolean pass = defects.isEmpty();
        ComponentCheck check = new ComponentCheck(
                pass ? "PASS" : "FAIL",
                detected.get("bolt"),
                detected.get("nut"),
                detected.get("washer"),
                pass ? "All required components are uniquely detected with usable masks"
                        : String.join("; ", details)
        );
        return new Evaluation(check, Map.copyOf(selected), Map.copyOf(confidences), List.copyOf(defects));
    }

    public record Evaluation(
            ComponentCheck check,
            Map<String, Detection> selected,
            Map<String, Double> confidences,
            List<String> defectCodes
    ) { }
}
