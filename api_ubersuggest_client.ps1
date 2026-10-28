<#
.SYNOPSIS
    api_ubersuggest_client.ps1 - Ubersuggest MCP Individual API Methods Client
    Category: api
    Function: ubersuggest_client
    Rule 05 Pure ASCII compliant.
#>

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Import MCP transport core module
. (Join-Path $ScriptDir "api_mcp_core.ps1")

function Invoke-UberMcpCall {
    param(
        [Parameter(Mandatory=$true)][string]$ToolName,
        [Parameter(Mandatory=$true)][hashtable]$Arguments,
        [string]$TargetKey = ""
    )

    $guidStr = [System.Guid]::NewGuid().ToString().Substring(0, 8)
    $reqPayload = @{
        jsonrpc = "2.0"
        id      = "req-$guidStr"
        method  = "tools/call"
        params  = @{
            name      = $ToolName
            arguments = $Arguments
        }
    } | ConvertTo-Json -Compress -Depth 10

    $rawResponse = Forward-RemoteMcp $reqPayload
    if ([string]::IsNullOrWhiteSpace($rawResponse)) {
        return $null
    }

    Save-RawArchive -endpoint $ToolName -targetKey $TargetKey -rawJson $rawResponse

    # Unwrap Server-Sent Events (SSE) if present: "event: message\ndata: {...}"
    $cleanJson = $rawResponse
    if ($cleanJson -match '(?ms)data:\s*(\{.*\})') {
        $cleanJson = $Matches[1]
    } elseif ($cleanJson -match '(?ms)data:\s*(.*)$') {
        $cleanJson = $Matches[1].Trim()
    }

    $parsed = $null
    try {
        $parsed = $cleanJson | ConvertFrom-Json
    } catch {
        throw "JSON parse failed on payload: $($_.Exception.Message)"
    }

    if ($parsed.error) {
        $msg = $parsed.error.message
        if ($msg -match $ExhaustPattern) {
            throw "EXHAUSTED: $msg"
        }
        throw "MCP RPC Error: $msg"
    }

    if ($parsed.result.isError) {
        $errMsg = $parsed.result.content[0].text
        if ($errMsg -match $ExhaustPattern) {
            throw "EXHAUSTED: $errMsg"
        }
        throw "Ubersuggest Upstream Error: $errMsg"
    }

    if ($parsed.result.content -and $parsed.result.content.Count -gt 0) {
        $text = $parsed.result.content[0].text
        return ($text | ConvertFrom-Json)
    }

    return $null
}

function Get-SerpAnalysis {
    param([Parameter(Mandatory=$true)][string]$Keyword)
    $argsObj = @{
        keyword  = $Keyword
        locId    = 2392
        language = "ja"
    }
    return Invoke-UberMcpCall -ToolName "serp_analysis" -Arguments $argsObj -TargetKey $Keyword
}

function Get-MatchingKeywords {
    param(
        [Parameter(Mandatory=$true)]$Keywords,
        [int]$Limit = 100
    )

    $kwArray = [System.Collections.ArrayList]@()
    if ($Keywords -is [System.Array]) {
        foreach ($k in $Keywords) { [void]$kwArray.Add([string]$k) }
    } else {
        [void]$kwArray.Add([string]$Keywords)
    }

    $argsObj = @{
        keywords = $kwArray
        locId    = 2392
        language = "ja"
        limit    = $Limit
    }
    return Invoke-UberMcpCall -ToolName "match_keywords" -Arguments $argsObj -TargetKey ($kwArray -join ", ")
}

function Get-DomainKeywords {
    param([Parameter(Mandatory=$true)][string]$Domain)
    $argsObj = @{
        domain = $Domain
        locId  = 2392
    }
    return Invoke-UberMcpCall -ToolName "domain_keywords" -Arguments $argsObj -TargetKey $Domain
}

function Get-KeywordOverview {
    param([Parameter(Mandatory=$true)][string]$Keyword)
    $argsObj = @{
        keyword  = $Keyword
        locId    = 2392
        language = "ja"
    }
    return Invoke-UberMcpCall -ToolName "keyword_overview" -Arguments $argsObj -TargetKey $Keyword
}
