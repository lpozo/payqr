import qrcode
from PIL import Image


class QRCodeGenerator:
    def __init__(
        self,
        box_size: int = 10,
        border: int = 4,
        error_correction: str = "L",
        fixed_size: tuple[int, int] | None = None,
    ):
        self.box_size = box_size
        self.border = border
        self.error_correction = error_correction
        self.fixed_size = fixed_size  # (width, height) or None

    def _ec_level(self):
        mapping = {
            "L": qrcode.constants.ERROR_CORRECT_L,
            "M": qrcode.constants.ERROR_CORRECT_M,
            "Q": qrcode.constants.ERROR_CORRECT_Q,
            "H": qrcode.constants.ERROR_CORRECT_H,
        }
        return mapping.get(
            self.error_correction.upper(), qrcode.constants.ERROR_CORRECT_L
        )

    def generate_qr_image(self, data: str) -> Image.Image:
        qr = qrcode.QRCode(
            version=None,
            error_correction=self._ec_level(),
            box_size=self.box_size,
            border=self.border,
        )
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        # qrcode returns a PilImage wrapper; get actual PIL Image
        pil_img = img.get_image() if hasattr(img, "get_image") else img

        # Resize to fixed size if specified
        if self.fixed_size:
            pil_img = pil_img.resize(self.fixed_size, Image.Resampling.LANCZOS)

        return pil_img

    def generate_and_save(self, data: str, output_path: str) -> str:
        img = self.generate_qr_image(data)
        img.save(output_path)
        return output_path
