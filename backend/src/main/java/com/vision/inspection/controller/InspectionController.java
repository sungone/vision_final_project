package com.vision.inspection.controller;
import com.vision.inspection.dto.*;
import com.vision.inspection.entity.Inspection;
import com.vision.inspection.repository.InspectionRepository;
import com.vision.inspection.service.*;
import java.time.Instant;
import java.util.UUID;
import org.springframework.http.*;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;
@RestController
@RequestMapping("/api/inspections")
public class InspectionController {
    private final InspectionService inspections; private final HistoryService history;
    public InspectionController(InspectionService inspections,HistoryService history) { this.inspections=inspections; this.history=history; }
    @PostMapping(consumes=MediaType.MULTIPART_FORM_DATA_VALUE)
    public ResponseEntity<InspectionResponse> inspect(@RequestPart("image") java.util.List<MultipartFile> images,
        @RequestParam(required=false) String equipmentId,@RequestParam(required=false) String productCode,
        @RequestParam(required=false) String lotNumber,@RequestParam(required=false) String operatorId) {
        if(images.size()!=1) throw new com.vision.inspection.exception.ApiException(400,"INVALID_IMAGE","이미지 한 장만 업로드하세요.");
        var response=inspections.inspect(images.get(0),new Inspection.Metadata(equipmentId,productCode,lotNumber,operatorId));
        return ResponseEntity.created(java.net.URI.create("/api/inspections/"+response.inspectionId())).body(response);
    }
    @GetMapping
    public HistoryResponse list(@RequestParam(defaultValue="0") int page,@RequestParam(defaultValue="20") int size,
        @RequestParam(required=false) String result,@RequestParam(required=false) Instant startDate,@RequestParam(required=false) Instant endDate,
        @RequestParam(required=false) String productCode,@RequestParam(required=false) String equipmentId,@RequestParam(required=false) String lotNumber) {
        return history.list(new InspectionRepository.Filter(result,startDate,endDate,productCode,equipmentId,lotNumber),page,size);
    }
    @GetMapping("/{id}") public InspectionResponse detail(@PathVariable UUID id) { return history.detail(id); }
    @GetMapping("/{id}/images/{variant}") public ResponseEntity<byte[]> image(@PathVariable UUID id,@PathVariable String variant) {
        var image=history.image(id,variant);
        return ResponseEntity.ok().contentType(MediaType.parseMediaType(image.contentType())).header("X-Content-Type-Options","nosniff")
            .cacheControl(CacheControl.noStore()).body(image.bytes());
    }
}

