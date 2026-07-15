import qrcode
import io
import base64

def generate_qr_code_base64(url):
    try:
        # Create QR code structure
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(url)
        qr.make(fit=True)

        # Draw the image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Save to buffer
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        
        # Encode to base64
        img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
        return f"data:image/png;base64,{img_str}"
    except Exception as e:
        # Handle exceptions gracefully
        print(f"Error generating QR code: {e}")
        return None
