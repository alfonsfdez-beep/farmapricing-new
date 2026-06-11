# ============================================================
# Instala la tarea programada de Gestion de Promociones
# Ejecutar UNA SOLA VEZ como Administrador
# Sin ventana negra: usa VBScript como lanzador invisible
# ============================================================

$TASK_NAME  = "FarmaPromo_30min"
$SCRIPT_DIR = "C:\Users\Admin\Dropbox\Archivos Alfonso\Buzon\Buzon Claude\Aplicaciones\Farmapricing_Agent_v2"
$VBS_FILE   = "C:\FarmaPromo\run_promociones.vbs"

# Buscar pythonw automaticamente
$cmd = Get-Command pythonw -ErrorAction SilentlyContinue
$PYTHONW = if ($cmd) { $cmd.Source } else { $null }
if (-not $PYTHONW) {
    $candidatos = @(
        "$env:LOCALAPPDATA\Programs\Python\Python312\pythonw.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python311\pythonw.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python310\pythonw.exe",
        "C:\Python312\pythonw.exe",
        "C:\Python311\pythonw.exe"
    )
    foreach ($c in $candidatos) {
        if (Test-Path $c) { $PYTHONW = $c; break }
    }
}

if (-not $PYTHONW) {
    Write-Host "ERROR: No se encontro pythonw.exe." -ForegroundColor Red
    exit 1
}

Write-Host "Usando: $PYTHONW" -ForegroundColor Cyan

# Crear carpeta sin espacios
New-Item -ItemType Directory -Force -Path "C:\FarmaPromo" | Out-Null

# Crear VBScript — el parametro 0 en oShell.Run = SW_HIDE (sin ventana)
$vbsContent = @"
Set oShell = CreateObject("WScript.Shell")
oShell.Run """$PYTHONW"" ""$SCRIPT_DIR\scripts\06_promociones.py""", 0, False
"@
Set-Content -Path $VBS_FILE -Value $vbsContent -Encoding ASCII
Write-Host "Creado: $VBS_FILE" -ForegroundColor Cyan

# Eliminar tarea anterior si existe
schtasks /delete /tn $TASK_NAME /f 2>$null | Out-Null

# Programar el VBS con wscript.exe (invisible por naturaleza)
$result = schtasks /create /tn $TASK_NAME /tr "wscript.exe ""$VBS_FILE""" /sc MINUTE /mo 30 /rl HIGHEST /f 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "OK Tarea '$TASK_NAME' registrada correctamente." -ForegroundColor Green
    Write-Host "   Se ejecutara cada 30 min SIN ventana negra." -ForegroundColor Green
    Write-Host "   Log en: $SCRIPT_DIR\scripts\promociones.log" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Comandos utiles:" -ForegroundColor Cyan
    Write-Host "  Ver estado:     schtasks /query /tn $TASK_NAME"
    Write-Host "  Ejecutar ahora: schtasks /run /tn $TASK_NAME"
    Write-Host "  Desinstalar:    schtasks /delete /tn $TASK_NAME /f"
} else {
    Write-Host "ERROR al registrar la tarea: $result" -ForegroundColor Red
}
