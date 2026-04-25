from langgraph.graph import END, START, StateGraph

from app.graph.nodes import (
    analyze_gaps_node,
    analyze_schema_node,
    analyze_topology_node,
    analyze_yoast_node,
    discover_keywords_node,
    extract_style_node,
    read_site_content_node,
)
from app.graph.state import WorkflowState


def build_workflow() -> StateGraph:
    """
    Build the SEO agent workflow graph.

    Flow:
        discover_keywords → read_site_content → extract_style →
        analyze_topology → analyze_yoast → analyze_schema → analyze_gaps

    The workflow now includes:
    - Style extraction for consistent tone
    - Content topology analysis (pillar/satellite structure)
    - Yoast SEO analysis (meta, keywords, issues)
    - Schema.org analysis (AI readiness, missing schemas)
    - GEO-enhanced gap analysis
    """
    graph = StateGraph(WorkflowState)

    graph.add_node("discover_keywords", discover_keywords_node)
    graph.add_node("read_site_content", read_site_content_node)
    graph.add_node("extract_style", extract_style_node)
    graph.add_node("analyze_topology", analyze_topology_node)
    graph.add_node("analyze_yoast", analyze_yoast_node)
    graph.add_node("analyze_schema", analyze_schema_node)
    graph.add_node("analyze_gaps", analyze_gaps_node)

    graph.add_edge(START, "discover_keywords")
    graph.add_edge("discover_keywords", "read_site_content")
    graph.add_edge("read_site_content", "extract_style")
    graph.add_edge("extract_style", "analyze_topology")
    graph.add_edge("analyze_topology", "analyze_yoast")
    graph.add_edge("analyze_yoast", "analyze_schema")
    graph.add_edge("analyze_schema", "analyze_gaps")
    graph.add_edge("analyze_gaps", END)

    return graph.compile()


workflow = build_workflow()
