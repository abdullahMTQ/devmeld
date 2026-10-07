import io
import re
import tokenize


class SyntaxCheckerAdapter:
    _BLOCK_HEADER = re.compile(
        r"^\s*(?:async\s+)?(?:def|class|if|else|elif|for|while|try|except|finally|with)\b"
    )
    _OPEN_BRACKETS = {"(": ")", "[": "]", "{": "}"}

    def check_syntax(self, content: str) -> list:
        """Return sorted error dictionaries for syntax and unfinished structures."""
        errors = set()

        def add_error(line_number, message):
            if line_number and line_number > 0:
                errors.add((line_number, message))

        try:
            compile(content, "<string>", "exec")
        except SyntaxError as error:
            if error.lineno:
                add_error(error.lineno, error.msg or "Syntax error")

        bracket_stack = []
        colon_lines = set()
        tokens = tokenize.generate_tokens(io.StringIO(content).readline)
        try:
            for token in tokens:
                if token.type != tokenize.OP:
                    continue
                if token.string in self._OPEN_BRACKETS:
                    bracket_stack.append((token.string, token.start[0]))
                elif token.string in self._OPEN_BRACKETS.values():
                    if (
                        bracket_stack
                        and self._OPEN_BRACKETS[bracket_stack[-1][0]]
                        == token.string
                    ):
                        bracket_stack.pop()
                    else:
                        add_error(
                            token.start[0], f"Unmatched '{token.string}'"
                        )
                elif token.string == ":":
                    colon_lines.add(token.start[0])
        except tokenize.TokenError as error:
            location = error.args[1]
            if location and location[0] > 0:
                add_error(location[0], error.args[0])
        except (IndentationError, SyntaxError) as error:
            if error.lineno:
                add_error(error.lineno, error.msg or "Syntax error")

        for bracket, line_number in bracket_stack:
            add_error(line_number, f"Unclosed '{bracket}'")

        for line_number, line in enumerate(content.splitlines(), 1):
            if not self._BLOCK_HEADER.match(line):
                continue
            if line_number in colon_lines:
                continue
            if line.rstrip().endswith("\\"):
                continue
            add_error(line_number, "Missing colon")

        return [
            {"line": line_number, "message": message}
            for line_number, message in sorted(errors)
        ]
