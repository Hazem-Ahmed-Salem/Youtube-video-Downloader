"""
StatusPanel Widget

A styled status panel widget for displaying status messages.
"""

from textual.app import ComposeResult
from textual.widgets import Static, Label


class StatusPanel(Static):
    """A styled status panel widget"""
    
    def __init__(self, title: str = "Status", **kwargs):
        super().__init__(**kwargs)
        self.title = title
        self.status_text = "Ready"
        
    def compose(self) -> ComposeResult:
        yield Label(self.status_text, id="status-text")
        
    def update_status(self, text: str):
        self.status_text = text
        label = self.query_one("#status-text", Label)
        label.update(text)
