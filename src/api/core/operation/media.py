# import os
# import time
# from src.api.core.response import api_response
# from PIL import Image, UnidentifiedImageError, ImageOps

# BASE_DIR = "/var/www"
# SUB_DIR = "media"
# MEDIA_DIR = os.path.join(BASE_DIR, SUB_DIR)

# ALLOWED_RAW_EXT = [".webp", ".avif", ".ico", ".svg"]
# MAX_SIZE = 2 * 1024 * 1024  # 1 MB
# THUMBNAIL_SIZE = (300, 300)  # max width/height
# MAX_SIZE_MB = MAX_SIZE / (1024 * 1024)


# async def uploadImage(files, thumbnail, unique=True):
#     saved_files = []

#     for file in files:
#         ext = os.path.splitext(file.filename)[1].lower()

#         # Base filename without extension
#         base_name = os.path.splitext(file.filename)[0]

#         # Generate unique suffix
#         timestamp = str(int(time.time() * 1000))  # milliseconds

#         # Apply unique name
#         if unique:
#             base_name = f"{base_name}-{timestamp}"

#         # Default file path
#         file_path = os.path.join(MEDIA_DIR, base_name + ext)

#         # RAW image handling
#         if ext in ALLOWED_RAW_EXT:
#             with open(file_path, "wb") as buffer:
#                 buffer.write(await file.read())
#         else:
#             try:
#                 img = Image.open(file.file)
#                 icc_profile = img.info.get("icc_profile")

#                 img = ImageOps.exif_transpose(img)

#                 # Convert to webp with unique naming
#                 output_filename = base_name + ".webp"
#                 file_path = os.path.join(MEDIA_DIR, output_filename)

#                 img.save(
#                     file_path,
#                     "webp",
#                     quality=95,
#                     method=6,
#                     icc_profile=icc_profile,
#                     lossless=False,
#                 )
#                 ext = ".webp"

#             except UnidentifiedImageError:
#                 raise api_response(
#                     400,
#                     f"File type {ext} is not a supported image format.",
#                 )

#         # Validate file size
#         size_bytes = os.path.getsize(file_path)
#         if size_bytes > MAX_SIZE:
#             os.remove(file_path)
#             size_mb = round(size_bytes / (1024 * 1024), 2)
#             return api_response(
#                 400,
#                 f"{file.filename} is still larger than {MAX_SIZE_MB} MB after optimization ({size_mb} MB)",
#             )

#         # File info response
#         file_info = {
#             "filename": os.path.basename(file_path),
#             "extension": ext,
#             "original": f"/media/{os.path.basename(file_path)}",
#             "size_mb": round(size_bytes / (1024 * 1024), 2),
#         }

#         # Thumbnail creation
#         if thumbnail and ext in [".jpg", ".jpeg", ".png", ".webp"]:
#             thumb_name = base_name + "_thumb.webp"
#             thumb_path = os.path.join(MEDIA_DIR, thumb_name)

#             with Image.open(file_path) as thumb:
#                 thumb.thumbnail(THUMBNAIL_SIZE)
#                 thumb.save(
#                     thumb_path,
#                     "webp",
#                     quality=85,
#                     method=6,
#                 )

#             file_info["thumbnail"] = f"/media/{thumb_name}"

#         saved_files.append(file_info)

#     return saved_files
