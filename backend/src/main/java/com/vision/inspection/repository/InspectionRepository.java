package com.vision.inspection.repository;
import com.vision.inspection.dto.*;
import com.vision.inspection.entity.Inspection;
import java.sql.*;
import java.time.Instant;
import java.util.*;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.support.TransactionTemplate;
@Repository
public class InspectionRepository {
    private final JdbcTemplate jdbc;
    private final JsonCodec json;
    private final TransactionTemplate transaction;
    private final InspectionDetectionRepository detections;
    public InspectionRepository(JdbcTemplate jdbc,JsonCodec json,TransactionTemplate transaction,InspectionDetectionRepository detections) {
        this.jdbc=jdbc; this.json=json; this.transaction=transaction; this.detections=detections;
    }
    public void reserve(Inspection i) {
        jdbc.update("""
            INSERT INTO inspection(id,inspection_time,status,original_image_path,processed_image_path,original_content_type,rule_snapshot,
                equipment_id,product_code,lot_number,operator_id,image_sha256)
            VALUES (?,?,'PROCESSING',?,?,?,CAST(? AS jsonb),?,?,?,?,?)
            """,i.id(),Timestamp.from(i.inspectionTime()),i.originalImagePath(),i.processedImagePath(),i.originalContentType(),
            json.write(i.ruleSnapshot()),i.metadata().equipmentId(),i.metadata().productCode(),i.metadata().lotNumber(),i.metadata().operatorId(),i.imageSha256());
    }
    public void complete(UUID id,VisionResult vision,InspectionDecision d) {
        transaction.executeWithoutResult(status -> {
            int changed=jdbc.update("""
                UPDATE inspection SET status='COMPLETED',overall_result=?,component_result=?,order_result=?,fastening_result=?,
                bolt_confidence=?,nut_confidence=?,washer_confidence=?,fastening_gap=?,model_version=?,decision=CAST(? AS jsonb),completed_at=now()
                WHERE id=? AND status='PROCESSING'
                """,d.overallResult(),d.componentCheck().result(),d.orderCheck().result(),d.fasteningCheck().result(),
                d.measurements().boltConfidence(),d.measurements().nutConfidence(),d.measurements().washerConfidence(),
                d.fasteningCheck().gap(),vision.modelVersion(),json.write(d),id);
            if(changed!=1) throw new IllegalStateException("Inspection cannot transition to completed");
            detections.insert(id,vision.detections());
        });
    }
    /** A confirmed FAILED transition is required before deleting images after an ambiguous commit. */
    public boolean fail(UUID id,String code) {
        return jdbc.update("UPDATE inspection SET status='FAILED',failure_code=?,completed_at=now() WHERE id=? AND status='PROCESSING'",code,id)==1;
    }
    public Optional<Inspection> find(UUID id) {
        return jdbc.query("SELECT * FROM inspection WHERE id=?",this::map,id).stream().findFirst();
    }
    public record Filter(String result,Instant startDate,Instant endDate,String productCode,String equipmentId,String lotNumber) {
        public Filter {
            if(result!=null && !Set.of("PASS","FAIL").contains(result)) throw new IllegalArgumentException("Invalid result");
            if(startDate!=null && endDate!=null && startDate.isAfter(endDate)) throw new IllegalArgumentException("Invalid date range");
        }
    }
    private record Where(String sql,List<Object> args) {}
    private Where where(Filter f) {
        StringBuilder sql=new StringBuilder(" WHERE status='COMPLETED'"); List<Object> args=new ArrayList<>();
        if(f.result()!=null) { sql.append(" AND overall_result=?"); args.add(f.result()); }
        if(f.startDate()!=null) { sql.append(" AND inspection_time>=?"); args.add(Timestamp.from(f.startDate())); }
        if(f.endDate()!=null) { sql.append(" AND inspection_time<=?"); args.add(Timestamp.from(f.endDate())); }
        for(var pair:List.of(new String[]{"product_code",f.productCode()},new String[]{"equipment_id",f.equipmentId()},new String[]{"lot_number",f.lotNumber()}))
            if(pair[1]!=null) { sql.append(" AND ").append(pair[0]).append("=?"); args.add(pair[1]); }
        return new Where(sql.toString(),args);
    }
    public long count(Filter f) { var w=where(f); return jdbc.queryForObject("SELECT count(*) FROM inspection"+w.sql(),Long.class,w.args().toArray()); }
    public List<Inspection> list(Filter f,int page,int size) {
        var w=where(f); var args=new ArrayList<>(w.args()); args.add(size); args.add((long)page*size);
        return jdbc.query("SELECT * FROM inspection"+w.sql()+" ORDER BY inspection_time DESC,id DESC LIMIT ? OFFSET ?",this::map,args.toArray());
    }
    public Map<String,Object> summary(Filter f) {
        var w=where(f);
        return jdbc.queryForMap("""
            SELECT count(*) AS total,
              count(*) FILTER (WHERE overall_result='PASS') AS passed,
              count(*) FILTER (WHERE overall_result='FAIL') AS failed,
              count(*) FILTER (WHERE component_result='FAIL') AS component,
              count(*) FILTER (WHERE order_result='FAIL') AS ordering,
              count(*) FILTER (WHERE fastening_result='FAIL') AS fastening,
              avg(bolt_confidence) AS bolt_confidence,avg(nut_confidence) AS nut_confidence,
              avg(washer_confidence) AS washer_confidence,avg(fastening_gap) AS gap
            FROM inspection
            """+w.sql(),w.args().toArray());
    }
    private Inspection map(ResultSet rs,int row) throws SQLException {
        String decision=rs.getString("decision");
        return new Inspection(rs.getObject("id",UUID.class),rs.getTimestamp("inspection_time").toInstant(),rs.getString("status"),
            rs.getString("original_image_path"),rs.getString("processed_image_path"),rs.getString("original_content_type"),rs.getString("model_version"),
            json.read(rs.getString("rule_snapshot"),RuleSettings.class),decision==null?null:json.read(decision,InspectionDecision.class),
            new Inspection.Metadata(rs.getString("equipment_id"),rs.getString("product_code"),rs.getString("lot_number"),rs.getString("operator_id")),rs.getString("image_sha256"));
    }
}
