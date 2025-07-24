"""
ActiZ Document Analyzer - Complete Flask Main Routes
V1.4 - Fixed syntax errors + added proper configuration management
"""

import logging
from datetime import datetime
from typing import Any, Dict, Tuple

from flask import Blueprint, current_app, jsonify, render_template, request

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Blueprint voor route organizatie
main = Blueprint("main", __name__)


@main.route("/")
def index() -> str:
    """
    Hoofdpagina - toont upload interface
    """
    logger.info("Index page accessed")
    return render_template("index.html")


@main.route("/health")
def health_check() -> Dict[str, Any]:
    """
    Health check endpoint - handig voor monitoring
    """
    return jsonify(
        {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "1.4",
            "service": "ActiZ Document Analyzer",
        }
    )


@main.route("/test-azure", methods=["GET"])
def test_azure() -> Tuple[Dict[str, Any], int]:
    """
    Test Azure OpenAI connection - ENHANCED
    """
    try:
        from app.services.azure_openai_service import AzureOpenAIService

        # Use app config
        config = current_app.config
        ai_service = AzureOpenAIService(config)

        # Check if configured
        if not ai_service.configured:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Azure OpenAI not configured - check environment variables",
                        "configured": False,
                        "endpoint": ai_service.endpoint is not None,
                        "api_key": ai_service.api_key is not None,
                    }
                ),
                400,
            )

        # Test connection using the enhanced method
        connection_result = ai_service.test_connection()

        if connection_result["success"]:
            return (
                jsonify(
                    {
                        "success": True,
                        "message": "Azure OpenAI connection successful!",
                        "configured": True,
                        "deployment": ai_service.deployment,
                        "response": connection_result.get("response", ""),
                    }
                ),
                200,
            )
        else:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": connection_result["message"],
                        "configured": True,
                    }
                ),
                500,
            )

    except Exception as e:
        logger.error(f"Azure test error: {str(e)}")
        return jsonify({"success": False, "message": f"Test failed: {str(e)}"}), 500


@main.route("/debug-azure", methods=["GET"])
def debug_azure() -> Tuple[Dict[str, Any], int]:
    """
    Debug Azure OpenAI connection with detailed info
    """
    try:
        from app.services.azure_openai_service import AzureOpenAIService

        config = current_app.config
        ai_service = AzureOpenAIService(config)

        debug_info = {
            "service_configured": ai_service.configured,
            "endpoint": ai_service.endpoint,
            "api_key_present": bool(ai_service.api_key),
            "api_key_length": len(ai_service.api_key) if ai_service.api_key else 0,
            "deployment": ai_service.deployment,
            "api_version": ai_service.api_version,
            "timestamp": datetime.now().isoformat(),
        }

        # Test simple completion if configured
        if ai_service.configured:
            try:
                test_result = ai_service.test_connection()
                debug_info["connection_test"] = test_result
            except Exception as e:
                debug_info["connection_test"] = {
                    "success": False,
                    "error": str(e),
                    "error_type": type(e).__name__,
                }

        return jsonify(debug_info), 200

    except Exception as e:
        logger.error(f"Debug error: {str(e)}")
        return (
            jsonify(
                {
                    "success": False,
                    "error": f"Debug failed: {str(e)}",
                    "error_type": type(e).__name__,
                    "timestamp": datetime.now().isoformat(),
                }
            ),
            500,
        )


@main.route("/validate-documents", methods=["POST"])
def validate_documents_endpoint() -> Tuple[Dict[str, Any], int]:
    """
    Pre-validate documents before analysis for better UX
    """
    try:
        if "file1" not in request.files or "file2" not in request.files:
            return (
                jsonify({"error": "Beide documenten zijn vereist voor validatie"}),
                400,
            )

        file1 = request.files["file1"]
        file2 = request.files["file2"]

        if file1.filename == "" or file2.filename == "":
            return jsonify({"error": "Beide documenten moeten geselecteerd zijn"}), 400

        logger.info(f"Validating documents: {file1.filename} vs {file2.filename}")

        # Import services
        from app.services.document_service import DocumentProcessor

        doc_processor = DocumentProcessor()

        try:
            text1 = doc_processor.extract_text(file1.stream, file1.filename)
            text2 = doc_processor.extract_text(file2.stream, file2.filename)

            # Simple validation
            if len(text1.strip()) < 50 or len(text2.strip()) < 50:
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "Een of beide documenten zijn te kort voor analyse",
                            "recommendation": "Upload documenten met meer inhoud",
                        }
                    ),
                    400,
                )

            # Basic similarity check
            words1 = set(text1.lower().split())
            words2 = set(text2.lower().split())
            similarity = (
                len(words1.intersection(words2)) / len(words1.union(words2))
                if words1.union(words2)
                else 0
            )

            validation_type = "normal_comparison"
            if similarity > 0.95:
                validation_type = "identical_documents"
            elif similarity < 0.1:
                validation_type = "very_different_documents"

            return (
                jsonify(
                    {
                        "success": True,
                        "validation_result": {
                            "valid": True,
                            "validation_type": validation_type,
                            "similarity_score": similarity,
                            "message": f"Documenten geschikt voor vergelijking (gelijkenis: {similarity:.1%})",
                        },
                        "fingerprints": {
                            "document1": {
                                "filename": file1.filename,
                                "word_count": len(text1.split()),
                                "char_count": len(text1),
                            },
                            "document2": {
                                "filename": file2.filename,
                                "word_count": len(text2.split()),
                                "char_count": len(text2),
                            },
                        },
                        "proceed_with_analysis": True,
                        "timestamp": datetime.now().isoformat(),
                    }
                ),
                200,
            )

        except Exception as e:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": f"Document processing failed: {str(e)}",
                        "timestamp": datetime.now().isoformat(),
                    }
                ),
                500,
            )

    except Exception as e:
        logger.error(f"Document validation error: {str(e)}")
        return (
            jsonify(
                {
                    "error": f"Validatie mislukt: {str(e)}",
                    "timestamp": datetime.now().isoformat(),
                }
            ),
            500,
        )


@main.route("/compare", methods=["POST"])
def compare_documents() -> Tuple[Dict[str, Any], int]:
    """
    Vergelijk twee documenten - ENHANCED with hybrid prompts
    """
    try:
        # Validate beide bestanden aanwezig zijn
        if "file1" not in request.files or "file2" not in request.files:
            return jsonify({"error": "Beide documenten zijn vereist"}), 400

        file1 = request.files["file1"]
        file2 = request.files["file2"]

        if file1.filename == "" or file2.filename == "":
            return jsonify({"error": "Beide documenten moeten geselecteerd zijn"}), 400

        # Validatie file extensions
        allowed_extensions = {"pdf", "docx", "txt"}

        file1_ext = file1.filename.rsplit(".", 1)[1].lower()
        file2_ext = file2.filename.rsplit(".", 1)[1].lower()

        if file1_ext not in allowed_extensions or file2_ext not in allowed_extensions:
            return (
                jsonify(
                    {"error": "Bestandstype niet toegestaan. Gebruik PDF, DOCX of TXT"}
                ),
                400,
            )

        logger.info(f"Comparing documents: {file1.filename} vs {file2.filename}")

        # Import services
        from app.services.azure_openai_service import AzureOpenAIService
        from app.services.document_service import DocumentProcessor

        # Process beide documenten
        doc_processor = DocumentProcessor()

        # Extract text from both documents
        text1 = doc_processor.extract_text(file1.stream, file1.filename)
        text2 = doc_processor.extract_text(file2.stream, file2.filename)

        logger.info(f"Document 1: {len(text1)} chars, Document 2: {len(text2)} chars")

        # Analyze with Azure OpenAI using HYBRID service
        config = current_app.config
        ai_service = AzureOpenAIService(config)
        comparison_result = ai_service.compare_documents(
            text1, text2, file1.filename, file2.filename
        )

        # Get summary metrics if available and not in demo mode
        summary_metrics = {}
        if comparison_result.get("result") and not comparison_result.get("demo_mode"):
            summary_result = ai_service.get_analysis_summary(
                comparison_result["result"]
            )
            if summary_result.get("success"):
                summary_metrics = summary_result["summary"]

        logger.info(f"Comparison completed: {file1.filename} vs {file2.filename}")

        return (
            jsonify(
                {
                    "success": True,
                    "filename1": file1.filename,
                    "filename2": file2.filename,
                    "analysis_type": "version_compare",
                    "analysis_result": comparison_result,
                    "summary_metrics": summary_metrics,
                    "stats1": {
                        "word_count": len(text1.split()),
                        "char_count": len(text1),
                    },
                    "stats2": {
                        "word_count": len(text2.split()),
                        "char_count": len(text2),
                    },
                    "text_preview1": text1[:200] + "..." if len(text1) > 200 else text1,
                    "text_preview2": text2[:200] + "..." if len(text2) > 200 else text2,
                    "timestamp": datetime.now().isoformat(),
                    "prompt_version": comparison_result.get(
                        "prompt_version", "unknown"
                    ),
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Document comparison error: {str(e)}")
        return (
            jsonify(
                {
                    "error": f"Vergelijking mislukt: {str(e)}",
                    "timestamp": datetime.now().isoformat(),
                }
            ),
            500,
        )


@main.route("/upload", methods=["POST"])
def upload_document() -> Tuple[Dict[str, Any], int]:
    """
    Single document upload endpoint - backward compatibility with enhanced features
    """
    try:
        if "file" not in request.files:
            return jsonify({"error": "Geen bestand gevonden"}), 400

        file = request.files["file"]
        if file.filename == "":
            return jsonify({"error": "Geen bestand geselecteerd"}), 400

        # Validatie
        allowed_extensions = {"pdf", "docx", "txt"}
        file_extension = file.filename.rsplit(".", 1)[1].lower()

        if file_extension not in allowed_extensions:
            return jsonify({"error": "Bestandstype niet toegestaan"}), 400

        # Get analysis type
        analysis_type = request.form.get("analysis_type", "version_compare")

        logger.info(f"Processing file: {file.filename}, type: {analysis_type}")

        # Import services
        from app.services.azure_openai_service import AzureOpenAIService
        from app.services.document_service import DocumentProcessor

        # Process document
        doc_processor = DocumentProcessor()
        text = doc_processor.extract_text(file.stream, file.filename)

        # Analyze with Azure OpenAI using enhanced service
        config = current_app.config
        ai_service = AzureOpenAIService(config)
        analysis_result = ai_service.analyze_document(text, analysis_type)

        logger.info(f"Analysis completed for {file.filename}")

        return (
            jsonify(
                {
                    "success": True,
                    "filename": file.filename,
                    "analysis_type": analysis_type,
                    "analysis_result": analysis_result,
                    "text_preview": text[:200] + "..." if len(text) > 200 else text,
                    "timestamp": datetime.now().isoformat(),
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Upload/analysis error: {str(e)}")
        return (
            jsonify(
                {
                    "error": f"Analyse mislukt: {str(e)}",
                    "timestamp": datetime.now().isoformat(),
                }
            ),
            500,
        )
