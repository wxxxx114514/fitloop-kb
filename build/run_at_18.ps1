$ErrorActionPreference = "Continue"
$log = "D:\project\fitloop-kb\corpus\run_18.log"
function Say($m) { $line = "$(Get-Date -Format 'HH:mm:ss') $m"; Write-Host $line; Add-Content -Path $log -Value $line -Encoding utf8 }

Say "scheduler started, waiting for 18:00"
$target = Get-Date "18:00"
while ((Get-Date) -lt $target) { Start-Sleep -Seconds 60 }
Say "time reached, rebuilding corpus"

Set-Location "D:\project\fitloop-kb"
$env:PYTHONIOENCODING = "utf-8"
$py = ".venv\Scripts\python.exe"

$n = (Get-ChildItem "corpus\boxes" -Filter *.json | Measure-Object).Count
Say "boxes json count: $n"

& $py build\build_corpus.py 2>&1 | Tee-Object -FilePath $log -Append
& $py eval\run_eval.py bm25 2>&1 | Tee-Object -FilePath $log -Append
Say "done"