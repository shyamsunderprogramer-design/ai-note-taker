"""
CLI entry point for the Interview Data Ingestion Pipeline.

Usage:
    # Ingest from local cloned repos
    python -m agents.ingestion --local /path/to/DevOps-Interview-Questions1 /path/to/Books_Materials_Devops_Practice

    # Ingest from GitHub (auto-clone)
    python -m agents.ingestion --github ShyamSunder89/DevOps-Interview-Questions1 ShyamSunder89/Books_Materials_Devops_Practice

    # Only load into cognitive graph (skip RAG)
    python -m agents.ingestion --github ShyamSunder89/DevOps-Interview-Questions1 --graph-only

    # Only load into Document RAG (skip graph)
    python -m agents.ingestion --github ShyamSunder89/Books_Materials_Devops_Practice --rag-only

    # Dry run (parse but don't load)
    python -m agents.ingestion --local /path/to/repo --dry-run

    # Load from cache (when Neo4j becomes available)
    python -m agents.ingestion --load-cache
"""

import argparse
import json
import logging
import sys

from agents.ingestion.pipeline import IngestionPipeline


def main():
    parser = argparse.ArgumentParser(
        description="Interview Data Ingestion Pipeline — Load Q&A and PDF content into Cognitive Graph and Document RAG"
    )

    # Input source
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "--local",
        nargs="+",
        help="Path(s) to locally cloned repo directories",
    )
    input_group.add_argument(
        "--github",
        nargs="+",
        help="GitHub repo URL(s) or owner/repo strings to clone and ingest",
    )
    input_group.add_argument(
        "--load-cache",
        action="store_true",
        help="Load Q&A pairs from the JSON cache into Neo4j (after it becomes available)",
    )

    # Mode
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--graph-only",
        action="store_true",
        help="Only load into Cognitive Graph (skip Document RAG)",
    )
    mode_group.add_argument(
        "--rag-only",
        action="store_true",
        help="Only load into Document RAG (skip Cognitive Graph)",
    )

    # Options
    parser.add_argument(
        "--clone-dir",
        default=None,
        help="Directory to clone GitHub repos into (default: temp dir)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse repos but don't load into data stores",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )

    args = parser.parse_args()

    # Configure logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    pipeline = IngestionPipeline()

    # Handle --load-cache
    if args.load_cache:
        logger = logging.getLogger("ingestion.cli")
        logger.info("[CLI] Loading from cache into Neo4j...")
        stats = pipeline.graph_loader.load_from_cache()
        result = stats.to_dict()
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Cache loaded: {stats.loaded} pairs, {stats.nodes_created} nodes created, {stats.errors} errors")
        sys.exit(0 if stats.errors == 0 else 1)

    # Determine mode
    mode = "full"
    if args.graph_only:
        mode = "graph_only"
    elif args.rag_only:
        mode = "rag_only"

    # Run ingestion
    if args.local:
        stats = pipeline.ingest_from_local(
            repo_paths=args.local,
            mode=mode,
            dry_run=args.dry_run,
        )
    elif args.github:
        stats = pipeline.ingest_from_github(
            repo_urls=args.github,
            clone_dir=args.clone_dir,
            mode=mode,
            dry_run=args.dry_run,
        )

    # Output results
    result = stats.to_dict()
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print("\n" + "=" * 60)
        print("INGESTION RESULTS")
        print("=" * 60)
        print(f"Repos processed:       {stats.repos_processed}")
        print(f"Q&A pairs found:       {stats.qa_pairs_found}")
        print(f"Q&A loaded to graph:  {stats.qa_pairs_loaded_graph}")
        print(f"Q&A cached (no Neo4j):{stats.qa_pairs_cached}")
        print(f"Q&A loaded to RAG:     {stats.qa_pairs_loaded_rag}")
        print(f"PDFs processed:        {stats.pdfs_processed}")
        print(f"PDFs loaded to RAG:    {stats.pdfs_loaded_rag}")
        print(f"Graph nodes created:   {stats.graph_nodes_created}")
        print(f"RAG chunks created:    {stats.rag_chunks_created}")
        print(f"Errors:                {len(stats.errors)}")
        print(f"Time:                  {stats.elapsed_seconds:.1f}s")
        if stats.errors:
            print("\nErrors:")
            for err in stats.errors[:10]:
                print(f"  - {err}")
            if len(stats.errors) > 10:
                print(f"  ... and {len(stats.errors) - 10} more")
        print("=" * 60)

    sys.exit(0 if not stats.errors else 1)


if __name__ == "__main__":
    main()