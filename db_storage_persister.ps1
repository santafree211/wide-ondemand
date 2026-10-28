<#
.SYNOPSIS
    db_storage_persister.ps1 - Multi-Tier Cache (Tier 2) & Master DB (Tier 1) Storage Engine
    Category: db
    Function: storage_persister
    Rule 05 Pure ASCII compliant.
#>

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$CacheFile = Join-Path $ScriptDir "verified_volume_cache.json"
$DbFile    = Join-Path $ScriptDir "keywords_db.json"
$CsvFile   = Join-Path $ScriptDir "keywords.csv"

function Load-Tier2Cache {
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
    return $cache
}

function Load-Tier1Db {
    $dbItems = [System.Collections.ArrayList]@()
    if (Test-Path $DbFile) {
        $rawDb = [System.IO.File]::ReadAllText($DbFile, [System.Text.Encoding]::UTF8)
        if (-not [string]::IsNullOrWhiteSpace($rawDb)) {
            $dbObj = $rawDb | ConvertFrom-Json
            if ($dbObj.keywords) { $dbItems = [System.Collections.ArrayList]@($dbObj.keywords) }
        }
    }
    return $dbItems
}

function Save-Tier2Cache($cache) {
    try {
        $cacheJson = $cache | ConvertTo-Json -Depth 5
        [System.IO.File]::WriteAllText($CacheFile, $cacheJson, [System.Text.Encoding]::UTF8)
    } catch {}
}

function Save-Tier1Db($dbItems, $nowStr) {
    try {
        $newDbObj = [PSCustomObject]@{
            updated_at = $nowStr
            keywords   = $dbItems
        }
        $newDbJson = $newDbObj | ConvertTo-Json -Depth 5
        [System.IO.File]::WriteAllText($DbFile, $newDbJson, [System.Text.Encoding]::UTF8)

        $dbItems | Select-Object star_rating, keyword, seed_keyword, expansion_type, volume, sd, search_intent, updated_at |
            Export-Csv -Path $CsvFile -NoTypeInformation -Encoding UTF8
    } catch {}
}
