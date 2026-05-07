# Run this once to apply branch protection to main.
# Requires a GitHub PAT with 'repo' scope.
# Usage: .\set-branch-protection.ps1 -Token "ghp_yourtoken"

param(
    [Parameter(Mandatory=$true)]
    [string]$Token
)

$headers = @{
    Authorization  = "Bearer $Token"
    Accept         = "application/vnd.github+json"
    "X-GitHub-Api-Version" = "2022-11-28"
}

$body = @{
    required_status_checks = @{
        strict   = $true
        contexts = @(
            "lint-and-typecheck",
            "test"
        )
    }
    enforce_admins                  = $false
    required_pull_request_reviews   = @{
        dismiss_stale_reviews           = $true
        require_code_owner_reviews      = $true
        required_approving_review_count = 0
    }
    restrictions                    = $null
    required_conversation_resolution = $true
    allow_force_pushes               = $false
    allow_deletions                  = $false
} | ConvertTo-Json -Depth 5

$uri = "https://api.github.com/repos/Farhan4711/psx-ai-quant-trading-intelligence/branches/main/protection"

try {
    $response = Invoke-RestMethod -Uri $uri -Method Put -Headers $headers -Body $body -ContentType "application/json"
    Write-Host "Branch protection applied successfully." -ForegroundColor Green
    Write-Host "URL: https://github.com/Farhan4711/psx-ai-quant-trading-intelligence/settings/branches"
} catch {
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Response: $($_.ErrorDetails.Message)" -ForegroundColor Red
}
