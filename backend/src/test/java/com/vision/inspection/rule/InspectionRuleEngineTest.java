package com.vision.inspection.rule;

import com.vision.inspection.dto.InspectionDecision;
import com.vision.inspection.dto.RuleSettings;
import com.vision.inspection.dto.VisionResult;
import com.vision.inspection.dto.VisionResult.Bbox;
import com.vision.inspection.dto.VisionResult.Detection;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

import java.util.ArrayList;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class InspectionRuleEngineTest {
    private final InspectionRuleEngine engine = new InspectionRuleEngine();
    private final RuleSettings settings = new RuleSettings(
            0.7, 3.0, "Y_POSITIVE", List.of("bolt", "washer", "nut"), 2.0, "test-v1");

    @Test
    void passesACompleteOrderedAndFastenedAssembly() {
        InspectionDecision decision = engine.evaluate(result(normalDetections()), settings);

        assertThat(decision.overallResult()).isEqualTo("PASS");
        assertThat(decision.componentCheck().result()).isEqualTo("PASS");
        assertThat(decision.orderCheck().result()).isEqualTo("PASS");
        assertThat(decision.fasteningCheck().result()).isEqualTo("PASS");
        assertThat(decision.fasteningCheck().gap()).isEqualTo(2.0);
        assertThat(decision.fasteningCheck().threshold()).isEqualTo(3.0);
        assertThat(decision.fasteningCheck().lateralOffset()).isEqualTo(0.0);
        assertThat(decision.measurements().boltConfidence()).isEqualTo(0.97);
        assertThat(decision.measurements().nutConfidence()).isEqualTo(0.95);
        assertThat(decision.measurements().washerConfidence()).isEqualTo(0.94);
        assertThat(decision.defectCodes()).isEmpty();
    }

    @ParameterizedTest
    @ValueSource(strings = {"bolt", "washer", "nut"})
    void failsAndSkipsDependentRulesWhenAComponentIsMissing(String missing) {
        List<Detection> detections = normalDetections().stream()
                .filter(detection -> !detection.className().equals(missing))
                .toList();

        InspectionDecision decision = engine.evaluate(result(detections), settings);

        assertThat(decision.overallResult()).isEqualTo("FAIL");
        assertThat(decision.componentCheck().result()).isEqualTo("FAIL");
        assertThat(decision.defectCodes()).contains("COMPONENT_MISSING");
        assertThat(decision.orderCheck().result()).isEqualTo("SKIPPED");
        assertThat(decision.fasteningCheck().result()).isEqualTo("SKIPPED");
    }

    @Test
    void retainsLowConfidenceMeasurementButDoesNotTreatItAsPresent() {
        List<Detection> detections = new ArrayList<>(normalDetections());
        detections.set(2, rectangle("nut", 0.69, 40, 42, 50, 52));

        InspectionDecision decision = engine.evaluate(result(detections), settings);

        assertThat(decision.componentCheck().nutDetected()).isFalse();
        assertThat(decision.measurements().nutConfidence()).isEqualTo(0.69);
        assertThat(decision.defectCodes()).contains("COMPONENT_MISSING", "LOW_CONFIDENCE");
    }

    @Test
    void failsOrderAndSkipsFasteningWhenWasherAndNutAreReversed() {
        VisionResult vision = result(List.of(
                rectangle("bolt", 0.97, 40, 10, 50, 20),
                rectangle("nut", 0.95, 40, 30, 50, 40),
                rectangle("washer", 0.94, 40, 42, 50, 52)));

        InspectionDecision decision = engine.evaluate(vision, settings);

        assertThat(decision.orderCheck().result()).isEqualTo("FAIL");
        assertThat(decision.orderCheck().actualOrder()).containsExactly("bolt", "nut", "washer");
        assertThat(decision.defectCodes()).containsExactly("ORDER_ERROR");
        assertThat(decision.fasteningCheck().result()).isEqualTo("SKIPPED");
    }

    @Test
    void passesWhenGapEqualsThresholdExactly() {
        VisionResult vision = result(List.of(
                rectangle("bolt", 0.97, 40, 10, 50, 20),
                rectangle("washer", 0.94, 40, 30, 50, 40),
                rectangle("nut", 0.95, 40, 43, 50, 53)));

        InspectionDecision decision = engine.evaluate(vision, settings);

        assertThat(decision.overallResult()).isEqualTo("PASS");
        assertThat(decision.fasteningCheck().gap()).isEqualTo(3.0);
    }

    @Test
    void failsFasteningForExcessGapOrWholeStackMisalignment() {
        VisionResult excessGap = result(List.of(
                rectangle("bolt", 0.97, 40, 10, 50, 20),
                rectangle("washer", 0.94, 40, 30, 50, 40),
                rectangle("nut", 0.95, 40, 44, 50, 54)));
        VisionResult boltMisaligned = result(List.of(
                rectangle("bolt", 0.97, 35, 10, 45, 20),
                rectangle("washer", 0.94, 40, 30, 50, 40),
                rectangle("nut", 0.95, 40, 42, 50, 52)));

        InspectionDecision gapDecision = engine.evaluate(excessGap, settings);
        InspectionDecision alignmentDecision = engine.evaluate(boltMisaligned, settings);

        assertThat(gapDecision.fasteningCheck().gap()).isEqualTo(4.0);
        assertThat(gapDecision.defectCodes()).containsExactly("FASTENING_ERROR");
        assertThat(alignmentDecision.fasteningCheck().lateralOffset()).isEqualTo(5.0);
        assertThat(alignmentDecision.defectCodes()).containsExactly("FASTENING_ERROR");
    }

    @Test
    void supportsAReversedAssemblyAxis() {
        RuleSettings reversed = new RuleSettings(
                0.7, 3.0, "Y_NEGATIVE", List.of("bolt", "washer", "nut"), 2.0, "test-v1");
        VisionResult vision = result(List.of(
                rectangle("bolt", 0.97, 40, 70, 50, 80),
                rectangle("washer", 0.94, 40, 50, 50, 60),
                rectangle("nut", 0.95, 40, 40, 50, 48)));

        InspectionDecision decision = engine.evaluate(vision, reversed);

        assertThat(decision.overallResult()).isEqualTo("PASS");
        assertThat(decision.orderCheck().actualOrder()).containsExactly("bolt", "washer", "nut");
        assertThat(decision.fasteningCheck().gap()).isEqualTo(2.0);
    }

    @Test
    void measuresGapCorrectlyForAnyConfiguredWasherNutOrder() {
        RuleSettings nutBeforeWasher = new RuleSettings(
                0.7, 3.0, "Y_POSITIVE", List.of("bolt", "nut", "washer"), 2.0, "test-v1");
        VisionResult vision = result(List.of(
                rectangle("bolt", 0.97, 40, 10, 50, 20),
                rectangle("nut", 0.95, 40, 30, 50, 40),
                rectangle("washer", 0.94, 40, 45, 50, 55)));

        InspectionDecision decision = engine.evaluate(vision, nutBeforeWasher);

        assertThat(decision.orderCheck().result()).isEqualTo("PASS");
        assertThat(decision.fasteningCheck().gap()).isEqualTo(5.0);
        assertThat(decision.overallResult()).isEqualTo("FAIL");
    }

    @Test
    void rejectsDuplicateQualifiedComponentsInsteadOfSelectingOneArbitrarily() {
        List<Detection> detections = new ArrayList<>(normalDetections());
        detections.add(rectangle("bolt", 0.91, 60, 10, 70, 20));

        InspectionDecision decision = engine.evaluate(result(detections), settings);

        assertThat(decision.defectCodes()).containsExactly("DUPLICATE_COMPONENT");
        assertThat(decision.orderCheck().result()).isEqualTo("SKIPPED");
    }

    @Test
    void emptySegmentationCannotProduceAFalsePass() {
        List<Detection> detections = new ArrayList<>(normalDetections());
        detections.set(1, new Detection("washer", 0.94, new Bbox(40, 30, 50, 40), List.of()));

        InspectionDecision decision = engine.evaluate(result(detections), settings);

        assertThat(decision.overallResult()).isEqualTo("FAIL");
        assertThat(decision.defectCodes()).containsExactly("INVALID_SEGMENTATION");
        assertThat(decision.orderCheck().result()).isEqualTo("SKIPPED");
    }

    @Test
    void validatesInvalidGeometryAndSettingsAtTheDtoBoundary() {
        assertThatThrownBy(() -> new Bbox(10, 10, 10, 20))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> result(List.of(rectangle("bolt", 0.9, 95, 10, 105, 20))))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("image bounds");
        assertThatThrownBy(() -> new RuleSettings(
                Double.NaN, 3, "Y_POSITIVE", List.of("bolt", "washer", "nut"), 2, "v1"))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new RuleSettings(
                0.7, 3, "DIAGONAL", List.of("bolt", "washer", "nut"), 2, "v1"))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new RuleSettings(
                0.7, 3, "Y_POSITIVE", List.of("bolt", "bolt", "nut"), 2, "v1"))
                .isInstanceOf(IllegalArgumentException.class);
    }

    private List<Detection> normalDetections() {
        return List.of(
                rectangle("bolt", 0.97, 40, 10, 50, 20),
                rectangle("washer", 0.94, 40, 30, 50, 40),
                rectangle("nut", 0.95, 40, 42, 50, 52));
    }

    private VisionResult result(List<Detection> detections) {
        return new VisionResult("model-test", 100, 100, detections);
    }

    private Detection rectangle(
            String className, double confidence, double x1, double y1, double x2, double y2) {
        return new Detection(className, confidence, new Bbox(x1, y1, x2, y2), List.of(
                List.of(x1, y1), List.of(x2, y1), List.of(x2, y2), List.of(x1, y2)));
    }
}