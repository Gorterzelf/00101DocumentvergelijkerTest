# 📄 ActiZ Document Analyzer

**Professional document comparison tool for ActiZ (Nederlandse branchevereniging voor ouderenzorg)**

Vergelijk beleidsdocumenten, wetgeving en andere teksten met AI-analyse en krijg gestructureerde rapporten over wijzigingen en impact.

---

## ✨ **Key Features**

### 🤖 **AI-Powered Analysis**
- Document vergelijking met Azure OpenAI GPT-4
- Intelligente detectie van wijzigingen, toevoegingen en verwijderingen
- ActiZ-specifieke impact analyse voor ouderenzorg sector

### 📊 **Professional Output**
- **Executive Summary** - Overzicht van belangrijkste wijzigingen
- **Change Table** - Gestructureerde tabel met alle aanpassingen
- **Impact Analysis** - Gevolgen voor ActiZ leden en operaties
- **Markdown formatting** - Professioneel opgemaakte rapporten

### 🎯 **Modern User Experience**
- **Drag & Drop** - Sleep bestanden naar upload gebied
- **Progress Tracking** - Real-time feedback tijdens analyse
- **Export Options** - Copy to clipboard, PDF download, print
- **Responsive Design** - Werkt op desktop, tablet en mobile

---

## 🚀 **Quick Start**

### **1. Repository Clonen**
```bash
git clone https://github.com/Gorterzelf/00101DocumentvergelijkerTest.git
cd 00101DocumentvergelijkerTest
```

### **2. Virtual Environment Setup**
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux  
python -m venv venv
source venv/bin/activate
```

### **3. Dependencies Installeren**
```bash
pip install -r actiz-document-analyzer/requirements/development.txt
```

### **4. Environment Variables**
Kopieer `.env.example` naar `.env` en vul je Azure OpenAI credentials in:
```bash
AZURE_OPENAI_API_KEY=your_api_key_here
AZURE_OPENAI_ENDPOINT=your_endpoint_here
AZURE_OPENAI_API_VERSION=2024-02-15-preview
FLASK_ENV=development
FLASK_DEBUG=True
```

### **5. Applicatie Starten**
```bash
# Windows
cd actiz-document-analyzer
python run.py

# Of gebruik de batch file
start.bat
```

### **6. Open Browser**
Navigeer naar: `http://localhost:5000`

---

## 🛠️ **Tech Stack**

### **Backend**
- **Python Flask** - Web framework
- **Azure OpenAI** - GPT-4 voor document analyse
- **Python-docx** - Word document processing
- **PyPDF2** - PDF document processing

### **Frontend**
- **Bootstrap 5** - Modern UI framework
- **JavaScript ES6** - Interactive features
- **Marked.js** - Markdown rendering
- **Prism.js** - Syntax highlighting
- **jsPDF** - Client-side PDF generation
- **Font Awesome** - Professional icons

### **Features**
- **File Upload** - Drag & drop + traditional upload
- **Progress Bars** - Visual feedback during processing  
- **Export System** - Multiple output formats
- **Responsive Design** - Mobile-first approach

---

## 📁 **Project Structure**

```
actiz-document-analyzer/
├── app/
│   ├── __init__.py
│   ├── main.py                 # Flask routes & main logic
│   ├── services/
│   │   ├── azure_openai_service.py    # AI integration
│   │   └── document_service.py        # File processing
│   ├── static/
│   │   ├── css/main.css              # Custom styling
│   │   └── js/main.js                # Enhanced JavaScript
│   └── templates/
│       ├── base.html                 # Base template with export
│       └── index.html                # Main upload interface
├── requirements/
│   ├── base.txt                      # Core dependencies
│   └── development.txt               # Dev dependencies
├── run.py                            # Application entry point
├── start.bat                         # Windows quick start
├── .env.example                      # Environment template
└── README.md                         # This file
```

---

## 🎯 **Usage Examples**

### **Document Types Supported**
- **PDF** - Beleidsdocumenten, rapporten, wetgeving
- **Word** - `.docx` bestanden, contracten, overeenkomsten  
- **Text** - `.txt` bestanden, eenvoudige teksten

### **Typical Workflow**
1. **Upload** twee versies van hetzelfde document
2. **Analyse** - AI vergelijkt automatisch de content
3. **Review** - Bekijk gestructureerd rapport met wijzigingen
4. **Export** - Download als PDF of kopieer naar klembord
5. **Share** - Deel resultaten met stakeholders

---

## 📊 **Sample Output**

```markdown
## 📋 Executive Samenvatting
**Documenten:** Hoofdlijnenakkoord_v1.0.pdf → Hoofdlijnenakkoord_v2.0.pdf
**Totaal wijzigingen:** 15 toevoegingen, 8 wijzigingen, 3 verwijderingen
**Impact niveau:** Hoog
**Actie vereist:** Ja - Budgetaanpassingen nodig voor Q4

## 📊 Wijzigingen Overzicht
| Sectie | Type | Oude Waarde | Nieuwe Waarde | Impact | Prioriteit |
|--------|------|-------------|---------------|---------|------------|
| Art. 4.2 | Bedrag | €21.0 miljard | €24.4 miljard | Financieel | Hoog |
| Sect. 3.1 | Nieuwe regel | - | Reablement verplicht | Operationeel | Gemiddeld |
```

---

## ⚙️ **Configuration**

### **Azure OpenAI Setup**
1. Maak Azure OpenAI resource aan
2. Deploy GPT-4 model  
3. Kopieer API key en endpoint naar `.env`
4. Test verbinding via `/test_azure` endpoint

### **Performance Tuning**
- **File Size Limit**: 16MB per document
- **Timeout**: 300 seconden voor analyse
- **Concurrent Uploads**: Max 1 vergelijking tegelijk

---

## 🔧 **Development**

### **Local Development**
```bash
# Start development server
flask run --debug

# Run tests (als geïmplementeerd)
python -m pytest

# Code formatting
black app/
```

### **Adding Features**
1. **Backend**: Extend `app/main.py` routes
2. **AI Prompts**: Modify `azure_openai_service.py`
3. **Frontend**: Update `static/js/main.js`
4. **Styling**: Edit `static/css/main.css`

---

## 🚨 **Troubleshooting**

### **Common Issues**

**❌ Azure OpenAI Connection Failed**
```
Solution: Check .env credentials and endpoint URL
Test: Visit http://localhost:5000/test_azure
```

**❌ File Upload Errors**
```
Solution: Check file size (<16MB) and supported formats
Supported: .pdf, .docx, .txt
```

**❌ JavaScript Errors**
```
Solution: Hard refresh browser (Ctrl+F5)
Check: Browser console for detailed errors
```

### **Debug Mode**
```bash
# Enable verbose logging
export FLASK_DEBUG=True
python run.py
```

---

## 🤝 **Contributing**

### **For ActiZ Team Members**
1. **Fork** repository
2. **Create** feature branch: `git checkout -b feature/new-analysis-type`
3. **Commit** changes: `git commit -m "✨ Add sector-specific analysis"`
4. **Push** branch: `git push origin feature/new-analysis-type`
5. **Submit** Pull Request

### **Code Standards**
- **Python**: Follow PEP 8
- **JavaScript**: ES6+ standards
- **Commits**: Use conventional commits with emojis
- **Documentation**: Update README for new features

---

## 📈 **Roadmap**

### **Version 2.0 (Q4 2025)**
- [ ] **Database Integration** - Opslaan van analyses
- [ ] **User Management** - Login systeem voor teams
- [ ] **Batch Processing** - Meerdere documenten tegelijk
- [ ] **API Endpoints** - REST API voor integraties

### **Version 2.1 (Q1 2026)**
- [ ] **Change Highlighting** - Visuele diff in documents
- [ ] **Email Integration** - Automatische rapporten
- [ ] **Dashboard** - Analytics over document changes
- [ ] **Mobile App** - iOS/Android companion

---

## 📞 **Support**

### **ActiZ Internal Use**
- **Contact**: IT Team ActiZ
- **Documentation**: Internal confluence
- **Issues**: GitHub Issues of internal ticketing

### **Technical Support**
- **Logs**: Check `logs/` directory
- **Monitoring**: Built-in health checks
- **Updates**: Automatic dependency scanning

---

## 📄 **License**

**Internal Use Only** - ActiZ Branchevereniging Ouderenzorg

This software is developed for internal use by ActiZ and its members. Not for public distribution.

---

## 🙏 **Acknowledgments**

- **ActiZ Team** - Requirements and domain expertise
- **Azure OpenAI** - AI-powered document analysis
- **Bootstrap Team** - Modern UI framework
- **Flask Community** - Lightweight web framework

---

**🚀 Ready to analyze your documents! Visit http://localhost:5000 to get started.**

*Last updated: July 2025 | Version 1.0*