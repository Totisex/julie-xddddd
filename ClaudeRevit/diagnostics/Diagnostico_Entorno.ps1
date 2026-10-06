<#
.SYNOPSIS
  CLAUDE BIM - FASE 0 - Diagnostico del entorno Windows (SOLO LECTURA).

.DESCRIPTION
  Recopila informacion del equipo donde correra la integracion Claude <-> pyRevit <-> Revit:
  sistema operativo, Revit instalado, pyRevit, extensiones, Python, .NET, puertos locales,
  Claude Desktop / Claude Code y ubicacion del archivo RVT.

  QUE NO HACE
    - No instala nada y no cambia ninguna configuracion.
    - No abre, copia, guarda ni modifica el archivo RVT (solo lee su cabecera para detectar
      con que version de Revit fue guardado; se abre con acceso de solo lectura).
    - No ejecuta nada recibido de fuera.
  UNICO EFECTO: crea la carpeta de salida (por defecto Documents\ClaudeRevit\reports) y escribe
  alli un JSON. Para probar puertos abre y cierra de inmediato un socket en 127.0.0.1.

.PARAMETER ArchivoRvt
  Nombre (sin extension) del RVT a localizar.
.PARAMETER CarpetaRvt
  Nombre de la carpeta que contiene el RVT.
.PARAMETER Salida
  Carpeta donde se escribe el JSON.
.PARAMETER PuertosCandidatos
  Puertos locales a comprobar (libres / ocupados).
.PARAMETER ProbarInternet
  Si se indica, prueba conexion TCP 443 a api.anthropic.com y claude.ai.
.PARAMETER BuscarEnTodosLosDiscos
  Si se indica, ademas del perfil de usuario busca el RVT en todos los discos fijos (puede tardar).

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File .\Diagnostico_Entorno.ps1
  (-ExecutionPolicy Bypass aplica solo a ESTA ejecucion; no cambia la politica del sistema)
#>
[CmdletBinding()]
param(
    [string]$ArchivoRvt = 'SANI COMPLETO JULIETTE100',
    [string]$CarpetaRvt = 'TIP II',
    [string]$Salida = (Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'ClaudeRevit\reports'),
    [int[]]$PuertosCandidatos = @(48884, 8765, 8000, 5000),
    [switch]$ProbarInternet,
    [switch]$BuscarEnTodosLosDiscos
)

$ErrorActionPreference = 'Continue'
$script:Errores = New-Object System.Collections.ArrayList

function Registrar-Error([string]$Contexto, $Err) {
    [void]$script:Errores.Add([ordered]@{ contexto = $Contexto; error = ($Err | Out-String).Trim() })
}

function Intentar([string]$Contexto, [scriptblock]$Bloque, $Defecto = $null) {
    try { return (& $Bloque) }
    catch { Registrar-Error $Contexto $_; return $Defecto }
}

function Ocultar-Credenciales([string]$url) {
    # Un proxy puede venir como http://usuario:clave@host:puerto; nunca se escribe la clave al informe.
    if ([string]::IsNullOrEmpty($url)) { return $url }
    return ($url -replace '://[^/@]*@', '://***@')
}

function Titulo([string]$t) { Write-Host ''; Write-Host ('== ' + $t) -ForegroundColor Cyan }

$informe = [ordered]@{}
$informe.meta = [ordered]@{
    script = 'Diagnostico_Entorno.ps1'
    version = '0.1.0-fase0'
    fecha = (Get-Date).ToString('s')
    modo = 'SOLO LECTURA'
}

# ---------------------------------------------------------------------------
Titulo 'Sistema operativo y permisos'
$informe.sistema = Intentar 'sistema' {
    $os = Get-CimInstance Win32_OperatingSystem
    $admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    [ordered]@{
        os = $os.Caption
        version = $os.Version
        build = $os.BuildNumber
        arquitectura = $os.OSArchitecture
        powershell = $PSVersionTable.PSVersion.ToString()
        ejecutando_como_administrador = $admin
        politica_de_ejecucion = @(Get-ExecutionPolicy -List | ForEach-Object { [ordered]@{ ambito = [string]$_.Scope; politica = [string]$_.ExecutionPolicy } })
        usuario_es_local = ($env:USERDOMAIN -eq $env:COMPUTERNAME)
    }
}
$informe.sistema | ConvertTo-Json -Depth 4 | Write-Host

# ---------------------------------------------------------------------------
Titulo 'Autodesk Revit instalado'
$informe.revit = Intentar 'revit' {
    $instalaciones = @()
    foreach ($raiz in @($env:ProgramFiles, ${env:ProgramFiles(x86)})) {
        if (-not $raiz) { continue }
        $base = Join-Path $raiz 'Autodesk'
        if (-not (Test-Path $base)) { continue }
        Get-ChildItem -Path $base -Directory -Filter 'Revit 20*' -ErrorAction SilentlyContinue | ForEach-Object {
            $exe = Join-Path $_.FullName 'Revit.exe'
            $api = Join-Path $_.FullName 'RevitAPI.dll'
            $ver = $null
            if (Test-Path $exe) { $ver = (Get-Item $exe).VersionInfo }
            $instalaciones += [ordered]@{
                carpeta = $_.FullName
                anio = ($_.Name -replace '[^0-9]', '')
                revit_exe_version = if ($ver) { $ver.FileVersion } else { $null }
                revit_exe_producto = if ($ver) { $ver.ProductVersion } else { $null }
                revit_api_dll = if (Test-Path $api) { (Get-Item $api).VersionInfo.FileVersion } else { $null }
                runtimeconfig_json_presente = (Test-Path (Join-Path $_.FullName 'Revit.runtimeconfig.json'))
            }
        }
    }
    $procesos = @(Get-Process -Name 'Revit' -ErrorAction SilentlyContinue | ForEach-Object {
        $pr = $_
        [ordered]@{
            pid = $pr.Id
            ruta = (Intentar 'revit.proceso.ruta' { $pr.Path })
            titulo_ventana = $pr.MainWindowTitle
            inicio = (Intentar 'revit.proceso.inicio' { $pr.StartTime.ToString('s') })
        }
    })
    $desinstalador = @()
    foreach ($k in @('HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*', 'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*')) {
        $desinstalador += Get-ItemProperty -Path $k -ErrorAction SilentlyContinue |
            Where-Object { $_.DisplayName -like 'Autodesk Revit*' } |
            ForEach-Object { [ordered]@{ nombre = $_.DisplayName; version = $_.DisplayVersion } }
    }
    [ordered]@{
        instalaciones = $instalaciones
        procesos_revit_abiertos = $procesos
        entradas_de_programas = $desinstalador
        nota_dotnet = 'Revit hasta 2024 usa .NET Framework 4.8; Revit 2025 en adelante usa .NET 8 (dato de referencia, confirmar con la version detectada).'
    }
}
$informe.revit | ConvertTo-Json -Depth 5 | Write-Host

# ---------------------------------------------------------------------------
Titulo 'Add-ins de Revit (solo nombres de archivo .addin)'
$informe.addins = Intentar 'addins' {
    $res = @()
    foreach ($raiz in @((Join-Path $env:APPDATA 'Autodesk\Revit\Addins'), (Join-Path $env:ProgramData 'Autodesk\Revit\Addins'))) {
        if (-not (Test-Path $raiz)) { continue }
        Get-ChildItem -Path $raiz -Recurse -Filter '*.addin' -ErrorAction SilentlyContinue | ForEach-Object {
            $res += [ordered]@{ archivo = $_.FullName; es_pyrevit = ($_.Name -match 'pyrevit') }
        }
    }
    $res
}
$informe.addins | ConvertTo-Json -Depth 3 | Write-Host

# ---------------------------------------------------------------------------
Titulo 'pyRevit'
$informe.pyrevit = Intentar 'pyrevit' {
    $dirs = @()
    foreach ($c in @(
            (Join-Path $env:APPDATA 'pyRevit-Master'),
            (Join-Path $env:APPDATA 'pyRevit'),
            (Join-Path $env:ProgramData 'pyRevit'),
            (Join-Path $env:ProgramFiles 'pyRevit-Master'),
            (Join-Path $env:ProgramFiles 'pyRevit CLI'),
            (Join-Path $env:LOCALAPPDATA 'pyRevit-Master'))) {
        if (Test-Path $c) { $dirs += $c }
    }
    $cli = Get-Command 'pyrevit' -ErrorAction SilentlyContinue
    $cliInfo = $null
    if ($cli) {
        # 'pyrevit env' solo imprime el entorno detectado; no modifica nada.
        $cliInfo = [ordered]@{
            ruta = $cli.Source
            version = (Intentar 'pyrevit.cli.version' { (& pyrevit --version 2>&1 | Out-String).Trim() })
            env = (Intentar 'pyrevit.cli.env' { (& pyrevit env 2>&1 | Out-String).Trim() })
        }
    }
    $extDir = Join-Path $env:APPDATA 'pyRevit\Extensions'
    $extensiones = @()
    if (Test-Path $extDir) { $extensiones = @(Get-ChildItem -Path $extDir -Directory -ErrorAction SilentlyContinue | ForEach-Object { $_.Name }) }
    # Configuracion: solo claves relevantes (no se vuelca el archivo completo).
    $cfg = Join-Path $env:APPDATA 'pyRevit\pyRevit_config.ini'
    $cfgInfo = [ordered]@{ existe = (Test-Path $cfg); lineas = @() }
    if ($cfgInfo.existe) {
        $seccion = ''
        foreach ($l in (Get-Content -Path $cfg -ErrorAction SilentlyContinue)) {
            if ($l -match '^\s*\[(.+)\]\s*$') { $seccion = $Matches[1]; continue }
            if ($seccion -eq 'routes') { $cfgInfo.lineas += ('[routes] ' + $l) }
            elseif ($seccion -eq 'core' -and $l -match '^\s*(userextensions|loadbeta|rocketmode|bincache|checkupdates)\s*=') { $cfgInfo.lineas += ('[core] ' + $l) }
        }
    }
    [ordered]@{
        carpetas_encontradas = $dirs
        cli = $cliInfo
        extensiones_usuario_en_AppData = $extensiones
        configuracion_relevante = $cfgInfo
    }
}
$informe.pyrevit | ConvertTo-Json -Depth 5 | Write-Host

# ---------------------------------------------------------------------------
Titulo 'Python, Node y .NET en el equipo (para el servidor local)'
$informe.herramientas = Intentar 'herramientas' {
    function Ver([string]$cmd, [string[]]$argumentos) {
        $c = Get-Command $cmd -ErrorAction SilentlyContinue | Select-Object -First 1
        if (-not $c) { return [ordered]@{ encontrado = $false } }
        $esAliasTienda = ($c.Source -like '*\WindowsApps\*')
        $txt = $null
        if (-not $esAliasTienda) { $txt = (Intentar ("version." + $cmd) { (& $c.Source @argumentos 2>&1 | Out-String).Trim() }) }
        [ordered]@{ encontrado = $true; ruta = $c.Source; alias_tienda_de_windows = $esAliasTienda; salida = $txt }
    }
    $netfx = Intentar 'netfx' {
        $r = (Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\NET Framework Setup\NDP\v4\Full' -ErrorAction Stop).Release
        [ordered]@{ release = $r; es_4_8_o_superior = ($r -ge 528040) }
    }
    [ordered]@{
        python = Ver 'python' @('--version')
        py_launcher = Ver 'py' @('-0p')
        python3 = Ver 'python3' @('--version')
        pip = Ver 'pip' @('--version')
        node = Ver 'node' @('--version')
        npm = Ver 'npm' @('--version')
        dotnet_runtimes = Ver 'dotnet' @('--list-runtimes')
        dotnet_sdks = Ver 'dotnet' @('--list-sdks')
        dotnet_framework = $netfx
    }
}
$informe.herramientas | ConvertTo-Json -Depth 4 | Write-Host

# ---------------------------------------------------------------------------
Titulo 'Red local: puertos candidatos y proxy'
$informe.red = Intentar 'red' {
    $escuchando = @(Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue)
    $puertos = @()
    foreach ($p in $PuertosCandidatos) {
        $dueno = $escuchando | Where-Object { $_.LocalPort -eq $p } | Select-Object -First 1
        $libre = $null
        if (-not $dueno) {
            $l = $null
            try {
                $l = New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Loopback, $p)
                $l.Start(); $l.Stop(); $libre = $true
            } catch { $libre = $false }
        }
        $proc = $null
        if ($dueno) { $proc = (Intentar 'red.proceso' { (Get-Process -Id $dueno.OwningProcess -ErrorAction Stop).ProcessName }) }
        $puertos += [ordered]@{
            puerto = $p
            en_escucha = [bool]$dueno
            proceso = $proc
            direccion = if ($dueno) { $dueno.LocalAddress } else { $null }
            libre_en_loopback = $libre
        }
    }
    $proxy = Intentar 'red.proxy' { [System.Net.WebRequest]::GetSystemWebProxy().GetProxy([Uri]'https://api.anthropic.com').AbsoluteUri }
    $r = [ordered]@{
        puertos = $puertos
        proxy_del_sistema_para_api_anthropic = $proxy
        variables_proxy = [ordered]@{
            HTTP_PROXY = (Ocultar-Credenciales $env:HTTP_PROXY)
            HTTPS_PROXY = (Ocultar-Credenciales $env:HTTPS_PROXY)
            NO_PROXY = $env:NO_PROXY
        }
    }
    if ($ProbarInternet) {
        $r.conectividad_443 = @(foreach ($h in @('api.anthropic.com', 'claude.ai')) {
            $t = Intentar ('internet.' + $h) { Test-NetConnection -ComputerName $h -Port 443 -WarningAction SilentlyContinue }
            [ordered]@{ host = $h; tcp_443_ok = if ($t) { [bool]$t.TcpTestSucceeded } else { $null } }
        })
    } else {
        $r.conectividad_443 = 'no probado (usa -ProbarInternet)'
    }
    $r
}
$informe.red | ConvertTo-Json -Depth 5 | Write-Host

# ---------------------------------------------------------------------------
Titulo 'Claude Desktop / Claude Code'
$informe.claude = Intentar 'claude' {
    $cfg = Join-Path $env:APPDATA 'Claude\claude_desktop_config.json'
    $servidoresMcp = $null
    if (Test-Path $cfg) {
        # Solo se listan los NOMBRES de servidores MCP; no se leen ni exportan comandos, rutas ni variables.
        $servidoresMcp = Intentar 'claude.mcp' {
            $j = Get-Content -Raw -Path $cfg | ConvertFrom-Json
            if ($j.mcpServers) { @($j.mcpServers.PSObject.Properties | ForEach-Object { $_.Name }) } else { @() }
        }
    }
    $cc = Get-Command 'claude' -ErrorAction SilentlyContinue | Select-Object -First 1
    [ordered]@{
        claude_desktop_config_existe = (Test-Path $cfg)
        servidores_mcp_configurados = $servidoresMcp
        claude_desktop_instalado = [bool](Intentar 'claude.appx' { Get-AppxPackage -Name '*Claude*' -ErrorAction SilentlyContinue })
        claude_code_cli = if ($cc) { [ordered]@{ ruta = $cc.Source; version = (Intentar 'claude.cli' { (& $cc.Source --version 2>&1 | Out-String).Trim() }) } } else { $null }
    }
}
$informe.claude | ConvertTo-Json -Depth 4 | Write-Host

# ---------------------------------------------------------------------------
Titulo ("Archivo RVT: '" + $ArchivoRvt + "' en carpeta '" + $CarpetaRvt + "'")

function Leer-VersionRvt([string]$ruta) {
    # Best-effort: la cabecera (BasicFileInfo) guarda texto UTF-16 con 'Format: 20xx'.
    # Se abre con FileShare.ReadWrite para no interferir si Revit lo tiene abierto. Solo lectura.
    $fs = [System.IO.File]::Open($ruta, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::ReadWrite)
    try {
        $n = [int][Math]::Min($fs.Length, 16777216)
        $buf = New-Object byte[] $n
        $leidos = $fs.Read($buf, 0, $n)
        $txt0 = [System.Text.Encoding]::Unicode.GetString($buf, 0, $leidos)
        $txt1 = [System.Text.Encoding]::Unicode.GetString($buf, 1, $leidos - 1)
        foreach ($t in @($txt0, $txt1)) {
            $m = [regex]::Match($t, 'Format:\s*(\d{4})')
            if ($m.Success) { return [ordered]@{ formato_guardado_con_revit = $m.Groups[1].Value; metodo = 'cabecera UTF-16' } }
        }
        return [ordered]@{ formato_guardado_con_revit = $null; metodo = 'no encontrado en los primeros 16 MB' }
    } finally { $fs.Dispose() }
}

$informe.archivo_rvt = Intentar 'archivo_rvt' {
    $raices = New-Object System.Collections.ArrayList
    # Perfil de usuario: se recorre cada carpeta de primer nivel excepto AppData (enorme y sin proyectos).
    Get-ChildItem -Path $env:USERPROFILE -Directory -Force -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -ne 'AppData' } | ForEach-Object { [void]$raices.Add($_.FullName) }
    if ($BuscarEnTodosLosDiscos) {
        Get-CimInstance Win32_LogicalDisk -Filter 'DriveType=3' | ForEach-Object {
            Get-ChildItem -Path ($_.DeviceID + '\') -Directory -Force -ErrorAction SilentlyContinue |
                Where-Object { $_.Name -notin @('Windows', 'Program Files', 'Program Files (x86)', 'ProgramData', '$Recycle.Bin', 'System Volume Information') } |
                ForEach-Object { [void]$raices.Add($_.FullName) }
        }
    }
    $hallados = @()
    foreach ($r in $raices) {
        $hallados += Get-ChildItem -Path $r -Recurse -Depth 8 -File -Filter ($ArchivoRvt + '*.rvt') -ErrorAction SilentlyContinue
    }
    $hallados = @($hallados | Sort-Object FullName -Unique)
    $filas = @()
    foreach ($f in $hallados) {
        $enCarpeta = ($f.DirectoryName -split '[\\/]') -contains $CarpetaRvt
        $esCopiaAutomatica = ($f.Name -match '\.\d{4}\.rvt$')
        $soloNube = (($f.Attributes -band 0x400000) -ne 0) -or (($f.Attributes -band 0x40000) -ne 0)
        $fila = [ordered]@{
            ruta = $f.FullName
            en_carpeta_esperada = $enCarpeta
            es_copia_de_respaldo_automatica = $esCopiaAutomatica
            tamano_mb = [Math]::Round($f.Length / 1048576, 2)
            ultima_modificacion = $f.LastWriteTime.ToString('s')
            solo_en_la_nube_onedrive = $soloNube
            respaldos_junto_al_archivo = @(Get-ChildItem -Path $f.DirectoryName -File -Filter (($f.BaseName -replace '\.\d{4}$', '') + '.0*.rvt') -ErrorAction SilentlyContinue | ForEach-Object { $_.Name })
            version_de_revit_del_archivo = $null
        }
        if (-not $soloNube) {
            $fila.version_de_revit_del_archivo = Intentar ('rvt.version.' + $f.Name) { Leer-VersionRvt $f.FullName }
        }
        $filas += $fila
    }
    [ordered]@{
        buscado = ($ArchivoRvt + '*.rvt')
        carpeta_esperada = $CarpetaRvt
        coincidencias = $filas
        nota = 'El archivo NO se abrio con Revit ni se modifico. Trabaja siempre sobre una copia.'
    }
}
$informe.archivo_rvt | ConvertTo-Json -Depth 6 | Write-Host

# ---------------------------------------------------------------------------
$informe.errores_del_script = $script:Errores

Titulo 'Guardando informe'
$ok = $false
try {
    if (-not (Test-Path $Salida)) { New-Item -ItemType Directory -Path $Salida -Force | Out-Null }
    $ruta = Join-Path $Salida ('diag_entorno_' + (Get-Date).ToString('yyyyMMdd_HHmmss') + '.json')
    $json = $informe | ConvertTo-Json -Depth 8
    [System.IO.File]::WriteAllText($ruta, $json, (New-Object System.Text.UTF8Encoding($false)))
    $ok = $true
    Write-Host ('JSON generado: ' + $ruta) -ForegroundColor Green
} catch {
    Write-Host ('No se pudo escribir el JSON en ' + $Salida + ': ' + $_) -ForegroundColor Red
}
Write-Host ('Errores no fatales registrados: ' + $script:Errores.Count)
if (-not $ok) { exit 1 }
