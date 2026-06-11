# ============================================================
# Instala las tareas programadas de Gestion de Promociones
# Ejecutar UNA SOLA VEZ como Administrador
# Sin ventana negra: usa VBScript como lanzador invisible
# Se ejecuta a las horas en punto (XX:00) y a las y media (XX:30)
# ============================================================

$TASK_EN_PUNTO = "FarmaPromo_EnPunto"
$TASK_Y_MEDIA  = "FarmaPromo_YMedia"
$SCRIPT_DIR    = "C:\Users\Admin\Dropbox\Archivos Alfonso\Buzon\Buzon Claude\Aplicaciones\Farmapricing_Agent_v2"
$VBS_FILE      = "C:\FarmaPromo\run_promociones.vbs"

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

# Crear VBScript — parametro 0 = SW_HIDE (sin ventana)
$vbsContent = @"
Set oShell = CreateObject("WScript.Shell")
oShell.Run """$PYTHONW"" ""$SCRIPT_DIR\scripts\06_promociones.py""", 0, False
"@
Set-Content -Path $VBS_FILE -Value $vbsContent -Encoding ASCII
Write-Host "Creado: $VBS_FILE" -ForegroundColor Cyan

$TR = "wscript.exe ""$VBS_FILE"""

# Eliminar tareas anteriores si existen
schtasks /delete /tn $TASK_EN_PUNTO /f 2>$null | Out-Null
schtasks /delete /tn $TASK_Y_MEDIA  /f 2>$null | Out-Null
schtasks /delete /tn "FarmaPromo_30min" /f 2>$null | Out-Null  # limpiar versión antigua

# Tarea 1: horas en punto (00:00, 01:00, 02:00 ... 23:00)
$r1 = schtasks /create /tn $TASK_EN_PUNTO /tr $TR /sc HOURLY /mo 1 /st 00:00 /rl HIGHEST /f 2>&1

# Tarea 2: horas y media (00:30, 01:30, 02:30 ... 23:30)
$r2 = schtasks /create /tn $TASK_Y_MEDIA  /tr $TR /sc HOURLY /mo 1 /st 00:30 /rl HIGHEST /f 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "OK Tareas registradas correctamente:" -ForegroundColor Green
    Write-Host "   '$TASK_EN_PUNTO' → se ejecuta cada hora en punto (XX:00)" -ForegroundColor Green
    Write-Host "   '$TASK_Y_MEDIA'  → se ejecuta cada hora y media (XX:30)" -ForegroundColor Green
    Write-Host "   Log en: $SCRIPT_DIR\scripts\promociones.log" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Comandos utiles:" -ForegroundColor Cyan
    Write-Host "  Ver estado:     schtasks /query /tn $TASK_EN_PUNTO"
    Write-Host "  Ejecutar ahora: schtasks /run /tn $TASK_EN_PUNTO"
    Write-Host "  Desinstalar:    schtasks /delete /tn $TASK_EN_PUNTO /f"
    Write-Host "                  schtasks /delete /tn $TASK_Y_MEDIA /f"
} else {
    Write-Host "ERROR al registrar alguna tarea." -ForegroundColor Red
    Write-Host $r1
    Write-Host $r2
}
