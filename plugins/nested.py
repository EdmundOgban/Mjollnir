
class NestedScanner:
    def __init__(self, opening="{", closing="}", escapechar="\\"):
        self.opening = opening
        self.closing = closing
        self.escapechar = escapechar

    def scan(self, text):
        self.reset()
        self.string = text
        self.total = len(text)
        while self.current < self.total:
            c = self.string[self.current]
            if c == self.escapechar:
                if self.peek() in (self.opening, self.closing, self.escapechar):
                    self.string = self.string[:self.current] + self.string[self.current + 1:]
                    self.total -= 1
            elif c == self.opening:
                self._found_opening()
                self.start = self.current + 1
            elif c == self.closing:
                self._found_closing()
                self.start = self.current + 1

            self.current += 1

        if self.depth > 0:
            raise ValueError(f"Missing {self.depth} closing '{self.closing}'")
        elif self.missing_opening:
            raise ValueError(f"Missing {-self.missing_opening} opening '{self.opening}'")

        if self.current_token:
            self.tree.append(self.current_token)

        return self.tree

    def peek(self):
        return self.string[self.current + 1] if self.current + 1 < self.total else ''

    def reset(self):
        self.tree = []
        self.frame = self.tree
        self.start = 0
        self.current = 0
        self.total = 0
        self.missing_opening = 0
        self.depth = 0

    @property
    def current_token(self):
        return self.string[self.start:self.current]

    def _found_opening(self):
        token = self.current_token
        if token:
            self.frame.append(token)

        if self.depth > 0:
            self.tree.append(self.frame)

        newf = []
        self.frame.append(newf)
        self.frame = newf
        self.depth += 1

    def _found_closing(self):
        token = self.current_token
        if token:
            self.frame.append(token)

        self.depth -= 1
        if self.depth > 0:
            self.frame = self.tree.pop()
        elif self.depth == 0:
            self.frame = self.tree
        elif self.depth < self.missing_opening:
            self.missing_opening = self.depth
