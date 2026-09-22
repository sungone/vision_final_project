package com.vision.inspection.rule;

import com.vision.inspection.dto.InspectionDecision;
import com.vision.inspection.dto.InspectionDecision.FasteningCheck;
import com.vision.inspection.dto.InspectionDecision.Measurements;
import com.vision.inspection.dto.InspectionDecision.OrderCheck;
import com.vision.inspection.dto.RuleSettings;
import com.vision.inspection.dto.VisionResult;

import java.util.ArrayList;
import java.util.List;
import java.util.Objects;

/** Pure, stateless orchestration of quality rules over normalized vision output. */
public final class InspectionRuleEngine {
    private final ComponentRule componentRule;
    private final AssemblyOrderRule orderRule;
    private final FasteningRule fasteningRule;

    public InspectionRuleEngine() {
        PostProcessor postProcessor = new PostProcessor();
        this.componentRule = new ComponentRule(postProcessor);
        this.orderRule = new AssemblyOrderRule(postProcessor);
        this.fasteningRule = new FasteningRule(postProcessor);
    }

    public InspectionDecision evaluate(VisionResult visionResult, RuleSettings settings) {
        Objects.requireNonNull(visionResult, "visionResult");
        Objects.requireNonNull(settings, "settings");
        ComponentRule.Evaluation component = componentRule.evaluate(visionResult, settings);
        List<String> defects = new ArrayList<>(component.defectCodes());
        OrderCheck orderCheck;
        FasteningCheck fasteningCheck;

        if (!"PASS".equals(component.check().result())) {
            orderCheck = orderRule.skipped(settings, "Component validation failed");
            fasteningCheck = fasteningRule.skipped(settings, "Component validation failed");
        } else {
            AssemblyOrderRule.Result order = orderRule.evaluate(component.selected(), settings);
            orderCheck = order.check();
            defects.addAll(order.defectCodes());
            if (!"PASS".equals(orderCheck.result())) {
                fasteningCheck = fasteningRule.skipped(settings, "Assembly order validation failed");
            } else {
                FasteningRule.Result fastening = fasteningRule.evaluate(component.selected(), settings);
                fasteningCheck = fastening.check();
                defects.addAll(fastening.defectCodes());
            }
        }

        Measurements measurements = new Measurements(
                component.confidences().get("bolt"),
                component.confidences().get("nut"),
                component.confidences().get("washer")
        );
        return new InspectionDecision(
                defects.isEmpty() ? "PASS" : "FAIL",
                component.check(),
                orderCheck,
                fasteningCheck,
                measurements,
                List.copyOf(defects)
        );
    }
}
