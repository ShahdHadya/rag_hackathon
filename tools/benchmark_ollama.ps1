param([int]$Runs = 2)
# Direct Ollama transport benchmark; no index writes or model downloads.
Add-Type -AssemblyName System.Net.Http
$http = [System.Net.Http.HttpClient]::new()
$http.Timeout = [TimeSpan]::FromMinutes(4)
$prompt = 'Answer only from context in Arabic. Context: [1] benchmark.txt, page 1: Technical RAG quality is worth 30 points. Question: كم علامة مخصصة لجودة نظام RAG التقنية؟ Cite [1]. Give only the answer.'
foreach ($mode in @('baseline', 'stream_no_thinking')) {
    for ($run = 1; $run -le $Runs; $run++) {
        $payload = @{model='qwen3:1.7b'; messages=@(@{role='user';content=$prompt}); stream=($mode -ne 'baseline'); options=@{temperature=0}; keep_alive='10m'}
        if ($mode -ne 'baseline') { $payload.think = $false }
        $request = [System.Net.Http.HttpRequestMessage]::new([System.Net.Http.HttpMethod]::Post, 'http://localhost:11434/api/chat')
        $request.Content = [System.Net.Http.StringContent]::new(($payload | ConvertTo-Json -Depth 6), [System.Text.Encoding]::UTF8, 'application/json')
        $watch = [System.Diagnostics.Stopwatch]::StartNew()
        $first = $null
        $outputText = ''
        $thinking = $false
        try {
            $response = $http.SendAsync($request, [System.Net.Http.HttpCompletionOption]::ResponseHeadersRead).GetAwaiter().GetResult()
            $response.EnsureSuccessStatusCode() | Out-Null
            $reader = [System.IO.StreamReader]::new($response.Content.ReadAsStreamAsync().GetAwaiter().GetResult())
            while ($null -ne ($line = $reader.ReadLine())) {
                if (-not $line) { continue }
                $item = $line | ConvertFrom-Json
                if ($item.message.thinking) { $thinking = $true }
                if ($item.message.content) {
                    if ($null -eq $first) { $first = $watch.Elapsed.TotalSeconds }
                    $outputText += $item.message.content
                }
            }
            [pscustomobject]@{mode=$mode;run=$run;first_visible_content_seconds=$first;total_seconds=$watch.Elapsed.TotalSeconds;thinking_observed=$thinking;answer=$outputText} | ConvertTo-Json -Compress
            $reader.Dispose()
            $response.Dispose()
        } finally { $request.Dispose() }
    }
}
$http.Dispose()
