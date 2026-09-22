package com.vision.inspection.rule;

import com.vision.inspection.dto.InspectionDecision.FasteningCheck;
import com.vision.inspection.dto.RuleSettings;
import com.vision.inspection.dto.VisionResult.Detection;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

public final class FasteningRule {
    private final PostProcessor postProcessor;

    public FasteningRule(PostProcessor postProcessor) {
        this.postProcessor = postProcessor;
    }

    public Result evaluate(Map<String, Detection> detections, RuleSettings settings) {
        Detection washer = detections.get("washer");
        Detection nut = detections.get("nut");
        PostProcessor.Projection washerProjection = postProcessor.projection(washer, settings.axisDirection());
        PostProcessor.Projection nutProjection = postProcessor.projection(nut, settings.axisDirection());
        double gap = Math.max(0, Math.max(
                nutProjection.min() - washerProjection.max(),
                washerProjection.min() - nutProjection.max()));
        Detection bolt = detections.get("bolt");
        double boltLateral = postProcessor.lateralCoordinate(
                postProcessor.centroid(bolt), settings.axisDirection());
        double washerLateral = postProcessor.lateralCoordinate(
                postProcessor.centroid(washer), settings.axisDirection());
        double nutLateral = postProcessor.lateralCoordinate(
                postProcessor.centroid(nut), settings.axisDirection());
        double lateralMin = Math.min(boltLateral, Math.min(washerLateral, nutLateral));
        double lateralMax = Math.max(boltLateral, Math.max(washerLateral, nutLateral));
        // Maximum cross-axis centroid spread captures alignment of the complete stack.
        double lateralOffset = lateralMax - lateralMin;

        boolean gapPass = gap <= settings.fasteningGapThreshold();
        boolean alignmentPass = lateralOffset <= settings.alignmentTolerance();
        boolean pass = gapPass && alignmentPass;
        List<String> failures = new ArrayList<>();
        if (!gapPass) {
            failures.add("gap " + gap + " exceeds " + settings.fasteningGapThreshold());
        }
        if (!alignmentPass) {
            failures.add("lateral offset " + lateralOffset + " exceeds " + settings.alignmentTolerance());
        }
        FasteningCheck check = new FasteningCheck(
                pass ? "PASS" : "FAIL",
                gap,
                settings.fasteningGapThreshold(),
                "px",
                lateralOffset,
                settings.alignmentTolerance(),
                pass ? "Gap and lateral alignment are within configured thresholds"
                        : String.join("; ", failures)
        );
        return new Result(check, pass ? List.of() : List.of("FASTENING_ERROR"));
    }

    public FasteningCheck skipped(RuleSettings settings, String detail) {
        return new FasteningCheck("SKIPPED", null, settings.fasteningGapThreshold(), "px",
                null, settings.alignmentTolerance(), detail);
    }

    public record Result(FasteningCheck check, List<String> defectCodes) { }
}
