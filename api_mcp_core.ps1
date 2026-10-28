<#
.SYNOPSIS
    api_mcp_core.ps1 - Ubersuggest MCP JSON-RPC 2.0 Transport & Raw Audit Logger
    Category: api
    Function: mcp_transport_core
    Rule 05 Pure ASCII compliant.
#>

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ArchiveFile = Join-Path $ScriptDir "raw_api_archive.json"

$ExhaustPattern = '(?i)(HTTP\s*429|HTTP\s*403|HTTP\s*502|HTTP\s*503|Rate\s*limited|daily\s*report\s*limit|bearer\s*token\s*expired|timed\s*out|temporarily\s*unavailable)'

function Get-UbersuggestEndpointConfig {
    $userHome = $env:USERPROFILE
    $candidateConfigs = @(
        (Join-Path $userHome ".gemini\antigravity\mcp_config.json"),
        (Join-Path $userHome ".gemini\config\mcp_config.json"),
        (Join-Path $userHome ".gemini\antigravity-cli\mcp_config.json")
    )
    $candidateTokens = @(
        (Join-Path $userHome ".gemini\antigravity\mcp_oauth_tokens.json"),
        (Join-Path $userHome ".gemini\antigravity-cli\mcp_oauth_tokens.json")
    )

    $serverUrl = "https://ubersuggest-mcp.neilpatelapi.com/mcp"
    $authToken = ""

    # Check tokens first for latest access_token
    foreach ($tf in $candidateTokens) {
        if (Test-Path $tf) {
            try {
                $rawT = [System.IO.File]::ReadAllText($tf, [System.Text.Encoding]::UTF8)
                $parsedT = $rawT | ConvertFrom-Json
                if ($parsedT.access_token) {
                    $authToken = $parsedT.access_token
                    break
                }
                foreach ($prop in $parsedT.PSObject.Properties) {
                    $val = $prop.Value
                    if ($val -and $val.token -and $val.token.access_token) {
                        $authToken = $val.token.access_token
                        break
                    } elseif ($val -and $val.access_token) {
                        $authToken = $val.access_token
                        break
                    }
                }
                if (-not [string]::IsNullOrWhiteSpace($authToken)) { break }
            } catch {}
        }
    }

    # Check configs
    foreach ($cf in $candidateConfigs) {
        if (Test-Path $cf) {
            try {
                $rawC = [System.IO.File]::ReadAllText($cf, [System.Text.Encoding]::UTF8)
                $parsedC = $rawC | ConvertFrom-Json
                if ($parsedC.mcpServers -and $parsedC.mcpServers.ubersuggest) {
                    $uber = $parsedC.mcpServers.ubersuggest
                    if ($uber.serverUrl) { $serverUrl = $uber.serverUrl }
                    if ([string]::IsNullOrWhiteSpace($authToken) -and $uber.headers -and $uber.headers.Authorization) {
                        $authToken = ($uber.headers.Authorization -replace "^Bearer\s+", "")
                    }
                    if (-not [string]::IsNullOrWhiteSpace($authToken)) { break }
                }
            } catch {}
        }
    }

    return [PSCustomObject]@{
        ServerUrl = $serverUrl
        AuthToken = $authToken
    }
}

function Save-RawArchive ($endpoint, $targetKey, $rawJson) {
    try {
        $archives = @()
        if (Test-Path $ArchiveFile) {
            $existingText = [System.IO.File]::ReadAllText($ArchiveFile, [System.Text.Encoding]::UTF8)
            if (-not [string]::IsNullOrWhiteSpace($existingText)) {
                $archives = [System.Collections.ArrayList]@($existingText | ConvertFrom-Json)
            }
        }
        $entry = [PSCustomObject]@{
            id          = "arc-" + [System.Guid]::NewGuid().ToString().Substring(0, 8)
            endpoint    = $endpoint
            target_key  = $targetKey
            response    = $rawJson
            created_at  = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
        }
        [void]$archives.Add($entry)
        $outJson = $archives | ConvertTo-Json -Depth 10
        [System.IO.File]::WriteAllText($ArchiveFile, $outJson, [System.Text.Encoding]::UTF8)
    } catch {}
}

function Forward-RemoteMcp([string]$PayloadJson) {
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.SecurityProtocolType]::Tls12

    $cfg = Get-UbersuggestEndpointConfig
    if ([string]::IsNullOrWhiteSpace($cfg.AuthToken)) {
        throw "EXHAUSTED: Ubersuggest Authorization token not found in user profile configurations."
    }

    $headers = @{
        "Authorization" = "Bearer $($cfg.AuthToken)"
        "Content-Type"  = "application/json"
        "Accept"        = "application/json, text/event-stream"
        "User-Agent"    = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AntigravityMCP/2.0"
    }

    try {
        $response = Invoke-RestMethod -Uri $cfg.ServerUrl -Method Post -Headers $headers -Body $PayloadJson -TimeoutSec 30
        if ($response -is [string]) {
            return $response
        }
        return ($response | ConvertTo-Json -Depth 10 -Compress)
    } catch [System.Net.WebException] {
        $webEx = $_.Exception
        $statusCode = ""
        $respBody = ""
        if ($webEx.Response) {
            $respStream = $webEx.Response.GetResponseStream()
            if ($respStream) {
                $reader = New-Object System.IO.StreamReader($respStream, [System.Text.Encoding]::UTF8)
                $respBody = $reader.ReadToEnd()
            }
            if ($webEx.Response.StatusCode) {
                $statusCode = [int]$webEx.Response.StatusCode
            }
        }
        $combinedMsg = "HTTP $statusCode $($webEx.Message) $respBody"
        Save-RawArchive -endpoint "error_upstream" -targetKey "HTTP_$statusCode" -rawJson $combinedMsg
        if ($combinedMsg -match $ExhaustPattern) {
            throw "EXHAUSTED: $combinedMsg"
        }
        throw "Ubersuggest MCP HTTP Error ($statusCode): $($webEx.Message)"
    } catch {
        $exMsg = $_.Exception.Message
        if ($exMsg -match $ExhaustPattern) {
            throw "EXHAUSTED: $exMsg"
        }
        throw $_
    }
}
