python -m PyInstaller --onefile --noconsole --name "FileEater.exe" main.py
move .\dist\FileEater.exe .\
FileEater.exe build
FileEater.exe dist
FileEater.exe FileEater.exe.spec