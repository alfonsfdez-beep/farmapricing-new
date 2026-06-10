# ============================================================
# Instala la tarea programada de Gestion de Promociones
# Ejecutar UNA SOLA VEZ como Administrador
# ============================================================

$TASK_NAME  = "FarmaPromo_30min"
$SCRIPT_DIR = "C:\Users\Admin\Dropbox\Archivos Alfonso\Buzon\Buzon Claude\Aplicaciones\Farmapricing_Agent_v2"
$BAT_FILE   = "$SCRIPT_DIR\run_promociones.bat"

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

# Crear fichero .bat intermedio (evita problemas con espacios en rutas)
$batContent = "@echo off`r`ncd /d `"$SCRIPT_DIR`"`r`n`"$PYTHONW`" scripts\06_promociones.py`r`n"
Set-Content -Path $BAT_FILE -Value $batContent -Encoding ASCII
Write-Host "Creado: $BAT_FILE" -ForegroundColor Cyan

# Eliminar tarea anterior si existe
schtasks /delete /tn $TASK_NAME /f 2>$null | Out-Null

# Programar el .bat cada 30 minutos
$result = schtasks /create /tn $TASK_NAME /tr $BAT_FILE /sc MINUTE /mo 30 /rl HIGHEST /f 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "OK Tarea '$TASK_NAME' registrada correctamente." -ForegroundColor Green
    Write-Host "   Se ejecutara cada 30 min en segundo plano (sin ventana)." -ForegroundColor Green
    Write-Host "   Log en: $SCRIPT_DIR\scripts\promociones.log" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Comandos utiles:" -ForegroundColor Cyan
    Write-Host "  Ver estado:     schtasks /query /tn $TASK_NAME"
    Write-Host "  Ejecutar ahora: schtasks /run /tn $TASK_NAME"
    Write-Host "  Desinstalar:    schtasks /delete /tn $TASK_NAME /f"
} else {
    Write-Host "ERROR al registrar la tarea: $result" -ForegroundColor Red
}
