package com.vision.inspection.storage;

import com.vision.inspection.dto.InspectionDecision;
import com.vision.inspection.dto.VisionResult;
import org.junit.jupiter.api.Test;

import javax.imageio.ImageIO;
import java.awt.image.BufferedImage;
import java.io.ByteArrayInputStream;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

class ProcessedImageRendererTest {

    @Test
    void rendersRgbJpegWithDetectionsMasksAndDecision() throws Exception {
        BufferedImage source = new BufferedImage(160, 120, BufferedImage.TYPE_INT_ARGB);
        VisionResult vision = new VisionResult(
                "test-model",
                160,
                120,
                List.of(new VisionResult.Detection(
                        "bolt",
                        0.97,
                        new VisionResult.Bbox(20, 20, 100, 90),
                        List.of(List.of(20.0, 20.0), List.of(100.0, 20.0), List.of(60.0, 90.0))
                ))
        );
        InspectionDecision decision = new InspectionDecision(
                "PASS",
                new InspectionDecision.ComponentCheck("PASS", true, true, true, "ok"),
                new InspectionDecision.OrderCheck(
                        "PASS", List.of("bolt", "washer", "nut"), List.of("bolt", "washer", "nut"), "Y", "ok"),
                new InspectionDecision.FasteningCheck("PASS", 1.2, 3.0, "px", 0.1, 2.0, "ok"),
                new InspectionDecision.Measurements(0.97, 0.95, 0.94),
                List.of()
        );

        byte[] jpeg = new ProcessedImageRenderer().render(source, vision, decision);
        BufferedImage decoded = ImageIO.read(new ByteArrayInputStream(jpeg));

        assertThat(jpeg).isNotEmpty();
        assertThat(decoded).isNotNull();
        assertThat(decoded.getWidth()).isEqualTo(160);
        assertThat(decoded.getHeight()).isEqualTo(120);
        assertThat(decoded.getType()).isNotEqualTo(BufferedImage.TYPE_INT_ARGB);
        assertThat(decoded.getRGB(20, 20)).isNotEqualTo(source.getRGB(20, 20));
    }
}
