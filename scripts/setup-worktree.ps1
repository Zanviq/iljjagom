<#
.SYNOPSIS
  일짜곰: 기능 브랜치용 git worktree를 만들고, documents/for-claude 를 메인 폴더와
  디렉터리 junction(링크)으로 공유시킨다. 멱등(여러 번 실행해도 안전).

.DESCRIPTION
  - for-claude 는 .gitignore 대상이라 새 worktree 에는 존재하지 않는다.
  - 이 스크립트가 메인 폴더의 실제 for-claude 를 가리키는 junction 을 만들어
    세 세션(main/backend/frontend)이 같은 문서를 즉시 공유하게 한다.
  - instructions 등 git 추적 문서는 각 worktree 에 git 이 자동으로 둔다(링크 불필요).

.EXAMPLE
  pwsh scripts/setup-worktree.ps1 -Branch frontend
  pwsh scripts/setup-worktree.ps1 -Branch backend
#>
param(
  [Parameter(Mandatory = $true)]
  [string]$Branch,                      # 예: frontend, backend
  [string]$MainPath = "C:\Users\jaemi\Documents\Project\iljjagom"
)

$ErrorActionPreference = 'Stop'

$wtPath = Join-Path (Split-Path $MainPath -Parent) ("iljjagom-" + $Branch)
$src    = Join-Path $MainPath "documents\for-claude"
$link   = Join-Path $wtPath  "documents\for-claude"

if (-not (Test-Path $src)) { throw "메인 for-claude 가 없습니다: $src (이 스크립트는 메인 폴더 기준으로 실행하세요)" }

# 1) worktree 보장
$listed = (& git -C $MainPath worktree list) -join "`n"
if ($listed -like "*$wtPath*") {
  Write-Host "worktree 이미 존재: $wtPath"
} else {
  $branchExists = (& git -C $MainPath branch --list $Branch)
  if ($branchExists) {
    & git -C $MainPath worktree add $wtPath $Branch
  } else {
    & git -C $MainPath worktree add -b $Branch $wtPath main
  }
  Write-Host "worktree 생성: $wtPath ($Branch)"
}

# 2) documents 디렉터리 보장 (instructions 가 tracked 라 보통 이미 존재)
$docsDir = Join-Path $wtPath "documents"
if (-not (Test-Path $docsDir)) { New-Item -ItemType Directory -Path $docsDir | Out-Null }

# 3) for-claude junction 보장
if (Test-Path $link) {
  $item = Get-Item $link -Force
  if ($item.LinkType -eq 'Junction') {
    Write-Host "junction 정상: $link"
  } else {
    throw "경로가 junction 이 아닙니다(수동 확인 필요): $link"
  }
} else {
  cmd /c mklink /J "$link" "$src" | Out-Null
  Write-Host "junction 생성: $link  ->  $src"
}

Write-Host ""
Write-Host "[완료] '$Branch' worktree 준비됨. for-claude 는 메인과 공유(junction)됩니다."
Write-Host "이 폴더에서 새 Claude 세션을 여세요: $wtPath"
