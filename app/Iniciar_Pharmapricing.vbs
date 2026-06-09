Set objShell = CreateObject("WScript.Shell")
objShell.CurrentDirectory = "C:\Users\Administrador\Dropbox\Archivos Alfonso\Buzon\Buzon Claude\Aplicaciones\Farmapricing Agent"
objShell.Run "python -m streamlit run app/streamlit_app.py", 0, False