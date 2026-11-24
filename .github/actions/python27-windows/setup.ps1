$ErrorActionPreference = 'Stop'

if (!$IsWindows -or !$env:RUNNER_TEMP -or !$env:GITHUB_ENV) {
    throw 'A Windows runner and its environment file are required.'
}

# The official Python Software Foundation x64 installer for CPython 2.7.18.
# The administrative extract keeps the runtime local to this job.
$source = 'https://www.python.org/ftp/python/2.7.18/python-2.7.18.amd64.msi'
$expected = 'B74A3AFA1E0BF2A6FC566A7B70D15C9BFABBA3756FB077797D16FFFA27800C05'
$directory = Join-Path $env:RUNNER_TEMP ('ss-python27-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $directory | Out-Null
$installer = Join-Path $directory 'python-2.7.18.amd64.msi'
$layout = Join-Path $directory 'runtime'
$log = Join-Path $directory 'extract.log'

Invoke-WebRequest -Uri $source -OutFile $installer -TimeoutSec 90
if ((Get-FileHash -LiteralPath $installer -Algorithm SHA256).Hash -ne $expected) {
    throw 'The Python 2.7.18 installer SHA-256 does not match the pinned official release.'
}
$arguments = @('/a', ('"' + $installer + '"'), '/qn', '/norestart',
               ('TARGETDIR="' + $layout + '"'), '/L*v', ('"' + $log + '"'))
$result = Start-Process -FilePath msiexec.exe -ArgumentList $arguments -PassThru -Wait -WindowStyle Hidden
if ($result.ExitCode -ne 0) {
    if (Test-Path -LiteralPath $log) { Get-Content -LiteralPath $log -Tail 30 }
    throw "Could not extract the Windows Python runtime (MSI exit $($result.ExitCode))."
}

$probe = @'
import ctypes
import hashlib
import imp
import struct
import sys
import zlib

assert sys.version_info[:3] == (2, 7, 18)
assert sys.platform == 'win32' and struct.calcsize('P') == 8
assert imp.get_magic() == b'\x03\xf3\r\n'
assert zlib.decompress(zlib.compress(b'probe')) == b'probe'
assert hashlib.sha256(b'abc').hexdigest() == 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad'
print(sys.version)
'@
function Test-VerifiedPython([string] $executable) {
    if (!(Test-Path -LiteralPath $executable -PathType Leaf)) { return $false }
    $PSNativeCommandUseErrorActionPreference = $false
    try {
        & $executable -E -s -B -c $probe | Write-Host
        return $LASTEXITCODE -eq 0
    } catch {
        return $false
    }
}

$python = Join-Path $layout 'python.exe'
if (!(Test-VerifiedPython $python)) {
    if ($env:GITHUB_ACTIONS -ne 'true') {
        throw 'The extracted Windows CPython failed the verification probe.'
    }
    # Some hosted images lack the VC90 runtime. The same pinned MSI supplies
    # its bundled private CRT during a per-user install on the disposable VM.
    Write-Host 'Preparing CPython with its bundled private Visual C++ runtime.'
    $layout = Join-Path $directory 'private-runtime'
    $log = Join-Path $directory 'install.log'
    $arguments = @('/i', ('"' + $installer + '"'), '/qn', '/norestart', 'ALLUSERS=""',
                   'ADDLOCAL=DefaultFeature,Extensions,PrivateCRT',
                   ('TARGETDIR="' + $layout + '"'), '/L*v', ('"' + $log + '"'))
    $result = Start-Process -FilePath msiexec.exe -ArgumentList $arguments -PassThru -Wait -WindowStyle Hidden
    $python = Join-Path $layout 'python.exe'
    if ($result.ExitCode -ne 0 -or !(Test-VerifiedPython $python)) {
        if (Test-Path -LiteralPath $log) { Get-Content -LiteralPath $log -Tail 30 }
        throw "Could not prepare verified Windows CPython (MSI exit $($result.ExitCode))."
    }
}
Add-Content -LiteralPath $env:GITHUB_ENV -Value "PYTHON27=$python" -Encoding utf8
