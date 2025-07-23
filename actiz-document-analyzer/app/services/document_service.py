import PyPDF2
from docx import Document
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class DocumentProcessor:
    """
    Service voor het verwerken van verschillende document types
    """
    
    def extract_text(self, file_stream, filename: str) -> Optional[str]:
        """
        Extract text from uploaded file based on extension
        """
        try:
            file_extension = filename.lower().split('.')[-1]
            
            if file_extension == 'pdf':
                return self._extract_from_pdf(file_stream)
            elif file_extension == 'docx':
                return self._extract_from_docx(file_stream)
            elif file_extension == 'txt':
                return self._extract_from_txt(file_stream)
            else:
                raise ValueError(f"Unsupported file type: {file_extension}")
                
        except Exception as e:
            logger.error(f"Error extracting text from {filename}: {str(e)}")
            raise
    
    def _extract_from_pdf(self, file_stream) -> str:
        """Extract text from PDF file"""
        try:
            file_stream.seek(0)
            pdf_reader = PyPDF2.PdfReader(file_stream)
            text = ""
            
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            
            if not text.strip():
                raise ValueError("PDF contains no extractable text")
                
            logger.info(f"Extracted {len(text)} characters from PDF")
            return text.strip()
            
        except Exception as e:
            logger.error(f"PDF extraction error: {str(e)}")
            raise ValueError(f"Could not read PDF: {str(e)}")
    
    def _extract_from_docx(self, file_stream) -> str:
        """Extract text from Word document"""
        try:
            file_stream.seek(0)
            doc = Document(file_stream)
            text = ""
            
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            
            if not text.strip():
                raise ValueError("Word document contains no text")
                
            logger.info(f"Extracted {len(text)} characters from Word document")
            return text.strip()
            
        except Exception as e:
            logger.error(f"Word extraction error: {str(e)}")
            raise ValueError(f"Could not read Word document: {str(e)}")
    
    def _extract_from_txt(self, file_stream) -> str:
        """Extract text from text file"""
        try:
            file_stream.seek(0)
            content = file_stream.read()
            
            # Try UTF-8 first
            try:
                text = content.decode('utf-8')
            except UnicodeDecodeError:
                text = content.decode('latin-1')
            
            if not text.strip():
                raise ValueError("Text file is empty")
                
            logger.info(f"Extracted {len(text)} characters from text file")
            return text.strip()
            
        except Exception as e:
            logger.error(f"Text extraction error: {str(e)}")
            raise ValueError(f"Could not read text file: {str(e)}")