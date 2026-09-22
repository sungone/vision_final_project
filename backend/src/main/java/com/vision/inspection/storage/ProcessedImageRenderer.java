package com.vision.inspection.storage;

import com.vision.inspection.dto.InspectionDecision;
import com.vision.inspection.dto.VisionResult;
import com.vision.inspection.exception.ApiException;

import javax.imageio.ImageIO;
import java.awt.BasicStroke;
import java.awt.Color;
import java.awt.Font;
import java.awt.Graphics2D;
import java.awt.Polygon;
import java.awt.RenderingHints;
import java.awt.image.BufferedImage;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.util.List;

public class ProcessedImageRenderer {

    private static final Color[] COLORS = {
            new Color(20, 184, 166),
            new Color(59, 130, 246),
            new Color(245, 158, 11),
            new Color(236, 72, 153)
    };

    public byte[] render(BufferedImage image, VisionResult vision, InspectionDecision decision) {
        if (image == null || vision == null || decision == null) {
            throw new ApiException(500, "IMAGE_STORAGE_FAILED", "후처리 이미지를 생성할 수 없습니다.");
        }

        BufferedImage rendered = new BufferedImage(image.getWidth(), image.getHeight(), BufferedImage.TYPE_INT_RGB);
        Graphics2D graphics = rendered.createGraphics();
        try {
            graphics.drawImage(image, 0, 0, null);
            graphics.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);
            graphics.setStroke(new BasicStroke(Math.max(2f, Math.min(image.getWidth(), image.getHeight()) / 300f)));
            graphics.setFont(new Font(Font.SANS_SERIF, Font.BOLD, Math.max(14, image.getWidth() / 60)));

            List<VisionResult.Detection> detections = vision.detections();
            if (detections != null) {
                for (int index = 0; index < detections.size(); index++) {
                    drawDetection(graphics, detections.get(index), COLORS[index % COLORS.length]);
                }
            }
            drawDecision(graphics, decision, image.getWidth());
        } finally {
            graphics.dispose();
        }

        try (ByteArrayOutputStream output = new ByteArrayOutputStream()) {
            if (!ImageIO.write(rendered, "jpeg", output)) {
                throw new IOException("No JPEG writer available");
            }
            return output.toByteArray();
        } catch (IOException exception) {
            throw new ApiException(500, "IMAGE_STORAGE_FAILED", "후처리 이미지 생성에 실패했습니다.");
        }
    }

    private void drawDetection(Graphics2D graphics, VisionResult.Detection detection, Color color) {
        if (detection == null) {
            return;
        }
        drawSegmentation(graphics, detection.segmentation(), color);

        var box = detection.bbox();
        if (box == null) {
            return;
        }
        int x = rounded(box.x1());
        int y = rounded(box.y1());
        int width = Math.max(1, rounded(box.x2() - box.x1()));
        int height = Math.max(1, rounded(box.y2() - box.y1()));

        graphics.setColor(color);
        graphics.drawRect(x, y, width, height);
        String label = "%s %.1f%%".formatted(detection.className(), detection.confidence() * 100.0);
        int labelHeight = graphics.getFontMetrics().getHeight() + 6;
        int labelWidth = graphics.getFontMetrics().stringWidth(label) + 10;
        int labelY = Math.max(labelHeight, y);
        graphics.fillRect(x, labelY - labelHeight, labelWidth, labelHeight);
        graphics.setColor(Color.WHITE);
        graphics.drawString(label, x + 5, labelY - 5);
    }

    private void drawSegmentation(Graphics2D graphics, List<List<Double>> points, Color color) {
        if (points == null || points.size() < 3) {
            return;
        }
        Polygon polygon = new Polygon();
        for (List<Double> point : points) {
            if (point != null && point.size() >= 2 && point.get(0) != null && point.get(1) != null) {
                polygon.addPoint(rounded(point.get(0)), rounded(point.get(1)));
            }
        }
        if (polygon.npoints < 3) {
            return;
        }
        graphics.setColor(new Color(color.getRed(), color.getGreen(), color.getBlue(), 64));
        graphics.fillPolygon(polygon);
        graphics.setColor(color);
        graphics.drawPolygon(polygon);
    }

    private void drawDecision(Graphics2D graphics, InspectionDecision decision, int imageWidth) {
        String result = String.valueOf(decision.overallResult());
        boolean pass = "PASS".equalsIgnoreCase(result);
        Color color = pass ? new Color(22, 163, 74) : new Color(220, 38, 38);
        int padding = 10;
        int width = graphics.getFontMetrics().stringWidth(result) + padding * 2;
        int height = graphics.getFontMetrics().getHeight() + padding;
        int x = Math.max(0, imageWidth - width - padding);
        graphics.setColor(color);
        graphics.fillRoundRect(x, padding, width, height, 10, 10);
        graphics.setColor(Color.WHITE);
        graphics.drawString(result, x + padding, padding + graphics.getFontMetrics().getAscent() + 4);
    }

    private int rounded(double value) {
        if (!Double.isFinite(value)) {
            return 0;
        }
        return (int) Math.max(Integer.MIN_VALUE, Math.min(Integer.MAX_VALUE, Math.round(value)));
    }
}
