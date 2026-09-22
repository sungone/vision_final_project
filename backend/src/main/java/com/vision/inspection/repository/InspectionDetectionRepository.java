package com.vision.inspection.repository;
import com.vision.inspection.dto.VisionResult;
import java.util.List;
import java.util.UUID;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;
@Repository
public class InspectionDetectionRepository {
    private final JdbcTemplate jdbc;
    private final JsonCodec json;
    public InspectionDetectionRepository(JdbcTemplate jdbc,JsonCodec json) { this.jdbc=jdbc; this.json=json; }
    public void insert(UUID id,List<VisionResult.Detection> detections) {
        jdbc.batchUpdate("INSERT INTO inspection_detection(inspection_id,class_name,confidence,bbox,segmentation) VALUES (?,?,?,CAST(? AS jsonb),CAST(? AS jsonb))",
            detections,100,(statement,d) -> {
                statement.setObject(1,id); statement.setString(2,d.className()); statement.setDouble(3,d.confidence());
                statement.setString(4,json.write(d.bbox())); statement.setString(5,json.write(d.segmentation()));
            });
    }
    public List<VisionResult.Detection> find(UUID id) {
        return jdbc.query("SELECT class_name,confidence,bbox,segmentation FROM inspection_detection WHERE inspection_id=? ORDER BY id",
            (rs,row) -> json.read("{\"className\":"+json.write(rs.getString(1))+",\"confidence\":"+rs.getDouble(2)+",\"bbox\":"+rs.getString(3)+",\"segmentation\":"+rs.getString(4)+"}",VisionResult.Detection.class),id);
    }
}
