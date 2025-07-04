import os
from typing import Tuple, Optional
from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app
from flask_login import login_required
from werkzeug.utils import secure_filename
import uuid

from .parsing import parse_packing_list
from .price_validation import validate_prices, enrich_with_prices
from .models import ProcessingResult

upload_bp = Blueprint("upload", __name__)

def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed"""
    if not filename or "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in current_app.config["ALLOWED_EXTENSIONS"]

def save_uploaded_file(file) -> Tuple[bool, Optional[str]]:
    """Save uploaded file, return (success flag, file path)"""
    if not file or not file.filename:
        return False, None
    
    if not allowed_file(file.filename):
        flash("Only supports the following formats: " + ", ".join(current_app.config["ALLOWED_EXTENSIONS"]))
        return False, None

    # Generate secure filename
    filename = secure_filename(file.filename)
    unique_filename = f"{uuid.uuid4()}_{filename}"
    
    # Ensure upload directory exists
    os.makedirs(current_app.config["UPLOAD_FOLDER"], exist_ok=True)
    
    # Save file
    filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], unique_filename)
    try:
        file.save(filepath)
        return True, filepath
    except Exception as e:
        current_app.logger.error(f"File save failed: {str(e)}")
        return False, None

@upload_bp.route("/", methods=["GET", "POST"])
@login_required
def upload():
    """Handle packing list file upload request"""
    if request.method == "POST":
        if "file" not in request.files:
            flash("No file selected")
            return redirect(request.url)
        
        file = request.files["file"]
        success, filepath = save_uploaded_file(file)
        
        if not success:
            return redirect(request.url)
        
        # Type guard to ensure filepath is not None
        if filepath is None:
            flash("File upload failed")
            return redirect(request.url)
        
        try:
            # Parse packing list file
            current_app.logger.info(f"Parsing file: {file.filename}")
            rows = parse_packing_list(filepath)
            
            if not rows:
                flash("No valid items found in the file")
                return redirect(request.url)
            
            # Enrich with prices from backend price list
            enriched_rows = enrich_with_prices(rows)
            
            # Price validation (optional, mainly for reporting)
            validation_errors = validate_prices(enriched_rows)
            
            # Generate result
            result = ProcessingResult(rows=enriched_rows, validation_errors=validation_errors)
            
            current_app.logger.info(f"Successfully processed {len(enriched_rows)} items")
            
            return render_template(
                "result.html",
                result=result.to_dict(),
                filename=file.filename
            )
            
        except Exception as e:
            current_app.logger.error(f"Processing failed: {str(e)}")
            flash(f"File processing failed: {str(e)}")
            return redirect(request.url)
        finally:
            # Always try to clean up temporary file with retry logic for Windows file locking
            try:
                if os.path.exists(filepath):
                    # Force garbage collection to release file handles
                    import gc
                    gc.collect()
                    
                    # Retry deletion with a small delay
                    import time
                    for attempt in range(3):
                        try:
                            os.remove(filepath)
                            break
                        except PermissionError:
                            if attempt < 2:  # Not the last attempt
                                time.sleep(0.5)  # Wait 500ms before retry
                                gc.collect()  # Force garbage collection again
                            else:
                                current_app.logger.warning(f"Could not delete temporary file: {filepath}")
            except Exception as cleanup_error:
                current_app.logger.error(f"Error during file cleanup: {str(cleanup_error)}")
    
    return render_template("upload.html")
