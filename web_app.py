# web_app.py - Completely unified version with advanced interface as main
import os
import uuid
import logging
from threading import Timer
from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import traceback
import json

# Import our modules
from document_processor import DocumentProcessor
from utils import (
    validate_multiple_upload_request,
    get_required_docs_for_mode,
    get_mode_display_name,
    cleanup_old_files,
    allowed_file
)

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'actiz-dev-key-2024-unified')

# Configuration
UPLOAD_FOLDER = 'uploads'
RESULTS_FOLDER = 'results'
FILE_CLEANUP_INTERVAL = 3600  # 1 hour

# Create directories
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULTS_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB

# File cleanup scheduler
def schedule_cleanup():
    cleanup_old_files(UPLOAD_FOLDER, RESULTS_FOLDER)
    Timer(FILE_CLEANUP_INTERVAL, schedule_cleanup).start()

schedule_cleanup()

# Initialize document processor
processor = DocumentProcessor()

# ========================================
# MAIN UNIFIED INTERFACE
# ========================================

@app.route('/')
def index():
    """Main page - Unified advanced interface only."""
    logger.info("Main page accessed - unified advanced interface")
    return render_template('analyze_multiple.html')

@app.route('/upload-multiple', methods=['POST'])
def upload_multiple():
    """Handle all document uploads through unified interface."""
    logger.info("Document upload started")
    
    mode = request.form.get('mode')
    if not mode:
        flash('Selecteer een analyse type!', 'error')
        return redirect(url_for('index'))
    
    error = validate_multiple_upload_request(request, mode)
    if error:
        logger.warning(f"Upload validation failed: {error}")
        flash(error, 'error')
        return redirect(url_for('index'))
    
    try:
        comparison_id = str(uuid.uuid4())
        
        # Determine files to upload based on mode
        if mode == 'version_comparison':
            files_to_upload = [('doc1', request.files['doc1']), ('doc2', request.files['doc2'])]
        elif mode in ['actiz_position', 'external_reaction']:
            files_to_upload = [('doc1', request.files['doc1']), ('doc2', request.files['doc2'])]
        elif mode == 'strategic_communication':
            files_to_upload = [('doc1', request.files['doc1']), ('doc2', request.files['doc2']), ('doc3', request.files['doc3'])]
        
        # Save files
        for doc_key, file_obj in files_to_upload:
            if file_obj and file_obj.filename:
                filename = secure_filename(f"{comparison_id}_{doc_key}_{file_obj.filename}")
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file_obj.save(filepath)
                logger.info(f"Uploaded {doc_key}: {filename}")
        
        # Save mode
        mode_file = os.path.join(app.config['UPLOAD_FOLDER'], f"{comparison_id}_mode.txt")
        with open(mode_file, 'w') as f:
            f.write(mode)
        
        logger.info(f"Files uploaded successfully for mode: {mode}")
        flash(f'Documenten geüpload! {get_mode_display_name(mode)} analyse gestart...', 'info')
        return redirect(url_for('process_documents', comparison_id=comparison_id))
        
    except Exception as e:
        logger.error(f'Upload error: {e}')
        flash(f'Upload fout: {e}', 'error')
        return redirect(url_for('index'))

@app.route('/process/<comparison_id>')
def process_documents(comparison_id):
    """Process documents - unified processing for all modes."""
    logger.info(f"Starting document processing for comparison_id: {comparison_id}")
    
    try:
        # Read mode
        mode_file = os.path.join(app.config['UPLOAD_FOLDER'], f"{comparison_id}_mode.txt")
        if not os.path.exists(mode_file):
            flash('Analyse mode niet gevonden!', 'error')
            return redirect(url_for('index'))
        
        with open(mode_file, 'r') as f:
            mode = f.read().strip()
        
        # Find uploaded files
        uploaded_files = {}
        for filename in os.listdir(UPLOAD_FOLDER):
            if filename.startswith(f"{comparison_id}_doc"):
                if "_doc1_" in filename:
                    uploaded_files['doc1'] = os.path.join(UPLOAD_FOLDER, filename)
                elif "_doc2_" in filename:
                    uploaded_files['doc2'] = os.path.join(UPLOAD_FOLDER, filename)
                elif "_doc3_" in filename:
                    uploaded_files['doc3'] = os.path.join(UPLOAD_FOLDER, filename)
        
        # Validate required files
        required_docs = get_required_docs_for_mode(mode)
        for doc_key in required_docs:
            if doc_key not in uploaded_files:
                flash(f'Vereist document ontbreekt: {doc_key}', 'error')
                return redirect(url_for('index'))
        
        # Extract text from files
        texts = {}
        filenames = {}
        for doc_key, filepath in uploaded_files.items():
            text = processor.extract_text_from_file(filepath)
            if text is None:
                text = ""
                logger.warning(f"Could not extract text from {filepath}")
            texts[doc_key] = text
            filenames[doc_key] = os.path.basename(filepath)
        
        # Perform mode-specific analysis
        if mode == 'strategic_communication' and 'doc3' in uploaded_files:
            analysis_result = processor.process_documents(
                uploaded_files['doc1'],
                uploaded_files['doc2'],
                uploaded_files.get('doc3'),
                mode=mode
            )
        else:
            analysis_result = processor.process_documents(
                uploaded_files['doc1'],
                uploaded_files['doc2'],
                None,
                mode=mode
            )
        
        # Save analysis result as JSON for later use (e.g., PDF)
        result_file = os.path.join(RESULTS_FOLDER, f"{comparison_id}_result.json")
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(analysis_result, f, ensure_ascii=False, indent=2)
        
        # Format results for display
        formatted_results = processor.format_results_for_display(analysis_result)
        
        # Calculate statistics
        total_chars = sum(len(text) for text in texts.values() if text)
        
        results = {
            'comparison_id': comparison_id,
            'mode': mode,
            'mode_display_name': get_mode_display_name(mode),
            'analysis_result': analysis_result,
            'filenames': filenames,
            'metadata': formatted_results.get('metadata', {}),
            'stats': {
                'total_docs': len(texts),
                'total_chars_k': f"{total_chars/1000:.1f}k",
                'mode_specific_stats': analysis_result.get('stats', {})
            }
        }
        
        logger.info(f"Document processing completed successfully for {comparison_id}")
        return render_template('results_multiple.html', results=results)
        
    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"Error in process_documents: {e}\n{error_details}")
        flash(f'Verwerkingsfout: {e}', 'error')
        return redirect(url_for('index'))

# ========================================
# LEGACY REDIRECTS - All old routes redirect to new system
# ========================================

@app.route('/upload', methods=['GET', 'POST'])
def legacy_upload():
    """Legacy upload route - redirect to main interface."""
    logger.info("Legacy upload route accessed - redirecting to main")
    if request.method == 'POST':
        flash('Gebruik de nieuwe interface hieronder. Selecteer "Versie Vergelijking" voor basis document vergelijking.', 'info')
    return redirect(url_for('index'))

@app.route('/analyze-multiple')
def legacy_analyze_multiple():
    """Legacy analyze-multiple route - redirect to main."""
    logger.info("Legacy analyze-multiple route accessed - redirecting to main")
    return redirect(url_for('index'))

@app.route('/process-multiple/<comparison_id>')
def legacy_process_multiple(comparison_id):
    """Legacy process-multiple route - redirect to unified processing."""
    logger.info(f"Legacy process-multiple route accessed for {comparison_id} - redirecting")
    return redirect(url_for('process_documents', comparison_id=comparison_id))

# ========================================
# UTILITY ROUTES
# ========================================

@app.route('/download_report/<comparison_id>')
def download_report(comparison_id):
    """Generate and download PDF report."""
    logger.info(f"Report download requested for comparison_id: {comparison_id}")
    
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        import io

        # Load saved analysis result
        result_file = os.path.join(RESULTS_FOLDER, f"{comparison_id}_result.json")
        if os.path.exists(result_file):
            with open(result_file, 'r', encoding='utf-8') as f:
                analysis_result = json.load(f)
        else:
            # Fallback: re-process
            mode_file = os.path.join(app.config['UPLOAD_FOLDER'], f"{comparison_id}_mode.txt")
            with open(mode_file, 'r') as f:
                mode = f.read().strip()
            
            uploaded_files = {}
            for filename in os.listdir(UPLOAD_FOLDER):
                if filename.startswith(f"{comparison_id}_doc"):
                    if "_doc1_" in filename:
                        uploaded_files['doc1'] = os.path.join(UPLOAD_FOLDER, filename)
                    elif "_doc2_" in filename:
                        uploaded_files['doc2'] = os.path.join(UPLOAD_FOLDER, filename)
                    elif "_doc3_" in filename:
                        uploaded_files['doc3'] = os.path.join(UPLOAD_FOLDER, filename)
            
            analysis_result = processor.process_documents(
                uploaded_files['doc1'],
                uploaded_files['doc2'],
                uploaded_files.get('doc3'),
                mode=mode
            )

        mode = analysis_result['mode']

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        story = [Paragraph("ActiZ Document Analyse Rapport", styles['h1'])]
        story.append(Paragraph(f"Mode: {get_mode_display_name(mode)}", styles['h2']))
        story.append(Spacer(1, 12))
        
        if mode == 'version_comparison':
            # Differences table
            story.append(Paragraph("Verschillen:", styles['h2']))
            data = [['Type', 'Origineel', 'Gewijzigd', 'Context']]
            for diff in analysis_result['basic_comparison']['differences']:
                data.append([diff['type'], diff['original'] or '-', diff['modified'] or '-', diff['section_context'] or '-'])
            table = Table(data, colWidths=[100, 150, 150, 100])
            table.setStyle([('BACKGROUND', (0,0), (-1,0), colors.grey),
                            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                            ('ALIGN', (0,0), (-1,-1), 'CENTER')])
            story.append(table)
            story.append(Spacer(1, 12))
            
            # AI Analysis
            story.append(Paragraph("AI Inzichten:", styles['h2']))
            ai = analysis_result['ai_analysis']
            story.append(Paragraph("Samenvatting: " + ', '.join(ai['summary']), styles['Normal']))
            story.append(Paragraph("Impact: " + ', '.join(ai['impact']), styles['Normal']))
            
            if ai['semantic_changes']:
                story.append(Paragraph("Semantische Wijzigingen:", styles['h2']))
                sem_data = [['Origineel', 'Nieuw', 'Score', 'Uitleg']]
                for change in ai['semantic_changes']:
                    sem_data.append([change['original'], change['new'], str(change['score']), change['explanation']])
                sem_table = Table(sem_data, colWidths=[100, 100, 50, 200])
                sem_table.setStyle([('BACKGROUND', (0,0), (-1,0), colors.grey)])
                story.append(sem_table)

        elif mode == 'actiz_position':
            position = analysis_result['position_analysis']
            story.append(Paragraph(f"Ondersteuning Score: {position['ondersteuning_score']}", styles['Normal']))
            story.append(Paragraph("Steunpunten: " + ', '.join(position['steunpunten']), styles['Normal']))
            story.append(Paragraph("Kritiekpunten: " + ', '.join(position['kritiekpunten']), styles['Normal']))
            story.append(Paragraph("Verbeteringen: " + ', '.join(position['verbeteringen']), styles['Normal']))
            story.append(Paragraph("Impact Zorgsector: " + position['impact_zorgsector'], styles['Normal']))

        elif mode == 'external_reaction':
            reaction = analysis_result['reaction_analysis']
            story.append(Paragraph("Toon: " + reaction['toon'], styles['Normal']))
            story.append(Paragraph("Hoofdpunten: " + ', '.join(reaction['hoofdpunten']), styles['Normal']))
            story.append(Paragraph("Zorgen: " + ', '.join(reaction['zorgen']), styles['Normal']))
            story.append(Paragraph("Complimenten: " + ', '.join(reaction['complimenten']), styles['Normal']))
            story.append(Paragraph("Aanbevelingen: " + ', '.join(reaction['aanbevelingen']), styles['Normal']))

        elif mode == 'strategic_communication':
            comm = analysis_result['communication_analysis']
            story.append(Paragraph("Gemeenschappelijke Thema's: " + ', '.join(comm['gemeenschappelijke_themas']), styles['Normal']))
            story.append(Paragraph("Inconsistenties: " + ', '.join(comm['inconsistenties']), styles['Normal']))
            story.append(Paragraph("Hoofdboodschappen: " + ', '.join(comm['hoofdboodschappen']), styles['Normal']))
            story.append(Paragraph("Communicatie Gaps: " + ', '.join(comm['communicatie_gaps']), styles['Normal']))
            story.append(Paragraph("Aanbevelingen: " + ', '.join(comm['aanbevelingen']), styles['Normal']))

        doc.build(story)
        buffer.seek(0)
        
        logger.info(f"PDF report generated successfully for {comparison_id}")
        return send_file(buffer, as_attachment=True, download_name=f'actiz_analyse_{comparison_id[:8]}.pdf', mimetype='application/pdf')
        
    except ImportError:
        logger.error("PDF generation failed: reportlab not installed")
        flash('PDF generatie vereist "reportlab". Installeer met: pip install reportlab', 'error')
        return redirect(url_for('index'))
    except Exception as e:
        logger.error(f'PDF generation failed: {e}')
        flash(f'PDF generatie mislukt: {e}', 'error')
        return redirect(url_for('index'))

@app.route('/docs')
def documentation():
    """Show technical documentation."""
    logger.info("Documentation page accessed")
    try:
        return send_file('docs/index.html')
    except:
        return "<h1>Documentatie niet beschikbaar</h1><p><a href='/'>Terug naar hoofdpagina</a></p>"

@app.route('/debug')
def debug():
    """Debug route to test if Flask works."""
    return "<h1>Flask Debug Test - Unified Version</h1><p>If you see this, the unified Flask app works!</p>"

@app.route('/status')
def status():
    """System status endpoint."""
    return {
        'status': 'running',
        'version': '2.0-unified',
        'interface': 'advanced-only',
        'processor_available': processor is not None,
        'upload_folder': UPLOAD_FOLDER,
        'results_folder': RESULTS_FOLDER
    }

# ========================================
# ERROR HANDLERS
# ========================================

@app.errorhandler(413)
def too_large(e):
    flash('Bestand te groot! Maximum grootte is 50MB.', 'error')
    return redirect(url_for('index'))

@app.errorhandler(404)
def not_found(e):
    flash('Pagina niet gevonden. Je bent doorgestuurd naar de hoofdpagina.', 'info')
    return redirect(url_for('index'))

@app.errorhandler(500)
def internal_error(e):
    logger.error(f'Internal server error: {e}')
    flash('Er is een interne fout opgetreden. Probeer het opnieuw.', 'error')
    return redirect(url_for('index'))

# ========================================
# APPLICATION STARTUP
# ========================================

if __name__ == '__main__':
    logger.info("Starting Flask application - UNIFIED VERSION with advanced interface only")
    logger.info("All legacy routes redirect to the new unified interface")
    logger.info("Version comparison is now integrated into the advanced interface")
    app.run(debug=True, port=5000, host='127.0.0.1')