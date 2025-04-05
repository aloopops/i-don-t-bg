import os
import io
import logging
import uuid
import tempfile
import shutil
import atexit
from flask import Flask, render_template, request, jsonify, send_file
from gradio_client import Client, handle_file
from PIL import Image
from werkzeug.middleware.dispatcher import DispatcherMiddleware

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default-secret-key")

# Configure static files
app.static_folder = 'static'
app.static_url_path = '/static'

# Determine environment
IS_VERCEL = os.environ.get('VERCEL') == '1'

# Configure upload folder - declare as global first
global UPLOAD_FOLDER
if IS_VERCEL:
    UPLOAD_FOLDER = '/tmp/bg_remover_uploads'
else:
    UPLOAD_FOLDER = os.path.join(tempfile.gettempdir(), 'bg_remover_uploads')

# Set allowed extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def create_upload_folder():
    """Create upload directory if it doesn't exist"""
    global UPLOAD_FOLDER  # Declare as global here too
    try:
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        logger.info(f"Upload directory created at: {UPLOAD_FOLDER}")
    except Exception as e:
        logger.error(f"Error creating upload directory: {e}")
        # Fallback to a temporary directory
        UPLOAD_FOLDER = tempfile.mkdtemp()
        logger.info(f"Using fallback directory: {UPLOAD_FOLDER}")

def cleanup():
    """Clean up upload directory on exit"""
    try:
        if os.path.exists(UPLOAD_FOLDER):
            shutil.rmtree(UPLOAD_FOLDER)
            logger.info(f"Cleaned up upload directory: {UPLOAD_FOLDER}")
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")

# Initialize upload directory and cleanup
create_upload_folder()
atexit.register(cleanup)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        # Validate request
        if request.content_type is None or 'multipart/form-data' not in request.content_type:
            return jsonify({'error': 'Invalid content type. Expected multipart/form-data'}), 400
            
        if 'image' not in request.files:
            return jsonify({'error': 'No file part'}), 400
        
        file = request.files['image']
        
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': f'File type not allowed. Please upload {", ".join(ALLOWED_EXTENSIONS)}'}), 400
    except Exception as e:
        logger.exception("Error in file upload validation")
        return jsonify({'error': f'Upload error: {str(e)}'}), 400
    
    try:
        # Generate unique filenames
        filename = str(uuid.uuid4())
        input_path = os.path.join(UPLOAD_FOLDER, f"{filename}_input.jpg")
        output_path = os.path.join(UPLOAD_FOLDER, f"{filename}_output.png")
        
        # Save uploaded file
        file.save(input_path)
        
        # Process the image using RMBG-Image-Background-Remover API
        try:
            logger.debug(f"Submitting job to remove background from {input_path}")
            client = Client("abdullahalioo/remove_background")
            result = client.predict(
                image=handle_file(input_path),
                api_name="/predict"
            )
            logger.debug(f"API returned: {result}")
            
            # If result is a URL or file path
            if isinstance(result, str):
                # If it's a URL (not a local file), make it available to the frontend
                if not os.path.exists(result) and (result.startswith('http://') or result.startswith('https://')):
                    return jsonify({
                        'original': f"/get_image/{filename}_input.jpg",
                        'processed': result,
                        'download': result,
                    })
                else:
                    # It's a local file path, copy it to our output_path
                    if os.path.exists(result):
                        shutil.copy(result, output_path)
                    else:
                        logger.error(f"API returned file path that doesn't exist: {result}")
                        return jsonify({'error': "API returned invalid file path"}), 500
            else:
                # Handle binary data
                logger.debug(f"API result is not a string, type: {type(result)}")
                with open(output_path, 'wb') as f:
                    if isinstance(result, bytes):
                        f.write(result)
                    else:
                        try:
                            f.write(bytes(result))
                        except:
                            return jsonify({'error': "API returned unsupported format"}), 500
            
            logger.debug(f"Image processed successfully and saved to {output_path}")
            
            return jsonify({
                'original': f"/get_image/{filename}_input.jpg",
                'processed': f"/get_image/{filename}_output.png",
                'download': f"/download/{filename}_output.png",
                'api_url': result if isinstance(result, str) else None
            })
        except Exception as e:
            logger.exception(f"Error during image processing: {str(e)}")
            return jsonify({'error': f"Image processing failed: {str(e)}"}), 500
            
    except Exception as e:
        logger.exception("Error processing image")
        return jsonify({'error': str(e)}), 500

@app.route('/get_image/<filename>')
def get_image(filename):
    """Serve the image files"""
    try:
        return send_file(os.path.join(UPLOAD_FOLDER, filename))
    except FileNotFoundError:
        return jsonify({'error': 'File not found'}), 404

@app.route('/download/<filename>')
def download_file(filename):
    """Download the processed image"""
    try:
        return send_file(
            os.path.join(UPLOAD_FOLDER, filename),
            as_attachment=True,
            download_name=f"removed_bg_{filename}"
        )
    except FileNotFoundError:
        return jsonify({'error': 'File not found'}), 404

# Configure WSGI middleware for Vercel


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
