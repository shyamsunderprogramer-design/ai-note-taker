import * as vscode from 'vscode';

export class InterviewPanel implements vscode.WebviewViewProvider {
    public static readonly viewType = 'ant.interviewPanel';
    private _view?: vscode.WebviewView;
    private _apiBase: string;

    constructor(private readonly _extensionUri: vscode.Uri) {
        const config = vscode.workspace.getConfiguration('ant');
        this._apiBase = config.get('apiUrl') || 'http://localhost:8000';
    }

    public resolveWebviewView(
        webviewView: vscode.WebviewView,
        context: vscode.WebviewViewResolveContext,
        _token: vscode.CancellationToken
    ) {
        this._view = webviewView;

        webviewView.webview.options = {
            enableScripts: true,
            localResourceRoots: [this._extensionUri]
        };

        webviewView.webview.html = this._getHtmlForWebview(webviewView.webview);

        // Handle messages from the webview
        webviewView.webview.onDidReceiveMessage(async (data) => {
            switch (data.type) {
                case 'askAI':
                    await this.askAI(data.question);
                    break;
                case 'getSuggestion':
                    await this.getCodeSuggestion();
                    break;
            }
        });
    }

    public async askAI(question: string) {
        if (!this._view) {
            vscode.window.showErrorMessage('ANT panel not available');
            return;
        }

        this._view.webview.postMessage({
            type: 'loading',
            message: 'Thinking...'
        });

        try {
            const response = await fetch(`${this._apiBase}/stream?q=${encodeURIComponent(question)}&mode=code`);
            const text = await response.text();

            // Parse SSE stream
            const lines = text.split('\n');
            let answer = '';
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.slice(6));
                        if (data.chunk) {
                            answer += data.chunk;
                        }
                    } catch (e) {
                        // Ignore parse errors
                    }
                }
            }

            this._view.webview.postMessage({
                type: 'response',
                question: question,
                answer: answer || 'No response from AI'
            });
        } catch (error) {
            this._view.webview.postMessage({
                type: 'error',
                message: 'Failed to connect to ANT backend. Is it running?'
            });
        }
    }

    public async getCodeSuggestion() {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showWarningMessage('No active editor');
            return;
        }

        const selection = editor.document.getText(editor.selection);
        if (!selection) {
            vscode.window.showInformationMessage('Select code to get suggestions');
            return;
        }

        await this.askAI(`Review this code and suggest improvements:\n\n${selection}`);
    }

    private _getHtmlForWebview(webview: vscode.Webview): string {
        return `<!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {
                    font-family: var(--vscode-font-family);
                    padding: 20px;
                    color: var(--vscode-foreground);
                    background: var(--vscode-panel-background);
                }
                .header {
                    margin-bottom: 20px;
                    padding-bottom: 10px;
                    border-bottom: 1px solid var(--vscode-panel-border);
                }
                .header h2 {
                    margin: 0;
                    color: #3b82f6;
                }
                .input-group {
                    display: flex;
                    gap: 8px;
                    margin-bottom: 16px;
                }
                input {
                    flex: 1;
                    padding: 8px 12px;
                    border: 1px solid var(--vscode-input-border);
                    background: var(--vscode-input-background);
                    color: var(--vscode-input-foreground);
                    border-radius: 4px;
                }
                button {
                    padding: 8px 16px;
                    background: #3b82f6;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    cursor: pointer;
                    font-weight: 500;
                }
                button:hover {
                    background: #2563eb;
                }
                .response {
                    background: var(--vscode-editor-background);
                    border: 1px solid var(--vscode-panel-border);
                    border-radius: 6px;
                    padding: 12px;
                    min-height: 100px;
                    white-space: pre-wrap;
                    overflow-wrap: break-word;
                }
                .loading {
                    color: var(--vscode-descriptionForeground);
                    font-style: italic;
                }
                .error {
                    color: #ef4444;
                    padding: 8px;
                    background: rgba(239, 68, 68, 0.1);
                    border-radius: 4px;
                }
                .quick-actions {
                    display: flex;
                    gap: 8px;
                    flex-wrap: wrap;
                    margin-bottom: 16px;
                }
                .quick-btn {
                    padding: 4px 12px;
                    background: rgba(59, 130, 246, 0.1);
                    color: #3b82f6;
                    border: 1px solid rgba(59, 130, 246, 0.3);
                    border-radius: 4px;
                    font-size: 12px;
                    cursor: pointer;
                }
                .quick-btn:hover {
                    background: rgba(59, 130, 246, 0.2);
                }
            </style>
        </head>
        <body>
            <div class="header">
                <h2>🐜 Interview Assistant</h2>
            </div>

            <div class="quick-actions">
                <button class="quick-btn" onclick="quickAsk('Explain this algorithm')">Explain</button>
                <button class="quick-btn" onclick="quickAsk('Optimize this code')">Optimize</button>
                <button class="quick-btn" onclick="quickAsk('Time complexity analysis')">Complexity</button>
                <button class="quick-btn" onclick="quickAsk('Test cases for this')">Tests</button>
            </div>

            <div class="input-group">
                <input type="text" id="questionInput" placeholder="Ask anything..."
                       onkeypress="if(event.key==='Enter') askAI()">
                <button onclick="askAI()">Ask</button>
            </div>

            <div id="response" class="response">
                Ask a question to get AI-powered assistance
            </div>

            <script>
                const vscode = acquireVsCodeApi();

                function askAI() {
                    const input = document.getElementById('questionInput');
                    const question = input.value.trim();
                    if (!question) return;

                    vscode.postMessage({ type: 'askAI', question: question });
                    input.value = '';
                }

                function quickAsk(prompt) {
                    const input = document.getElementById('questionInput');
                    input.value = prompt;
                    askAI();
                }

                window.addEventListener('message', event => {
                    const message = event.data;
                    const responseDiv = document.getElementById('response');

                    switch (message.type) {
                        case 'loading':
                            responseDiv.innerHTML = '<div class="loading">' + message.message + '</div>';
                            break;
                        case 'response':
                            responseDiv.innerHTML = '<strong>Q: ' + escapeHtml(message.question) + '</strong><br><br>' +
                                                  escapeHtml(message.answer);
                            break;
                        case 'error':
                            responseDiv.innerHTML = '<div class="error">' + escapeHtml(message.message) + '</div>';
                            break;
                    }
                });

                function escapeHtml(text) {
                    const div = document.createElement('div');
                    div.textContent = text;
                    return div.innerHTML;
                }
            </script>
        </body>
        </html>
        `;
    }
}
