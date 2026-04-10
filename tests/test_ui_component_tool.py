from learning_core.skills.activity_generate.scripts.tooling import (
    ALLOWED_UI_SPEC_PATHS,
    read_ui_spec,
)


def test_read_valid_component_path():
    result = read_ui_spec.invoke({"path": "ui_components/short_answer.md"})
    assert "# short_answer" in result
    assert "prompt" in result


def test_read_valid_widget_path():
    result = read_ui_spec.invoke({"path": "ui_widgets/board_surface__chess.md"})
    assert "# board_surface + chess" in result
    assert "expectedMoves" in result


def test_read_valid_spec_without_prefix_when_unique():
    result = read_ui_spec.invoke({"path": "short_answer.md"})
    assert "# short_answer" in result


def test_read_all_allowlisted_specs():
    for path in ALLOWED_UI_SPEC_PATHS:
        result = read_ui_spec.invoke({"path": path})
        assert not result.startswith("Error"), f"Failed to read {path}: {result}"


def test_path_traversal_rejected():
    result = read_ui_spec.invoke({"path": "ui_components/../../../etc/passwd"})
    assert result.startswith("Error")
    assert "invalid path" in result


def test_path_traversal_without_prefix_rejected():
    result = read_ui_spec.invoke({"path": "../secrets.md"})
    assert result.startswith("Error")
    assert "invalid path" in result


def test_unknown_path_rejected():
    result = read_ui_spec.invoke({"path": "ui_widgets/nonexistent_widget.md"})
    assert result.startswith("Error")
    assert "not a recognized UI spec" in result


def test_non_indexed_path_rejected():
    result = read_ui_spec.invoke({"path": "ui_components/../../pyproject.toml"})
    assert result.startswith("Error")


def test_arbitrary_file_rejected():
    result = read_ui_spec.invoke({"path": "main.py"})
    assert result.startswith("Error")
    assert "not a recognized UI spec" in result


def test_subdirectory_traversal_rejected():
    result = read_ui_spec.invoke({"path": "ui_components/subdir/short_answer.md"})
    assert result.startswith("Error")
    assert "not a recognized UI spec" in result or "invalid path" in result
