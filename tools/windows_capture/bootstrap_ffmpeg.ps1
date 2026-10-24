$ErrorActionPreference = 'Stop'
$build = 'n9.0.2-28-g669f5ab083'
$asset = 'ffmpeg-n9.0.2-28-g669f5ab083-win64-gpl-9.0.zip'
$sha256 = 'a38198cc130ed3fa02097d0baebcea9c1b8a9d9d3d1d8161d691d1f03709158b'
$url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/autobuild-2026-10-18-13-01/$asset"
$root = Join-Path $PSScriptRoot "..\runtime\ffmpeg\$build"
$archive = Join-Path $env:TEMP $asset
Invoke-WebRequest -Uri $url -OutFile $archive
if ((Get-FileHash $archive -Algorithm SHA256).Hash.ToLowerInvariant() -ne $sha256) { throw 'FFmpeg archive checksum mismatch.' }
Remove-Item -Recurse -Force $root -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force $root | Out-Null
Expand-Archive -Path $archive -DestinationPath $root
$ffmpeg = Get-ChildItem $root -Recurse -Filter ffmpeg.exe | Select-Object -First 1
$ffprobe = Get-ChildItem $root -Recurse -Filter ffprobe.exe | Select-Object -First 1
if (!$ffmpeg -or !$ffprobe) { throw 'Pinned archive did not contain ffmpeg.exe and ffprobe.exe.' }
New-Item -ItemType Directory -Force (Join-Path $root 'bin') | Out-Null
Copy-Item $ffmpeg.FullName (Join-Path $root 'bin\ffmpeg.exe')
Copy-Item $ffprobe.FullName (Join-Path $root 'bin\ffprobe.exe')
if (!((& (Join-Path $root 'bin\ffmpeg.exe') -version) -match $build)) { throw 'Pinned ffmpeg version mismatch.' }
& (Join-Path $root 'bin\ffprobe.exe') -version | Out-Null
Write-Host "Pinned FFmpeg $build installed at $root"
