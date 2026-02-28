# Seed the database once
Write-Host "Seeding database..." -ForegroundColor Cyan
Invoke-RestMethod "http://localhost:1111/tools.descartes.teastore.persistence/rest/generatedb?categories=5&products=10&users=100&orders=10"

# Then poll until seeding is complete
do {
    $result = Invoke-RestMethod "http://localhost:1111/tools.descartes.teastore.persistence/rest/generatedb/finished"
    Write-Host "$(Get-Date -Format 'HH:mm:ss') - $result"
    Start-Sleep -Seconds 3
} while ($result -ne "true")

Write-Host "Database is ready!" -ForegroundColor Green

# param(
#     [string]$Host = 'localhost',
#     [int]$Port = 1111,
#     [int]$Categories = 5,
#     [int]$Products = 10,
#     [int]$Users = 100,
#     [int]$Orders = 10,
#     [int]$PollIntervalSeconds = 3,
#     [int]$MaxRetries = 0
# )

# $baseUrl = "http://$Host:$Port/tools.descartes.teastore.persistence/rest"

# Write-Host "Triggering DB generation at $baseUrl/generatedb?categories=$Categories&products=$Products&users=$Users&orders=$Orders"
# try {
#     Invoke-RestMethod "$baseUrl/generatedb?categories=$Categories&products=$Products&users=$Users&orders=$Orders" -Method Get -ErrorAction Stop | Out-Null
# } catch {
#     Write-Host "Failed to trigger generation: $_" -ForegroundColor Red
#     exit 2
# }

# $attempt = 0
# do {
#     try {
#         $result = Invoke-RestMethod "$baseUrl/generatedb/finished" -Method Get -ErrorAction Stop
#     } catch {
#         Write-Host "Error polling status: $_" -ForegroundColor Yellow
#         $result = 'false'
#     }

#     $timestamp = Get-Date -Format 'HH:mm:ss'
#     Write-Host "$timestamp - generation finished? -> $result"

#     if ($result -eq 'true') { break }

#     Start-Sleep -Seconds $PollIntervalSeconds
#     $attempt++
#     if ($MaxRetries -gt 0 -and $attempt -ge $MaxRetries) {
#         Write-Host "Reached max retries ($MaxRetries). Exiting." -ForegroundColor Red
#         exit 3
#     }
# } while ($true)

# Write-Host "Database is ready!" -ForegroundColor Green

# <#
# Usage examples:
# .
#   # Default:
#   .\wait_for_generatedb.ps1

#   # Custom host/port and counts:
#   .\wait_for_generatedb.ps1 -Host 127.0.0.1 -Port 1111 -Categories 5 -Products 10 -Users 100 -Orders 10

#   # Stop after 100 polls (3s interval -> ~5 minutes):
#   .\wait_for_generatedb.ps1 -MaxRetries 100
# #>
