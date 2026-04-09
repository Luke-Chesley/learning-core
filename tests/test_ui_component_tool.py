from learning_core.skills.activity_generate.scripts.tooling import (
    ALLOWED_COMPONENT_DOCS,
    read_ui_component,
)


def test_read_valid_component_path():
    result = read_ui_component.invoke({"path": "ui_components/short_answer.md"})
    assert "# short_answer" in result
    assert "prompt" in result


def test_read_valid_component_without_prefix():
    result = read_ui_component.invoke({"path": "short_answer.md"})
    assert "# short_answer" in result


def test_read_all_indexed_components():
    for filename in ALLOWED_COMPONENT_DOCS:
        result = read_ui_component.invoke({"path": f"ui_components/{filename}"})
        assert not result.startswith("Error"), f"Failed to read {filename}: {result}"


def test_path_traversal_rejected():
    result = read_ui_component.invoke({"path": "ui_components/../../../etc/passwd"})
    assert result.startswith("Error")
    assert "invalid path" in result


def test_path_traversal_without_prefix_rejected():
    result = read_ui_component.invoke({"path": "../secrets.md"})
    assert result.startswith("Error")
    assert "invalid path" in result


def test_unknown_path_rejected():
    result = read_ui_component.invoke({"path": "ui_components/nonexistent_widget.md"})
    assert result.startswith("Error")
    assert "not a recognized component" in result


def test_non_indexed_path_rejected():
    result = read_ui_component.invoke({"path": "ui_components/../../pyproject.toml"})
    assert result.startswith("Error")


def test_arbitrary_file_rejected():
    result = read_ui_component.invoke({"path": "main.py"})
    assert result.startswith("Error")
    assert "not a recognized component" in result


def test_subdirectory_traversal_rejected():
    result = read_ui_component.invoke({"path": "ui_components/subdir/short_answer.md"})
    assert result.startswith("Error")
    assert "invalid path" in result
