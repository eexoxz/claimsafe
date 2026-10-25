param(
    [Parameter(Mandatory=$true)][string]$DocumentPath,
    [Parameter(Mandatory=$true)][string]$PdfPath
)
$ErrorActionPreference = 'Stop'
$wordReport = $null
$reportDocument = $null
try {
    $wordReport = New-Object -ComObject Word.Application
    $wordReport.Visible = $false
    $wordReport.DisplayAlerts = 0
    $wordReport.AutomationSecurity = 3
    $reportDocument = $wordReport.Documents.Open([IO.Path]::GetFullPath($DocumentPath), $false, $false)
    # Update captions before building navigation, then refresh pagination and page fields.
    $reportDocument.Fields.Update() | Out-Null
    foreach ($tableOfContents in $reportDocument.TablesOfContents) { $tableOfContents.Update() }
    foreach ($tableOfFigures in $reportDocument.TablesOfFigures) { $tableOfFigures.Update() }
    $reportDocument.Repaginate()
    foreach ($tableOfContents in $reportDocument.TablesOfContents) { $tableOfContents.UpdatePageNumbers() }
    foreach ($tableOfFigures in $reportDocument.TablesOfFigures) { $tableOfFigures.UpdatePageNumbers() }
    foreach ($reportSection in $reportDocument.Sections) {
        foreach ($footer in $reportSection.Footers) { $footer.Range.Fields.Update() | Out-Null }
    }
    $reportDocument.Save()
    # PDF comes from the saved Word document. Use headings as PDF bookmarks.
    $reportDocument.ExportAsFixedFormat([IO.Path]::GetFullPath($PdfPath), 17, $false, 0, 0, 1, 9999, 0, $true, $true, 1)
    Write-Output ('Exported ' + $reportDocument.ComputeStatistics(2) + ' pages')
} finally {
    if ($null -ne $reportDocument) {
        $reportDocument.Close(0)
        [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($reportDocument)
    }
    if ($null -ne $wordReport) {
        $wordReport.Quit()
        [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($wordReport)
    }
}
