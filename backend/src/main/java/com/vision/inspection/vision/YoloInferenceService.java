package com.vision.inspection.vision;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.vision.inspection.dto.VisionResult;
import com.vision.inspection.exception.ApiException;
import java.net.http.HttpClient;
import java.time.Duration;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.http.*;
import org.springframework.http.client.JdkClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.web.client.RestClient;
@Component
public class YoloInferenceService implements VisionService {
    private final RestClient client;
    private final ObjectMapper mapper;
    public YoloInferenceService(ObjectMapper mapper,@Value("${inspection.vision-url}") String url,
            @Value("${inspection.vision-timeout-seconds}") int timeout, @Value("${inspection.vision-service-token:}") String token) {
        this.mapper=mapper;
        var factory=new JdkClientHttpRequestFactory(HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(3)).build());
        factory.setReadTimeout(Duration.ofSeconds(timeout));
        var builder=RestClient.builder().baseUrl(url).requestFactory(factory);
        if(!token.isBlank()) builder.defaultHeader("X-Vision-Service-Token",token);
        this.client=builder.build();
    }
    @Override public VisionResult predict(byte[] image,String filename,String contentType) {
        var parts=new LinkedMultiValueMap<String,Object>();
        var headers=new HttpHeaders(); headers.setContentType(MediaType.parseMediaType(contentType));
        parts.add("image",new HttpEntity<>(new ByteArrayResource(image) { @Override public String getFilename() { return filename; } },headers));
        // Recognition floor stays below the configurable quality threshold, preserving low-confidence evidence.
        parts.add("confidenceThreshold","0.001");
        try {
            return client.post().uri("/internal/v1/infer/segmentation").contentType(MediaType.MULTIPART_FORM_DATA).body(parts)
                .exchange((request,response) -> {
                    byte[] body=response.getBody().readNBytes(8*1024*1024+1);
                    if(body.length>8*1024*1024) throw failure();
                    if(!response.getStatusCode().is2xxSuccessful()) {
                        String code="";
                        try { code=mapper.readTree(body).path("code").asText(); } catch(Exception ignored) { }
                        if(code.equals("MODEL_NOT_AVAILABLE")) throw new ApiException(503,code,"Vision 모델이 준비되지 않았습니다.");
                        throw failure();
                    }
                    VisionResult result=mapper.readValue(body,VisionResult.class);
                    validate(result);
                    return result;
                });
        } catch(ApiException e) { throw e; }
        catch(Exception e) { throw failure(); }
    }
    private void validate(VisionResult result) {
        if(result==null || result.modelVersion()==null || result.modelVersion().isBlank() || result.modelVersion().length()>200
            || result.width()<=0 || result.height()<=0 || result.detections()==null || result.detections().size()>1000) throw failure();
        for(var d:result.detections()) {
            if(d==null || d.className()==null || d.className().length()>64 || !Double.isFinite(d.confidence()) || d.confidence()<0 || d.confidence()>1 || d.bbox()==null || d.segmentation()==null || d.segmentation().size()>10000) throw failure();
            var b=d.bbox();
            if(!Double.isFinite(b.x1()) || !Double.isFinite(b.x2()) || !Double.isFinite(b.y1()) || !Double.isFinite(b.y2())
                || b.x1()<0 || b.y1()<0 || b.x2()>result.width() || b.y2()>result.height() || b.x1()>=b.x2() || b.y1()>=b.y2()) throw failure();
            for(var p:d.segmentation()) if(p==null || p.size()!=2 || p.get(0)==null || p.get(1)==null
                || !Double.isFinite(p.get(0)) || !Double.isFinite(p.get(1)) || p.get(0)<0 || p.get(1)<0 || p.get(0)>result.width() || p.get(1)>result.height()) throw failure();
        }
    }
    private ApiException failure() { return new ApiException(502,"VISION_INFERENCE_FAILED","Vision 추론에 실패했습니다."); }
}

