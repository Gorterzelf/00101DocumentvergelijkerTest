@echo off
echo 🚀 Starting ActiZ Document Analyzer...
cd /d "C:\Users\MartijnGorter\00101DocumentvergelijkerTest\actiz-document-analyzer"
echo 📁 Changed to project directory
call venv\Scripts\activate.bat
echo 🐍 Virtual environment activated
echo 🌐 Starting Flask server...
python run.py
pause