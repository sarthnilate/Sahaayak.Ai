import io
from typing import Tuple

from backend.app.core.config import settings
from backend.app.core.errors import BadRequestError
from PIL import Image, ImageOps

# Prevent decompression bomb attacks
MAX_IMAGE_DIMENSION = 4096
MAX_TOTAL_PIXELS = 16_000_000  # 16 Megapixels
Image.MAX_IMAGE_PIXELS = MAX_TOTAL_PIXELS

ALLOWED_FORMAT_MAPPING = {
    "JPEG": ("jpg", "image/jpeg"),
    "PNG": ("png", "image/png"),
    "WEBP": ("webp", "image/webp"),
}


def sanitize_and_reencode_image(
    raw_bytes: bytes, max_size_mb: int = settings.MAX_UPLOAD_MB
) -> Tuple[bytes, str, str]:
    """
    Validates and sanitizes uploaded image:
    1. Enforces byte-size limit
    2. Validates magic bytes using Pillow (does not trust filename or client MIME)
    3. Guards against decompression bombs via dimension and total pixel checks
    4. Re-encodes the image into a clean buffer, stripping all EXIF, GPS, and metadata

    Returns:
        (sanitized_bytes, extension, mime_type)
    """
    max_bytes = max_size_mb * 1024 * 1024
    if len(raw_bytes) > max_bytes:
        raise BadRequestError(
            message=f"File exceeds maximum upload size of {max_size_mb} MB",
            error_code="PAYLOAD_TOO_LARGE",
        )

    if not raw_bytes:
        raise BadRequestError(message="Uploaded file is empty", error_code="INVALID_EMPTY_FILE")

    try:
        # Open image from raw bytes to check magic headers
        with Image.open(io.BytesIO(raw_bytes)) as img:
            image_format = (img.format or "").upper()
            if image_format not in ALLOWED_FORMAT_MAPPING:
                raise BadRequestError(
                    message=f"Disallowed image format '{image_format}'. Allowed: JPEG, PNG, WebP",
                    error_code="INVALID_IMAGE_FORMAT",
                )

            # Decompression bomb guard
            width, height = img.size
            if width > MAX_IMAGE_DIMENSION or height > MAX_IMAGE_DIMENSION:
                raise BadRequestError(
                    message=f"Image dimensions ({width}x{height}) exceed maximum allowed {MAX_IMAGE_DIMENSION}px",
                    error_code="IMAGE_DIMENSIONS_EXCEEDED",
                )

            if width * height > MAX_TOTAL_PIXELS:
                raise BadRequestError(
                    message=f"Total pixel count exceeds safety threshold of {MAX_TOTAL_PIXELS}",
                    error_code="DECOMPRESSION_BOMB_PREVENTED",
                )

            # Correct orientation if EXIF orientation is present before stripping
            try:
                img = ImageOps.exif_transpose(img)
            except Exception:
                pass

            ext, mime_type = ALLOWED_FORMAT_MAPPING[image_format]

            # Re-encode to clean in-memory buffer without metadata/EXIF
            output_buffer = io.BytesIO()

            if image_format == "JPEG":
                # Convert RGBA to RGB for JPEG
                clean_img = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
                    clean_img.paste(img, mask=img.convert("RGBA").split()[3])
                else:
                    clean_img.paste(img.convert("RGB"))
                clean_img.save(output_buffer, format="JPEG", quality=85, optimize=True)
            elif image_format == "PNG":
                clean_img = img.convert("RGBA" if "A" in img.mode else "RGB")
                clean_img.save(output_buffer, format="PNG", optimize=True)
            elif image_format == "WEBP":
                clean_img = img.convert("RGBA" if "A" in img.mode else "RGB")
                clean_img.save(output_buffer, format="WEBP", quality=85)
            else:
                raise BadRequestError(
                    message="Unsupported format encoding", error_code="UNSUPPORTED_ENCODING"
                )

            output_bytes = output_buffer.getvalue()
            return output_bytes, ext, mime_type

    except BadRequestError:
        raise
    except Exception as e:
        raise BadRequestError(
            message=f"Failed to process or corrupted image file: {str(e)}",
            error_code="CORRUPTED_IMAGE",
        )
