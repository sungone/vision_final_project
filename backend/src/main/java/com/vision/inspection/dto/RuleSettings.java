package com.vision.inspection.dto;

import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Objects;
import java.util.Set;

public record RuleSettings(
        double confidenceThreshold,
        double fasteningGapThreshold,
        String axisDirection,
        List<String> expectedOrder,
        double alignmentTolerance,
        String ruleVersion
) {
    private static final Set<String> AXES = Set.of(
            "X_POSITIVE", "X_NEGATIVE", "Y_POSITIVE", "Y_NEGATIVE");
    private static final Set<String> COMPONENTS = Set.of("bolt", "washer", "nut");

    public RuleSettings {
        if (!Double.isFinite(confidenceThreshold)
                || confidenceThreshold < 0 || confidenceThreshold > 1) {
            throw new IllegalArgumentException("confidenceThreshold must be finite and between 0 and 1");
        }
        if (!Double.isFinite(fasteningGapThreshold) || fasteningGapThreshold < 0) {
            throw new IllegalArgumentException("fasteningGapThreshold must be finite and non-negative");
        }
        if (!Double.isFinite(alignmentTolerance) || alignmentTolerance < 0) {
            throw new IllegalArgumentException("alignmentTolerance must be finite and non-negative");
        }
        axisDirection = Objects.requireNonNull(axisDirection, "axisDirection").trim().toUpperCase(Locale.ROOT);
        if (!AXES.contains(axisDirection)) {
            throw new IllegalArgumentException("unsupported axisDirection: " + axisDirection);
        }
        Objects.requireNonNull(expectedOrder, "expectedOrder");
        expectedOrder = expectedOrder.stream()
                .map(value -> Objects.requireNonNull(value, "expectedOrder item").trim().toLowerCase(Locale.ROOT))
                .toList();
        if (expectedOrder.size() != COMPONENTS.size()
                || !new HashSet<>(expectedOrder).equals(COMPONENTS)) {
            throw new IllegalArgumentException("expectedOrder must be a permutation of bolt, washer and nut");
        }
        if (ruleVersion == null || ruleVersion.isBlank()) {
            throw new IllegalArgumentException("ruleVersion must not be blank");
        }
    }

    public static RuleSettings defaultSettings() {
        return new RuleSettings(
                0.70,
                3.0,
                "Y_POSITIVE",
                List.of("bolt", "washer", "nut"),
                10.0,
                "geometry-v1"
        );
    }
}
