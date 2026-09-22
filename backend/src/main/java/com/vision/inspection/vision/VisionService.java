package com.vision.inspection.vision;
import com.vision.inspection.dto.VisionResult;
public interface VisionService {
    VisionResult predict(byte[] image,String filename,String contentType);
}
