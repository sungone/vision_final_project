package com.vision.inspection.storage;

import com.vision.inspection.exception.ApiException;
import org.springframework.web.multipart.MultipartFile;

import javax.imageio.ImageIO;
import javax.imageio.ImageReader;
import javax.imageio.stream.ImageInputStream;
import java.awt.image.BufferedImage;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.util.Iterator;
import java.util.Locale;
import java.util.Map;
import java.util.Set;

public class ImageValidator {

    private static final Set<String> ALLOWED_EXTENSIONS = Set.of("jpg", "jpeg", "png");
    private static final Set<String> ALLOWED_CONTENT_TYPES = Set.of("image/jpeg", "image/png");
    private static final Map<String, String> FORMAT_CONTENT_TYPES = Map.of(
            "jpeg", "image/jpeg",
            "jpg", "image/jpeg",
            "png", "image/png"
    );

    private final long maxBytes;
    private final long maxPixels;
    private final int maxDimension;

    public ImageValidator(long maxBytes, long maxPixels) {
        this(maxBytes, maxPixels, 8192);
    }

    public ImageValidator(long maxBytes, long maxPixels, int maxDimension) {
        if (maxBytes <= 0 || maxPixels <= 0 || maxDimension <= 0) {
            throw new IllegalArgumentException("Image limits must be positive");
        }
        this.maxBytes = maxBytes;
        this.maxPixels = maxPixels;
        this.maxDimension = maxDimension;
    }

    public ValidatedImage validate(MultipartFile file) {
        if (file == null || file.isEmpty()) {
            throw invalidImage("이미지 파일이 비어 있습니다.");
        }
        if (file.getSize() > maxBytes) {
            throw tooLarge();
        }

        String extension = extensionOf(file.getOriginalFilename());
        String declaredContentType = normalizeContentType(file.getContentType());
        if (!ALLOWED_EXTENSIONS.contains(extension) || !ALLOWED_CONTENT_TYPES.contains(declaredContentType)) {
            throw invalidImage("지원하지 않는 이미지 형식입니다.");
        }

        byte[] bytes = readBounded(file);
        try (ImageInputStream imageInput = ImageIO.createImageInputStream(new ByteArrayInputStream(bytes))) {
            if (imageInput == null) {
                throw invalidImage("이미지 파일을 읽을 수 없습니다.");
            }
            Iterator<ImageReader> readers = ImageIO.getImageReaders(imageInput);
            if (!readers.hasNext()) {
                throw invalidImage("손상되었거나 지원하지 않는 이미지입니다.");
            }

            ImageReader reader = readers.next();
            try {
                reader.setInput(imageInput, true, true);
                String actualFormat = reader.getFormatName().toLowerCase(Locale.ROOT);
                String actualContentType = FORMAT_CONTENT_TYPES.get(actualFormat);
                if (actualContentType == null
                        || !actualContentType.equals(declaredContentType)
                        || !extensionMatches(extension, actualFormat)) {
                    throw invalidImage("파일 확장자, MIME Type, 실제 이미지 형식이 일치하지 않습니다.");
                }

                int width = reader.getWidth(0);
                int height = reader.getHeight(0);
                if (width <= 0 || height <= 0 || width > maxDimension || height > maxDimension || (long) width * height > maxPixels) {
                    throw tooLarge();
                }
                BufferedImage image = reader.read(0);
                if (image == null) {
                    throw invalidImage("이미지 디코딩에 실패했습니다.");
                }
                return new ValidatedImage(bytes, image, canonicalExtension(actualFormat), actualContentType);
            } finally {
                reader.dispose();
            }
        } catch (ApiException exception) {
            throw exception;
        } catch (IOException | RuntimeException exception) {
            throw invalidImage("손상되었거나 지원하지 않는 이미지입니다.");
        }
    }

    private byte[] readBounded(MultipartFile file) {
        try (InputStream input = file.getInputStream();
             ByteArrayOutputStream output = new ByteArrayOutputStream((int) Math.min(file.getSize(), 8192))) {
            byte[] buffer = new byte[8192];
            long total = 0;
            int count;
            while ((count = input.read(buffer)) != -1) {
                total += count;
                if (total > maxBytes) {
                    throw tooLarge();
                }
                output.write(buffer, 0, count);
            }
            return output.toByteArray();
        } catch (ApiException exception) {
            throw exception;
        } catch (IOException exception) {
            throw invalidImage("이미지 파일을 읽을 수 없습니다.");
        }
    }

    private String extensionOf(String filename) {
        if (filename == null) {
            return "";
        }
        int separator = Math.max(filename.lastIndexOf('/'), filename.lastIndexOf('\\'));
        int dot = filename.lastIndexOf('.');
        if (dot <= separator || dot == filename.length() - 1) {
            return "";
        }
        return filename.substring(dot + 1).toLowerCase(Locale.ROOT);
    }

    private String normalizeContentType(String contentType) {
        if (contentType == null) {
            return "";
        }
        int parameters = contentType.indexOf(';');
        String value = parameters >= 0 ? contentType.substring(0, parameters) : contentType;
        return value.trim().toLowerCase(Locale.ROOT);
    }

    private boolean extensionMatches(String extension, String actualFormat) {
        return actualFormat.equals("png") ? extension.equals("png") : extension.equals("jpg") || extension.equals("jpeg");
    }

    private String canonicalExtension(String actualFormat) {
        return actualFormat.equals("png") ? "png" : "jpg";
    }

    private ApiException invalidImage(String message) {
        return new ApiException(400, "INVALID_IMAGE", message);
    }

    private ApiException tooLarge() {
        return new ApiException(413, "IMAGE_TOO_LARGE", "이미지 크기가 허용 한도를 초과했습니다.");
    }

    public record ValidatedImage(byte[] bytes, BufferedImage image, String extension, String contentType) {
        public ValidatedImage {
            bytes = bytes.clone();
        }

        @Override
        public byte[] bytes() {
            return bytes.clone();
        }
    }
}

