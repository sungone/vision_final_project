package com.vision.inspection.dto;
import java.time.Instant;
import java.util.*;
public record HistoryResponse(List<Item> content,int page,int size,long totalElements,long totalPages) {
    public record Item(UUID inspectionId,Instant inspectionTime,String overallResult,String thumbnailUrl) {}
    public record RecentItem(UUID inspectionId,Instant inspectionTime,String result,String thumbnailUrl) {}
}
