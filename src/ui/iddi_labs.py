"""IddiLabs branding and information view."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QScrollArea, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


class IddiLabsView(QWidget):
    """
    IddiLabs branding and information view.

    Displays information about IddiLabs and the project philosophy.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        """Set up the view UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Scroll area for content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        layout.addWidget(scroll)

        # Content container
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(48, 48, 48, 48)
        content_layout.setSpacing(24)

        # Title
        title = QLabel("Who is IddiLabs?")
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("color: #2D3E50;")
        content_layout.addWidget(title)

        # Description card
        description_card = QFrame()
        description_card.setProperty("card", True)
        card_layout = QVBoxLayout(description_card)
        card_layout.setContentsMargins(32, 32, 32, 32)
        card_layout.setSpacing(20)

        # Intro text
        intro = QLabel(
            "I am a Risk Manager working in Luxembourg's financial sector with no coding background. "
            "I am using AI tools and applied expertise to build small software solutions, free and open to everyone. \n\n"
            "IddiLabs is not a software company, not a VAT registered individual, not a team of developers. "
        )
        intro.setWordWrap(True)
        intro_font = QFont()
        intro_font.setPointSize(11)
        intro.setFont(intro_font)
        intro.setStyleSheet("color: #2D3E50; line-height: 1.6;")
        card_layout.addWidget(intro)

        # Why I'm doing this section
        why_title = QLabel("Why I'm doing this")
        why_title_font = QFont()
        why_title_font.setPointSize(13)
        why_title_font.setBold(True)
        why_title.setFont(why_title_font)
        why_title.setStyleSheet("color: #2D3E50; margin-top: 8px;")
        card_layout.addWidget(why_title)

        why_text = QLabel(
            "I believe we're at the beginning of a shift where domain expertise becomes the differentiator "
            "as technical implementation becomes increasingly automated. A risk manager who effectively uses AI "
            "will be more valuable than one who does not."
        )
        why_text.setWordWrap(True)
        why_text_font = QFont()
        why_text_font.setPointSize(11)
        why_text.setFont(why_text_font)
        why_text.setStyleSheet("color: #2D3E50; line-height: 1.6;")
        card_layout.addWidget(why_text)

        # Why it's free section
        free_title = QLabel("Why it's free")
        free_title_font = QFont()
        free_title_font.setPointSize(13)
        free_title_font.setBold(True)
        free_title.setFont(free_title_font)
        free_title.setStyleSheet("color: #2D3E50; margin-top: 8px;")
        card_layout.addWidget(free_title)

        free_text = QLabel(
            "Lot of companies, especially small and medium enterprises, do not have budget for this type of tools and keep using excel sheets. "
            "This software is production ready and free to use, so that everyone can benefit from it.\n\n"
            "Additionally I'm doing it for my personal upskilling, career development and to prove what"
            " Subject Matter Experts and AI can bring to companies."
        )
        free_text.setWordWrap(True)
        free_text_font = QFont()
        free_text_font.setPointSize(11)
        free_text.setFont(free_text_font)
        free_text.setStyleSheet("color: #2D3E50; line-height: 1.6;")
        card_layout.addWidget(free_text)

        # Learn More section
        learn_title = QLabel("Learn More")
        learn_title_font = QFont()
        learn_title_font.setPointSize(13)
        learn_title_font.setBold(True)
        learn_title.setFont(learn_title_font)
        learn_title.setStyleSheet("color: #2D3E50; margin-top: 8px;")
        card_layout.addWidget(learn_title)

        learn_text = QLabel(
            "In-depth guides about this software are available at iddi-labs.com, in the 'Blog'. "
            "Visit the 'Project' section for further tools."
        )
        learn_text.setWordWrap(True)
        learn_text_font = QFont()
        learn_text_font.setPointSize(11)
        learn_text.setFont(learn_text_font)
        learn_text.setStyleSheet("color: #2D3E50; line-height: 1.6;")
        card_layout.addWidget(learn_text)

        # Get in touch section
        contact_title = QLabel("Get in touch")
        contact_title_font = QFont()
        contact_title_font.setPointSize(13)
        contact_title_font.setBold(True)
        contact_title.setFont(contact_title_font)
        contact_title.setStyleSheet("color: #2D3E50; margin-top: 8px;")
        card_layout.addWidget(contact_title)

        contact_text = QLabel(
            "Website: www.iddi-labs.com\n"
            "LinkedIn: IddiLabs\n"
            "Email: contact@iddi-labs.com\n\n"
            "Feel free to reach out for any questions or suggestions! Feedback is always welcome."
        )
        contact_text.setWordWrap(True)
        contact_text_font = QFont()
        contact_text_font.setPointSize(11)
        contact_text.setFont(contact_text_font)
        contact_text.setStyleSheet("color: #2D3E50; line-height: 1.6;")
        card_layout.addWidget(contact_text)

        content_layout.addWidget(description_card)

        # Add stretch to push content to top
        content_layout.addStretch()

        scroll.setWidget(content)

    def refresh(self):
        """Refresh the view (no-op for static content)."""
        pass
