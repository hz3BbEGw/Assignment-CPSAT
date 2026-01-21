from enum import Enum
from typing import Dict, List, Optional, Union
from pydantic import BaseModel, field_validator

class CriterionType(str, Enum):
    MINIMIZE = "minimize"
    PREREQUISITE = "prerequisite"
    PULL = "pull"

class CriterionConfig(BaseModel):
    type: CriterionType
    min_ratio: Optional[float] = None

class GroupConfig(BaseModel):
    id: int
    size: int
    criteria: Dict[str, Union[CriterionConfig, List[CriterionConfig]]]

    @field_validator('criteria', mode='after')
    @classmethod
    def ensure_list_configs(cls, v):
        return {
            name: [config] if isinstance(config, CriterionConfig) else config
            for name, config in v.items()
        }

class StudentConfig(BaseModel):
    id: int
    possible_groups: List[int]
    values: Dict[str, float]
    rankings: Optional[Dict[int, float]] = None

class ProblemInput(BaseModel):
    num_students: int
    num_groups: int
    groups: List[GroupConfig]
    students: List[StudentConfig]
    exclude: List[List[int]] = []
    max_time_in_seconds: Optional[float] = 60
    ranking_percentage: float = 50.0

class AssignmentResult(BaseModel):
    student_id: int
    group_id: int

class RankingsStats(BaseModel):
    avg_rank: Optional[float] = None
    min_rank: Optional[float] = None

class MinimizeCriterionStats(BaseModel):
    max_group_avg_diff: float
    max_group_global_diff: float

class ProblemStats(BaseModel):
    rankings: Optional[RankingsStats] = None
    minimize: Optional[Dict[str, MinimizeCriterionStats]] = None

class ProblemOutput(BaseModel):
    assignments: List[AssignmentResult]
    status: str
    stats: Optional[ProblemStats] = None
