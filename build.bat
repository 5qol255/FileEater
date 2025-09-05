python -m PyInstaller --onefile --noconsole --name "ForceDelete.exe" main.py
move .\dist\ForceDelete.exe .\
ForceDelete.exe build
ForceDelete.exe dist
ForceDelete.exe ForceDelete.exe.spec