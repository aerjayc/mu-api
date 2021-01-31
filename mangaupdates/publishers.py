from dataclasses import dataclass


@dataclass
class Publisher:
    name: str
    id: int
    note: str = None

    def __repr__(self):
        return f'Publisher({repr(self.name)}, id={self.id}, note={repr(self.note)})'

@dataclass
class Magazine:
    name: str
    url: str
    parent: str = None

    def __repr__(self):
        return f'Magazine({repr(self.name)}, url={repr(self.url)}, parent={repr(self.parent)})'
