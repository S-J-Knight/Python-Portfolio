@echo off
REM filepath: c:\Users\havea\Desktop\Portfolio\Python-Portfolio\cleanup_carts.bat
cd /d "c:\Users\havea\Desktop\Portfolio\Python-Portfolio\website"
python manage.py cleanup_abandoned_carts >> "c:\Users\havea\Desktop\Portfolio\Python-Portfolio\cleanup_log.txt" 2>&1