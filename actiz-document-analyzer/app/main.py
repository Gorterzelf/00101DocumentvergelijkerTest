from flask import Blueprint, render_template, request, jsonify, flash
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Blueprint voor route organizatie
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """
    Hoofdpagina - toont upload interface
    """
    logger.info("Index page accessed")
    return render_template('index.html')

@main_bp.route('/compare', methods=['POST'])
def compare_documents():
    """
    Vergelijk twee documenten - nieuwe hoofdfunctionaliteit
    """
    try:
        # Validate beide bestanden aanwezig zijn
        if 'file1' not in request.files or 'file2' not in request.files:
            return jsonify({'error': 'Beide documenten zijn vereist'}), 400
        
        file1 = request.files['file1']
        file2 = request.files['file2']
        
        if file1.filename == '' or file2.filename == '':
            return jsonify({'error': 'Beide documenten moeten geselecteerd zijn'}), 400
        
        # Validatie file extensions
        allowed_extensions = {'pdf', 'docx', 'txt'}
        
        file1_ext = file1.filename.rsplit('.', 1)[1].lower()
        file2_ext = file2.filename.rsplit('.', 1)[1].lower()
        
        if file1_ext not in allowed_extensions or file2_ext not in allowed_extensions:
            return jsonify({'error': 'Bestandstype niet toegestaan. Gebruik PDF, DOCX of TXT'}), 400
        
        logger.info(f"Comparing documents: {file1.filename} vs {file2.filename}")
        
        # Import services
        from app.services.document_service import DocumentProcessor
        from app.services.azure_openai_service import AzureOpenAIService
        
        # Process beide documenten
        doc_processor = DocumentProcessor()
        
        # Extract text from both documents
        text1 = doc_processor.extract_text(file1.stream, file1.filename)
        text2 = doc_processor.extract_text(file2.stream, file2.filename)
        
        logger.info(f"Document 1: {len(text1)} chars, Document 2: {len(text2)} chars")
        
        # Analyze with Azure OpenAI
        ai_service = AzureOpenAIService()
        comparison_result = ai_service.compare_documents(text1, text2, file1.filename, file2.filename)
        
        logger.info(f"Comparison completed: {file1.filename} vs {file2.filename}")
        
        return jsonify({
            'success': True,
            'filename1': file1.filename,
            'filename2': file2.filename,
            'analysis_type': 'version_compare',
            'analysis_result': comparison_result,
            'stats1': {
                'word_count': len(text1.split()),
                'char_count': len(text1)
            },
            'stats2': {
                'word_count': len(text2.split()),
                'char_count': len(text2)
            },
            'text_preview1': text1[:200] + "..." if len(text1) > 200 else text1,
            'text_preview2': text2[:200] + "..." if len(text2) > 200 else text2
        })
        
    except Exception as e:
        logger.error(f"Document comparison error: {str(e)}")
        return jsonify({'error': f'Vergelijking mislukt: {str(e)}'}), 500

@main_bp.route('/upload', methods=['POST'])
def upload_document():
    """
    Single document upload endpoint - backward compatibility
    """
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'Geen bestand gevonden'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'Geen bestand geselecteerd'}), 400
        
        # Validatie
        allowed_extensions = {'pdf', 'docx', 'txt'}
        file_extension = file.filename.rsplit('.', 1)[1].lower()
        
        if file_extension not in allowed_extensions:
            return jsonify({'error': 'Bestandstype niet toegestaan'}), 400
        
        # Get analysis type
        analysis_type = request.form.get('analysis_type', 'version_compare')
        
        logger.info(f"Processing file: {file.filename}, type: {analysis_type}")
        
        # Import services
        from app.services.document_service import DocumentProcessor
        from app.services.azure_openai_service import AzureOpenAIService
        
        # Process document
        doc_processor = DocumentProcessor()
        text = doc_processor.extract_text(file.stream, file.filename)
        
        # Analyze with Azure OpenAI
        ai_service = AzureOpenAIService()
        analysis_result = ai_service.analyze_document(text, analysis_type)
        
        logger.info(f"Analysis completed for {file.filename}")
        
        return jsonify({
            'success': True,
            'filename': file.filename,
            'analysis_type': analysis_type,
            'analysis_result': analysis_result,
            'text_preview': text[:200] + "..." if len(text) > 200 else text
        })
        
    except Exception as e:
        logger.error(f"Upload/analysis error: {str(e)}")
        return jsonify({'error': f'Analyse mislukt: {str(e)}'}), 500

@main_bp.route('/health')
def health_check():
    """
    Health check endpoint - handig voor monitoring
    """
    return jsonify({'status': 'healthy'})

@main_bp.route('/test-azure', methods=['GET'])
def test_azure():
    """
    Test Azure OpenAI connection
    """
    try:
        from app.services.azure_openai_service import AzureOpenAIService
        
        ai_service = AzureOpenAIService()
        
        # Check if configured
        if not ai_service.configured:
            return jsonify({
                'success': False,
                'message': 'Azure OpenAI not configured - check environment variables',
                'configured': False,
                'endpoint': ai_service.endpoint is not None,
                'api_key': ai_service.api_key is not None
            }), 400
        
        # Test connection
        if ai_service.test_connection():
            return jsonify({
                'success': True,
                'message': 'Azure OpenAI connection successful!',
                'configured': True,
                'deployment': ai_service.deployment
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Azure OpenAI connection failed - check logs',
                'configured': True
            }), 500
            
    except Exception as e:
        logger.error(f"Azure test error: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Test failed: {str(e)}'
        }), 500