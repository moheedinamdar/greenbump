from __future__ import annotations

from greenbump.guardrails import (
    Limits,
    check_changes,
    count_tests,
    package_aliases,
    protected_reason,
)

PKG = {"numpy"}


def rules(before: dict[str, str], after: dict[str, str], limits: Limits | None = None) -> set[str]:
    return {v.rule for v in check_changes(before, after, PKG, limits)}


def test_dependency_and_ci_files_are_protected() -> None:
    for p in [
        "requirements.txt",
        "requirements-dev.txt",
        "sub/constraints.txt",
        "pyproject.toml",
        "poetry.lock",
        ".github/workflows/ci.yml",
        "tests/conftest.py",
        "pytest.ini",
    ]:
        assert protected_reason(p), p
    assert protected_reason("app/requirements_helper.py") is None
    assert protected_reason("app/models.py") is None


def test_clean_api_migration_passes() -> None:
    before = {"m.py": "import numpy as np\nx = np.float_\n"}
    after = {"m.py": "import numpy as np\nx = np.float64\n"}
    assert rules(before, after) == set()


def test_monkeypatching_the_library_is_caught() -> None:
    before = {"m.py": "import numpy as np\nx = np.float_\n"}
    after = {"m.py": "import numpy as np\nnp.float_ = np.float64\nx = np.float_\n"}
    assert "patches-library" in rules(before, after)


def test_skips_and_silencers_are_caught() -> None:
    before = {"tests/test_a.py": "def test_a():\n    assert f()\n"}
    for added in [
        "@pytest.mark.skip\n",
        "@pytest.mark.xfail\n",
        "pytestmark = pytest.mark.filterwarnings('ignore')\n",
    ]:
        after = {"tests/test_a.py": added + before["tests/test_a.py"]}
        assert rules(before, after) & {"skips-tests", "silences-warnings"}, added
    after = {"m.py": "x = f()  # type: ignore\n"}
    assert "suppression-comment" in rules({"m.py": "x = f()\n"}, after)


def test_existing_suppressions_are_not_blamed_on_the_agent() -> None:
    before = {"m.py": "import numpy as np  # noqa: F401\nx = np.float_\n"}
    after = {"m.py": "import numpy as np  # noqa: F401\nx = np.float64\n"}
    assert rules(before, after) == set()


def test_removing_tests_or_asserts_is_caught() -> None:
    before = {
        "tests/test_a.py": "def test_a():\n    assert 1\n    assert 2\n\n\ndef test_b():\n    assert 3\n"
    }
    fewer_asserts = {"tests/test_a.py": "def test_a():\n    assert 1\n\n\ndef test_b():\n    assert 3\n"}
    fewer_tests = {"tests/test_a.py": "def test_a():\n    assert 1\n    assert 2\n    assert 3\n"}
    assert "weakens-tests" in rules(before, fewer_asserts)
    assert "removes-tests" in rules(before, fewer_tests)


def test_network_and_process_calls_are_caught_but_urllib_parse_is_fine() -> None:
    assert "process-or-network" in rules({"m.py": ""}, {"m.py": "import subprocess\n"})
    assert "process-or-network" in rules({"m.py": ""}, {"m.py": "from urllib.request import urlopen\n"})
    assert rules({"m.py": "x = 1\n"}, {"m.py": "from urllib.parse import quote\nx = 1\n"}) == set()


def test_new_and_deleted_files_are_caught() -> None:
    assert "new-file" in rules({}, {"m.py": "x = 1\n"})
    assert "deleted-file" in rules({"m.py": "x = 1\n"}, {})


def test_diff_size_limit() -> None:
    before = {"m.py": "".join(f"a{i} = {i}\n" for i in range(50))}
    after = {"m.py": "".join(f"a{i} = {i + 1}\n" for i in range(50))}
    assert "diff-too-large" in rules(before, after, Limits(max_files=10, max_changed_lines=20))
    assert "diff-too-large" not in rules(before, after)


def test_package_aliases_cover_module_and_from_imports() -> None:
    src = {"a.py": "import numpy as np\nfrom flask import Markup as M, request\nimport os\n"}
    assert package_aliases(src, {"numpy", "flask"}) == {"np", "M", "request"}


def test_count_tests_only_counts_test_files() -> None:
    src = {
        "tests/test_a.py": "def test_a(): pass\ndef test_b(): pass\ndef helper(): pass\n",
        "app.py": "def test_not_a_test(): pass\n",
    }
    assert count_tests(src) == 2
