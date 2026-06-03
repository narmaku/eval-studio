"""Unit tests for GooseOutputParser."""

from app.harnesses.parsers.goose import GooseOutputParser


def test_text_lines():
    """Regular text lines are buffered and emitted as message_chunks."""
    parser = GooseOutputParser()
    events = parser.parse_line("Hello, I'm working on that.\n")
    # Text is buffered, not emitted immediately
    assert len(events) == 0

    # Flush emits the buffered text
    flush_events = parser.flush()
    assert len(flush_events) == 1
    assert flush_events[0].type == "message_chunk"
    assert "Hello" in flush_events[0].data["content"]


def test_tool_call_detection():
    """Lines starting with box-drawing characters trigger a tool_call event."""
    parser = GooseOutputParser()

    # First buffer some text
    parser.parse_line("Let me check that for you.\n")

    # Tool call marker flushes the buffer and emits a tool_call
    events = parser.parse_line("── read_file\n")
    # Should get: message_chunk (flushed buffer) + tool_call
    assert len(events) == 2
    assert events[0].type == "message_chunk"
    assert events[1].type == "tool_call"
    assert events[1].data["tool_name"] == "read_file"


def test_tool_line_pattern():
    """Lines matching 'Tool: <name>' trigger a tool_call event."""
    parser = GooseOutputParser()
    events = parser.parse_line("Tool: search_files\n")
    assert len(events) == 1
    assert events[0].type == "tool_call"
    assert events[0].data["tool_name"] == "search_files"


def test_result_line_in_tool_block():
    """Result lines in a tool block emit tool_result events."""
    parser = GooseOutputParser()
    # Enter tool block
    parser.parse_line("Tool: read_file\n")
    # Result
    events = parser.parse_line("Result: file contents here\n")
    assert len(events) == 1
    assert events[0].type == "tool_result"
    assert events[0].data["result"] == "file contents here"


def test_flush_empty():
    """Flushing with no buffered content returns nothing."""
    parser = GooseOutputParser()
    events = parser.flush()
    assert events == []


def test_unknown_lines_do_not_crash():
    """Unknown or malformed lines are silently handled."""
    parser = GooseOutputParser()
    # Various weird inputs should not raise
    events = parser.parse_line("\x00\x01\x02\n")
    # Unknown lines just get buffered
    assert len(events) == 0

    # Even binary garbage in flush doesn't crash
    flush_events = parser.flush()
    assert len(flush_events) == 1


def test_multiline_text_buffering():
    """Multiple text lines are buffered and emitted together on flush."""
    parser = GooseOutputParser()
    parser.parse_line("Line 1\n")
    parser.parse_line("Line 2\n")
    parser.parse_line("Line 3\n")

    events = parser.flush()
    assert len(events) == 1
    content = events[0].data["content"]
    assert "Line 1" in content
    assert "Line 2" in content
    assert "Line 3" in content
