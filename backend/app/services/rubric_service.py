"""Rubric service for import, AI generation, and refinement.

Wraps rubric-kit interactions for parsing YAML, generating rubrics from
descriptions, and refining existing rubrics with feedback.
"""

import contextlib
import os
import re
import tempfile

import structlog
import yaml
from rubric_kit import Criterion, Dimension, Rubric, RubricValidationError
from rubric_kit import generate as rubric_kit_generate
from rubric_kit import refine as rubric_kit_refine
from rubric_kit.validator import load_rubric

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


def detect_rubric_format(data: dict) -> str:
    """Detect the format of parsed rubric YAML data.

    Returns one of: ``"ls_eval_system_config"``, ``"geval"``,
    ``"rubric_kit"``, ``"simple"``, or ``"unknown"``.

    Detection heuristics (evaluated in order):
    - ``ls_eval_system_config``: has ``metrics_metadata`` key with
      ``turn_level`` or ``conversation_level`` containing ``geval:`` keys.
    - ``geval``: has a string ``criteria`` key AND no ``dimensions`` key.
    - ``rubric_kit``: has ``dimensions`` list where any element has ``grading_type``.
    - ``simple``: has ``dimensions`` list (without ``grading_type``).
    - ``unknown``: none of the above.
    """
    # ls-eval system config
    metrics_metadata = data.get("metrics_metadata")
    if isinstance(metrics_metadata, dict):
        for level_key in ("turn_level", "conversation_level"):
            level = metrics_metadata.get(level_key)
            if isinstance(level, dict) and any(str(k).startswith("geval:") for k in level):
                return "ls_eval_system_config"

    # geval: criteria must be a string (not a list, which is rubric-kit style)
    criteria = data.get("criteria")
    has_dimensions = bool(data.get("dimensions"))
    if isinstance(criteria, str) and not has_dimensions:
        return "geval"

    # rubric_kit / simple: requires dimensions list
    raw_dims = data.get("dimensions")
    if isinstance(raw_dims, list) and raw_dims:
        if any(isinstance(d, dict) and "grading_type" in d for d in raw_dims):
            return "rubric_kit"
        return "simple"

    return "unknown"


def _parse_geval_format(data: dict, name: str | None = None) -> dict:
    """Convert a Geval metric dict to internal rubric format.

    Args:
        data: Parsed Geval metric YAML dict with ``criteria`` string
            and optional ``evaluation_steps`` list.
        name: Optional override for the rubric name.

    Returns:
        Dict matching internal rubric schema.
    """
    criteria_text = data.get("criteria", "")
    evaluation_steps = data.get("evaluation_steps", [])
    threshold = data.get("threshold")
    description = data.get("description")

    # Determine the rubric name
    if name:
        rubric_name = name
    elif description:
        rubric_name = description
    else:
        rubric_name = "Imported Rubric"

    # Build criteria list from evaluation_steps or the criteria text itself
    if evaluation_steps:
        criteria = [
            {"name": f"step_{i + 1}", "criterion": step, "weight": 1.0} for i, step in enumerate(evaluation_steps)
        ]
    else:
        criteria = [{"name": "step_1", "criterion": criteria_text, "weight": 1.0}]

    dimension = {
        "name": "evaluation",
        "weight": 1.0,
        "description": criteria_text,
        "criteria": criteria,
    }

    return {
        "name": rubric_name,
        "description": description,
        "dimensions": [dimension],
        "pass_threshold": threshold if threshold is not None else 0.7,
        "aggregation": "weighted_average",
        "prompt_template": None,
    }


def _extract_system_config_metrics(data: dict) -> list[dict]:
    """Extract geval metrics from an ls-eval system config.

    Walks ``metrics_metadata.turn_level`` and
    ``metrics_metadata.conversation_level``, returning each ``geval:*``
    metric.

    Args:
        data: Parsed system.yaml dict.

    Returns:
        List of ``{"metric_id": str, "level": str, "metric_data": dict}``.
    """
    metrics: list[dict] = []
    mm = data.get("metrics_metadata", {})
    if not isinstance(mm, dict):
        return metrics

    for level_key in ("turn_level", "conversation_level"):
        level = mm.get(level_key)
        if not isinstance(level, dict):
            continue
        for key, metric_data in level.items():
            if str(key).startswith("geval:") and isinstance(metric_data, dict):
                metrics.append(
                    {
                        "metric_id": str(key),
                        "level": level_key,
                        "metric_data": metric_data,
                    }
                )
    return metrics


def _parse_system_config(data: dict, metric_id: str | None = None) -> dict:
    """Extract and parse a specific geval metric from a system config.

    Args:
        data: Parsed system.yaml dict.
        metric_id: The metric key to extract (e.g. ``"geval:accuracy"``).
            If ``None``, uses the first available metric.

    Returns:
        Dict matching internal rubric schema.

    Raises:
        ValueError: If no geval metrics found or metric_id not found.
    """
    metrics = _extract_system_config_metrics(data)
    if not metrics:
        raise ValueError("No geval metrics found in system config")

    if metric_id is not None:
        target = next((m for m in metrics if m["metric_id"] == metric_id), None)
        if target is None:
            available = [m["metric_id"] for m in metrics]
            raise ValueError(f"Metric '{metric_id}' not found in system config. Available: {available}")
    else:
        target = metrics[0]

    return _parse_geval_format(target["metric_data"])


def _build_dimension_previews(dimensions: list[dict]) -> list[dict]:
    """Build dimension preview dicts from parsed dimensions.

    Args:
        dimensions: List of internal-format dimension dicts.

    Returns:
        List of preview dicts with name, description, weight, criteria_count.
    """
    previews = []
    for dim in dimensions:
        previews.append(
            {
                "name": dim.get("name", "unnamed"),
                "description": dim.get("description", ""),
                "weight": dim.get("weight", 1.0),
                "criteria_count": len(dim.get("criteria", [])),
            }
        )
    return previews


def analyze_rubric_yaml(yaml_content: str) -> dict:
    """Analyze YAML content and return format detection + preview.

    Does not create a rubric -- only detects the format and returns
    preview information about the metrics/dimensions found.

    Args:
        yaml_content: Raw YAML string.

    Returns:
        Dict with ``detected_format`` and ``metrics`` list.

    Raises:
        ValueError: If YAML is invalid.
    """
    yaml_content = clean_yaml_block(yaml_content)

    try:
        data = yaml.safe_load(yaml_content)
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML: {exc}") from exc

    if not data or not isinstance(data, dict):
        return {"detected_format": "unknown", "metrics": []}

    # Handle nested 'rubric' key
    rubric_data = data.get("rubric", data)
    fmt = detect_rubric_format(rubric_data)

    if fmt == "ls_eval_system_config":
        extracted = _extract_system_config_metrics(rubric_data)
        metrics_list = []
        for m in extracted:
            parsed = _parse_geval_format(m["metric_data"])
            total_criteria = sum(len(d.get("criteria", [])) for d in parsed["dimensions"])
            metrics_list.append(
                {
                    "metric_id": m["metric_id"],
                    "suggested_name": parsed["name"],
                    "suggested_description": parsed.get("description"),
                    "dimensions_preview": _build_dimension_previews(parsed["dimensions"]),
                    "criteria_count": total_criteria,
                    "pass_threshold": parsed.get("pass_threshold"),
                }
            )
        return {"detected_format": fmt, "metrics": metrics_list}

    if fmt == "geval":
        parsed = _parse_geval_format(rubric_data)
        total_criteria = sum(len(d.get("criteria", [])) for d in parsed["dimensions"])
        return {
            "detected_format": fmt,
            "metrics": [
                {
                    "metric_id": None,
                    "suggested_name": parsed["name"],
                    "suggested_description": parsed.get("description"),
                    "dimensions_preview": _build_dimension_previews(parsed["dimensions"]),
                    "criteria_count": total_criteria,
                    "pass_threshold": parsed.get("pass_threshold"),
                }
            ],
        }

    if fmt in ("rubric_kit", "simple"):
        # Parse the rubric normally to get full dimension info
        try:
            if fmt == "rubric_kit":
                parsed = _parse_rubric_kit_format(rubric_data)
            else:
                dims = _normalize_simple_dimensions(rubric_data.get("dimensions", []))
                parsed = {
                    "name": rubric_data.get("name", "Imported Rubric"),
                    "description": rubric_data.get("description"),
                    "dimensions": dims,
                    "pass_threshold": rubric_data.get("pass_threshold", 0.7),
                }
        except ValueError:
            return {"detected_format": fmt, "metrics": []}

        total_criteria = sum(len(d.get("criteria", [])) for d in parsed["dimensions"])
        return {
            "detected_format": fmt,
            "metrics": [
                {
                    "metric_id": None,
                    "suggested_name": parsed.get("name", "Imported Rubric"),
                    "suggested_description": parsed.get("description"),
                    "dimensions_preview": _build_dimension_previews(parsed["dimensions"]),
                    "criteria_count": total_criteria,
                    "pass_threshold": parsed.get("pass_threshold"),
                }
            ],
        }

    return {"detected_format": "unknown", "metrics": []}


def parse_rubric_yaml(yaml_content: str, metric_id: str | None = None) -> dict:
    """Parse YAML content into internal rubric dict.

    Supports multiple formats:
    1. Internal/simple format (name + dimensions with weight/description)
    2. rubric-kit format (dimensions with grading_type + criteria)
    3. Geval format (criteria string + evaluation_steps)
    4. ls-eval system config (metrics_metadata with geval: metrics)

    rubric-kit format YAML is delegated to ``load_rubric()`` for full
    validation, variable substitution, and ``from_scores`` handling.

    Args:
        yaml_content: Raw YAML string.
        metric_id: For system config format, the specific metric to extract.

    Returns:
        Dict with name, description, dimensions, pass_threshold, aggregation, prompt_template.

    Raises:
        ValueError: If YAML is invalid, format is unrecognized, or
            rubric-kit validation fails.
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

    fmt = detect_rubric_format(rubric_data)

    if fmt == "ls_eval_system_config":
        return _parse_system_config(rubric_data, metric_id=metric_id)

    if fmt == "geval":
        return _parse_geval_format(rubric_data)

    if fmt == "rubric_kit":
        return _parse_rubric_kit_format(rubric_data)

    if fmt == "simple":
        raw_dimensions = rubric_data.get("dimensions", [])
        dimensions = _normalize_simple_dimensions(raw_dimensions)
        return {
            "name": rubric_data.get("name", "Imported Rubric"),
            "description": rubric_data.get("description"),
            "dimensions": dimensions,
            "pass_threshold": rubric_data.get("pass_threshold", 0.7),
            "aggregation": rubric_data.get("aggregation", "weighted_average"),
            "prompt_template": rubric_data.get("prompt_template"),
        }

    raise ValueError(
        "Unrecognized rubric format. Expected one of: rubric-kit (with "
        "dimensions + grading_type), Geval (with criteria string), "
        "ls-eval system config (with metrics_metadata), or simple "
        "(with dimensions list)."
    )


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


def _to_rubric_kit_format(rubric_data: dict) -> dict:
    """Convert parsed rubric data to rubric-kit native YAML format.

    rubric-kit's ``parse_nested_dict`` expects:
    - Dimensions as ``[{dim_name: description, grading_type: ..., scores: ...}]``
    - Criteria as ``{crit_name: {weight: ..., dimension: ..., criterion: ...}}``

    Dimensions and criteria with explicit ``name`` fields are converted to the
    native key-based format so ``parse_nested_dict`` handles them correctly.
    """
    result: dict = {}

    # Convert dimensions to native key-based format
    raw_dims = rubric_data.get("dimensions", [])
    if isinstance(raw_dims, list):
        converted_dims = []
        for d in raw_dims:
            if isinstance(d, dict) and "name" in d and "description" in d:
                d_copy = dict(d)
                name = d_copy.pop("name")
                desc = d_copy.pop("description")
                converted_dims.append({name: desc, **d_copy})
            elif isinstance(d, dict):
                converted_dims.append(dict(d))
            else:
                converted_dims.append(d)
        result["dimensions"] = converted_dims

    # Convert criteria list to dict-of-dicts keyed by criterion name
    raw_criteria = rubric_data.get("criteria", [])
    if isinstance(raw_criteria, list):
        criteria_dict: dict = {}
        for i, c in enumerate(raw_criteria):
            if isinstance(c, dict):
                c_copy = dict(c)
                name = c_copy.pop("name", f"criterion_{i}")
                criteria_dict[name] = c_copy
        result["criteria"] = criteria_dict
    elif isinstance(raw_criteria, dict):
        result["criteria"] = raw_criteria

    # Copy variables
    if "variables" in rubric_data:
        result["variables"] = rubric_data["variables"]

    return result


def _parse_rubric_kit_format(rubric_data: dict) -> dict:
    """Parse rubric-kit format YAML using rubric-kit's ``load_rubric`` API.

    Converts the parsed rubric data to rubric-kit native format, writes it to
    a temporary file, and delegates to ``load_rubric()`` for full validation,
    variable substitution, and ``from_scores`` handling.

    Args:
        rubric_data: Parsed YAML dict (already unwrapped from ``rubric:`` key).

    Returns:
        Dict matching internal rubric schema.

    Raises:
        ValueError: If rubric-kit validation fails.
    """
    kit_data = _to_rubric_kit_format(rubric_data)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=True) as f:
        yaml.dump(kit_data, f, default_flow_style=False, sort_keys=False)
        f.flush()
        try:
            rubric = load_rubric(f.name)
        except RubricValidationError as exc:
            raise ValueError(str(exc)) from exc

    result = convert_rubric_kit_to_internal(rubric)
    result["name"] = rubric_data.get("name", "Imported Rubric")
    result["description"] = rubric_data.get("description")
    result["pass_threshold"] = rubric_data.get("pass_threshold", 0.7)
    result["aggregation"] = rubric_data.get("aggregation", "weighted_average")
    result["prompt_template"] = rubric_data.get("prompt_template")
    return result


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
