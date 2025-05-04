from pocketflow import Flow
# Import all node classes from nodes.py
from nodes import (
    FetchRepo,
    IdentifyAbstractions,
    AnalyzeRelationships,
    OrderChapters,
    WriteChapters,
    CombineTutorial
)

def create_tutorial_flow(shared={}):
    """Creates and returns the codebase tutorial generation flow."""

    max_retries, wait = shared.get("max_retries",3), shared.get("wait",10)

    # Instantiate nodes
    fetch_repo = FetchRepo()
    identify_abstractions = IdentifyAbstractions(max_retries=max_retries, wait=wait)
    analyze_relationships = AnalyzeRelationships(max_retries=max_retries, wait=wait)
    order_chapters = OrderChapters(max_retries=max_retries, wait=wait)
    write_chapters = WriteChapters(max_retries=max_retries, wait=wait) # This is a BatchNode
    combine_tutorial = CombineTutorial()

    # Connect nodes in sequence based on the design
    fetch_repo >> identify_abstractions
    identify_abstractions >> analyze_relationships
    analyze_relationships >> order_chapters
    order_chapters >> write_chapters
    write_chapters >> combine_tutorial

    # Create the flow starting with FetchRepo
    tutorial_flow = Flow(start=fetch_repo)

    return tutorial_flow
