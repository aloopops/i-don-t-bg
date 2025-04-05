import os
import io
import logging
import uuid
import tempfile
import shutil
from flask import Flask, render_template, request, jsonify, send_file
from gradio_client import Client, handle_file
from PIL import Image
import os
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from werkzeug.serving import run_simple

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default-secret-key")

# Add these lines to ensure static files are served correctly
app.static_folder = 'static'
app.static_url_path = '/static'

# Create temp directory for storing uploaded and processed images
UPLOAD_FOLDER = os.path.join(tempfile.gettempdir(), 'bg_remover_uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Set allowed extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
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
		api_name="/predict",
)
            print(result)
            logger.debug(f"API returned: {result}")
            
            # If result is a URL or file path
            if isinstance(result, str):
                # If it's a URL (not a local file), make it available to the frontend
                if not os.path.exists(result) and (result.startswith('http://') or result.startswith('https://')):
                    # Return the direct URL from the API
                    return jsonify({
                        'original': f"/get_image/{filename}_input.jpg",
                        'processed': result,  # Direct URL from the API
                        'download': result,   # Use the same URL for download
                        
                    })
                else:
                    # It's a local file path, copy it to our output_path
                    if os.path.exists(result):
                        shutil.copy(result, output_path)
                    else:
                        # If file doesn't exist (unexpected), log error
                        logger.error(f"API returned file path that doesn't exist: {result}")
                        return jsonify({'error': "API returned invalid file path"}), 500
            else:
                # Handle case where result is binary data or another format
                logger.debug(f"API result is not a string, type: {type(result)}")
                
                # If it's binary data, save it directly
                with open(output_path, 'wb') as f:
                    if isinstance(result, bytes):
                        f.write(result)
                    else:
                        # Try to convert to bytes if possible
                        try:
                            f.write(bytes(result))
                        except:
                            return jsonify({'error': "API returned unsupported format"}), 500
            
            logger.debug(f"Image processed successfully and saved to {output_path}")
            
            # Return the paths for the frontend to use
            return jsonify({
                'original': f"/get_image/{filename}_input.jpg",
                'processed': f"/get_image/{filename}_output.png",
                'download': f"/download/{filename}_output.png",
                'api_url': result if isinstance(result, str) else None  # Include API URL if available
            })
        except Exception as e:
            logger.exception(f"Error during local image processing: {str(e)}")
            return jsonify({'error': f"Image processing failed: {str(e)}"}), 500
            
    except Exception as e:
        logger.exception("Error processing image")
        return jsonify({'error': str(e)}), 500

@app.route('/get_image/<filename>')
def get_image(filename):
    """Serve the image files"""
    return send_file(os.path.join(UPLOAD_FOLDER, filename))

@app.route('/download/<filename>')
def download_file(filename):
    """Download the processed image"""
    return send_file(
        os.path.join(UPLOAD_FOLDER, filename),
        as_attachment=True,
        download_name=f"removed_bg_{filename}"
    )

# app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {
#     '/static': app.static_folder
# })

if __name__ == "__main__":
    # For local development
    app.run(host="0.0.0.0", port=5000, debug=True)
else:
    # For Vercel deployment
    app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {
        '/static': {
            'target': app.static_folder,
            'path': '/static'
        }
    })
