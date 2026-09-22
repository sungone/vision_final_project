package com.vision.inspection.repository;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.stereotype.Component;
@Component
public class JsonCodec {
    private final ObjectMapper mapper;
    public JsonCodec(ObjectMapper mapper) { this.mapper=mapper; }
    public String write(Object value) {
        try { return mapper.writeValueAsString(value); }
        catch(JsonProcessingException e) { throw new IllegalStateException("Cannot serialize persisted data",e); }
    }
    public <T> T read(String value,Class<T> type) {
        try { return mapper.readValue(value,type); }
        catch(JsonProcessingException e) { throw new IllegalStateException("Cannot read persisted data",e); }
    }
}
