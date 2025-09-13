from fastapi import APIRouter, Query, UploadFile, File, Form
from fastapi.responses import FileResponse, JSONResponse
from starlette.background import BackgroundTask
import qrcode, hashlib, os, uuid, base64
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers import RoundedModuleDrawer, SquareModuleDrawer, CircleModuleDrawer
from qrcode.image.styles.colormasks import RadialGradiantColorMask, SquareGradiantColorMask
from PIL import Image
from io import BytesIO

router = APIRouter()

@router.get("/generate")
async def generate_qr(link: str = Query(...)):
    filename = hashlib.md5(link.encode()).hexdigest() + ".png"
    qrcode.make(link).save(filename)
    return FileResponse(
        filename,
        media_type="image/png",
        filename="qrcode.png",
        background=BackgroundTask(os.remove, filename)
    )

@router.post("/generate_advanced")
async def generate_qr_advanced(
    text: str = Form(...),
    size: int = Form(10),
    border: int = Form(1),
    fill_color: str = Form("black"),
    back_color: str = Form("white"),
    style: str = Form("square"),
    gradient: str = Form("none"),
    logo: UploadFile = File(None)
):
    filename = f"qr_{hashlib.md5(text.encode()).hexdigest()}.png"
    logo_path = None

    try:
        # Handle logo upload
        if logo and logo.filename:
            logo_ext = os.path.splitext(logo.filename)[1].lower()
            if logo_ext not in ['.png', '.jpg', '.jpeg']:
                return JSONResponse({"error": "Logo must be PNG or JPG"}, status_code=400)
            logo_path = f"temp_logo_{uuid.uuid4().hex}{logo_ext}"
            with open(logo_path, "wb") as buffer:
                buffer.write(await logo.read())
            with Image.open(logo_path) as img:
                img.thumbnail((100, 100))
                img.save(logo_path)

        # Create QR
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=size,
            border=border,
        )
        qr.add_data(text)
        qr.make(fit=True)

        # Drawer style
        if style == "rounded":
            module_drawer = RoundedModuleDrawer()
        elif style == "circle":
            module_drawer = CircleModuleDrawer()
        else:
            module_drawer = SquareModuleDrawer()

        # Gradient
        color_mask = None
        if gradient == "radial":
            color_mask = RadialGradiantColorMask(back_color=back_color, center_color=fill_color, edge_color=fill_color)
        elif gradient == "square":
            color_mask = SquareGradiantColorMask(back_color=back_color, center_color=fill_color, edge_color=fill_color)

        # Build image
        make_image_args = {"image_factory": StyledPilImage, "module_drawer": module_drawer}
        if color_mask:
            make_image_args["color_mask"] = color_mask
        if logo_path:
            make_image_args["embeded_image_path"] = logo_path

        img = qr.make_image(**make_image_args)
        img.save(filename)

        buffered = BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()

        return {"image_url": f"/qr/download/{filename}", "image_base64": img_str, "filename": filename}

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
    finally:
        if logo_path and os.path.exists(logo_path):
            os.remove(logo_path)

@router.get("/download/{filename}")
async def download_qr(filename: str):
    if not os.path.exists(filename):
        return JSONResponse({"error": "File not found"}, status_code=404)
    return FileResponse(
        filename,
        media_type="image/png",
        filename="custom_qrcode.png",
        background=BackgroundTask(lambda: os.remove(filename) if os.path.exists(filename) else None)
    )
