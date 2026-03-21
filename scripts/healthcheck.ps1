$ErrorActionPreference = "Continue"

Write-Output "API health:"
try {
  $health = Invoke-WebRequest -UseBasicParsing http://localhost:8000/health
  Write-Output $health.Content
} catch {
  Write-Output $_.Exception.Message
}

Write-Output "Frontend status:"
try {
  $web = Invoke-WebRequest -UseBasicParsing http://localhost:3000
  Write-Output $web.StatusCode
} catch {
  Write-Output $_.Exception.Message
}

