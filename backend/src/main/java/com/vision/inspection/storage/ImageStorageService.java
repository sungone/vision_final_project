package com.vision.inspection.storage;

public interface ImageStorageService {

    void save(String key, byte[] bytes);

    byte[] read(String key);

    void deleteInspection(String prefix);
}
