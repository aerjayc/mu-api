from dataclasses import dataclass


@dataclass
class Author:
    name: str
    id: int

    def __repr__(self):
        return f'Author({repr(self.name)}, id={self.id})'

