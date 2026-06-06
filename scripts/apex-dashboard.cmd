@echo off
setlocal
set "ROOT=%~dp0.."
set "URL=http://localhost:4177"

powershell.exe -NoProfile -ExecutionPolicy Bypass -Command ^
  "$url = '%URL%';" ^
  "$root = (Resolve-Path '%ROOT%').Path;" ^
  "$server = Join-Path $root 'dashboard/server.js';" ^
  "$alive = $false;" ^
  "try { Invoke-WebRequest -UseBasicParsing -Uri ($url + '/api/state') -TimeoutSec 2 | Out-Null; $alive = $true } catch {}" ^
  "$env:APEX_CHAT_PROVIDER = [Environment]::GetEnvironmentVariable('APEX_CHAT_PROVIDER','User');" ^
  "$env:GROQ_API_KEY = [Environment]::GetEnvironmentVariable('GROQ_API_KEY','User');" ^
  "$env:GROQ_MODEL = [Environment]::GetEnvironmentVariable('GROQ_MODEL','User');" ^
  "if (-not $alive) { Start-Process -FilePath 'node' -ArgumentList @($server) -WorkingDirectory $root -WindowStyle Hidden; Start-Sleep -Seconds 2 }" ^
  "Start-Process $url"
