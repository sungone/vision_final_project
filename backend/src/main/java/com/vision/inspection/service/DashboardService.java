package com.vision.inspection.service;
import com.vision.inspection.dto.*;
import com.vision.inspection.repository.InspectionRepository;
import java.util.*;
import org.springframework.stereotype.Service;
@Service
public class DashboardService {
    private final InspectionRepository repository;
    public DashboardService(InspectionRepository repository) { this.repository=repository; }
    public DashboardSummary summary(InspectionRepository.Filter filter) {
        var row=repository.summary(filter);
        long total=count(row,"total"),pass=count(row,"passed"),fail=count(row,"failed");
        return new DashboardSummary(total,pass,fail,rate(pass,total),rate(fail,total),
            new DashboardSummary.Defects(count(row,"component"),count(row,"ordering"),count(row,"fastening")),
            new DashboardSummary.Averages(average(row,"bolt_confidence"),average(row,"nut_confidence"),average(row,"washer_confidence"),average(row,"gap")));
    }
    public List<HistoryResponse.RecentItem> recent(int limit) {
        if(limit<1 || limit>100) throw new IllegalArgumentException("Invalid limit");
        return repository.list(new InspectionRepository.Filter(null,null,null,null,null,null),0,limit).stream()
            .map(i -> new HistoryResponse.RecentItem(i.id(),i.inspectionTime(),i.decision().overallResult(),"/api/inspections/"+i.id()+"/images/processed")).toList();
    }
    private long count(Map<String,Object> row,String key) { return ((Number)row.get(key)).longValue(); }
    private Double average(Map<String,Object> row,String key) { return row.get(key)==null?null:((Number)row.get(key)).doubleValue(); }
    private double rate(long value,long total) { return total==0?0:Math.round(value*10000.0/total)/100.0; }
}
