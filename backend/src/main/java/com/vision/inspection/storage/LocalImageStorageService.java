package com.vision.inspection.storage;

import com.vision.inspection.exception.ApiException;

import java.io.IOException;
import java.nio.file.AtomicMoveNotSupportedException;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.nio.file.attribute.BasicFileAttributes;
import java.util.Comparator;

public class LocalImageStorageService implements ImageStorageService {

    private final Path root;

    public LocalImageStorageService(Path root) {
        if (root == null) {
            throw new IllegalArgumentException("Storage root is required");
        }
        this.root = root.toAbsolutePath().normalize();
        initializeRoot();
    }

    @Override
    public void save(String key, byte[] bytes) {
        if (bytes == null) {
            throw new ApiException(500, "IMAGE_STORAGE_FAILED", "저장할 이미지 데이터가 없습니다.");
        }

        Path target = resolveSafe(key, false);
        Path temporary = null;
        try {
            createDirectoriesWithoutLinks(target.getParent());
            ensureNoSymbolicLink(target.getParent());
            if (Files.exists(target, LinkOption.NOFOLLOW_LINKS) && Files.isSymbolicLink(target)) {
                throw storageFailure();
            }

            temporary = Files.createTempFile(target.getParent(), ".upload-", ".tmp");
            Files.write(temporary, bytes);
            try {
                Files.move(temporary, target, StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING);
            } catch (AtomicMoveNotSupportedException ignored) {
                Files.move(temporary, target, StandardCopyOption.REPLACE_EXISTING);
            }
        } catch (ApiException exception) {
            throw exception;
        } catch (IOException exception) {
            throw storageFailure();
        } finally {
            if (temporary != null) {
                try {
                    Files.deleteIfExists(temporary);
                } catch (IOException ignored) {
                    // Best-effort cleanup; the primary storage error is more useful to callers.
                }
            }
        }
    }

    @Override
    public byte[] read(String key) {
        Path target = resolveSafe(key, false);
        try {
            ensureNoSymbolicLink(target);
            if (!Files.isRegularFile(target, LinkOption.NOFOLLOW_LINKS)) {
                throw new ApiException(404, "IMAGE_NOT_FOUND", "이미지를 찾을 수 없습니다.");
            }
            return Files.readAllBytes(target);
        } catch (ApiException exception) {
            throw exception;
        } catch (IOException exception) {
            throw storageFailure();
        }
    }

    @Override
    public void deleteInspection(String prefix) {
        Path target = resolveSafe(prefix, true);
        if (!Files.exists(target, LinkOption.NOFOLLOW_LINKS)) {
            return;
        }

        try {
            ensureNoSymbolicLink(target);
            try (var paths = Files.walk(target)) {
                for (Path path : paths.sorted(Comparator.reverseOrder()).toList()) {
                    if (Files.isSymbolicLink(path)) {
                        throw storageFailure();
                    }
                    Files.deleteIfExists(path);
                }
            }
        } catch (ApiException exception) {
            throw exception;
        } catch (IOException exception) {
            throw storageFailure();
        }
    }

    private void initializeRoot() {
        try {
            Files.createDirectories(root);
            if (Files.isSymbolicLink(root) || !Files.isDirectory(root, LinkOption.NOFOLLOW_LINKS)) {
                throw storageFailure();
            }
        } catch (ApiException exception) {
            throw exception;
        } catch (IOException exception) {
            throw storageFailure();
        }
    }

    private Path resolveSafe(String key, boolean rejectRoot) {
        if (key == null || key.isBlank()) {
            throw storageFailure();
        }

        Path supplied;
        try {
            supplied = Path.of(key);
        } catch (RuntimeException exception) {
            throw storageFailure();
        }
        if (supplied.isAbsolute()) {
            throw storageFailure();
        }

        Path target = root.resolve(supplied).normalize();
        if (!target.startsWith(root) || (rejectRoot && target.equals(root))) {
            throw storageFailure();
        }
        ensureNoSymbolicLink(target);
        return target;
    }

    private void createDirectoriesWithoutLinks(Path directory) throws IOException {
        if (directory == null || !directory.startsWith(root)) {
            throw storageFailure();
        }
        Path current = root;
        for (Path part : root.relativize(directory)) {
            current = current.resolve(part);
            if (Files.exists(current, LinkOption.NOFOLLOW_LINKS)) {
                if (Files.isSymbolicLink(current) || !Files.isDirectory(current, LinkOption.NOFOLLOW_LINKS)) {
                    throw storageFailure();
                }
            } else {
                Files.createDirectory(current);
            }
        }
    }

    private void ensureNoSymbolicLink(Path target) {
        Path current = root;
        if (Files.isSymbolicLink(root)) {
            throw storageFailure();
        }
        Path relative;
        try {
            relative = root.relativize(target);
        } catch (IllegalArgumentException exception) {
            throw storageFailure();
        }
        for (Path part : relative) {
            current = current.resolve(part);
            if (Files.exists(current, LinkOption.NOFOLLOW_LINKS) && Files.isSymbolicLink(current)) {
                throw storageFailure();
            }
        }
    }

    private ApiException storageFailure() {
        return new ApiException(500, "IMAGE_STORAGE_FAILED", "이미지 저장소 처리에 실패했습니다.");
    }
}
