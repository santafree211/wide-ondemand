<#
.SYNOPSIS
    engine_star_evaluator.ps1 - SERP Star Rating Bridge for PowerShell Pipeline
    Category: engine
    Function: star_evaluator
    Rule 05 Pure ASCII compliant.
#>

$STAR_3 = "$([char]0x2606)$([char]0x2606)$([char]0x2606)"
$STAR_2 = "$([char]0x2606)$([char]0x2606)"
$STAR_1 = "$([char]0x2606)"
$STAR_NONE = "-"

function Get-StarScore([string]$kw, [int]$vol = 0, [int]$sd = 0) {
    # Calls engine_star_evaluator.py (Google Official SERP + 1-digit DA check)
    try {
        $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
        $evalScript = Join-Path $scriptDir "engine_star_evaluator.py"
        if (Test-Path $evalScript) {
            $cmd = "import sys, engine_star_evaluator, json; s, m = engine_star_evaluator.evaluate_keyword_stars(sys.argv[1]); print(json.dumps({'star': s, 'meta': m}))"
            $out = & python -c $cmd "$kw" 2>$null
            if ($out) {
                $parsed = $out | ConvertFrom-Json
                if ($parsed.star) { return $parsed.star }
            }
        }
    } catch {}

    # Fallback to Vol/SD metrics if Python call unavailable
    if ($vol -ge 1000 -and $sd -le 35) { return $STAR_2 }
    if ($vol -ge 100 -and $sd -le 50) { return $STAR_1 }
    return $STAR_NONE
}
