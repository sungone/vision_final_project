package com.vision.inspection.storage;

import com.vision.inspection.exception.ApiException;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockMultipartFile;

import javax.imageio.ImageIO;
import java.awt.Color;
import java.awt.image.BufferedImage;
import java.io.ByteArrayOutputStream;
import java.io.DataOutputStream;
import java.nio.charset.StandardCharsets;
import java.util.zip.CRC32;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class ImageValidatorTest {

    @Test
    void acceptsValidPngAndReturnsDecodedImage() throws Exception {
        byte[] png = imageBytes("png", 12, 8);
        MockMultipartFile file = new MockMultipartFile("image", "sample.png", "image/png", png);

        ImageValidator.ValidatedImage validated = new ImageValidator(10_000, 100).validate(file);

        assertThat(validated.extension()).isEqualTo("png");
        assertThat(validated.contentType()).isEqualTo("image/png");
        assertThat(validated.image().getWidth()).isEqualTo(12);
        assertThat(validated.bytes()).isEqualTo(png);
    }

    @Test
    void rejectsUnsupportedFile() {
        MockMultipartFile file = new MockMultipartFile(
                "image", "sample.gif", "image/gif", "GIF89a".getBytes(StandardCharsets.US_ASCII));

        assertApiError(() -> new ImageValidator(1_000, 1_000).validate(file), 400, "INVALID_IMAGE");
    }

    @Test
    void rejectsFileLargerThanByteLimit() {
        MockMultipartFile file = new MockMultipartFile(
                "image", "sample.jpg", "image/jpeg", new byte[101]);

        assertApiError(() -> new ImageValidator(100, 1_000).validate(file), 413, "IMAGE_TOO_LARGE");
    }

    @Test
    void rejectsCorruptImage() {
        MockMultipartFile file = new MockMultipartFile(
                "image", "sample.png", "image/png", "not a png".getBytes(StandardCharsets.UTF_8));

        assertApiError(() -> new ImageValidator(1_000, 1_000).validate(file), 400, "INVALID_IMAGE");
    }

    @Test
    void rejectsMismatchedMimeAndActualFormat() throws Exception {
        byte[] png = imageBytes("png", 2, 2);
        MockMultipartFile file = new MockMultipartFile("image", "sample.jpg", "image/jpeg", png);

        assertApiError(() -> new ImageValidator(10_000, 1_000).validate(file), 400, "INVALID_IMAGE");
    }

    @Test
    void rejectsOversizedPixelDimensionsBeforeDecode() throws Exception {
        byte[] pngHeader = pngHeader(100_000, 100_000);
        MockMultipartFile file = new MockMultipartFile("image", "bomb.png", "image/png", pngHeader);

        assertApiError(() -> new ImageValidator(10_000, 1_000_000).validate(file), 413, "IMAGE_TOO_LARGE");
    }

    private static byte[] imageBytes(String format, int width, int height) throws Exception {
        BufferedImage image = new BufferedImage(width, height, BufferedImage.TYPE_INT_RGB);
        image.setRGB(0, 0, Color.RED.getRGB());
        ByteArrayOutputStream output = new ByteArrayOutputStream();
        ImageIO.write(image, format, output);
        return output.toByteArray();
    }

    private static byte[] pngHeader(int width, int height) throws Exception {
        ByteArrayOutputStream output = new ByteArrayOutputStream();
        try (DataOutputStream data = new DataOutputStream(output)) {
            data.write(new byte[]{(byte) 0x89, 'P', 'N', 'G', 13, 10, 26, 10});
            ByteArrayOutputStream ihdrData = new ByteArrayOutputStream();
            try (DataOutputStream ihdr = new DataOutputStream(ihdrData)) {
                ihdr.writeInt(width);
                ihdr.writeInt(height);
                ihdr.writeByte(8);
                ihdr.writeByte(2);
                ihdr.writeByte(0);
                ihdr.writeByte(0);
                ihdr.writeByte(0);
            }
            writeChunk(data, "IHDR", ihdrData.toByteArray());
            writeChunk(data, "IEND", new byte[0]);
        }
        return output.toByteArray();
    }

    private static void writeChunk(DataOutputStream output, String type, byte[] bytes) throws Exception {
        byte[] typeBytes = type.getBytes(StandardCharsets.US_ASCII);
        output.writeInt(bytes.length);
        output.write(typeBytes);
        output.write(bytes);
        CRC32 crc = new CRC32();
        crc.update(typeBytes);
        crc.update(bytes);
        output.writeInt((int) crc.getValue());
    }

    private static void assertApiError(Runnable action, int status, String code) {
        assertThatThrownBy(action::run)
                .isInstanceOfSatisfying(ApiException.class, exception -> {
                    assertThat(exception.status()).isEqualTo(status);
                    assertThat(exception.code()).isEqualTo(code);
                });
    }
}
