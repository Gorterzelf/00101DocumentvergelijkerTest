# utils.py - Utility functions for document analysis
import os
import time
import logging
from typing import Optional, List, Dict
from werkzeug.datastructures import FileStorage

logger = logging.getLogger(__name__)

# File type configuration
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_upload_request(request) -> Optional[str]:
    """Validate legacy upload request (for backwards compatibility)."""
    if 'file1' not in request.files or 'file2' not in request.files:
        return 'Selecteer beide documenten!'
    
    file1 = request.files['file1']
    file2 = request.files['file2']
    
    if file1.filename == '' or file2.filename == '':
        return 'Beide bestanden moeten geselecteerd zijn!'
    
    if not (allowed_file(file1.filename) and allowed_file(file2.filename)):
        return f'Alleen {", ".join(ALLOWED_EXTENSIONS)} bestanden zijn toegestaan!'
    
    return None

def validate_multiple_upload_request(request, mode: str) -> Optional[str]:
    """Validate multiple document upload request based on mode."""
    required_docs = get_required_docs_for_mode(mode)
    
    if not required_docs:
        return f'Onbekende analyse mode: {mode}'
    
    # Check if all required documents are present
    for doc_key in required_docs:
        if doc_key not in request.files:
            return f'Document {doc_key} ontbreekt!'
        
        file_obj = request.files[doc_key]
        if not file_obj or file_obj.filename == '':
            return f'Document {doc_key} moet geselecteerd zijn!'
        
        if not allowed_file(file_obj.filename):
            return f'Document {doc_key}: alleen {", ".join(ALLOWED_EXTENSIONS)} bestanden zijn toegestaan!'
    
    return None

def get_required_docs_for_mode(mode: str) -> List[str]:
    """Get list of required document keys for each analysis mode."""
    mode_requirements = {
        'version_comparison': ['doc1', 'doc2'],
        'actiz_position': ['doc1', 'doc2'],
        'external_reaction': ['doc1', 'doc2'],
        'strategic_communication': ['doc1', 'doc2', 'doc3']
    }
    return mode_requirements.get(mode, [])

def get_mode_display_name(mode: str) -> str:
    """Get human-readable display name for analysis mode."""
    display_names = {
        'version_comparison': 'Versie Vergelijking',
        'actiz_position': 'ActiZ Positie Analyse',
        'external_reaction': 'Externe Reactie Analyse',
        'strategic_communication': 'Strategische Communicatie'
    }
    return display_names.get(mode, mode.replace('_', ' ').title())

def get_mode_description(mode: str) -> str:
    """Get detailed description for analysis mode."""
    descriptions = {
        'version_comparison': 'Vergelijk twee versies van hetzelfde document en identificeer alle wijzigingen met gedetailleerde AI-analyse.',
        'actiz_position': 'Analyseer een extern document tegen ActiZ standpunten en identificeer beleidsmatige implicaties.',
        'external_reaction': 'Vergelijk een beleidsdocument met externe reacties en identificeer kritiekpunten en kansen.',
        'strategic_communication': 'Analyseer drie documenten voor strategische communicatie-inzichten en beleidsalignment.'
    }
    return descriptions.get(mode, 'Onbekende analyse mode.')

def get_mode_requirements(mode: str) -> Dict[str, str]:
    """Get detailed requirements and labels for each document in a mode."""
    requirements = {
        'version_comparison': {
            'doc1': 'Origineel Document',
            'doc2': 'Nieuwe Versie'
        },
        'actiz_position': {
            'doc1': 'Extern Document',
            'doc2': 'ActiZ Positiedocument'
        },
        'external_reaction': {
            'doc1': 'Beleidsdocument', 
            'doc2': 'Externe Reactie'
        },
        'strategic_communication': {
            'doc1': 'Beleidsdocument',
            'doc2': 'Communicatiestuk',
            'doc3': 'Context Document'
        }
    }
    return requirements.get(mode, {})

def cleanup_old_files(*directories, max_age_hours: int = 24):
    """Clean up old files in specified directories."""
    max_age_seconds = max_age_hours * 3600
    current_time = time.time()
    
    total_removed = 0
    
    for directory in directories:
        if not os.path.exists(directory):
            continue
            
        try:
            for filename in os.listdir(directory):
                filepath = os.path.join(directory, filename)
                
                if os.path.isfile(filepath):
                    file_age = current_time - os.path.getmtime(filepath)
                    
                    if file_age > max_age_seconds:
                        try:
                            os.remove(filepath)
                            logger.info(f"Removed old file: {filepath}")
                            total_removed += 1
                        except Exception as e:
                            logger.error(f"Failed to remove {filepath}: {e}")
                            
        except Exception as e:
            logger.error(f"Error cleaning directory {directory}: {e}")
    
    if total_removed > 0:
        logger.info(f"Cleanup completed: {total_removed} files removed")

def validate_file_size(file_obj: FileStorage) -> bool:
    """Validate file size is within limits."""
    try:
        file_obj.seek(0, 2)  # Seek to end
        size = file_obj.tell()
        file_obj.seek(0)  # Reset to beginning
        return size <= MAX_FILE_SIZE
    except Exception as e:
        logger.error(f"Error checking file size: {e}")
        return False

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe storage."""
    # Remove or replace problematic characters
    import re
    # Keep only alphanumeric, dots, hyphens, and underscores
    sanitized = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
    # Prevent double extensions and long names
    if len(sanitized) > 255:
        name, ext = os.path.splitext(sanitized)
        sanitized = name[:250] + ext
    return sanitized

def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"

def get_file_info(filepath: str) -> Dict[str, any]:
    """Get comprehensive file information."""
    try:
        stat = os.stat(filepath)
        return {
            'filename': os.path.basename(filepath),
            'size_bytes': stat.st_size,
            'size_formatted': format_file_size(stat.st_size),
            'modified_time': stat.st_mtime,
            'extension': os.path.splitext(filepath)[1].lower(),
            'exists': True
        }
    except Exception as e:
        logger.error(f"Error getting file info for {filepath}: {e}")
        return {
            'filename': os.path.basename(filepath) if filepath else 'Unknown',
            'size_bytes': 0,
            'size_formatted': '0 B',
            'modified_time': 0,
            'extension': '',
            'exists': False,
            'error': str(e)
        }

def log_analysis_start(mode: str, comparison_id: str, filenames: Dict[str, str]):
    """Log the start of an analysis session."""
    logger.info(f"=== ANALYSIS START ===")
    logger.info(f"Mode: {mode} ({get_mode_display_name(mode)})")
    logger.info(f"Comparison ID: {comparison_id}")
    logger.info(f"Files: {', '.join(f'{k}={v}' for k, v in filenames.items())}")

def log_analysis_complete(mode: str, comparison_id: str, success: bool, stats: Dict = None):
    """Log the completion of an analysis session."""
    status = "SUCCESS" if success else "FAILED"
    logger.info(f"=== ANALYSIS {status} ===")
    logger.info(f"Mode: {mode}")
    logger.info(f"Comparison ID: {comparison_id}")
    if stats:
        logger.info(f"Stats: {stats}")

def create_error_response(error_message: str, comparison_id: str = None) -> Dict[str, any]:
    """Create standardized error response."""
    return {
        'error': error_message,
        'comparison_id': comparison_id,
        'basic_comparison': None,
        'ai_analysis': None,
        'stats': {
            'error': True,
            'message': error_message
        }
    }

def get_analysis_summary(results: Dict[str, any]) -> str:
    """Generate a brief summary of analysis results."""
    try:
        mode = results.get('mode', 'unknown')
        mode_name = get_mode_display_name(mode)
        
        if results.get('error'):
            return f"{mode_name}: Fout - {results['error']}"
        
        stats = results.get('stats', {})
        
        if mode == 'version_comparison':
            diff_count = stats.get('differences_count', 0)
            return f"{mode_name}: {diff_count} wijzigingen gevonden"
        
        elif mode == 'actiz_position':
            alignment_score = stats.get('alignment_score', 0)
            return f"{mode_name}: {alignment_score}% afstemming"
        
        elif mode == 'external_reaction':
            sentiment = stats.get('reaction_sentiment', 'neutraal')
            return f"{mode_name}: {sentiment} reactie"
        
        elif mode == 'strategic_communication':
            themes = stats.get('strategic_themes', 0)
            return f"{mode_name}: {themes} strategische thema's"
        
        else:
            return f"{mode_name}: Analyse voltooid"
            
    except Exception as e:
        logger.error(f"Error generating analysis summary: {e}")
        return "Analyse voltooid"

# Configuration helpers
def get_upload_config() -> Dict[str, any]:
    """Get upload configuration settings."""
    return {
        'allowed_extensions': list(ALLOWED_EXTENSIONS),
        'max_file_size': MAX_FILE_SIZE,
        'max_file_size_formatted': format_file_size(MAX_FILE_SIZE),
        'supported_modes': list(get_required_docs_for_mode(mode) for mode in [
            'version_comparison', 'actiz_position', 'external_reaction', 'strategic_communication'
        ])
    }

def is_development_mode() -> bool:
    """Check if running in development mode."""
    return os.getenv('FLASK_ENV') == 'development' or os.getenv('DEBUG', '').lower() in ['true', '1', 'yes']

def get_app_version() -> str:
    """Get application version string."""
    return os.getenv('APP_VERSION', '2.0.0-multi')

# Error handling helpers
class DocumentProcessingError(Exception):
    """Custom exception for document processing errors."""
    def __init__(self, message: str, error_type: str = 'processing'):
        self.message = message
        self.error_type = error_type
        super().__init__(self.message)

class FileValidationError(Exception):
    """Custom exception for file validation errors."""
    def __init__(self, message: str, filename: str = None):
        self.message = message
        self.filename = filename
        super().__init__(self.message)

def handle_processing_error(e: Exception, context: str = "") -> Dict[str, any]:
    """Handle and format processing errors."""
    error_msg = f"{context}: {str(e)}" if context else str(e)
    logger.error(f"Processing error - {error_msg}")
    
    return create_error_response(
        error_message=f"Verwerkingsfout: {error_msg}",
        comparison_id=None
    )