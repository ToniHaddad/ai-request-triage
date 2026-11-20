import pytest

from triage.model import Request, load_config


@pytest.fixture(scope="session")
def cfg():
    return load_config()


def make(**kw) -> Request:
    base = dict(id=1, team="T", office="Lebanon", title="X", description="", per_week=4, people=10,
                minutes=30, owner="Sam", data_class="internal", success_text="5 days to 2",
                success_measurable=True, existing_tool="no", task_kind="language",
                consequence="medium", systems=2)
    base.update(kw)
    return Request(**base)
