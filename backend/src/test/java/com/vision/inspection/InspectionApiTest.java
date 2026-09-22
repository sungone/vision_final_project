package com.vision.inspection;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.vision.inspection.dto.*;
import com.vision.inspection.exception.ApiException;
import com.vision.inspection.repository.*;
import com.vision.inspection.storage.ImageStorageService;
import com.vision.inspection.vision.VisionService;
import java.awt.image.BufferedImage;
import java.io.ByteArrayOutputStream;
import java.nio.file.*;
import java.util.*;
import javax.imageio.ImageIO;
import org.junit.jupiter.api.*;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.dao.DataAccessResourceFailureException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.context.bean.override.mockito.*;
import org.springframework.test.web.servlet.MockMvc;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.*;
import static org.assertj.core.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
@AutoConfigureMockMvc
@Testcontainers
class InspectionApiTest {
    @Container static final PostgreSQLContainer<?> postgres=new PostgreSQLContainer<>("postgres:16-alpine");
    static final Path STORAGE=Path.of("target","integration-images",UUID.randomUUID().toString()).toAbsolutePath();
    @DynamicPropertySource static void properties(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url",postgres::getJdbcUrl);
        registry.add("spring.datasource.username",postgres::getUsername);
        registry.add("spring.datasource.password",postgres::getPassword);
        registry.add("inspection.storage-root",STORAGE::toString);
        registry.add("inspection.settings-api-key",() -> "test-only-secret");
    }
    @Autowired MockMvc mvc;
    @Autowired ObjectMapper mapper;
    @Autowired JdbcTemplate jdbc;
    @MockitoBean VisionService vision;
    @MockitoSpyBean InspectionDetectionRepository detections;
    @MockitoSpyBean InspectionRepository repository;
    @MockitoSpyBean ImageStorageService storage;

    @BeforeEach void setup() {
        jdbc.execute("TRUNCATE inspection CASCADE");
        jdbc.update("UPDATE inspection_rule_settings SET settings=CAST(? AS jsonb)",json(RuleSettings.defaultSettings()));
        when(vision.predict(any(),anyString(),anyString())).thenReturn(normal());
    }
    @Test void uploadPersistsImagesDetectionsAndReturnsSnapshot() throws Exception {
        String id=upload();
        mvc.perform(get("/api/inspections/"+id)).andExpect(status().isOk())
            .andExpect(jsonPath("$.overallResult").value("PASS"))
            .andExpect(jsonPath("$.fasteningCheck.gap").value(2.0))
            .andExpect(jsonPath("$.ruleSnapshot.fasteningGapThreshold").value(3.0))
            .andExpect(jsonPath("$.metadata.productCode").value("P-001"))
            .andExpect(jsonPath("$.modelVersion").value("test-model-sha256"))
            .andExpect(jsonPath("$.detections.length()").value(3))
            .andExpect(jsonPath("$.originalImagePath").doesNotExist());
        mvc.perform(get("/api/inspections/"+id+"/images/original")).andExpect(status().isOk()).andExpect(content().contentType("image/png"));
        var bytes=mvc.perform(get("/api/inspections/"+id+"/images/processed")).andExpect(status().isOk()).andExpect(content().contentType("image/jpeg")).andReturn().getResponse().getContentAsByteArray();
        assertThat(ImageIO.read(new java.io.ByteArrayInputStream(bytes)).getWidth()).isEqualTo(100);
        assertThat(jdbc.queryForObject("SELECT count(*) FROM inspection_detection",Long.class)).isEqualTo(3);
    }
    @Test void historyFiltersAndKpisComeFromCompletedRows() throws Exception {
        upload();
        when(vision.predict(any(),anyString(),anyString())).thenReturn(new VisionResult("test",100,100,List.of(rect("bolt",10,20))));
        upload();
        mvc.perform(get("/api/inspections").param("result","FAIL").param("size","1").param("productCode","P-001"))
            .andExpect(status().isOk()).andExpect(jsonPath("$.totalElements").value(1)).andExpect(jsonPath("$.totalPages").value(1));
        mvc.perform(get("/api/inspections").param("productCode","other")).andExpect(jsonPath("$.totalElements").value(0));
        mvc.perform(get("/api/dashboard/summary")).andExpect(status().isOk())
            .andExpect(jsonPath("$.totalInspections").value(2)).andExpect(jsonPath("$.passCount").value(1))
            .andExpect(jsonPath("$.failCount").value(1)).andExpect(jsonPath("$.passRate").value(50.0))
            .andExpect(jsonPath("$.defects.component").value(1)).andExpect(jsonPath("$.defects.order").value(0))
            .andExpect(jsonPath("$.averages.fasteningGap").value(2.0));
        mvc.perform(get("/api/dashboard/recent-inspections").param("limit","1")).andExpect(jsonPath("$.length()").value(1)).andExpect(jsonPath("$[0].result").value("FAIL"));
    }
    @Test void settingsDoNotRewriteHistoricalThresholds() throws Exception {
        String id=upload();
        var changed=new RuleSettings(.7,1,"Y_POSITIVE",List.of("bolt","washer","nut"),10,"geometry-v1");
        mvc.perform(put("/api/settings/inspection-rules").header("X-Settings-Key","test-only-secret").contentType("application/json").content(json(changed)))
            .andExpect(status().isOk()).andExpect(jsonPath("$.fasteningGapThreshold").value(1));
        mvc.perform(get("/api/inspections/"+id)).andExpect(jsonPath("$.fasteningCheck.threshold").value(3.0));
        mvc.perform(multipart("/api/inspections").file(image())).andExpect(status().isCreated()).andExpect(jsonPath("$.overallResult").value("FAIL"));
    }
    @Test void settingsRequireAuthorizationAndValidateValues() throws Exception {
        mvc.perform(put("/api/settings/inspection-rules").contentType("application/json").content(json(RuleSettings.defaultSettings())))
            .andExpect(status().isForbidden());
        mvc.perform(put("/api/settings/inspection-rules").header("X-Settings-Key","test-only-secret").contentType("application/json")
            .content(json(RuleSettings.defaultSettings()).replace("0.7","1.7")))
            .andExpect(status().isBadRequest()).andExpect(jsonPath("$.code").value("INVALID_RULE_SETTING"));
    }
    @Test void modelFailureLeavesFailedAuditButNoImagesOrKpi() throws Exception {
        when(vision.predict(any(),anyString(),anyString())).thenThrow(new ApiException(503,"MODEL_NOT_AVAILABLE","모델이 없습니다."));
        mvc.perform(multipart("/api/inspections").file(image())).andExpect(status().isServiceUnavailable()).andExpect(jsonPath("$.code").value("MODEL_NOT_AVAILABLE"));
        assertFailedAndClean();
        mvc.perform(get("/api/dashboard/summary")).andExpect(jsonPath("$.totalInspections").value(0)).andExpect(jsonPath("$.passRate").value(0));
    }
    @Test void inferenceFailureIsNotAnInspectionDefect() throws Exception {
        when(vision.predict(any(),anyString(),anyString())).thenThrow(new ApiException(502,"VISION_INFERENCE_FAILED","실패"));
        mvc.perform(multipart("/api/inspections").file(image())).andExpect(status().isBadGateway()).andExpect(jsonPath("$.code").value("VISION_INFERENCE_FAILED"));
        assertFailedAndClean();
    }
    @Test void detectionInsertFailureRollsBackCompletionAndCleansFiles() throws Exception {
        doThrow(new DataAccessResourceFailureException("internal SQL must not leak")).when(detections).insert(any(),anyList());
        mvc.perform(multipart("/api/inspections").file(image())).andExpect(status().isServiceUnavailable())
            .andExpect(jsonPath("$.code").value("DATABASE_ERROR")).andExpect(content().string(org.hamcrest.Matchers.not(org.hamcrest.Matchers.containsString("internal SQL"))));
        assertFailedAndClean();
        assertThat(jdbc.queryForObject("SELECT count(*) FROM inspection_detection",Long.class)).isZero();
    }
    @Test void ambiguousCommitNeverDeletesCompletedImages() throws Exception {
        doAnswer(invocation -> { invocation.callRealMethod(); throw new DataAccessResourceFailureException("lost acknowledgement"); }).when(repository).complete(any(),any(),any());
        String id=upload();
        mvc.perform(get("/api/inspections/"+id+"/images/processed")).andExpect(status().isOk());
        assertThat(jdbc.queryForObject("SELECT status FROM inspection",String.class)).isEqualTo("COMPLETED");
    }
    @Test void storageFailureCleansOriginalAndDoesNotComplete() throws Exception {
        doThrow(new ApiException(500,"IMAGE_STORAGE_FAILED","저장 실패")).when(storage).save(endsWith("processed.jpg"),any());
        mvc.perform(multipart("/api/inspections").file(image())).andExpect(status().isInternalServerError()).andExpect(jsonPath("$.code").value("IMAGE_STORAGE_FAILED"));
        assertFailedAndClean();
    }
    @Test void invalidAndOversizedFilesNeverReachVision() throws Exception {
        mvc.perform(multipart("/api/inspections").file(new MockMultipartFile("image","a.txt","text/plain",new byte[]{1})))
            .andExpect(status().isBadRequest()).andExpect(jsonPath("$.code").value("INVALID_IMAGE"));
        mvc.perform(multipart("/api/inspections").file(new MockMultipartFile("image","a.png","image/png",new byte[10485761])))
            .andExpect(status().isPayloadTooLarge()).andExpect(jsonPath("$.code").value("IMAGE_TOO_LARGE"));
        mvc.perform(multipart("/api/inspections").file(image()).file(image())).andExpect(status().isBadRequest()).andExpect(jsonPath("$.code").value("INVALID_IMAGE"));
        verifyNoInteractions(vision);
        assertThat(jdbc.queryForObject("SELECT count(*) FROM inspection",Long.class)).isZero();
    }
    @Test void rejectsExcessiveDimensionBeforeInference() throws Exception {
        var bytes=new ByteArrayOutputStream();
        ImageIO.write(new BufferedImage(8193,1,BufferedImage.TYPE_INT_RGB),"png",bytes);
        mvc.perform(multipart("/api/inspections").file(new MockMultipartFile("image","wide.png","image/png",bytes.toByteArray())))
            .andExpect(status().isPayloadTooLarge()).andExpect(jsonPath("$.code").value("IMAGE_TOO_LARGE"));
        verifyNoInteractions(vision);
    }
    @Test void missingInspectionAndInvalidFiltersAreExplicit() throws Exception {
        mvc.perform(get("/api/inspections/"+UUID.randomUUID())).andExpect(status().isNotFound()).andExpect(jsonPath("$.code").value("INSPECTION_NOT_FOUND"));
        mvc.perform(get("/api/inspections").param("page","-1")).andExpect(status().isBadRequest());
        mvc.perform(get("/api/inspections").param("result","invalid")).andExpect(status().isBadRequest());
        mvc.perform(get("/api/inspections").param("startDate","2026-10-01T00:00:00Z").param("endDate","2026-09-01T00:00:00Z")).andExpect(status().isBadRequest());
    }
    private String upload() throws Exception {
        String body=mvc.perform(multipart("/api/inspections").file(image()).param("productCode","P-001"))
            .andExpect(status().isCreated()).andReturn().getResponse().getContentAsString();
        return mapper.readTree(body).get("inspectionId").asText();
    }
    private void assertFailedAndClean() {
        assertThat(jdbc.queryForObject("SELECT status FROM inspection",String.class)).isEqualTo("FAILED");
        String original=jdbc.queryForObject("SELECT original_image_path FROM inspection",String.class);
        assertThat(Files.exists(STORAGE.resolve(original).getParent())).isFalse();
    }
    private String json(Object value) { try { return mapper.writeValueAsString(value); } catch(Exception e) { throw new RuntimeException(e); } }
    private MockMultipartFile image() throws Exception {
        var out=new ByteArrayOutputStream(); ImageIO.write(new BufferedImage(100,100,BufferedImage.TYPE_INT_RGB),"png",out);
        return new MockMultipartFile("image","sample.png","image/png",out.toByteArray());
    }
    private VisionResult normal() { return new VisionResult("test-model-sha256",100,100,List.of(rect("bolt",10,20),rect("washer",30,40),rect("nut",42,52))); }
    private VisionResult.Detection rect(String name,double top,double bottom) {
        return new VisionResult.Detection(name,.95,new VisionResult.Bbox(40,top,60,bottom),List.of(List.of(40.0,top),List.of(60.0,top),List.of(60.0,bottom),List.of(40.0,bottom)));
    }
}


