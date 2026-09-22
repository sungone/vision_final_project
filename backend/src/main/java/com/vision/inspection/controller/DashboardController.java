package com.vision.inspection.controller;
import com.vision.inspection.dto.*;
import com.vision.inspection.repository.InspectionRepository;
import com.vision.inspection.service.DashboardService;
import java.time.Instant;
import java.util.List;
import org.springframework.web.bind.annotation.*;
@RestController
@RequestMapping("/api/dashboard")
public class DashboardController {
    private final DashboardService service;
    public DashboardController(DashboardService service) { this.service=service; }
    @GetMapping("/summary") public DashboardSummary summary(@RequestParam(required=false) Instant startDate,@RequestParam(required=false) Instant endDate,
        @RequestParam(required=false) String productCode,@RequestParam(required=false) String equipmentId,@RequestParam(required=false) String lotNumber) {
        return service.summary(new InspectionRepository.Filter(null,startDate,endDate,productCode,equipmentId,lotNumber));
    }
    @GetMapping("/recent-inspections") public List<HistoryResponse.RecentItem> recent(@RequestParam(defaultValue="8") int limit) { return service.recent(limit); }
}
