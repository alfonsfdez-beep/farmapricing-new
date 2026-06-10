# ============================================================
# Instala la tarea programada de Gestión de Promociones
# Ejecutar UNA SOLA VEZ como Administrador
# ============================================================

$TASK_NAME  = "FarmaPromo_30min"
$SCRIPT_DIR = "C:\Users\Admin\Dropbox\Archivos Alfonso\Buzon\Buzon Claude\Aplicaciones\Farmapricing_Agent_v2"

# Buscar pythonw automáticamente
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

# Comando completo para schtasks
$CMD = "`"$PYTHONW`" `"$SCRIPT_DIR\scripts\06_promociones.py`""

# Eliminar tarea anterior si existe
schtasks /delete /tn $TASK_NAME /f 2>$null

# Crear tarea: cada 30 minutos, en segundo plano, indefinidamente
schtasks /create `
    /tn  $TASK_NAME `
    /tr  $CMD `
    /sc  MINUTE `
    /mo  30 `
    /sd  (Get-Date -Format "dd/MM/yyyy") `
    /st  (Get-Date -Format "HH:mm") `
    /rl  HIGHEST `
    /f

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "OK Tarea '$TASK_NAME' registrada correctamente." -ForegroundColor Green
    Write-Host "   Se ejecutara cada 30 minutos en segundo plano." -ForegroundColor Green
    Write-Host "   Log en: $SCRIPT_DIR\scripts\promociones.log" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Comandos utiles:" -ForegroundColor Cyan
    Write-Host "  Ver estado:     schtasks /query /tn '$TASK_NAME'"
    Write-Host "  Ejecutar ahora: schtasks /run /tn '$TASK_NAME'"
    Write-Host "  Desinstalar:    schtasks /delete /tn '$TASK_NAME' /f"
} else {
    Write-Host "ERROR al registrar la tarea." -ForegroundColor Red
}
