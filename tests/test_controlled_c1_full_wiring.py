from types import SimpleNamespace

import pytest

from solo_harness.runtime.controlled_c1_prompt_context import execution_overlay_hash
from solo_harness.studies.controlled_c1 import (
    ControlledC1Error, contract, contract_hash, is_controlled_c1, new_c1_state,
)


@pytest.mark.parametrize("subsection", ["C1.1", "C1.2", "C1.3", "C1.4"])
def test_full_c1_detection_accepts_each_authorized_subsection(subsection):
    progress = SimpleNamespace(subsection_id=subsection, instructional_state={"controlled_c11": new_c1_state()})
    assert is_controlled_c1(progress)


@pytest.mark.parametrize("subsection", ["C1.2", "C1.3", "C1.4"])
def test_later_subsections_require_full_scope_hash(subsection):
    state = new_c1_state()
    state["execution_overlay_sha256"] = "different"
    progress = SimpleNamespace(subsection_id=subsection, instructional_state={"controlled_c11": state})
    assert is_controlled_c1(progress)
    assert state["contract_sha256"] == contract_hash()
    assert execution_overlay_hash() != state["execution_overlay_sha256"]
    assert subsection in contract()["subsections"]


def test_c11_only_state_does_not_enable_later_subsection():
    legacy = {"contract_id": contract()["contract_id"], "contract_sha256": contract_hash(),
              "move_index": 0, "status": "TEACHING", "approval_version": 0}
    assert not is_controlled_c1(SimpleNamespace(subsection_id="C1.2", instructional_state={"controlled_c11": legacy}))
