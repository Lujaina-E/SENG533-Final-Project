foreach ($users in @(10, 25, 50, 100, 200)) {
    Write-Host "Running $users users..." -ForegroundColor Cyan
    locust -f locust_persistence.py `
        --host http://localhost:1111 `
        --headless `
        --users $users `
        --spawn-rate 10 `
        --run-time 30s `
        --csv "results_${users}users" `
        --csv-full-history
    Write-Host "Done. Waiting 5s..." -ForegroundColor Yellow
    Start-Sleep -Seconds 5
}
Write-Host "All done!" -ForegroundColor Green