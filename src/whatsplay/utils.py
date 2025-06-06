import platform
import subprocess
import tempfile
import os

def show_qr_window(qr_image_bytes):
    """
    Muestra un QR en la terminal usando 'chafa' o 'catimg'.
    Funciona en servidores sin GUI.
    """
    # Guardar imagen temporal desde los bytes
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
        temp_file.write(qr_image_bytes)
        temp_file_path = temp_file.name

    try:
        subprocess.run(["chafa", temp_file_path])
    finally:
        os.remove(temp_file_path)


def copy_file_to_clipboard(filepath):
    system = platform.system()
    
    if system == "Windows":
        # En Windows usamos PowerShell Set-Clipboard -LiteralPath
        command = ['powershell', 'Set-Clipboard', '-LiteralPath', filepath]
        try:
            subprocess.run(command, check=True)
            print("Archivo copiado al portapapeles en Windows.")
        except subprocess.CalledProcessError:
            print("Error copiando archivo al portapapeles en Windows.")
    
    elif system == "Linux":
        # En Linux no hay un portapapeles nativo para archivos como en Windows,
        # pero podemos copiar la ruta como texto al portapapeles (ejemplo con xclip)
        try:
            # Asegúrate de tener xclip instalado: sudo apt install xclip
            subprocess.run(['xclip', '-selection', 'clipboard'], input=filepath.encode(), check=True)
            print("Ruta del archivo copiada al portapapeles en Linux (como texto).")
        except FileNotFoundError:
            print("xclip no está instalado. Instálalo para copiar al portapapeles.")
        except subprocess.CalledProcessError:
            print("Error copiando ruta al portapapeles en Linux.")
    
    else:
        print(f"Sistema operativo '{system}' no soportado para copiar archivos al portapapeles.")