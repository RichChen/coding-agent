from events.handlers import echo_handler
from events.message import EventMessage
from events.pipeline import EventPipeline
from events.registry import HandlerRegistry
from events.serializer import serialize_v1


def test_pipeline_processes_registered_handler():
    registry = HandlerRegistry()
    registry.register("echo", echo_handler)
    pipeline = EventPipeline(registry)
    raw = serialize_v1(EventMessage("echo", {"text": "hi"}))
    result = pipeline.process_raw(raw)
    assert result.ok
    assert result.value["echo"] == "hi"
