from dataclasses import dataclass


@dataclass
class Category:
    name: str
    score: int
    agree: int
    disagree: int

    def __repr__(self):
        return (f'Category({repr(self.name)}, score={self.score}, '
                f'agree={self.agree}, disagree={self.disagree})')
