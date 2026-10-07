from PySide6.QtCore import QRegularExpression
from PySide6.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat


class CodeHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.highlighting_rules = []

        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#569cd6"))
        keyword_format.setFontWeight(QFont.Weight.Bold)
        keywords = (
            "def class if else elif return import from for while try except with as "
            "in not and or lambda yield async await pass break continue raise "
            "function var let const public private void int string new this null true false"
        ).split()
        keyword_pattern = QRegularExpression(
            r"\b(?:" + "|".join(keywords) + r")\b"
        )
        self.highlighting_rules.append((keyword_pattern, keyword_format))

        type_format = QTextCharFormat()
        type_format.setForeground(QColor("#4ec9b0"))
        types = (
            "True False None self cls print len range str int float bool list dict "
            "tuple set object type bytes"
        ).split()
        type_pattern = QRegularExpression(r"\b(?:" + "|".join(types) + r")\b")
        self.highlighting_rules.append((type_pattern, type_format))

        function_format = QTextCharFormat()
        function_format.setForeground(QColor("#dcdcaa"))
        self.highlighting_rules.append(
            (
                QRegularExpression(r"\b[a-zA-Z_]\w*(?=\s*\()"),
                function_format,
            )
        )

        number_format = QTextCharFormat()
        number_format.setForeground(QColor("#b5cea8"))
        self.highlighting_rules.append(
            (
                QRegularExpression(
                    r"\b(?:0[xX][0-9A-Fa-f]+|0[bB][01]+|"
                    r"\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?\b"
                ),
                number_format,
            )
        )

        decorator_format = QTextCharFormat()
        decorator_format.setForeground(QColor("#dcdcaa"))
        self.highlighting_rules.append(
            (QRegularExpression(r"@\w+"), decorator_format)
        )

        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#ce9178"))
        self.highlighting_rules.extend(
            (
                (
                    QRegularExpression(
                        r"(?:[fFrRuUbB]{1,2})?\"(?:[^\"\\]|\\.)*\""
                    ),
                    string_format,
                ),
                (
                    QRegularExpression(
                        r"(?:[fFrRuUbB]{1,2})?'(?:[^'\\]|\\.)*'"
                    ),
                    string_format,
                ),
            )
        )

        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#6a9955"))
        self.highlighting_rules.extend(
            (
                (QRegularExpression(r"#[^\n]*"), comment_format),
                (QRegularExpression(r"//[^\n]*"), comment_format),
                (QRegularExpression(r"/\*.*?\*/"), comment_format),
            )
        )

    def highlightBlock(self, text):
        for pattern, text_format in self.highlighting_rules:
            matches = pattern.globalMatch(text)
            while matches.hasNext():
                match = matches.next()
                self.setFormat(
                    match.capturedStart(), match.capturedLength(), text_format
                )
