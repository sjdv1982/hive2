# Copyright (C) 2008 Christophe Kibleur <kib2@free.fr>
#
# This file is part of WikiParser (http://thewikiblog.appspot.com/).
# Adapted for use in Hive2 - 2016

from .qt_gui import QTextEdit, QFont, QSyntaxHighlighter, QColor, QTextCharFormat
from .qt_core import Signal
from pygments.formatter import Formatter
from pygments.lexers import get_lexer_by_name
from pygments import highlight
from sys import version_info


def hex_to_qcolor(c):
    r = int(c[0:2], 16)
    g = int(c[2:4], 16)
    b = int(c[4:6], 16)
    return QColor(r, g, b)


class QFormatter(Formatter):

    def __init__(self, style="", font=None):
        Formatter.__init__(self, style=style)

        self._character_formats = []
        self._token_styles = {}

        for token, style in self.style:
            text_char_format = QTextCharFormat()

            if font is not None:
                text_char_format.setFont(font)

            if style['color']:
                text_char_format.setForeground(hex_to_qcolor(style['color']))

            if style['bgcolor']:
                text_char_format.setBackground(hex_to_qcolor(style['bgcolor']))

            if style['bold']:
                text_char_format.setFontWeight(QFont.Bold)

            if style['italic']:
                text_char_format.setFontItalic(True)

            if style['underline']:
                text_char_format.setFontUnderline(True)

            self._token_styles[token] = text_char_format

        self._default_format = QTextCharFormat()

        if font is not None:
            self._default_format.setFont(font)

    def get_format(self, index):
        try:
            return self._character_formats[index]

        except IndexError:
            return self._default_format

    def format(self, tokens, outfile):
        self._character_formats.clear()

        for token, value in tokens:
            self._character_formats.extend((self._token_styles[token],) * len(value))


class CodeHighlighter(QSyntaxHighlighter):

    def __init__(self, parent, lexer, formatter):
        QSyntaxHighlighter.__init__(self, parent)

        self._formatter = formatter
        self._lexer = lexer

    def highlightBlock(self, text):
        current_block = self.currentBlock()
        position = current_block.position()

        text = self.document().toPlainText() + '\n'
        highlight(text, self._lexer, self._formatter)

        for i in range(len(text)):
            text_format = self._formatter.get_format(position + i)
            self.setFormat(i, 1, text_format)


class CodeEditor(QTextEdit):

    def __init__(self):
        super(CodeEditor, self).__init__()

        # Highlighting
        lexer_name = "python" if version_info.major == 2 else "python3"
        lexer = get_lexer_by_name(lexer_name)

        formatter = QFormatter(style="paraiso-dark", font=QFont("Consolas"))
        self._highlighter = CodeHighlighter(self.document(), lexer, formatter)
