from app.schemas.dataset import DatasetCreate, DatasetItemCreate
from app.schemas.evaluation import EvaluationMode


def test_dataset_create_schema_valid():
    data = DatasetCreate(
        name="Test Dataset",
        items=[DatasetItemCreate(question="What is RHEL?", expected_answer="Red Hat Enterprise Linux")],
    )
    assert data.name == "Test Dataset"
    assert len(data.items) == 1
    assert data.format == "qa_pairs"


def test_dataset_create_schema_defaults():
    data = DatasetCreate(name="Minimal")
    assert data.items == []
    assert data.tags == []
    assert data.version == "1.0"


def test_evaluation_mode_enum():
    assert EvaluationMode.QA == "qa"
    assert EvaluationMode.AGENT == "agent"
    assert EvaluationMode.RAG == "rag"
    assert EvaluationMode.ARENA == "arena"
