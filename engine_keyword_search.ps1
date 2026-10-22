<#
.SYNOPSIS
    engine_keyword_search.ps1 - Zero-Redundancy 1-Shot Mega-Batch Architecture
    Category: engine
    Function: keyword_search
    API Consumption is GUARANTEED to be:
    - 0 Calls: If all target keywords already exist in Tier 2 Cache.
    - Exactly 1 Call: Merges Multi-Seeds + Missing Keywords into ONE array, executed via match_keywords (limit: 100).
#>

param(
    [string]$QueryFile = "query.json",
    [switch]$ForceRefresh = $false,
    [int]$MinThreshold = 25
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $ScriptDir "api_ubersuggest_client.ps1")

$CacheFile = Join-Path $ScriptDir "verified_volume_cache.json"
$DbFile    = Join-Path $ScriptDir "keywords_db.json"
$CsvFile   = Join-Path $ScriptDir "keywords.csv"

if (-not (Test-Path $QueryFile)) {
    Write-Error "Query file not found: $QueryFile"
    exit 1
}

$queryJson = [System.IO.File]::ReadAllText($QueryFile, [System.Text.Encoding]::UTF8)
$parsedQuery = $queryJson | ConvertFrom-Json

$keywordList = [System.Collections.ArrayList]@()
$seeds = [System.Collections.ArrayList]@()

if ($parsedQuery -is [System.Array]) {
    foreach ($item in $parsedQuery) {
        if ($item -is [string]) { [void]$keywordList.Add($item) }
        elseif ($item.keyword) { [void]$keywordList.Add($item.keyword) }
    }
} elseif ($parsedQuery.keywords -and ($parsedQuery.keywords -is [System.Array])) {
    foreach ($kw in $parsedQuery.keywords) { [void]$keywordList.Add($kw) }
    if ($parsedQuery.seed_keywords -and ($parsedQuery.seed_keywords -is [System.Array])) {
        foreach ($s in $parsedQuery.seed_keywords) { [void]$seeds.Add($s) }
    } elseif ($parsedQuery.seed_keyword) {
        [void]$seeds.Add($parsedQuery.seed_keyword)
    }
} elseif ($parsedQuery.keyword) {
    [void]$keywordList.Add($parsedQuery.keyword)
    if ($parsedQuery.seed_keyword) { [void]$seeds.Add($parsedQuery.seed_keyword) }
}

if ($keywordList.Count -eq 0) {
    Write-Error "No keywords found in $QueryFile"
    exit 1
}

$STAR_3 = "$([char]0x2606)$([char]0x2606)$([char]0x2606)"
$STAR_2 = "$([char]0x2606)$([char]0x2606)"
$STAR_1 = "$([char]0x2606)"
$STAR_NONE = "-"

function Get-StarScore([string]$kw, [int]$vol = 0, [int]$sd = 0) {
    # ユーザー規約に基づく真の星判定ロジック:
    # 1. 検索上位10位のドメイン取得
    # 2. UbersuggestでDA調査
    # 3. DA一桁(1〜9)のサイト数 = ★の数
    # 4. 知恵袋などのQ&Aサイト = ☆扱い（参入チャンスとして加点）
    # 5. noteは除く
    try {
        $evalScript = Join-Path $ScriptDir "engine_star_evaluator.py"
        if (Test-Path $evalScript) {
            $cmd = "import sys, engine_star_evaluator, json; s, m = engine_star_evaluator.evaluate_keyword_stars(sys.argv[1]); print(json.dumps({'star': s, 'meta': m}))"
            $out = & python -c $cmd "$kw" 2>$null
            if ($out) {
                $parsed = $out | ConvertFrom-Json
                if ($parsed.star) { return $parsed.star }
            }
        }
    } catch {}

    # フォールバック (万一SERP取得不能時)
    if ($vol -ge 1000 -and $sd -le 35) { return $STAR_2 }
    if ($vol -ge 100 -and $sd -le 50) { return $STAR_1 }
    return $STAR_NONE
}

# 1. Load Tier 2 Cache
$cache = @{}
if (Test-Path $CacheFile) {
    $rawCache = [System.IO.File]::ReadAllText($CacheFile, [System.Text.Encoding]::UTF8)
    if (-not [string]::IsNullOrWhiteSpace($rawCache)) {
        $parsedCache = $rawCache | ConvertFrom-Json
        foreach ($prop in $parsedCache.PSObject.Properties) {
            $cache[$prop.Name] = $prop.Value
        }
    }
}

# 2. Load Tier 1 DB
$dbItems = [System.Collections.ArrayList]@()
if (Test-Path $DbFile) {
    $rawDb = [System.IO.File]::ReadAllText($DbFile, [System.Text.Encoding]::UTF8)
    if (-not [string]::IsNullOrWhiteSpace($rawDb)) {
        $dbObj = $rawDb | ConvertFrom-Json
        if ($dbObj.keywords) { $dbItems = [System.Collections.ArrayList]@($dbObj.keywords) }
    }
}

# 3. Diff Guard: Check Missing Keywords
$missingKeywords = [System.Collections.ArrayList]@()
foreach ($kw in $keywordList) {
    if ($ForceRefresh -or (-not $cache.ContainsKey($kw))) {
        [void]$missingKeywords.Add($kw)
    }
}

Write-Host ">>> Total Target Keywords: $($keywordList.Count)"
Write-Host ">>> Cache Hit: $($keywordList.Count - $missingKeywords.Count) (API: 0)"
Write-Host ">>> Missing: $($missingKeywords.Count)"

$nowStr = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
$cacheModified = $false
$dbModified = $false

$thresholdBlocked = $false
# 4. If any are missing, merge seeds + missing keywords into ONE MEGA-BATCH array and call API EXACTLY ONCE
if ($missingKeywords.Count -gt 0) {
    $megaBatchArray = [System.Collections.ArrayList]@()

    # Add seeds first
    foreach ($s in $seeds) {
        if (-not [string]::IsNullOrWhiteSpace($s) -and (-not $megaBatchArray.Contains($s))) {
            [void]$megaBatchArray.Add($s)
        }
    }

    # Add missing target keywords
    foreach ($m in $missingKeywords) {
        if (-not [string]::IsNullOrWhiteSpace($m) -and (-not $megaBatchArray.Contains($m))) {
            [void]$megaBatchArray.Add($m)
        }
    }

    if ($megaBatchArray.Count -lt $MinThreshold) {
        $thresholdBlocked = $true
        $deficit = $MinThreshold - $megaBatchArray.Count
        Write-Host "`n>>> [THRESHOLD_GUARD_BLOCKED] Aborting API Call!"
        Write-Host ">>> Current terms: $($megaBatchArray.Count). Required minimum: $MinThreshold (Deficit: $deficit terms)."
        Write-Host ">>> To maximize API efficiency, at least $MinThreshold terms are required before calling Ubersuggest API."
    } else {
        Write-Host "`n>>> [1-SHOT MEGA-BATCH] Executing EXACTLY 1 API call for $($megaBatchArray.Count) merged terms..."
        Write-Host ">>> Merged Terms: $($megaBatchArray -join ', ')"

        try {
            $apiResults = Get-MatchingKeywords -Keywords $megaBatchArray -Limit 100
            
            # Normalize $apiResults to an array of keyword items
            $normalizedResults = @()
            if ($apiResults) {
                if ($apiResults.keywords -and ($apiResults.keywords -is [System.Array])) {
                    $normalizedResults = $apiResults.keywords
                } elseif ($apiResults -is [System.Array]) {
                    $normalizedResults = $apiResults
                } elseif ($apiResults.data -and ($apiResults.data -is [System.Array])) {
                    $normalizedResults = $apiResults.data
                } else {
                    $normalizedResults = @($apiResults)
                }
            }

            if ($normalizedResults -and $normalizedResults.Count -gt 0) {
                Write-Host ">>> [MEGA-INGESTION] Received $($normalizedResults.Count) keywords. Ingesting into Cache & DB..."
                foreach ($item in $normalizedResults) {
                    $kwName = $item.keyword
                    if ([string]::IsNullOrWhiteSpace($kwName)) { continue }
                    $vol = if ($item.search_volume) { [int]$item.search_volume } elseif ($item.volume) { [int]$item.volume } else { 0 }
                    $sd  = if ($item.seo_difficulty) { [int]$item.seo_difficulty } elseif ($item.sd) { [int]$item.sd } else { 0 }
                    $star = Get-StarScore -kw $kwName -vol $vol -sd $sd

                    # Update Tier 2 Cache
                    $cache[$kwName] = [PSCustomObject]@{
                        volume      = $vol
                        sd          = $sd
                        star_rating = $star
                        verified_at = $nowStr
                    }
                    $cacheModified = $true

                    # Update Tier 1 DB
                    $foundDb = $null
                    foreach ($it in $dbItems) { if ($it.keyword -eq $kwName) { $foundDb = $it; break } }
                    if ($foundDb) {
                        $foundDb.volume = $vol
                        $foundDb.sd = $sd
                        $foundDb.star_rating = $star
                        $foundDb.updated_at = $nowStr
                    } else {
                        $newDb = [PSCustomObject]@{
                            keyword        = $kwName
                            seed_keyword   = ($seeds -join ", ")
                            expansion_type = "MEGA_BATCH"
                            volume         = $vol
                            sd             = $sd
                            star_rating    = $star
                            search_intent  = ""
                            created_at     = $nowStr
                            updated_at     = $nowStr
                        }
                        [void]$dbItems.Add($newDb)
                    }
                    $dbModified = $true
                }
            }
        } catch {
            Write-Host "Mega-Batch Notice: $($_.Exception.Message)"
        }

        # If keywords are not in DB, add them with unverified/exhausted status so UI displays them
        foreach ($m in $missingKeywords) {
            $alreadyInDb = $false
            foreach ($it in $dbItems) {
                if ($it.keyword -eq $m) { $alreadyInDb = $true; break }
            }
            if (-not $alreadyInDb) {
                $newDb = [PSCustomObject]@{
                    keyword        = $m
                    seed_keyword   = ($seeds -join ", ")
                    expansion_type = "MEGA_BATCH"
                    volume         = $null
                    sd             = $null
                    star_rating    = "UNCHECKED"
                    search_intent  = ""
                    created_at     = $nowStr
                    updated_at     = $nowStr
                }
                [void]$dbItems.Add($newDb)
                $dbModified = $true
            }
        }
    }
} else {
    Write-Host "`n>>> [PERFECT CACHE HIT] All $($keywordList.Count) keywords resolved locally. API Consumption: 0 Calls!"
}

# 5. Persist Storage if updated
if ($cacheModified) {
    $cacheJson = $cache | ConvertTo-Json -Depth 5
    [System.IO.File]::WriteAllText($CacheFile, $cacheJson, [System.Text.Encoding]::UTF8)
}

if ($dbModified) {
    $newDbObj = [PSCustomObject]@{
        updated_at = $nowStr
        keywords   = $dbItems
    }
    $newDbJson = $newDbObj | ConvertTo-Json -Depth 5
    [System.IO.File]::WriteAllText($DbFile, $newDbJson, [System.Text.Encoding]::UTF8)

    $dbItems | Select-Object star_rating, keyword, seed_keyword, expansion_type, volume, sd, search_intent, updated_at |
        Export-Csv -Path $CsvFile -NoTypeInformation -Encoding UTF8
}

# 6. Format Final Result Table
$finalResults = [System.Collections.ArrayList]@()
foreach ($kw in $keywordList) {
    if ($cache.ContainsKey($kw)) {
        $cached = $cache[$kw]
        $entry = [PSCustomObject]@{
            keyword     = $kw
            volume      = $cached.volume
            sd          = $cached.sd
            star_rating = $cached.star_rating
            source      = "RESOLVED"
            status      = "OK"
        }
        [void]$finalResults.Add($entry)
    } else {
        $src = if ($thresholdBlocked) { "THRESHOLD_NOT_MET(<25)" } else { "API_EXHAUSTED_OR_MISSING" }
        $entry = [PSCustomObject]@{
            keyword     = $kw
            volume      = $null
            sd          = $null
            star_rating = "UNCHECKED"
            source      = $src
            status      = "UNAVAILABLE"
        }
        [void]$finalResults.Add($entry)
    }
}

Write-Host "`n=== 1-SHOT MEGA-BATCH FINAL SUMMARY ==="
$finalResults | Format-Table -Property star_rating, keyword, volume, sd, source, status -AutoSize
