param(
    [Parameter(Mandatory)][string]$Image,
    [Parameter(Mandatory)][string]$OutputPath,
    [ValidateRange(1, 65535)][int]$ContainerPort = 80
)
$ErrorActionPreference = 'Stop'
if ($Image -cnotmatch '^[^@\s]+(:[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}|@sha256:[a-f0-9]{64})$' -or $Image.EndsWith(':latest')) {
    throw 'Supply a public release image tag or digest, not latest.'
}
$bundlePath = [IO.Path]::GetFullPath($OutputPath)
$manifest = @{
    AWSEBDockerrunVersion = '1'
    Image = @{ Name = $Image; Update = 'true' }
    Ports = @(@{ ContainerPort = [string]$ContainerPort })
} | ConvertTo-Json -Depth 5
$stream = [IO.File]::Open($bundlePath, [IO.FileMode]::CreateNew)
try {
    $archive = [IO.Compression.ZipArchive]::new($stream, [IO.Compression.ZipArchiveMode]::Create, $true)
    try {
        $entry = $archive.CreateEntry('Dockerrun.aws.json')
        $writer = [IO.StreamWriter]::new($entry.Open(), [Text.UTF8Encoding]::new($false))
        try { $writer.Write($manifest) } finally { $writer.Dispose() }
    } finally { $archive.Dispose() }
} finally { $stream.Dispose() }
Write-Output $bundlePath
