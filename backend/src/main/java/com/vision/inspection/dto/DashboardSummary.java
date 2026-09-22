package com.vision.inspection.dto;
public record DashboardSummary(long totalInspections,long passCount,long failCount,double passRate,double failRate,
    Defects defects,Averages averages) {
    public record Defects(long component,long order,long fastening) {}
    public record Averages(Double boltConfidence,Double nutConfidence,Double washerConfidence,Double fasteningGap) {}
}
