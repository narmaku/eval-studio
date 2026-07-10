"""Rubric service for import, AI generation, and refinement.

Wraps rubric-kit interactions for parsing YAML, generating rubrics from
descriptions, and refining existing rubrics with feedback.
"""

import contextlib
import os
import re

import structlog
import yaml
from rubric_kit import Criterion, Dimension, Rubric
from rubric_kit import generate as rubric_kit_generate
from rubric_kit import refine as rubric_kit_refine

logger = structlog.get_logger()


def clean_yaml_block(text: str) -> str:
    """Strip markdown code fences from a YAML string.

    LLM responses often wrap YAML in ```yaml ... ``` blocks.
    """
    text = text.strip()
    if not text:
        return text
    # Remove opening fence
    text = re.sub(r"^\s*```(?:ya?ml)?\s*\n?", "", text)
    # Remove closing fence
    text = re.sub(r"\n?\s*```\s*$", "", text)
    return text.strip()


def _substitute_variables(text: str, variables: dict[str, str]) -> str:
    """Replace ``{{var}}`` placeholders with values from *variables*.

    Resolved placeholders are replaced in-place.  Any ``{{...}}`` tokens
    that do **not** have a matching key are left as-is and a warning is
    logged so the caller knows something was missed.
    """
    if not variables:
        return text

    for key, value in variables.items():
        text = text.replace("{{" + key + "}}", str(value))

    # Warn about any remaining unresolved placeholders
    unresolved = re.findall(r"\{\{(\w+)\}\}", text)
    if unresolved:
        logger.warning(
            "rubric.variable_substitution.unresolved",
            unresolved_placeholders=unresolved,
            text_preview=text[:200],
        )

    return text


def parse_rubric_yaml(yaml_content: str) -> dict:
    """Parse YAML content into internal rubric dict.

    Supports two formats:
    1. Internal format (name + dimensions with weight/description)
    2. rubric-kit format (dimensions with grading_type + criteria)

    Args:
        yaml_content: Raw YAML string.

    Returns:
        Dict with name, description, dimensions, pass_threshold, aggregation, prompt_template.

    Raises:
        ValueError: If YAML is invalid or no dimensions are found.
    """
    yaml_content = clean_yaml_block(yaml_content)

    try:
        data = yaml.safe_load(yaml_content)
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML: {exc}") from exc

    if not data or not isinstance(data, dict):
        raise ValueError("No dimensions found in YAML content")

    # Handle nested 'rubric' key or flat format
    rubric_data = data.get("rubric", data)

    raw_dimensions = rubric_data.get("dimensions", [])
    raw_criteria = rubric_data.get("criteria", [])
    variables = rubric_data.get("variables", {}) or {}

    if not raw_dimensions:
        raise ValueError("No dimensions found in YAML content")

    # Detect format: rubric-kit format has grading_type on dimensions
    is_rubric_kit_format = any(isinstance(d, dict) and "grading_type" in d for d in raw_dimensions)

    if is_rubric_kit_format:
        dimensions = _convert_rubric_kit_dims_and_criteria(raw_dimensions, raw_criteria, variables)
    else:
        dimensions = _normalize_simple_dimensions(raw_dimensions)

    return {
        "name": rubric_data.get("name", "Imported Rubric"),
        "description": rubric_data.get("description"),
        "dimensions": dimensions,
        "pass_threshold": rubric_data.get("pass_threshold", 0.7),
        "aggregation": rubric_data.get("aggregation", "weighted_average"),
        "prompt_template": rubric_data.get("prompt_template"),
    }


def _normalize_simple_dimensions(raw_dims: list[dict]) -> list[dict]:
    """Normalize simple format dimensions (name, weight, description)."""
    dims = []
    for d in raw_dims:
        if not isinstance(d, dict):
            continue
        dims.append(
            {
                "name": d.get("name", "unnamed"),
                "weight": float(d.get("weight", 1.0)),
                "description": d.get("description", d.get("name", "unnamed")),
            }
        )
    return dims


def _extract_dim_name_and_desc(d: dict) -> tuple[str, str]:
    """Extract dimension name and description from a rubric-kit dimension entry.

    rubric-kit format: {dim_name: description, grading_type: ..., scores: ...}
    The dimension name is the first key that isn't a reserved field.
    """
    reserved = {"grading_type", "scores", "name", "description"}
    for key, val in d.items():
        if key not in reserved and isinstance(val, str):
            return key, val
    return d.get("name", "unnamed"), d.get("description", "unnamed")


def _convert_rubric_kit_dims_and_criteria(
    raw_dims: list[dict],
    raw_criteria: list | dict,
    variables: dict[str, str] | None = None,
) -> list[dict]:
    """Convert rubric-kit format (dimensions + criteria) to internal weighted dimensions.

    Criteria are stored per dimension as a list of ``{name, criterion, weight}``
    dicts.  Template variables (``{{var}}``) in criterion text are substituted
    from *variables*.  Criteria referencing non-existent dimensions are skipped
    with a warning.
    """
    variables = variables or {}

    # Criteria can be a dict of dicts (keyed by criterion name) or a list
    criteria_items: list[dict] = []
    if isinstance(raw_criteria, dict):
        for key, val in raw_criteria.items():
            if isinstance(val, dict):
                if "name" not in val:
                    val = {**val, "name": key}
                criteria_items.append(val)
    elif isinstance(raw_criteria, list):
        criteria_items = [c for c in raw_criteria if isinstance(c, dict)]

    # Build dimension lookup: name → (scores dict, grading_type)
    dim_info: dict[str, tuple[dict, str]] = {}
    dim_names: set[str] = set()
    for d in raw_dims:
        if not isinstance(d, dict):
            continue
        name, _ = _extract_dim_name_and_desc(d)
        dim_names.add(name)
        raw_scores = d.get("scores", {})
        scores = {int(k): str(v) for k, v in raw_scores.items()} if isinstance(raw_scores, dict) else {}
        dim_info[name] = (scores, d.get("grading_type", ""))

    # Group criteria by dimension, applying variable substitution
    criteria_by_dim: dict[str, list[dict]] = {}
    dim_weights: dict[str, float] = {}

    for c in criteria_items:
        dim_name = c.get("dimension", "")
        if dim_name not in dim_names:
            logger.warning(
                "rubric.criteria.unknown_dimension",
                criterion_name=c.get("name", "unknown"),
                dimension=dim_name,
                known_dimensions=sorted(dim_names),
            )
            continue

        scores, _grading_type = dim_info.get(dim_name, ({}, ""))

        weight = c.get("weight", 1)
        if weight == "from_scores":
            weight = max(scores.keys()) if scores else 1
        elif isinstance(weight, str):
            weight = 1
        weight = float(weight)

        criterion_text = c.get("criterion", "")
        if criterion_text == "from_scores" and scores:
            criterion_text = "\n".join(f"{k}: {v}" for k, v in sorted(scores.items()))
        elif criterion_text == "from_scores":
            criterion_text = ""
        if variables and criterion_text:
            criterion_text = _substitute_variables(criterion_text, variables)

        criteria_by_dim.setdefault(dim_name, []).append(
            {
                "name": c.get("name", "unnamed"),
                "criterion": criterion_text,
                "weight": weight,
            }
        )
        dim_weights[dim_name] = dim_weights.get(dim_name, 0) + weight

    total_weight = sum(dim_weights.values()) or 1.0

    dims = []
    for d in raw_dims:
        if not isinstance(d, dict):
            continue
        name, description = _extract_dim_name_and_desc(d)
        raw_w = dim_weights.get(name, 1.0)
        dim_dict: dict = {
            "name": name,
            "weight": round(raw_w / total_weight, 4),
            "description": description,
        }
        dim_criteria = criteria_by_dim.get(name)
        if dim_criteria:
            dim_dict["criteria"] = dim_criteria
        dims.append(dim_dict)

    return dims


def convert_rubric_kit_to_internal(rubric: Rubric, name: str = "Generated Rubric") -> dict:
    """Convert a rubric-kit Rubric object to internal rubric dict format.

    Criteria from the rubric-kit ``Rubric`` are preserved per dimension as a
    list of ``{name, criterion, weight}`` dicts.

    Args:
        rubric: A rubric-kit Rubric instance.
        name: Default name for the rubric.

    Returns:
        Dict matching internal rubric schema.
    """
    # Group criteria by dimension and compute weights
    criteria_by_dim: dict[str, list[dict]] = {}
    dim_weights: dict[str, float] = {}

    # Build dimension scores lookup for resolving from_scores
    dim_scores: dict[str, dict[int, str]] = {}
    for dim in rubric.dimensions:
        if dim.scores:
            dim_scores[dim.name] = {int(k): str(v) for k, v in dim.scores.items()}

    for criterion in rubric.criteria:
        scores = dim_scores.get(criterion.dimension, {})

        if criterion.weight == "from_scores":
            w = float(max(scores.keys())) if scores else 1.0
        elif isinstance(criterion.weight, int):
            w = float(criterion.weight)
        else:
            w = 1.0
        dim_weights[criterion.dimension] = dim_weights.get(criterion.dimension, 0) + w

        crit_text = criterion.criterion
        if (crit_text == "from_scores" or crit_text is None) and scores:
            crit_text = "\n".join(f"{k}: {v}" for k, v in sorted(scores.items()))
        elif crit_text == "from_scores" or crit_text is None:
            crit_text = ""

        criteria_by_dim.setdefault(criterion.dimension, []).append(
            {
                "name": criterion.name,
                "criterion": crit_text,
                "weight": w,
            }
        )

    total_weight = sum(dim_weights.values()) or 1.0

    dimensions = []
    for dim in rubric.dimensions:
        raw_w = dim_weights.get(dim.name, 1.0)
        dim_dict: dict = {
            "name": dim.name,
            "weight": round(raw_w / total_weight, 4),
            "description": dim.description,
        }
        dim_criteria = criteria_by_dim.get(dim.name)
        if dim_criteria:
            dim_dict["criteria"] = dim_criteria
        dimensions.append(dim_dict)

    return {
        "name": name,
        "description": None,
        "dimensions": dimensions,
        "pass_threshold": 0.7,
        "aggregation": "weighted_average",
        "prompt_template": None,
    }


@contextlib.contextmanager
def _api_key_env_patch(api_key: str | None):
    """Temporarily set LITELLM_API_KEY so rubric-kit's litellm calls pick it up."""
    if not api_key:
        yield
        return
    old = os.environ.get("LITELLM_API_KEY")
    os.environ["LITELLM_API_KEY"] = api_key
    try:
        yield
    finally:
        if old is None:
            os.environ.pop("LITELLM_API_KEY", None)
        else:
            os.environ["LITELLM_API_KEY"] = old


def generate_rubric(
    description: str,
    sample_data: str | None,
    model: str,
    api_base: str | None,
    api_key: str | None = None,
) -> dict:
    """Generate a rubric from a description using rubric-kit + LLM.

    Args:
        description: Text describing what the rubric should evaluate.
        sample_data: Optional sample Q&A or chat data for context.
        model: LiteLLM model identifier.
        api_base: Optional API base URL.
        api_key: Optional API key for the LLM provider.

    Returns:
        Dict matching internal rubric schema.
    """
    # Build input content combining description and sample data
    input_content = f"Description: {description}"
    if sample_data:
        input_content += f"\n\nSample data:\n{sample_data}"

    logger.info("rubric.generate.start", model=model, has_sample_data=bool(sample_data))

    env_patch = _api_key_env_patch(api_key)
    with env_patch:
        result = rubric_kit_generate(
            input_content=input_content,
            input_type="qna",
            model=model,
            base_url=api_base,
            track_metrics=False,
        )

    rubric_dict = convert_rubric_kit_to_internal(result.rubric, name="Generated Rubric")
    rubric_dict["description"] = description

    logger.info("rubric.generate.complete", dimensions=len(rubric_dict["dimensions"]))
    return rubric_dict


def refine_rubric(
    existing_rubric: dict,
    feedback: str,
    model: str,
    api_base: str | None,
    api_key: str | None = None,
) -> dict:
    """Refine an existing rubric based on feedback using rubric-kit + LLM.

    Args:
        existing_rubric: Current rubric as internal dict format.
        feedback: User feedback describing desired changes.
        model: LiteLLM model identifier.
        api_base: Optional API base URL.

    Returns:
        Dict matching internal rubric schema with refined dimensions.
    """
    # Convert internal rubric to rubric-kit Rubric object
    rk_dimensions = []
    rk_criteria = []
    for dim in existing_rubric.get("dimensions", []):
        rk_dimensions.append(
            Dimension(
                name=dim["name"],
                description=dim.get("description", dim["name"]),
                grading_type="score",
                scores={1: "Poor", 3: "Average", 5: "Excellent"},
            )
        )
        rk_criteria.append(
            Criterion(
                name=f"{dim['name']}_criterion",
                weight=min(3, max(1, round(dim.get("weight", 1.0) * 3))),
                dimension=dim["name"],
                criterion=dim.get("description", dim["name"]),
            )
        )

    rk_rubric = Rubric(dimensions=rk_dimensions, criteria=rk_criteria)

    logger.info("rubric.refine.start", model=model, feedback_length=len(feedback))

    env_patch = _api_key_env_patch(api_key)
    with env_patch:
        result = rubric_kit_refine(
            rubric=rk_rubric,
            model=model,
            base_url=api_base,
            feedback=feedback,
            track_metrics=False,
        )

    refined = convert_rubric_kit_to_internal(result.rubric, name=existing_rubric.get("name", "Refined Rubric"))
    # Preserve metadata from existing rubric
    refined["description"] = existing_rubric.get("description")
    refined["pass_threshold"] = existing_rubric.get("pass_threshold", 0.7)
    refined["aggregation"] = existing_rubric.get("aggregation", "weighted_average")
    refined["prompt_template"] = existing_rubric.get("prompt_template")

    logger.info("rubric.refine.complete", dimensions=len(refined["dimensions"]))
    return refined
