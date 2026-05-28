"""Rubric service for import, AI generation, and refinement.

Wraps rubric-kit interactions for parsing YAML, generating rubrics from
descriptions, and refining existing rubrics with feedback.
"""

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

    if not raw_dimensions:
        raise ValueError("No dimensions found in YAML content")

    # Detect format: rubric-kit format has grading_type on dimensions
    is_rubric_kit_format = any(isinstance(d, dict) and "grading_type" in d for d in raw_dimensions)

    if is_rubric_kit_format:
        dimensions = _convert_rubric_kit_dims_and_criteria(raw_dimensions, raw_criteria)
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


def _convert_rubric_kit_dims_and_criteria(raw_dims: list[dict], raw_criteria: list[dict]) -> list[dict]:
    """Convert rubric-kit format (dimensions + criteria) to internal weighted dimensions."""
    # Aggregate criteria weights per dimension
    dim_weights: dict[str, float] = {}
    for c in raw_criteria:
        if not isinstance(c, dict):
            continue
        dim_name = c.get("dimension", "")
        weight = c.get("weight", 1)
        if isinstance(weight, str):
            weight = 1
        dim_weights[dim_name] = dim_weights.get(dim_name, 0) + float(weight)

    total_weight = sum(dim_weights.values()) or 1.0

    dims = []
    for d in raw_dims:
        if not isinstance(d, dict):
            continue
        name = d.get("name", "unnamed")
        raw_w = dim_weights.get(name, 1.0)
        dims.append(
            {
                "name": name,
                "weight": round(raw_w / total_weight, 4),
                "description": d.get("description", name),
            }
        )

    return dims


def convert_rubric_kit_to_internal(rubric: Rubric, name: str = "Generated Rubric") -> dict:
    """Convert a rubric-kit Rubric object to internal rubric dict format.

    Args:
        rubric: A rubric-kit Rubric instance.
        name: Default name for the rubric.

    Returns:
        Dict matching internal rubric schema.
    """
    # Compute weights from criteria
    dim_weights: dict[str, float] = {}
    for criterion in rubric.criteria:
        w = criterion.weight if isinstance(criterion.weight, int) else 1
        dim_weights[criterion.dimension] = dim_weights.get(criterion.dimension, 0) + float(w)

    total_weight = sum(dim_weights.values()) or 1.0

    dimensions = []
    for dim in rubric.dimensions:
        raw_w = dim_weights.get(dim.name, 1.0)
        dimensions.append(
            {
                "name": dim.name,
                "weight": round(raw_w / total_weight, 4),
                "description": dim.description,
            }
        )

    return {
        "name": name,
        "description": None,
        "dimensions": dimensions,
        "pass_threshold": 0.7,
        "aggregation": "weighted_average",
        "prompt_template": None,
    }


def generate_rubric(
    description: str,
    sample_data: str | None,
    model: str,
    api_base: str | None,
) -> dict:
    """Generate a rubric from a description using rubric-kit + LLM.

    Args:
        description: Text describing what the rubric should evaluate.
        sample_data: Optional sample Q&A or chat data for context.
        model: LiteLLM model identifier.
        api_base: Optional API base URL.

    Returns:
        Dict matching internal rubric schema.
    """
    # Build input content combining description and sample data
    input_content = f"Description: {description}"
    if sample_data:
        input_content += f"\n\nSample data:\n{sample_data}"

    logger.info("rubric.generate.start", model=model, has_sample_data=bool(sample_data))

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
