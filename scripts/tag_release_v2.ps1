Param(
    [string]$Version = "v2.0.0",
    [switch]$SkipTests,
    [switch]$Force
)

Write-Host "[tag] Preparing release tag $Version" -ForegroundColor Cyan

# 1. Ensure git is available
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Error "git CLI não encontrado. Instale antes de prosseguir."; exit 1
}

# 2. Validate current branch
$branch = (git rev-parse --abbrev-ref HEAD).Trim()
if ($branch -ne "inicial" -and -not $Force) {
    Write-Warning "Branch atual: $branch. Recomenda-se taggar a partir de 'inicial'. Use -Force para ignorar."; exit 1
}

# 3. Check working tree cleanliness
$status = git status --porcelain
if ($status) {
    Write-Warning "Working tree tem alterações não commitadas. Limpe ou use -Force.";
    if (-not $Force) { exit 1 }
}

# 4. Optional test run
if (-not $SkipTests) {
    Write-Host "[tag] Executando suite de testes (pytest -q)" -ForegroundColor Yellow
    Push-Location backend
    & D:/provemaps_beta/venv/Scripts/python.exe -m pytest -q
    $testExitCode = $LASTEXITCODE
    Pop-Location
    if ($testExitCode -ne 0) { Write-Error "Testes falharam. Abortando tagging."; exit 1 }
    Write-Host "[tag] Testes OK" -ForegroundColor Green
}

# 5. Check existing tag
$existing = git tag --list $Version
if ($existing -and -not $Force) {
    Write-Error "Tag $Version já existe. Use -Force para recriar (irá sobrescrever remoto)."; exit 1
}

# 6. Create annotated tag
Write-Host "[tag] Criando tag anotada $Version" -ForegroundColor Cyan
$tagMessage = "Release $Version - Refatoração Modular (Fase 5)"
if ($existing -and $Force) {
    git tag -d $Version | Out-Null
}

git tag -a $Version -m $tagMessage
if ($LASTEXITCODE -ne 0) { Write-Error "Falha ao criar tag."; exit 1 }

# 7. Push tag
Write-Host "[tag] Enviando tag para origin" -ForegroundColor Cyan
git push origin $Version
if ($LASTEXITCODE -ne 0) { Write-Error "Falha ao enviar tag."; exit 1 }

Write-Host "[tag] Tag $Version criada e enviada com sucesso." -ForegroundColor Green

# 8. Optional release notes hint
Write-Host "[tag] Crie release no GitHub usando CHANGELOG e PR template." -ForegroundColor Yellow
