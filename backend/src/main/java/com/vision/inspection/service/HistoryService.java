package com.vision.inspection.service;
import com.vision.inspection.dto.*;
import com.vision.inspection.entity.Inspection;
import com.vision.inspection.exception.ApiException;
import com.vision.inspection.repository.*;
import com.vision.inspection.storage.ImageStorageService;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
@Service
public class HistoryService {
    private final InspectionRepository repository; private final InspectionDetectionRepository detections; private final ImageStorageService storage;
    public HistoryService(InspectionRepository repository,InspectionDetectionRepository detections,ImageStorageService storage) {
        this.repository=repository; this.detections=detections; this.storage=storage;
    }
    public InspectionResponse detail(UUID id) { return InspectionResponse.from(completed(id),detections.find(id)); }
    private Inspection completed(UUID id) {
        return repository.find(id).filter(i -> i.status().equals("COMPLETED"))
            .orElseThrow(() -> new ApiException(404,"INSPECTION_NOT_FOUND","검사 결과를 찾을 수 없습니다."));
    }
    @Transactional(readOnly=true,isolation=org.springframework.transaction.annotation.Isolation.REPEATABLE_READ)
    public HistoryResponse list(InspectionRepository.Filter filter,int page,int size) {
        if(page<0 || size<1 || size>100) throw new IllegalArgumentException("Invalid pagination");
        long count=repository.count(filter);
        var items=repository.list(filter,page,size).stream().map(i -> new HistoryResponse.Item(i.id(),i.inspectionTime(),i.decision().overallResult(),
            "/api/inspections/"+i.id()+"/images/processed")).toList();
        return new HistoryResponse(items,page,size,count,(count+size-1)/size);
    }
    public record ImageContent(byte[] bytes,String contentType) {}
    public ImageContent image(UUID id,String variant) {
        var i=completed(id);
        return switch(variant) {
            case "original" -> new ImageContent(storage.read(i.originalImagePath()),i.originalContentType());
            case "processed" -> new ImageContent(storage.read(i.processedImagePath()),"image/jpeg");
            default -> throw new ApiException(404,"IMAGE_NOT_FOUND","이미지를 찾을 수 없습니다.");
        };
    }
}
