# ============================================================
# Instala la tarea programada de Gestión de Promociones
# Ejecutar UNA SOLA VEZ como Administrador
# ============================================================

$TASK_NAME   = "FarmaPromo_30min"
$SCRIPT_DIR  = "C:\Users\Admin\Dropbox\Archivos Alfonso\Buzon\Buzon Claude\Aplicaciones\Farmapricing_Agent_v2"
$SCRIPT_PATH = "scripts\06_promociones.py"

# Buscar pythonw automáticamente
$cmd = Get-Command pythonw -ErrorAction SilentlyContinue
$PYTHONW = if ($cmd) { $cmd.Source } else { $null }
if (-not $PYTHONW) {
    # Intentar rutas habituales
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
    Write-Host "ERROR: No se encontró pythonw.exe. Instala Python con la opción 'Add to PATH'." -ForegroundColor Red
    exit 1
}

Write-Host "Usando: $PYTHONW" -ForegroundColor Cyan

# Eliminar tarea anterior si existe
Unregister-ScheduledTask -TaskName $TASK_NAME -Confirm:$false -ErrorAction SilentlyContinue

# Acción: ejecutar pythonw sin ventana
$action = New-ScheduledTaskAction `
    -Execute $PYTHONW `
    -Argument $SCRIPT_PATH `
    -WorkingDirectory $SCRIPT_DIR

# Trigger: cada 30 minutos indefinidamente
$trigger = New-ScheduledTaskTrigger `
    -Once `
    -At (Get-Date) `
    -RepetitionInterval  (New-TimeSpan -Minutes 30) `
    -RepetitionDuration  ([TimeSpan]::MaxValue)

# Configuración: sin ventana, timeout 5 min, arrancar aunque no haya sesión
$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit  (New-TimeSpan -Minutes 5) `
    -MultipleInstances   IgnoreNew `
    -StartWhenAvailable  $true `
    -Hidden              $true

# Principal: usuario actual con permisos elevados
$principal = New-ScheduledTaskPrincipal `
    -UserId    $env:USERNAME `
    -RunLevel  Highest `
    -LogonType Interactive

# Registrar
Register-ScheduledTask `
    -TaskName   $TASK_NAME `
    -Action     $action `
    -Trigger    $trigger `
    -Settings   $settings `
    -Principal  $principal `
    -Description "Gestión automática de promociones Farmapricing (cada 30 min)"

Write-Host ""
Write-Host "✅ Tarea '$TASK_NAME' registrada correctamente." -ForegroundColor Green
Write-Host "   Se ejecutará cada 30 minutos en segundo plano." -ForegroundColor Green
Write-Host "   Log en: $SCRIPT_DIR\scripts\promociones.log" -ForegroundColor Yellow
Write-Host ""
Write-Host "Comandos útiles:" -ForegroundColor Cyan
Write-Host "  Ver estado:      Get-ScheduledTask -TaskName '$TASK_NAME'"
Write-Host "  Ejecutar ahora:  Start-ScheduledTask -TaskName '$TASK_NAME'"
Write-Host "  Desinstalar:     Unregister-ScheduledTask -TaskName '$TASK_NAME' -Confirm:`$false"
