#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Production stress battery: three complementary worst-case eval scenarios.

.DESCRIPTION
    Scenario A — Budget crunch    (n=15, d=50,  budget=80,  noise=0.10)
      Context window is half the standard size. CAC's admission control should
      select the most critical evidence; RAG greedy-fills with lower-value chunks.

    Scenario B — Distractor flood  (n=20, d=100, budget=160, noise=0.10)
      2x the distractor load used in the stress eval. At 50d fixed_context_rag
      already hit 0% safe rate — this confirms the trend for all RAG methods.

    Scenario C — Metadata corruption (n=15, d=50, budget=160, noise=0.50)
      50% of metadata fields (topics, risk_tags) are stripped/corrupted.
      Schema-aware RAG depends heavily on metadata; CAC uses structural slot
      matching which is more robust to noisy tagging.

    Each scenario writes to its own output directory and includes a full
    LLM-as-judge pass (--judge flag).

.USAGE
    cd C:\Python310\CAC_v1_4_AUDIT_FULL
    $env:PYTHONPATH = '.'
    .\benchmarks\llm_runner\run_production_stress_battery.ps1
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Continue'   # don't abort on Python stderr (symlink warning)

$PYTHON   = 'C:\Python310\python.exe'
$RUNNER   = '-m benchmarks.llm_runner.run'
$MODEL    = 'microsoft/phi-3-mini-4k-instruct'
$DEVICE   = 'cuda'
$MAX_TOK  = '350'
$JTOK     = '80'
$env:PYTHONPATH = '.'

$scenarios = @(
    @{
        label  = 'A: Budget crunch (budget=80, d=50, n=15)'
        args   = "--n 15 --budget 80  --distractors 50  --metadata-noise 0.10 --max-new-tokens $MAX_TOK --judge --judge-max-new-tokens $JTOK --output-dir outputs/llm_eval_budget_crunch"
    },
    @{
        label  = 'B: Distractor flood (d=100, budget=160, n=20)'
        args   = "--n 20 --budget 160 --distractors 100 --metadata-noise 0.10 --max-new-tokens $MAX_TOK --judge --judge-max-new-tokens $JTOK --output-dir outputs/llm_eval_extreme_noise"
    },
    @{
        label  = 'C: Metadata corruption (noise=0.50, d=50, budget=160, n=15)'
        args   = "--n 15 --budget 160 --distractors 50  --metadata-noise 0.50 --max-new-tokens $MAX_TOK --judge --judge-max-new-tokens $JTOK --output-dir outputs/llm_eval_metadata_corruption"
    }
)

$start = Get-Date
Write-Host ""
Write-Host "=== CAC Production Stress Battery ===" -ForegroundColor Cyan
Write-Host "Started: $start"
Write-Host ""

foreach ($s in $scenarios) {
    $sStart = Get-Date
    Write-Host "--- $($s.label) ---" -ForegroundColor Yellow
    Write-Host "Started: $sStart"
    Write-Host ""

    $cmdArgs = "$RUNNER --model $MODEL --device $DEVICE $($s.args)"
    & $PYTHON $cmdArgs.Split(' ')

    $sEnd  = Get-Date
    $elapsed = ($sEnd - $sStart).ToString("hh\:mm\:ss")
    Write-Host ""
    Write-Host "Finished scenario in $elapsed" -ForegroundColor Green
    Write-Host ""
}

$end     = Get-Date
$total   = ($end - $start).ToString("hh\:mm\:ss")
Write-Host "=== Battery complete. Total time: $total ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Results:"
foreach ($s in $scenarios) {
    $dir = ($s.args -replace '.*--output-dir\s+(\S+).*','$1')
    Write-Host "  $dir"
}
