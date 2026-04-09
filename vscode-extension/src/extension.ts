import * as vscode from 'vscode';
import { InterviewPanel } from './interviewPanel';

export function activate(context: vscode.ExtensionContext) {
    console.log('ANT Interview Assistant is now active');

    // Register the webview provider
    const provider = new InterviewPanel(context.extensionUri);

    context.subscriptions.push(
        vscode.window.registerWebviewViewProvider(
            InterviewPanel.viewType,
            provider
        )
    );

    // Start Interview Mode command
    const startInterview = vscode.commands.registerCommand('ant.startInterview', () => {
        vscode.commands.executeCommand('workbench.view.extension.ant');
        vscode.window.showInformationMessage('🐜 Interview Mode activated');
    });

    // Ask Question command
    const askQuestion = vscode.commands.registerCommand('ant.askQuestion', async () => {
        const question = await vscode.window.showInputBox({
            prompt: 'Ask ANT a question',
            placeHolder: 'e.g., How do I implement a binary search?'
        });

        if (question) {
            provider.askAI(question);
        }
    });

    // Toggle Sidebar command
    const toggleSidebar = vscode.commands.registerCommand('ant.toggleSidebar', () => {
        vscode.commands.executeCommand('workbench.view.extension.ant');
    });

    context.subscriptions.push(startInterview, askQuestion, toggleSidebar);

    // Status bar item
    const statusBarItem = vscode.window.createStatusBarItem(
        vscode.StatusBarAlignment.Right,
        100
    );
    statusBarItem.text = "🐜 ANT";
    statusBarItem.tooltip = "ANT Interview Assistant";
    statusBarItem.command = 'ant.startInterview';
    statusBarItem.show();

    context.subscriptions.push(statusBarItem);
}

export function deactivate() {
    console.log('ANT Interview Assistant deactivated');
}
