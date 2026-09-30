param(
    [ValidateSet('Approve','Reject','Expire')][string]$Decision = 'Approve',
    [string]$BaseUrl = 'http://127.0.0.1:8000'
)
$ErrorActionPreference = 'Stop'
$analyst = @{ Authorization = "Bearer $env:GOVERNOR_ANALYST_TOKEN" }
$support = @{ Authorization = "Bearer $env:GOVERNOR_SUPPORT_TOKEN" }
$reviewer = @{ Authorization = "Bearer $env:GOVERNOR_REVIEWER_TOKEN" }
function Post-Json($Path, $Headers, $Payload) {
    Invoke-RestMethod -Method Post -Uri "$BaseUrl$Path" -Headers $Headers -ContentType 'application/json' -Body ($Payload | ConvertTo-Json -Depth 10)
}
$read = Post-Json '/api/actions' $analyst @{task_id='sales-report'; tool='database.read'; resource='sales_summary'; arguments=@{limit=3}}
if ($read.state -ne 'SUCCEEDED') { throw 'Analyst read failed' }
Post-Json '/api/actions' $support @{task_id='support-review'; tool='database.read'; resource='support_summary'; arguments=@{limit=10}}
$report = Post-Json '/api/actions' $analyst @{task_id='sales-report'; tool='report.create'; resource='sales_report'; arguments=@{source_artifact_id=$read.result.artifact_id; format='csv'}}
if ($report.state -ne 'SUCCEEDED') { throw 'Report creation failed' }
$pending = Post-Json '/api/actions' $analyst @{task_id='sales-report'; tool='report.send'; resource='sales_report'; arguments=@{artifact_id=$report.result.artifact_id; recipient='review@example.test'}}
$pending
$rid = $pending.request_id
$detail = Invoke-RestMethod -Uri "$BaseUrl/api/reviews/$rid" -Headers $reviewer
$detail
switch ($Decision) {
    'Approve' { Post-Json "/api/reviews/$rid/approve" $reviewer @{comment='Checked synthetic data and destination'} }
    'Reject' { Post-Json "/api/reviews/$rid/reject" $reviewer @{comment='Demo rejection'} }
    'Expire' {
        $waitSeconds = [Math]::Max(1, [Math]::Ceiling($detail.expires_at - [DateTimeOffset]::UtcNow.ToUnixTimeSeconds() + 1))
        Write-Host "Waiting $waitSeconds seconds for the configured expiry."
        Start-Sleep -Seconds $waitSeconds
    }
}
Invoke-RestMethod -Uri "$BaseUrl/api/actions/$rid" -Headers $analyst
$checkpoint = Invoke-RestMethod -Uri "$BaseUrl/api/audit/checkpoint" -Headers $reviewer
Post-Json '/api/audit/verify' $reviewer $checkpoint
Write-Host 'Retain a checkpoint independently of the governance database for meaningful later comparison.'
