package com.vision.inspection.dto;

import java.util.List;
import java.util.Locale;
import java.util.Objects;

/**
 * Model-independent vision output consumed by the inspection rules.
 */
public record VisionResult(
        String modelVersion,
        int width,
        int height,
        List<Detection> detections
) {
    public VisionResult {
        if (modelVersion == null || modelVersion.isBlank()) {
            throw new IllegalArgumentException("modelVersion must not be blank");
        }
        if (width <= 0 || height <= 0) {
            throw new IllegalArgumentException("image dimensions must be positive");
        }
        detections = List.copyOf(Objects.requireNonNull(detections, "detections"));
        for (Detection detection : detections) {
            Objects.requireNonNull(detection, "detections must not contain null");
            if (detection.bbox().x2() > width || detection.bbox().y2() > height) {
                throw new IllegalArgumentException("detection bbox must be inside image bounds");
            }
            for (List<Double> point : detection.segmentation()) {
                double x = point.get(0);
                double y = point.get(1);
                if (x < 0 || x > width || y < 0 || y > height) {
                    throw new IllegalArgumentException("segmentation point must be inside image bounds");
                }
            }
        }
    }

    public record Detection(
            String className,
            double confidence,
            Bbox bbox,
            List<List<Double>> segmentation
    ) {
        public Detection {
            if (className == null || className.isBlank()) {
                throw new IllegalArgumentException("className must not be blank");
            }
            className = className.trim().toLowerCase(Locale.ROOT);
            if (!Double.isFinite(confidence) || confidence < 0 || confidence > 1) {
                throw new IllegalArgumentException("confidence must be finite and between 0 and 1");
            }
            bbox = Objects.requireNonNull(bbox, "bbox");
            Objects.requireNonNull(segmentation, "segmentation");
            segmentation = segmentation.stream().map(point -> {
                Objects.requireNonNull(point, "segmentation must not contain null points");
                if (point.size() != 2 || point.get(0) == null || point.get(1) == null
                        || !Double.isFinite(point.get(0)) || !Double.isFinite(point.get(1))) {
                    throw new IllegalArgumentException("each segmentation point must contain two finite coordinates");
                }
                return List.copyOf(point);
            }).toList();
        }
    }

    public record Bbox(double x1, double y1, double x2, double y2) {
        public Bbox {
            if (!Double.isFinite(x1) || !Double.isFinite(y1)
                    || !Double.isFinite(x2) || !Double.isFinite(y2)) {
                throw new IllegalArgumentException("bbox coordinates must be finite");
            }
            if (x1 < 0 || y1 < 0 || x2 <= x1 || y2 <= y1) {
                throw new IllegalArgumentException("bbox must have positive area and non-negative coordinates");
            }
        }
    }
}
