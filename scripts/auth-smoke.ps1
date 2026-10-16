$ErrorActionPreference = "Stop"

$apiBaseUrl = $env:VITE_API_BASE_URL
if (-not $apiBaseUrl) {
  $apiBaseUrl = "http://localhost:8050/api"
}

$timestamp = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
$email = "auth-smoke-$timestamp@example.com"
$password = "codesense123"
$displayName = "Auth Smoke User"

Write-Host "Checking backend health..."
Invoke-RestMethod -Uri "$apiBaseUrl/health" -Method Get | Out-Null

Write-Host "Registering test user $email..."
$registerBody = @{
  displayName = $displayName
  email = $email
  password = $password
} | ConvertTo-Json

$registerResponse = Invoke-RestMethod `
  -Uri "$apiBaseUrl/auth/register" `
  -Method Post `
  -ContentType "application/json" `
  -Body $registerBody

if (-not $registerResponse.token) {
  throw "Register did not return a JWT token."
}

Write-Host "Logging in with test user..."
$loginBody = @{
  email = $email
  password = $password
} | ConvertTo-Json

$loginResponse = Invoke-RestMethod `
  -Uri "$apiBaseUrl/auth/login" `
  -Method Post `
  -ContentType "application/json" `
  -Body $loginBody

if (-not $loginResponse.token) {
  throw "Login did not return a JWT token."
}

Write-Host "Auth smoke test passed."
Write-Host "User: $($loginResponse.user.email)"
