package com.vision.inspection.dto;

import java.util.List;
import java.util.Objects;

public record InspectionDecision(
        String overallResult,
        ComponentCheck componentCheck,
        OrderCheck orderCheck,
        FasteningCheck fasteningCheck,
        Measurements measurements,
        List<String> defectCodes
) {
    public InspectionDecision {
        overallResult = required(overallResult, "overallResult");
        componentCheck = Objects.requireNonNull(componentCheck, "componentCheck");
        orderCheck = Objects.requireNonNull(orderCheck, "orderCheck");
        fasteningCheck = Objects.requireNonNull(fasteningCheck, "fasteningCheck");
        measurements = Objects.requireNonNull(measurements, "measurements");
        defectCodes = List.copyOf(Objects.requireNonNull(defectCodes, "defectCodes"));
    }

    public record ComponentCheck(
            String result,
            boolean boltDetected,
            boolean nutDetected,
            boolean washerDetected,
            String detail
    ) {
        public ComponentCheck {
            result = required(result, "component result");
            detail = required(detail, "component detail");
        }
    }

    public record OrderCheck(
            String result,
            List<String> actualOrder,
            List<String> expectedOrder,
            String axisDirection,
            String detail
    ) {
        public OrderCheck {
            result = required(result, "order result");
            actualOrder = List.copyOf(Objects.requireNonNull(actualOrder, "actualOrder"));
            expectedOrder = List.copyOf(Objects.requireNonNull(expectedOrder, "expectedOrder"));
            axisDirection = required(axisDirection, "axisDirection");
            detail = required(detail, "order detail");
        }
    }

    public record FasteningCheck(
            String result,
            Double gap,
            double threshold,
            String unit,
            Double lateralOffset,
            double alignmentTolerance,
            String detail
    ) {
        public FasteningCheck {
            result = required(result, "fastening result");
            if (gap != null && !Double.isFinite(gap)) {
                throw new IllegalArgumentException("gap must be finite when supplied");
            }
            if (lateralOffset != null && !Double.isFinite(lateralOffset)) {
                throw new IllegalArgumentException("lateralOffset must be finite when supplied");
            }
            if (!Double.isFinite(threshold) || threshold < 0
                    || !Double.isFinite(alignmentTolerance) || alignmentTolerance < 0) {
                throw new IllegalArgumentException("fastening thresholds must be finite and non-negative");
            }
            unit = required(unit, "unit");
            detail = required(detail, "fastening detail");
        }
    }

    public record Measurements(
            Double boltConfidence,
            Double nutConfidence,
            Double washerConfidence
    ) {
        public Measurements {
            validateConfidence(boltConfidence, "boltConfidence");
            validateConfidence(nutConfidence, "nutConfidence");
            validateConfidence(washerConfidence, "washerConfidence");
        }
    }

    private static String required(String value, String name) {
        if (value == null || value.isBlank()) {
            throw new IllegalArgumentException(name + " must not be blank");
        }
        return value;
    }

    private static void validateConfidence(Double value, String name) {
        if (value != null && (!Double.isFinite(value) || value < 0 || value > 1)) {
            throw new IllegalArgumentException(name + " must be between 0 and 1 when supplied");
        }
    }
}
