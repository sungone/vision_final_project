package com.vision.inspection.vision;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.sun.net.httpserver.HttpServer;
import com.vision.inspection.exception.ApiException;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.atomic.AtomicReference;
import org.junit.jupiter.api.*;
import static org.assertj.core.api.Assertions.*;
class YoloInferenceServiceTest {
    HttpServer server;
    YoloInferenceService service;
    AtomicReference<String> received=new AtomicReference<>();
    @BeforeEach void start() throws Exception {
        server=HttpServer.create(new InetSocketAddress("127.0.0.1",0),0);
        service=new YoloInferenceService(new ObjectMapper(),"http://127.0.0.1:"+server.getAddress().getPort(),2,"test-internal-token");
        server.start();
    }
    @AfterEach void stop() { server.stop(0); }
    private void respond(int status,String body) {
        server.createContext("/internal/v1/infer/segmentation",exchange -> {
            assertThat(exchange.getRequestHeaders().getFirst("X-Vision-Service-Token")).isEqualTo("test-internal-token");
            received.set(new String(exchange.getRequestBody().readAllBytes(),StandardCharsets.UTF_8));
            byte[] bytes=body.getBytes(StandardCharsets.UTF_8);
            exchange.getResponseHeaders().add("Content-Type","application/json");
            exchange.sendResponseHeaders(status,bytes.length);
            exchange.getResponseBody().write(bytes); exchange.close();
        });
    }
    @Test void sendsMultipartAndParsesModelIndependentContract() {
        respond(200,"""
          {"modelVersion":"sha256","width":100,"height":100,"detections":[
          {"className":"BOLT","confidence":0.97,"bbox":{"x1":1,"y1":2,"x2":10,"y2":20},
          "segmentation":[[1,2],[10,2],[10,20],[1,20]]}]}
          """);
        var result=service.predict(new byte[]{1,2,3},"image.png","image/png");
        assertThat(result.detections().get(0).className()).isEqualTo("bolt");
        assertThat(received.get()).contains("name=\"image\"","filename=\"image.png\"","name=\"confidenceThreshold\"");
    }
    @Test void modelUnavailableRemainsDistinctWithoutLeakingInternalMessage() {
        respond(503,"{\"code\":\"MODEL_NOT_AVAILABLE\",\"message\":\"secret path\"}");
        assertThatThrownBy(() -> service.predict(new byte[]{1},"a.png","image/png"))
            .isInstanceOfSatisfying(ApiException.class,e -> { assertThat(e.code()).isEqualTo("MODEL_NOT_AVAILABLE"); assertThat(e.getMessage()).doesNotContain("secret"); });
    }
    @Test void malformedGeometryIsInfrastructureError() {
        respond(200,"""
          {"modelVersion":"sha","width":10,"height":10,"detections":[
          {"className":"bolt","confidence":2,"bbox":{"x1":0,"y1":0,"x2":1,"y2":1},"segmentation":[]}]}
          """);
        assertFailure();
    }
    @Test void invalidJsonIsInfrastructureError() { respond(200,"not-json"); assertFailure(); }
    @Test void upstreamFailureIsInfrastructureError() { respond(500,"{\"message\":\"stack trace\"}"); assertFailure(); }
    private void assertFailure() {
        assertThatThrownBy(() -> service.predict(new byte[]{1},"a.png","image/png"))
            .isInstanceOfSatisfying(ApiException.class,e -> { assertThat(e.code()).isEqualTo("VISION_INFERENCE_FAILED"); assertThat(e.status()).isEqualTo(502); });
    }
}

