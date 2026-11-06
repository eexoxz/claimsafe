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
    $pages = [int](Invoke-Word $reportDocument 'ComputeStatistics' @(2))
    $allWords = [int](Invoke-Word $reportDocument 'ComputeStatistics' @(0))
    $bodySection = Invoke-Word $sections 'Item' @(3)
    $bodyRange = Invoke-Word $bodySection 'Range' -Flags GetProperty
    $bodyStart = [int](Invoke-Word $bodyRange 'Start' -Flags GetProperty)
    $bodyEnd = [int](Invoke-Word $bodyRange 'End' -Flags GetProperty)
    $referenceSearch = Invoke-Word $reportDocument 'Range' @($bodyStart, $bodyEnd)
    $finder = Invoke-Word $referenceSearch 'Find' -Flags GetProperty
    $found = Invoke-Word $finder 'Execute' @('6.0 References')
    if (!$found) { throw 'Reference boundary missing; cannot verify the main report word count.' }
    $referenceStart = [int](Invoke-Word $referenceSearch 'Start' -Flags GetProperty)
    $mainRange = Invoke-Word $reportDocument 'Range' @($bodyStart, $referenceStart)
    $mainWords = [int](Invoke-Word $mainRange 'ComputeStatistics' @(0))
    $counts = [ordered]@{ pages=$pages; word_count_whole_document=$allWords; word_count_main_sections=$mainWords; method='Native Microsoft Word ComputeStatistics. Main sections run from body section 1.0 to before 6.0 References, including headings, tables, captions and code. Whole document includes preliminary material, references and appendix; words inside images are not counted.' }
    $counts | ConvertTo-Json | Set-Content -LiteralPath ([IO.Path]::ChangeExtension([IO.Path]::GetFullPath($DocumentPath), '.layout.json')) -Encoding UTF8
    Write-Output "Exported $pages pages; Word count $mainWords main / $allWords whole document"
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
