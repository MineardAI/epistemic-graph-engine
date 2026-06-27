from __future__ import annotations

from typing import Iterable

from ..hash_utils import stable_id
from .schema import TraceStep, TraceStepType


def build_trace_step(
    step_type: TraceStepType,
    *,
    source_ids: Iterable[str] = (),
    input_ids: Iterable[str] = (),
    output_ids: Iterable[str] = (),
    detail_code: str,
    detail_message: str,
    question_id: str,
) -> TraceStep:
    source_ids_list = sorted(dict.fromkeys(source_ids))
    input_ids_list = sorted(dict.fromkeys(input_ids))
    output_ids_list = sorted(dict.fromkeys(output_ids))
    step_payload = {
        "question_id": question_id,
        "step_type": step_type.value,
        "source_ids": source_ids_list,
        "input_ids": input_ids_list,
        "output_ids": output_ids_list,
        "detail_code": detail_code,
        "detail_message": detail_message,
    }
    return TraceStep(
        step_id=stable_id("resolution-step", step_payload),
        step_type=step_type,
        source_ids=source_ids_list,
        input_ids=input_ids_list,
        output_ids=output_ids_list,
        detail_code=detail_code,
        detail_message=detail_message,
    )

