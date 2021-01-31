from dataclasses import dataclass


@dataclass
class UserReview:
    id: int
    reviewer: str
    name: str

@dataclass
class UserRating:
    average: float
    bayesian_average: float
    votes: int
    distribution: dict
