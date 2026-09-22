package com.vision.inspection.rule;

import com.vision.inspection.dto.InspectionDecision.OrderCheck;
import com.vision.inspection.dto.RuleSettings;
import com.vision.inspection.dto.VisionResult.Detection;

import java.util.Comparator;
import java.util.List;
import java.util.Map;

public final class AssemblyOrderRule {
    private static final double EPSILON = 1.0e-9;

    private final PostProcessor postProcessor;

    public AssemblyOrderRule(PostProcessor postProcessor) {
        this.postProcessor = postProcessor;
    }

    /**
     * The bolt position uses the centroid of the model's bolt mask. If a model labels a long
     * shank rather than the relevant bolt-head/contact region, its centroid is not a reliable
     * assembly-order landmark; train a bolt-head class or emit an explicit landmark instead.
     */
    public Result evaluate(Map<String, Detection> detections, RuleSettings settings) {
        List<Position> positions = ComponentRule.REQUIRED.stream()
                .map(name -> new Position(name, postProcessor.axisCoordinate(
                        postProcessor.centroid(detections.get(name)), settings.axisDirection())))
                .sorted(Comparator.comparingDouble(Position::coordinate))
                .toList();
        boolean ambiguous = false;
        for (int i = 1; i < positions.size(); i++) {
            if (Math.abs(positions.get(i).coordinate() - positions.get(i - 1).coordinate()) <= EPSILON) {
                ambiguous = true;
            }
        }
        List<String> actual = positions.stream().map(Position::name).toList();
        boolean pass = !ambiguous && actual.equals(settings.expectedOrder());
        String detail = ambiguous
                ? "Component centroids overlap on the configured assembly axis"
                : pass ? "Component order matches the configured order"
                : "Expected " + settings.expectedOrder() + " but measured " + actual;
        return new Result(
                new OrderCheck(pass ? "PASS" : "FAIL", actual, settings.expectedOrder(),
                        settings.axisDirection(), detail),
                pass ? List.of() : List.of("ORDER_ERROR")
        );
    }

    public OrderCheck skipped(RuleSettings settings, String detail) {
        return new OrderCheck("SKIPPED", List.of(), settings.expectedOrder(),
                settings.axisDirection(), detail);
    }

    private record Position(String name, double coordinate) { }

    public record Result(OrderCheck check, List<String> defectCodes) { }
}
