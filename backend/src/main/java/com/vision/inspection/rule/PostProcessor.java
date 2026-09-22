package com.vision.inspection.rule;

import com.vision.inspection.dto.VisionResult.Detection;

import java.util.HashSet;
import java.util.List;
import java.util.Set;

/** Geometry features derived from model-independent segmentation polygons. */
public final class PostProcessor {
    private static final double EPSILON = 1.0e-9;

    public boolean hasUsableMask(Detection detection) {
        List<List<Double>> points = detection.segmentation();
        if (points.size() < 3) {
            return false;
        }
        Set<List<Double>> unique = new HashSet<>(points);
        return unique.size() >= 3 && Math.abs(signedDoubleArea(points)) > EPSILON;
    }

    public Point centroid(Detection detection) {
        requireUsableMask(detection);
        List<List<Double>> points = detection.segmentation();
        double crossSum = 0;
        double xSum = 0;
        double ySum = 0;
        for (int i = 0; i < points.size(); i++) {
            List<Double> current = points.get(i);
            List<Double> next = points.get((i + 1) % points.size());
            double cross = current.get(0) * next.get(1) - next.get(0) * current.get(1);
            crossSum += cross;
            xSum += (current.get(0) + next.get(0)) * cross;
            ySum += (current.get(1) + next.get(1)) * cross;
        }
        return new Point(xSum / (3 * crossSum), ySum / (3 * crossSum));
    }

    public double axisCoordinate(Point point, String axisDirection) {
        return switch (axisDirection) {
            case "X_POSITIVE" -> point.x();
            case "X_NEGATIVE" -> -point.x();
            case "Y_POSITIVE" -> point.y();
            case "Y_NEGATIVE" -> -point.y();
            default -> throw new IllegalArgumentException("unsupported axisDirection: " + axisDirection);
        };
    }

    public double lateralCoordinate(Point point, String axisDirection) {
        return switch (axisDirection) {
            case "X_POSITIVE", "X_NEGATIVE" -> point.y();
            case "Y_POSITIVE", "Y_NEGATIVE" -> point.x();
            default -> throw new IllegalArgumentException("unsupported axisDirection: " + axisDirection);
        };
    }

    public Projection projection(Detection detection, String axisDirection) {
        requireUsableMask(detection);
        double min = Double.POSITIVE_INFINITY;
        double max = Double.NEGATIVE_INFINITY;
        for (List<Double> point : detection.segmentation()) {
            double value = axisCoordinate(new Point(point.get(0), point.get(1)), axisDirection);
            min = Math.min(min, value);
            max = Math.max(max, value);
        }
        return new Projection(min, max);
    }

    private void requireUsableMask(Detection detection) {
        if (!hasUsableMask(detection)) {
            throw new IllegalArgumentException("detection requires a non-degenerate segmentation polygon");
        }
    }

    private double signedDoubleArea(List<List<Double>> points) {
        double sum = 0;
        for (int i = 0; i < points.size(); i++) {
            List<Double> current = points.get(i);
            List<Double> next = points.get((i + 1) % points.size());
            sum += current.get(0) * next.get(1) - next.get(0) * current.get(1);
        }
        return sum;
    }

    public record Point(double x, double y) { }

    public record Projection(double min, double max) { }
}
