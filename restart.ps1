$port = 8000
$pids_list = netstat -ano | findstr ":$port " | ForEach-Object { ($_ -split '\s+')[-1] } | Sort-Object -Unique
foreach ($p in $pids_list) {
    taskkill /PID $p /F 2>$null
}
uvicorn app.main:app --port $port --reload
