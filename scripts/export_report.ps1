param(
    [Parameter(Mandatory=$true)][string]$DocumentPath,
    [Parameter(Mandatory=$true)][string]$PdfPath
)
$ErrorActionPreference = 'Stop'
# Invoke Word through IDispatch rather than the cached Office interop interfaces.
# This also works when Office's installed type library and the cached PIA differ.
function Invoke-Word {
    param($Object, [string]$Member, [object[]]$Arguments = @(),
        [Reflection.BindingFlags]$Flags = [Reflection.BindingFlags]::InvokeMethod)
    $result = $Object.GetType().InvokeMember($Member, $Flags, $null, $Object, $Arguments)
    if ($null -ne $result) { return ,$result }
}
$wordReport = $null
$reportDocument = $null
try {
    $wordReport = New-Object -ComObject Word.Application
    Invoke-Word $wordReport 'Visible' @($false) -Flags SetProperty
    Invoke-Word $wordReport 'DisplayAlerts' @(0) -Flags SetProperty
    Invoke-Word $wordReport 'AutomationSecurity' @(3) -Flags SetProperty
    $documents = Invoke-Word $wordReport 'Documents' -Flags GetProperty
    $reportDocument = Invoke-Word $documents 'Open' @([IO.Path]::GetFullPath($DocumentPath), $false, $false)
    # Update captions before building navigation, then refresh pagination and page fields.
    $fields = Invoke-Word $reportDocument 'Fields' -Flags GetProperty
    Invoke-Word $fields 'Update' | Out-Null
    $contents = Invoke-Word $reportDocument 'TablesOfContents' -Flags GetProperty
    $figures = Invoke-Word $reportDocument 'TablesOfFigures' -Flags GetProperty
    foreach ($collection in @($contents, $figures)) {
        $count = Invoke-Word $collection 'Count' -Flags GetProperty
        for ($index = 1; $index -le $count; $index++) {
            $entry = Invoke-Word $collection 'Item' @($index)
            Invoke-Word $entry 'Update' | Out-Null
        }
    }
    Invoke-Word $reportDocument 'Repaginate'
    foreach ($collection in @($contents, $figures)) {
        $count = Invoke-Word $collection 'Count' -Flags GetProperty
        for ($index = 1; $index -le $count; $index++) {
            $entry = Invoke-Word $collection 'Item' @($index)
            Invoke-Word $entry 'UpdatePageNumbers' | Out-Null
        }
    }
    $sections = Invoke-Word $reportDocument 'Sections' -Flags GetProperty
    $sectionCount = Invoke-Word $sections 'Count' -Flags GetProperty
    for ($index = 1; $index -le $sectionCount; $index++) {
        $section = Invoke-Word $sections 'Item' @($index)
        $footers = Invoke-Word $section 'Footers' -Flags GetProperty
        for ($kind = 1; $kind -le 3; $kind++) {
            $footer = Invoke-Word $footers 'Item' @($kind)
            $range = Invoke-Word $footer 'Range' -Flags GetProperty
            $footerFields = Invoke-Word $range 'Fields' -Flags GetProperty
            Invoke-Word $footerFields 'Update' | Out-Null
        }
    }
    Invoke-Word $reportDocument 'Save'
    # PDF comes from the saved Word document. Use headings as PDF bookmarks.
    Invoke-Word $reportDocument 'ExportAsFixedFormat' @([IO.Path]::GetFullPath($PdfPath), 17, $false, 0, 0, 1, 9999, 0, $true, $true, 1)
    Write-Output ('Exported ' + (Invoke-Word $reportDocument 'ComputeStatistics' @(2)) + ' pages')
} finally {
    if ($null -ne $reportDocument) {
        Invoke-Word $reportDocument 'Close' @(0)
        [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($reportDocument)
    }
    if ($null -ne $wordReport) {
        Invoke-Word $wordReport 'Quit'
        [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($wordReport)
    }
}
