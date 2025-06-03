import cv2
import numpy as np

def show_qr_window(qr_image_bytes):
    """
    Shows a QR code window with proper sizing and settings.
    Now works with Playwright's screenshot bytes format.
    """
    # Convert Playwright's screenshot bytes to OpenCV image
    nparr = np.frombuffer(qr_image_bytes, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    window_name = "Scan WhatsApp QR Code"
    # Create window with proper settings
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.imshow(window_name, image)
    cv2.setWindowProperty(window_name, cv2.WND_PROP_TOPMOST, 1)
    
    # Resize window for better visibility
    if image is not None:
        height, width = image.shape[:2]
        target_size = 500
        aspect_ratio = width / height
        new_width = int(target_size * aspect_ratio)
        cv2.resizeWindow(window_name, new_width, target_size)
    
    # Display window until key press or timeout
    cv2.waitKey(1)  # This will show the window and return immediately

def close_all_windows():
    """
    Ensures all OpenCV windows are closed
    """
    cv2.destroyAllWindows()
    # Sometimes windows don't close properly on Windows, so we need to call waitKey
    cv2.waitKey(1)
