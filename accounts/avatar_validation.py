
from django import forms
from PIL import Image, UnidentifiedImageError


def validate_avatar(file):
    if not file:
        return

    if file.size > 3 * 1024 * 1024:
        raise forms.ValidationError("Максимальный размер фотографии — 3 МБ.")

    try:
        image = Image.open(file)
        if image.format not in ("JPEG", "PNG", "WEBP"):
            raise forms.ValidationError("Используй JPG, PNG или WebP.")
        image.verify()
    except (UnidentifiedImageError, OSError, ValueError):
        raise forms.ValidationError("Не удалось прочитать изображение.")
    finally:
        file.seek(0)
