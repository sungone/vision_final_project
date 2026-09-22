package com.vision.inspection.storage;

import com.vision.inspection.exception.ApiException;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Path;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class LocalImageStorageServiceTest {

    @TempDir
    Path root;

    @Test
    void savesReadsAndDeletesInspectionDirectory() {
        LocalImageStorageService storage = new LocalImageStorageService(root);
        byte[] image = {1, 2, 3, 4};
        String key = "2026/09/22/inspection-id/original.jpg";

        storage.save(key, image);

        assertThat(storage.read(key)).isEqualTo(image);
        storage.deleteInspection("2026/09/22/inspection-id");
        assertThatThrownBy(() -> storage.read(key))
                .isInstanceOfSatisfying(ApiException.class,
                        exception -> assertThat(exception.status()).isEqualTo(404));
    }

    @Test
    void rejectsParentTraversal() {
        LocalImageStorageService storage = new LocalImageStorageService(root);

        assertStorageFailure(() -> storage.save("../outside.jpg", new byte[]{1}));
        assertStorageFailure(() -> storage.read("nested/../../../outside.jpg"));
        assertStorageFailure(() -> storage.deleteInspection(".."));
    }

    @Test
    void rejectsAbsolutePaths() {
        LocalImageStorageService storage = new LocalImageStorageService(root);

        assertStorageFailure(() -> storage.save(root.resolve("absolute.jpg").toString(), new byte[]{1}));
    }

    @Test
    void rejectsDeletingStorageRoot() {
        LocalImageStorageService storage = new LocalImageStorageService(root);

        assertStorageFailure(() -> storage.deleteInspection("."));
        assertThat(root).exists();
    }

    private static void assertStorageFailure(Runnable action) {
        assertThatThrownBy(action::run)
                .isInstanceOfSatisfying(ApiException.class,
                        exception -> assertThat(exception.code()).isEqualTo("IMAGE_STORAGE_FAILED"));
    }
}
