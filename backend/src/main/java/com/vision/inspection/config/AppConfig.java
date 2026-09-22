package com.vision.inspection.config;
import com.vision.inspection.rule.InspectionRuleEngine;
import com.vision.inspection.storage.*;
import java.nio.file.Path;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.*;
import org.springframework.web.servlet.config.annotation.*;
@Configuration
public class AppConfig {
    @Bean ImageStorageService imageStorage(@Value("${inspection.storage-root}") String root) { return new LocalImageStorageService(Path.of(root)); }
    @Bean ImageValidator imageValidator(@Value("${inspection.max-image-bytes}") long bytes,@Value("${inspection.max-image-pixels}") long pixels, @Value("${inspection.max-image-dimension}") int dimension) { return new ImageValidator(bytes,pixels,dimension); }
    @Bean ProcessedImageRenderer renderer() { return new ProcessedImageRenderer(); }
    @Bean InspectionRuleEngine ruleEngine() { return new InspectionRuleEngine(); }
    @Bean WebMvcConfigurer cors(@Value("${inspection.allowed-origin}") String origin) {
        return new WebMvcConfigurer() {
            @Override public void addCorsMappings(CorsRegistry registry) {
                registry.addMapping("/api/**").allowedOrigins(origin).allowedMethods("GET","POST","PUT").allowedHeaders("Content-Type","X-Settings-Key");
            }
        };
    }
}

