#! /usr/bin/env python3

# Architecture Diagram Generator: Multi-Agent Git Project Graph
from diagrams import Cluster, Diagram
from diagrams.aws.compute import ECS
from diagrams.aws.database import Neptune
from diagrams.custom import Custom
from diagrams.generic.storage import Storage
from diagrams.onprem.client import User
from diagrams.onprem.inmemory import Redis
from diagrams.onprem.queue import Kafka
from diagrams.onprem.vcs import Github
from diagrams.programming.language import Python

with Diagram("Multi-Agent Git Artifact Relationship System", show=False):
    user = User("Developer / API Client")

    with Cluster("Ingestion Layer"):
        git_sources = [Github("GitHub"), Custom("GitLab", "./icons/gitlab.png")]
        fetcher = Python("Git Fetcher")
        parser = Python("Build Parser / ORT")
        storage = Storage("Repo Cache")
        git_sources >> fetcher >> storage >> parser

    with Cluster("Artifact/Dependency Extraction"):
        extractor = Python("Artifact Extractor")
        normalizer = Python("Normalizer")
        artifact_store = Storage("Artifact Metadata")
        parser >> extractor >> normalizer >> artifact_store

    with Cluster("Graph Layer"):
        graphdb = Neptune("Graph DB (Neo4j / Neptune)")
        artifact_store >> graphdb

    with Cluster("MCP & Agent System"):
        agent_router = Python("Agent Router")
        kafka = Kafka("Event Bus")
        redis = Redis("Agent Memory")

        agents = [
            Python("Scaffolder Agent"),
            Python("Dependency Advisor"),
            Python("Security Checker"),
            Python("Test Generator"),
            Python("PR Validator"),
        ]

        agent_router >> kafka >> agents
        agents >> redis
        redis >> agent_router
        graphdb >> agent_router

    with Cluster("API & Insights"):
        api = Python("FastAPI / GraphQL")
        dashboard = Custom("UI Dashboard", "./icons/webapp.png")

        graphdb >> api
        agent_router >> api
        user >> dashboard >> api
