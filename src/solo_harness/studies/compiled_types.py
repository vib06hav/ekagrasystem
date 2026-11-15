from dataclasses import dataclass
from types import MappingProxyType
from solo_harness.studies.canonicalization import SNAPSHOT_SCHEMA_VERSION

@dataclass(frozen=True)
class CompiledStudy:
    study_id: str; content_version: str; authored: dict; knowledge_slices: MappingProxyType; cells: MappingProxyType
    intervention_moves: MappingProxyType; tutor_prompt_recipes: MappingProxyType; assessment_families: MappingProxyType; rubrics: MappingProxyType; protocol: dict
    def to_snapshot(self): return {"schema_version":SNAPSHOT_SCHEMA_VERSION,"study_id":self.study_id,"content_version":self.content_version,"authored":self.authored,"knowledge_slices":dict(self.knowledge_slices),"cells":dict(self.cells),"intervention_moves":dict(self.intervention_moves),"tutor_prompt_recipes":dict(self.tutor_prompt_recipes),"assessment_families":dict(self.assessment_families),"rubrics":dict(self.rubrics),"protocol":self.protocol}
    @classmethod
    def from_snapshot(cls,x): return cls(x["study_id"],x["content_version"],x["authored"],MappingProxyType(x["knowledge_slices"]),MappingProxyType(x["cells"]),MappingProxyType(x["intervention_moves"]),MappingProxyType(x["tutor_prompt_recipes"]),MappingProxyType(x["assessment_families"]),MappingProxyType(x["rubrics"]),x["protocol"])
