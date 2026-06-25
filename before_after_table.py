
import pandas as pd
import numpy as np
from scipy import stats
from pydriller import Repository
from datetime import datetime
import re
import lizard

EPOS = {
    "astminer": "https://github.com/JetBrains-Research/astminer",
    "teamcity-dottrace": "https://github.com/JetBrains/teamcity-dottrace",
    "TeamCity.SonarQubePlugin": "https://github.com/JetBrains/TeamCity.SonarQubePlugin",
    "kotlin-code-smells-detector": "https://github.com/JetBrains-Research/kotlin-code-smells-detector",
    "inspection-plugin": "https://github.com/JetBrains/inspection-plugin",
    "eslint-config": "https://github.com/JetBrains/eslint-config",
    "authorship-detection": "https://github.com/JetBrains-Research/authorship-detection",
    "resharper-cyclomatic-complexity": "https://github.com/JetBrains/resharper-cyclomatic-complexity",
    "kotlin-refactoring-samples": "https://github.com/JetBrains-Research/kotlin-refactoring-samples",
    "bugs-classification": "https://github.com/JetBrains-Research/bugs-classification",
    "teamcity-dotmemory": "https://github.com/JetBrains/teamcity-dotmemory",
    "JetBrains.Rider.Debugger.Launcher": "https://github.com/JetBrains/JetBrains.Rider.Debugger.Launcher",
    "intellij-coverage": "https://github.com/JetBrains/intellij-coverage",
    "RefactorInsight": "https://github.com/JetBrains-Research/RefactorInsight",
    "clion-debugger-plugin-stub": "https://github.com/JetBrains/clion-debugger-plugin-stub",
    "topias": "https://github.com/JetBrains-Research/topias",
    "profiler-self-api": "https://github.com/JetBrains/profiler-self-api",
    "metrics-evaluation": "https://github.com/JetBrains-Research/metrics-evaluation",
    "ring-ui-license-checker": "https://github.com/JetBrains/ring-ui-license-checker",
    "intellij-structural-search-for-kotlin": "https://github.com/JetBrains/intellij-structural-search-for-kotlin",
    "profiler-api": "https://github.com/JetBrains/profiler-api",
    "dotmemory-demos": "https://github.com/JetBrains/dotmemory-demos",
    "stylelint-config": "https://github.com/JetBrains/stylelint-config",
    "kotlinRMiner": "https://github.com/JetBrains-Research/kotlinRMiner",
    "MoveMethodGenerator": "https://github.com/JetBrains-Research/MoveMethodGenerator",
    "debugger-memory-agent": "https://github.com/JetBrains/debugger-memory-agent",
    "coverage-report": "https://github.com/JetBrains/coverage-report",
    "DeepBugsPlugin": "https://github.com/JetBrains-Research/DeepBugsPlugin",
    "ruby-type-inference": "https://github.com/JetBrains/ruby-type-inference",
    "viktor": "https://github.com/JetBrains-Research/viktor",
    "python-ml-type-hints": "https://github.com/JetBrains-Research/python-ml-type-hints",
    "embeddings-for-trees": "https://github.com/JetBrains-Research/embeddings-for-trees",
    "nlc2cmd": "https://github.com/JetBrains/nlc2cmd",
    "dotnet-project-model": "https://github.com/JetBrains/dotnet-project-model",
    "teamcity-search-ql": "https://github.com/JetBrains/teamcity-search-ql",
    "contrastive-learning-framework": "https://github.com/JetBrains-Research/contrastive-learning-framework",
    "teamcity-xml-tests-reporting": "https://github.com/JetBrains/teamcity-xml-tests-reporting",
    "code-summarization-dataset": "https://github.com/JetBrains-Research/code-summarization-dataset",
    "deep-gene": "https://github.com/JetBrains-Research/deep-gene",
    "code-completion-benchmark-toolkit": "https://github.com/JetBrains-Research/code-completion-benchmark-toolkit",
    "dataset-anonymizer": "https://github.com/JetBrains-Research/dataset-anonymizer",
    "fishbone": "https://github.com/JetBrains-Research/fishbone",
    "commit_message_generation": "https://github.com/JetBrains-Research/commit_message_generation",
    "kinference": "https://github.com/JetBrains-Research/kinference",
    "optimization-methods": "https://github.com/JetBrains-Research/optimization-methods",
    "span": "https://github.com/JetBrains-Research/span",
    "kinference-primitives": "https://github.com/JetBrains-Research/kinference-primitives",
    "sample-resharper-plugin": "https://github.com/JetBrains/sample-resharper-plugin",
    "teamcity-maven-archetypes": "https://github.com/JetBrains/teamcity-maven-archetypes",
    "intellij-obsolete-plugins": "https://github.com/JetBrains/intellij-obsolete-plugins",
    "teamcity-github-auth": "https://github.com/JetBrains/teamcity-github-auth",
    "intellij-compiler-indices": "https://github.com/JetBrains/intellij-compiler-indices",
    "intellij-sdk-code-samples": "https://github.com/JetBrains/intellij-sdk-code-samples",
    "intellij-micropython": "https://github.com/JetBrains/intellij-micropython",
    "teamcity-aws-core-plugin": "https://github.com/JetBrains/teamcity-aws-core-plugin",
    "plugin-repository-rest-client": "https://github.com/JetBrains/plugin-repository-rest-client",
    "teamcity-dashboard-plugin": "https://github.com/JetBrains/teamcity-dashboard-plugin",
    "resharper-plugins": "https://github.com/JetBrains/resharper-plugins",
    "teamcity-local-cloud": "https://github.com/JetBrains/teamcity-local-cloud",
    "phpstorm-phpstan-plugin": "https://github.com/JetBrains/phpstorm-phpstan-plugin",
    "intellij-scala-historical": "https://github.com/JetBrains/intellij-scala-historical",
    "teamcity-commit-hooks": "https://github.com/JetBrains/teamcity-commit-hooks",
    "IntelliJDeodorant": "https://github.com/JetBrains-Research/IntelliJDeodorant",
    "intellij-stats-collector": "https://github.com/JetBrains/intellij-stats-collector",
    "teamcity-torrent-plugin": "https://github.com/JetBrains/teamcity-torrent-plugin",
    "teamcity-hashicorp-vault-plugin": "https://github.com/JetBrains/teamcity-hashicorp-vault-plugin",
    "teamcity-aws-codepipeline-plugin": "https://github.com/JetBrains/teamcity-aws-codepipeline-plugin",
    "teamcity-investigations-hub-widget": "https://github.com/JetBrains/teamcity-investigations-hub-widget",
    "gradle-changelog-plugin": "https://github.com/JetBrains/gradle-changelog-plugin",
    "intellij-arend": "https://github.com/JetBrains/intellij-arend",
    "mocha-intellij": "https://github.com/JetBrains/mocha-intellij",
    "teamcity-vscode-extension": "https://github.com/JetBrains/teamcity-vscode-extension",
    "hub-dashboard-addons": "https://github.com/JetBrains/hub-dashboard-addons",
    "teamcity-github-issues": "https://github.com/JetBrains/teamcity-github-issues",
    "teamcity-bitbucket-issues": "https://github.com/JetBrains/teamcity-bitbucket-issues",
    "projector-server": "https://github.com/JetBrains/projector-server",
    "resharper-nuget": "https://github.com/JetBrains/resharper-nuget",
    "intellij-platform-plugin-template": "https://github.com/JetBrains/intellij-platform-plugin-template",
    "intellij-kotlin": "https://github.com/JetBrains/intellij-kotlin",
    "ReSharperPowerToys": "https://github.com/JetBrains/ReSharperPowerToys",
    "teamcity-gradle": "https://github.com/JetBrains/teamcity-gradle",
    "js-graphql-intellij-plugin": "https://github.com/JetBrains/js-graphql-intellij-plugin",
    "ij_tutorial_gradle": "https://github.com/JetBrains/ij_tutorial_gradle",
    "hub-widget-ui": "https://github.com/JetBrains/hub-widget-ui",
    "teamcity-sakura-ui-plugins": "https://github.com/JetBrains/teamcity-sakura-ui-plugins",
    "teamcity-caches-cleanup-plugin": "https://github.com/JetBrains/teamcity-caches-cleanup-plugin",
    "teamcity-dotcover": "https://github.com/JetBrains/teamcity-dotcover",
    "sbt-intellij": "https://github.com/JetBrains/sbt-intellij",
    "sbt-idea-shell": "https://github.com/JetBrains/sbt-idea-shell",
    "youtrack-workflows": "https://github.com/JetBrains/youtrack-workflows",
    "plugin-blockmap-patches": "https://github.com/JetBrains/plugin-blockmap-patches",
    "intellij-scala": "https://github.com/JetBrains/intellij-scala",
    "intellij-deps-trove4j": "https://github.com/JetBrains/intellij-deps-trove4j",
    "TeamCity.SESPlugin": "https://github.com/JetBrains/TeamCity.SESPlugin",
    "projector-markdown-plugin": "https://github.com/JetBrains/projector-markdown-plugin",
    "teamcity-shared-resources": "https://github.com/JetBrains/teamcity-shared-resources",
    "educational-plugin": "https://github.com/JetBrains/educational-plugin",
}

EPOS = {
    "astminer": "https://github.com/JetBrains-Research/astminer",
    "teamcity-dottrace": "https://github.com/JetBrains/teamcity-dottrace",
    "TeamCity.SonarQubePlugin": "https://github.com/JetBrains/TeamCity.SonarQubePlugin",
    "kotlin-code-smells-detector": "https://github.com/JetBrains-Research/kotlin-code-smells-detector",
    "inspection-plugin": "https://github.com/JetBrains/inspection-plugin",
    "eslint-config": "https://github.com/JetBrains/eslint-config",
    "authorship-detection": "https://github.com/JetBrains-Research/authorship-detection",
    "resharper-cyclomatic-complexity": "https://github.com/JetBrains/resharper-cyclomatic-complexity",
    "kotlin-refactoring-samples": "https://github.com/JetBrains-Research/kotlin-refactoring-samples",
    "bugs-classification": "https://github.com/JetBrains-Research/bugs-classification",
    "teamcity-dotmemory": "https://github.com/JetBrains/teamcity-dotmemory",
    "JetBrains.Rider.Debugger.Launcher": "https://github.com/JetBrains/JetBrains.Rider.Debugger.Launcher",
    "intellij-coverage": "https://github.com/JetBrains/intellij-coverage",
    "RefactorInsight": "https://github.com/JetBrains-Research/RefactorInsight",
    "clion-debugger-plugin-stub": "https://github.com/JetBrains/clion-debugger-plugin-stub",
    "topias": "https://github.com/JetBrains-Research/topias",
    "profiler-self-api": "https://github.com/JetBrains/profiler-self-api",
    "metrics-evaluation": "https://github.com/JetBrains-Research/metrics-evaluation",
    "ring-ui-license-checker": "https://github.com/JetBrains/ring-ui-license-checker",
    "intellij-structural-search-for-kotlin": "https://github.com/JetBrains/intellij-structural-search-for-kotlin",
    "profiler-api": "https://github.com/JetBrains/profiler-api",
    "dotmemory-demos": "https://github.com/JetBrains/dotmemory-demos",
    "stylelint-config": "https://github.com/JetBrains/stylelint-config",
    "kotlinRMiner": "https://github.com/JetBrains-Research/kotlinRMiner",
    "MoveMethodGenerator": "https://github.com/JetBrains-Research/MoveMethodGenerator",
    "debugger-memory-agent": "https://github.com/JetBrains/debugger-memory-agent",
    "coverage-report": "https://github.com/JetBrains/coverage-report",
    "DeepBugsPlugin": "https://github.com/JetBrains-Research/DeepBugsPlugin",
    "teamcity-build-agents-diff": "https://github.com/JetBrains/teamcity-build-agents-diff",
    "teamcity-environment-fetcher": "https://github.com/JetBrains/teamcity-environment-fetcher",
    "dataset-anonymizer": "https://github.com/JetBrains-Research/dataset-anonymizer",
    "span": "https://github.com/JetBrains-Research/span",
    "nlc2cmd": "https://github.com/JetBrains/nlc2cmd",
    "teamcity-agent-state-plugin": "https://github.com/JetBrains/teamcity-agent-state-plugin",
    "teamcity-xml-tests-reporting": "https://github.com/JetBrains/teamcity-xml-tests-reporting",
    "dotnet-project-model": "https://github.com/JetBrains/dotnet-project-model",
    "commit_message_generation": "https://github.com/JetBrains-Research/commit_message_generation",
    "teamcity-google-agent": "https://github.com/JetBrains/teamcity-google-agent",
    "teamcity-azure-agent": "https://github.com/JetBrains/teamcity-azure-agent",
    "kinference": "https://github.com/JetBrains-Research/kinference",
    "fishbone": "https://github.com/JetBrains-Research/fishbone",
    "contrastive-learning-framework": "https://github.com/JetBrains-Research/contrastive-learning-framework",
    "viktor": "https://github.com/JetBrains-Research/viktor",
    "teamcity-search-ql": "https://github.com/JetBrains/teamcity-search-ql",
    "kinference-primitives": "https://github.com/JetBrains-Research/kinference-primitives",
    "optimization-methods": "https://github.com/JetBrains-Research/optimization-methods",
    "embeddings-for-trees": "https://github.com/JetBrains-Research/embeddings-for-trees",
    "code-completion-benchmark-toolkit": "https://github.com/JetBrains-Research/code-completion-benchmark-toolkit",
    "python-ml-type-hints": "https://github.com/JetBrains-Research/python-ml-type-hints",
    "teamcity-agent-info": "https://github.com/JetBrains/teamcity-agent-info",
    "deep-gene": "https://github.com/JetBrains-Research/deep-gene",
    "code-summarization-dataset": "https://github.com/JetBrains-Research/code-summarization-dataset",
    "ruby-type-inference": "https://github.com/JetBrains/ruby-type-inference",
    "projector-client": "https://github.com/JetBrains/projector-client",
    "projector-demo": "https://github.com/JetBrains/projector-demo",
    "teamcity-amazon-ecs-plugin": "https://github.com/JetBrains/teamcity-amazon-ecs-plugin",
    "RiderSourceCodeAccess": "https://github.com/JetBrains/RiderSourceCodeAccess",
    "teamcity-process-output-parsers": "https://github.com/JetBrains/teamcity-process-output-parsers",
    "teamcity-sccache-plugin": "https://github.com/JetBrains/teamcity-sccache-plugin",
    "resharper-plugins": "https://github.com/JetBrains/resharper-plugins",
    "teamcity-local-cloud": "https://github.com/JetBrains/teamcity-local-cloud",
    "exposed-intellij-plugin": "https://github.com/JetBrains/exposed-intellij-plugin",
    "teamcity-nunit-samples": "https://github.com/JetBrains/teamcity-nunit-samples",
    "teamcity-invitations-plugin": "https://github.com/JetBrains/teamcity-invitations-plugin",
    "teamcity-maven-archetypes": "https://github.com/JetBrains/teamcity-maven-archetypes",
    "teamcity-runas-plugin": "https://github.com/JetBrains/teamcity-runas-plugin",
    "teamcity-torrent-plugin": "https://github.com/JetBrains/teamcity-torrent-plugin",
    "youtrack-scripting": "https://github.com/JetBrains/youtrack-scripting",
    "teamcity-s3-artifact-storage-plugin": "https://github.com/JetBrains/teamcity-s3-artifact-storage-plugin",
    "intellij-deps-java-compatibility": "https://github.com/JetBrains/intellij-deps-java-compatibility",
    "phpstorm-psalm-plugin": "https://github.com/JetBrains/phpstorm-psalm-plugin",
    "sample-resharper-plugin": "https://github.com/JetBrains/sample-resharper-plugin",
    "ReSharperPowerToys": "https://github.com/JetBrains/ReSharperPowerToys",
    "teamcity-hashicorp-vault-plugin": "https://github.com/JetBrains/teamcity-hashicorp-vault-plugin",
    "intellij-arend": "https://github.com/JetBrains/intellij-arend",
    "sbt-idea-example": "https://github.com/JetBrains/sbt-idea-example",
    "teamcity-sysinfo-plugin": "https://github.com/JetBrains/teamcity-sysinfo-plugin",
    "resharper-nuget": "https://github.com/JetBrains/resharper-nuget",
    "teamcity-helm-plugin": "https://github.com/JetBrains/teamcity-helm-plugin",
    "teamcity-ui": "https://github.com/JetBrains/teamcity-ui",
    "teamcity-deployer-plugin": "https://github.com/JetBrains/teamcity-deployer-plugin",
    "teamcity-pipelines-dsl": "https://github.com/JetBrains/teamcity-pipelines-dsl",
    "teamcity-dotnet-plugin": "https://github.com/JetBrains/teamcity-dotnet-plugin",
}

EPOS = {
    # Group 1: Static Analysis & Code Quality
    "astminer": "https://github.com/JetBrains-Research/astminer",
    "refactorinsight": "https://github.com/JetBrains-Research/refactorinsight",
    "kotlin-ref-miner": "https://github.com/JetBrains-Research/kotlin-ref-miner",
    "code-change-miner": "https://github.com/JetBrains-Research/code-change-miner",
    "bug-finder": "https://github.com/JetBrains-Research/bug-finder",
    "buckwheat": "https://github.com/JetBrains-Research/buckwheat",
    "authorship-detection": "https://github.com/JetBrains-Research/authorship-detection",
    "kotlinRMiner": "https://github.com/JetBrains-Research/kotlinRMiner",
    # Group 2: AI & ML Research
    "reflekt": "https://github.com/JetBrains-Research/reflekt",
    "commit_message_generation": "https://github.com/JetBrains-Research/commit_message_generation",
    "washu": "https://github.com/JetBrains-Research/washu",
    "codetracker": "https://github.com/JetBrains-Research/codetracker",
    "formal-lang-course": "https://github.com/JetBrains-Research/formal-lang-course",
    # Group 3: Developer Tools & Infrastructure
    "compose-multiplatform": "https://github.com/JetBrains/compose-multiplatform",
    "educational-plugin": "https://github.com/JetBrains/educational-plugin",
    "intellij-plugins": "https://github.com/JetBrains/intellij-plugins",
    "markdown": "https://github.com/JetBrains/markdown",
    "ideavim": "https://github.com/JetBrains/ideavim",
    "plugin-utilities": "https://github.com/JetBrains-Research/plugin-utilities",
    "spla": "https://github.com/JetBrains-Research/spla",
}

EPOS = {
    # Group 1: Static Analysis & Code Quality
    "astminer": "https://github.com/JetBrains-Research/astminer",
    "refactorinsight": "https://github.com/JetBrains-Research/refactorinsight",
    "kotlin-ref-miner": "https://github.com/JetBrains-Research/kotlin-ref-miner",
    "code-change-miner": "https://github.com/JetBrains-Research/code-change-miner",
    "bug-finder": "https://github.com/JetBrains-Research/bug-finder",
    "buckwheat": "https://github.com/JetBrains-Research/buckwheat",
    "authorship-detection": "https://github.com/JetBrains-Research/authorship-detection",
    "kotlinRMiner": "https://github.com/JetBrains-Research/kotlinRMiner",
    # Group 2: AI & ML Research
    "reflekt": "https://github.com/JetBrains-Research/reflekt",
    "commit_message_generation": "https://github.com/JetBrains-Research/commit_message_generation",
    "washu": "https://github.com/JetBrains-Research/washu",
    "codetracker": "https://github.com/JetBrains-Research/codetracker",
    "formal-lang-course": "https://github.com/JetBrains-Research/formal-lang-course",
    # Group 3: Developer Tools & Infrastructure
    "compose-multiplatform": "https://github.com/JetBrains/compose-multiplatform",
    "educational-plugin": "https://github.com/JetBrains/educational-plugin",
    "intellij-plugins": "https://github.com/JetBrains/intellij-plugins",
    "markdown": "https://github.com/JetBrains/markdown",
    "ideavim": "https://github.com/JetBrains/ideavim",
    "plugin-utilities": "https://github.com/JetBrains-Research/plugin-utilities",
    "spla": "https://github.com/JetBrains-Research/spla",
}

EPOS = {
    "astminer": "https://github.com/JetBrains-Research/astminer",
    "refactorinsight": "https://github.com/JetBrains-Research/refactorinsight",
    "kotlin-ref-miner": "https://github.com/JetBrains-Research/kotlin-ref-miner",
    "code-change-miner": "https://github.com/JetBrains-Research/code-change-miner",
    "bug-finder": "https://github.com/JetBrains-Research/bug-finder",
    "TestSpark": "https://github.com/JetBrains-Research/TestSpark",
    "lca-baselines": "https://github.com/JetBrains-Research/lca-baselines",
    "reflekt": "https://github.com/JetBrains-Research/reflekt",
    "docs-fine-tuning": "https://github.com/JetBrains-Research/docs-fine-tuning",
    "commit_message_generation": "https://github.com/JetBrains-Research/commit_message_generation",
    "code-summarization-dataset": "https://github.com/JetBrains-Research/code-summarization-dataset",
    "similar-python-dependencies": "https://github.com/JetBrains-Research/similar-python-dependencies",
    "compose-multiplatform": "https://github.com/JetBrains/compose-multiplatform",
    "educational-plugin": "https://github.com/JetBrains/educational-plugin",
    "intellij-plugins": "https://github.com/JetBrains/intellij-plugins",
    "markdown": "https://github.com/JetBrains/markdown",
    "ideavim": "https://github.com/JetBrains/ideavim",
    "spbla": "https://github.com/JetBrains-Research/spbla",
    "spla": "https://github.com/JetBrains-Research/spla",
    "paddle": "https://github.com/JetBrains-Research/paddle",
}

GROUPS = {
    "astminer": "Static Analysis",
    "refactorinsight": "Static Analysis",
    "kotlin-ref-miner": "Static Analysis",
    "code-change-miner": "Static Analysis",
    "bug-finder": "Static Analysis",
    "TestSpark": "AI & ML Research",
    "lca-baselines": "AI & ML Research",
    "reflekt": "AI & ML Research",
    "docs-fine-tuning": "AI & ML Research",
    "commit_message_generation": "AI & ML Research",
    "code-summarization-dataset": "AI & ML Research",
    "similar-python-dependencies": "AI & ML Research",
    "compose-multiplatform": "Developer Tools",
    "educational-plugin": "Developer Tools",
    "intellij-plugins": "Developer Tools",
    "markdown": "Developer Tools",
    "ideavim": "Developer Tools",
    "spbla": "Developer Tools",
    "spla": "Developer Tools",
    "paddle": "Developer Tools",
}


REPOS = {
    "astminer": "https://github.com/JetBrains-Research/astminer",
    "teamcity-dottrace": "https://github.com/JetBrains/teamcity-dottrace",
    "TeamCity.SonarQubePlugin": "https://github.com/JetBrains/TeamCity.SonarQubePlugin",
    "kotlin-code-smells-detector": "https://github.com/JetBrains-Research/kotlin-code-smells-detector",
    "inspection-plugin": "https://github.com/JetBrains/inspection-plugin",
    "eslint-config": "https://github.com/JetBrains/eslint-config",
    "authorship-detection": "https://github.com/JetBrains-Research/authorship-detection",
    "resharper-cyclomatic-complexity": "https://github.com/JetBrains/resharper-cyclomatic-complexity",
    "kotlin-refactoring-samples": "https://github.com/JetBrains-Research/kotlin-refactoring-samples",
    "bugs-classification": "https://github.com/JetBrains-Research/bugs-classification",
    "teamcity-dotmemory": "https://github.com/JetBrains/teamcity-dotmemory",
    "JetBrains.Rider.Debugger.Launcher": "https://github.com/JetBrains/JetBrains.Rider.Debugger.Launcher",
    "intellij-coverage": "https://github.com/JetBrains/intellij-coverage",
    "RefactorInsight": "https://github.com/JetBrains-Research/RefactorInsight",
    "clion-debugger-plugin-stub": "https://github.com/JetBrains/clion-debugger-plugin-stub",
    "topias": "https://github.com/JetBrains-Research/topias",
    "profiler-self-api": "https://github.com/JetBrains/profiler-self-api",
    "metrics-evaluation": "https://github.com/JetBrains-Research/metrics-evaluation",
    "ring-ui-license-checker": "https://github.com/JetBrains/ring-ui-license-checker",
    "intellij-structural-search-for-kotlin": "https://github.com/JetBrains/intellij-structural-search-for-kotlin",
    "profiler-api": "https://github.com/JetBrains/profiler-api",
    "dotmemory-demos": "https://github.com/JetBrains/dotmemory-demos",
    "stylelint-config": "https://github.com/JetBrains/stylelint-config",
    "kotlinRMiner": "https://github.com/JetBrains-Research/kotlinRMiner",
    "MoveMethodGenerator": "https://github.com/JetBrains-Research/MoveMethodGenerator",
    "debugger-memory-agent": "https://github.com/JetBrains/debugger-memory-agent",
    "coverage-report": "https://github.com/JetBrains/coverage-report",
    "DeepBugsPlugin": "https://github.com/JetBrains-Research/DeepBugsPlugin",
    "ruby-type-inference": "https://github.com/JetBrains/ruby-type-inference",
    "viktor": "https://github.com/JetBrains-Research/viktor",
    "python-ml-type-hints": "https://github.com/JetBrains-Research/python-ml-type-hints",
    "embeddings-for-trees": "https://github.com/JetBrains-Research/embeddings-for-trees",
    "nlc2cmd": "https://github.com/JetBrains/nlc2cmd",
    "dotnet-project-model": "https://github.com/JetBrains/dotnet-project-model",
    "teamcity-search-ql": "https://github.com/JetBrains/teamcity-search-ql",
    "contrastive-learning-framework": "https://github.com/JetBrains-Research/contrastive-learning-framework",
    "teamcity-xml-tests-reporting": "https://github.com/JetBrains/teamcity-xml-tests-reporting",
    "code-summarization-dataset": "https://github.com/JetBrains-Research/code-summarization-dataset",
    "deep-gene": "https://github.com/JetBrains-Research/deep-gene",
    "code-completion-benchmark-toolkit": "https://github.com/JetBrains-Research/code-completion-benchmark-toolkit",
    "dataset-anonymizer": "https://github.com/JetBrains-Research/dataset-anonymizer",
    "fishbone": "https://github.com/JetBrains-Research/fishbone",
    "commit_message_generation": "https://github.com/JetBrains-Research/commit_message_generation",
    "kinference": "https://github.com/JetBrains-Research/kinference",
    "optimization-methods": "https://github.com/JetBrains-Research/optimization-methods",
    "span": "https://github.com/JetBrains-Research/span",
    "kinference-primitives": "https://github.com/JetBrains-Research/kinference-primitives",
    "sample-resharper-plugin": "https://github.com/JetBrains/sample-resharper-plugin",
    "teamcity-maven-archetypes": "https://github.com/JetBrains/teamcity-maven-archetypes",
    "intellij-obsolete-plugins": "https://github.com/JetBrains/intellij-obsolete-plugins",
    "teamcity-github-auth": "https://github.com/JetBrains/teamcity-github-auth",
    "intellij-compiler-indices": "https://github.com/JetBrains/intellij-compiler-indices",
    "intellij-sdk-code-samples": "https://github.com/JetBrains/intellij-sdk-code-samples",
    "intellij-micropython": "https://github.com/JetBrains/intellij-micropython",
    "teamcity-aws-core-plugin": "https://github.com/JetBrains/teamcity-aws-core-plugin",
    "plugin-repository-rest-client": "https://github.com/JetBrains/plugin-repository-rest-client",
    "teamcity-dashboard-plugin": "https://github.com/JetBrains/teamcity-dashboard-plugin",
    "resharper-plugins": "https://github.com/JetBrains/resharper-plugins",
    "teamcity-local-cloud": "https://github.com/JetBrains/teamcity-local-cloud",
    "phpstorm-phpstan-plugin": "https://github.com/JetBrains/phpstorm-phpstan-plugin",
    "intellij-scala-historical": "https://github.com/JetBrains/intellij-scala-historical",
    "teamcity-commit-hooks": "https://github.com/JetBrains/teamcity-commit-hooks",
    "IntelliJDeodorant": "https://github.com/JetBrains-Research/IntelliJDeodorant",
    "intellij-stats-collector": "https://github.com/JetBrains/intellij-stats-collector",
    "teamcity-torrent-plugin": "https://github.com/JetBrains/teamcity-torrent-plugin",
    "teamcity-hashicorp-vault-plugin": "https://github.com/JetBrains/teamcity-hashicorp-vault-plugin",
    "teamcity-aws-codepipeline-plugin": "https://github.com/JetBrains/teamcity-aws-codepipeline-plugin",
    "teamcity-investigations-hub-widget": "https://github.com/JetBrains/teamcity-investigations-hub-widget",
    "gradle-changelog-plugin": "https://github.com/JetBrains/gradle-changelog-plugin",
    "intellij-arend": "https://github.com/JetBrains/intellij-arend",
    "mocha-intellij": "https://github.com/JetBrains/mocha-intellij",
    "teamcity-vscode-extension": "https://github.com/JetBrains/teamcity-vscode-extension",
    "hub-dashboard-addons": "https://github.com/JetBrains/hub-dashboard-addons",
    "teamcity-github-issues": "https://github.com/JetBrains/teamcity-github-issues",
    "teamcity-bitbucket-issues": "https://github.com/JetBrains/teamcity-bitbucket-issues",
    "projector-server": "https://github.com/JetBrains/projector-server",
    "resharper-nuget": "https://github.com/JetBrains/resharper-nuget",
    "intellij-platform-plugin-template": "https://github.com/JetBrains/intellij-platform-plugin-template",
    "intellij-kotlin": "https://github.com/JetBrains/intellij-kotlin",
    "ReSharperPowerToys": "https://github.com/JetBrains/ReSharperPowerToys",
    "teamcity-gradle": "https://github.com/JetBrains/teamcity-gradle",
    "js-graphql-intellij-plugin": "https://github.com/JetBrains/js-graphql-intellij-plugin",
    "ij_tutorial_gradle": "https://github.com/JetBrains/ij_tutorial_gradle",
    "hub-widget-ui": "https://github.com/JetBrains/hub-widget-ui",
    "teamcity-sakura-ui-plugins": "https://github.com/JetBrains/teamcity-sakura-ui-plugins",
    "teamcity-caches-cleanup-plugin": "https://github.com/JetBrains/teamcity-caches-cleanup-plugin",
    "teamcity-dotcover": "https://github.com/JetBrains/teamcity-dotcover",
    "sbt-intellij": "https://github.com/JetBrains/sbt-intellij",
    "sbt-idea-shell": "https://github.com/JetBrains/sbt-idea-shell",
    "youtrack-workflows": "https://github.com/JetBrains/youtrack-workflows",
    "plugin-blockmap-patches": "https://github.com/JetBrains/plugin-blockmap-patches",
    "intellij-scala": "https://github.com/JetBrains/intellij-scala",
    "intellij-deps-trove4j": "https://github.com/JetBrains/intellij-deps-trove4j",
    "TeamCity.SESPlugin": "https://github.com/JetBrains/TeamCity.SESPlugin",
    "projector-markdown-plugin": "https://github.com/JetBrains/projector-markdown-plugin",
    "teamcity-shared-resources": "https://github.com/JetBrains/teamcity-shared-resources",
    "educational-plugin": "https://github.com/JetBrains/educational-plugin",
}

GROUPS = {
    "astminer": "Static Analysis",
    "teamcity-dottrace": "Static Analysis",
    "TeamCity.SonarQubePlugin": "Static Analysis",
    "kotlin-code-smells-detector": "Static Analysis",
    "inspection-plugin": "Static Analysis",
    "eslint-config": "Static Analysis",
    "authorship-detection": "Static Analysis",
    "resharper-cyclomatic-complexity": "Static Analysis",
    "kotlin-refactoring-samples": "Static Analysis",
    "bugs-classification": "Static Analysis",
    "teamcity-dotmemory": "Static Analysis",
    "JetBrains.Rider.Debugger.Launcher": "Static Analysis",
    "intellij-coverage": "Static Analysis",
    "RefactorInsight": "Static Analysis",
    "clion-debugger-plugin-stub": "Static Analysis",
    "topias": "Static Analysis",
    "profiler-self-api": "Static Analysis",
    "metrics-evaluation": "Static Analysis",
    "ring-ui-license-checker": "Static Analysis",
    "intellij-structural-search-for-kotlin": "Static Analysis",
    "profiler-api": "Static Analysis",
    "dotmemory-demos": "Static Analysis",
    "stylelint-config": "Static Analysis",
    "kotlinRMiner": "Static Analysis",
    "MoveMethodGenerator": "Static Analysis",
    "debugger-memory-agent": "Static Analysis",
    "coverage-report": "Static Analysis",
    "DeepBugsPlugin": "Static Analysis",
    "ruby-type-inference": "AI & ML Research",
    "viktor": "AI & ML Research",
    "python-ml-type-hints": "AI & ML Research",
    "embeddings-for-trees": "AI & ML Research",
    "nlc2cmd": "AI & ML Research",
    "dotnet-project-model": "AI & ML Research",
    "teamcity-search-ql": "AI & ML Research",
    "contrastive-learning-framework": "AI & ML Research",
    "teamcity-xml-tests-reporting": "AI & ML Research",
    "code-summarization-dataset": "AI & ML Research",
    "deep-gene": "AI & ML Research",
    "code-completion-benchmark-toolkit": "AI & ML Research",
    "dataset-anonymizer": "AI & ML Research",
    "fishbone": "AI & ML Research",
    "commit_message_generation": "AI & ML Research",
    "kinference": "AI & ML Research",
    "optimization-methods": "AI & ML Research",
    "span": "AI & ML Research",
    "kinference-primitives": "AI & ML Research",
    "sample-resharper-plugin": "Developer Tools",
    "teamcity-maven-archetypes": "Developer Tools",
    "intellij-obsolete-plugins": "Developer Tools",
    "teamcity-github-auth": "Developer Tools",
    "intellij-compiler-indices": "Developer Tools",
    "intellij-sdk-code-samples": "Developer Tools",
    "intellij-micropython": "Developer Tools",
    "teamcity-aws-core-plugin": "Developer Tools",
    "plugin-repository-rest-client": "Developer Tools",
    "teamcity-dashboard-plugin": "Developer Tools",
    "resharper-plugins": "Developer Tools",
    "teamcity-local-cloud": "Developer Tools",
    "phpstorm-phpstan-plugin": "Developer Tools",
    "intellij-scala-historical": "Developer Tools",
    "teamcity-commit-hooks": "Developer Tools",
    "IntelliJDeodorant": "Developer Tools",
    "intellij-stats-collector": "Developer Tools",
    "teamcity-torrent-plugin": "Developer Tools",
    "teamcity-hashicorp-vault-plugin": "Developer Tools",
    "teamcity-aws-codepipeline-plugin": "Developer Tools",
    "teamcity-investigations-hub-widget": "Developer Tools",
    "gradle-changelog-plugin": "Developer Tools",
    "intellij-arend": "Developer Tools",
    "mocha-intellij": "Developer Tools",
    "teamcity-vscode-extension": "Developer Tools",
    "hub-dashboard-addons": "Developer Tools",
    "teamcity-github-issues": "Developer Tools",
    "teamcity-bitbucket-issues": "Developer Tools",
    "projector-server": "Developer Tools",
    "resharper-nuget": "Developer Tools",
    "intellij-platform-plugin-template": "Developer Tools",
    "intellij-kotlin": "Developer Tools",
    "ReSharperPowerToys": "Developer Tools",
    "teamcity-gradle": "Developer Tools",
    "js-graphql-intellij-plugin": "Developer Tools",
    "ij_tutorial_gradle": "Developer Tools",
    "hub-widget-ui": "Developer Tools",
    "teamcity-sakura-ui-plugins": "Developer Tools",
    "teamcity-caches-cleanup-plugin": "Developer Tools",
    "teamcity-dotcover": "Developer Tools",
    "sbt-intellij": "Developer Tools",
    "sbt-idea-shell": "Developer Tools",
    "youtrack-workflows": "Developer Tools",
    "plugin-blockmap-patches": "Developer Tools",
    "intellij-scala": "Developer Tools",
    "intellij-deps-trove4j": "Developer Tools",
    "TeamCity.SESPlugin": "Developer Tools",
    "projector-markdown-plugin": "Developer Tools",
    "teamcity-shared-resources": "Developer Tools",
    "educational-plugin": "Developer Tools",
}

BUG_KEYWORDS = re.compile(r"\b(fix|bug|error|issue|crash|defect|patch|hotfix|broken|failure)\b", re.IGNORECASE)
PRE_END = datetime(2021, 6, 1)
POST_START = datetime(2023, 1, 1)

def comment_ratio(source_code, extension):
    if not source_code:
        return None
    lines = source_code.split("\n")
    total = len([l for l in lines if l.strip()])
    if total == 0:
        return None
    if extension == ".py":
        comments = len([l for l in lines if l.strip().startswith("#")])
    elif extension in [".kt", ".java"]:
        comments = len([l for l in lines if l.strip().startswith("//")])
    else:
        return None
    return comments / total

def get_cc(source_code, filename):
    try:
        analysis = lizard.analyze_file.analyze_source_code(filename, source_code)
        if not analysis.function_list:
            return None, None
        cc = sum(f.cyclomatic_complexity for f in analysis.function_list) / len(analysis.function_list)
        fl = sum(f.length for f in analysis.function_list) / len(analysis.function_list)
        return cc, fl
    except:
        return None, None

all_results = []

for repo_name, repo_url in REPOS.items():
    print(f"-> {repo_name}...")
    pre_metrics = {"comment_ratio": [], "bugfix": [], "lines": [], "del_add": [], "cc": [], "fn_len": []}
    post_metrics = {"comment_ratio": [], "bugfix": [], "lines": [], "del_add": [], "cc": [], "fn_len": []}

    try:
        for commit in Repository(repo_url, since=datetime(2019,1,1), only_no_merge=True).traverse_commits():
            dt = commit.committer_date.replace(tzinfo=None)
            if dt <= PRE_END:
                period = "pre"
            elif dt >= POST_START:
                period = "post"
            else:
                continue

            bucket = pre_metrics if period == "pre" else post_metrics
            is_bugfix = 1 if BUG_KEYWORDS.search(commit.msg or "") else 0
            added = sum(f.added_lines for f in commit.modified_files)
            deleted = sum(f.deleted_lines for f in commit.modified_files)
            bucket["bugfix"].append(is_bugfix)
            bucket["lines"].append(added + deleted)
            if added > 0:
                bucket["del_add"].append(deleted / added)

            for file in commit.modified_files:
                ext = None
                for e in [".py", ".kt", ".java"]:
                    if file.filename.endswith(e):
                        ext = e
                        break
                if ext and file.source_code:
                    r = comment_ratio(file.source_code, ext)
                    if r is not None:
                        bucket["comment_ratio"].append(r)
                    cc, fl = get_cc(file.source_code, file.filename)
                    if cc is not None:
                        bucket["cc"].append(cc)
                        bucket["fn_len"].append(fl)

        def safe_mean(lst):
            return np.mean(lst) if lst else None

        def mw_pval(pre, post):
            if len(pre) < 5 or len(post) < 5:
                return None
            _, p = stats.mannwhitneyu(pre, post, alternative="two-sided")
            return p

        for metric_key, label in [
            ("comment_ratio", "Comment Density"),
            ("bugfix", "Bug-Fix Ratio"),
            ("lines", "Avg Lines/Commit"),
            ("del_add", "Del/Add Ratio"),
            ("cc", "Cyclomatic Complexity"),
            ("fn_len", "Avg Function Length"),
        ]:
            pre_vals = pre_metrics[metric_key]
            post_vals = post_metrics[metric_key]
            pre_mean = safe_mean(pre_vals)
            post_mean = safe_mean(post_vals)
            pval = mw_pval(pre_vals, post_vals)

            if pre_mean is not None and post_mean is not None and pre_mean != 0:
                change_pct = ((post_mean - pre_mean) / pre_mean) * 100
            else:
                change_pct = None

            # Cohen d effect size
            def cohens_d(a, b):
                if len(a) < 2 or len(b) < 2:
                    return None
                pooled_std = np.sqrt((np.std(a, ddof=1)**2 + np.std(b, ddof=1)**2) / 2)
                if pooled_std == 0:
                    return None
                return (np.mean(b) - np.mean(a)) / pooled_std

            d = cohens_d(pre_vals, post_vals) if pre_vals and post_vals else None

            all_results.append({
                "Group": GROUPS[repo_name],
                "Repository": repo_name,
                "Metric": label,
                "Pre-LLM Mean": round(pre_mean, 4) if pre_mean else "N/A",
                "Post-LLM Mean": round(post_mean, 4) if post_mean else "N/A",
                "Change %": f"{change_pct:+.1f}%" if change_pct is not None else "N/A",
                "p-value": f"{pval:.4f}" if pval else "N/A",
                "Significant": "✓" if pval and pval < 0.05 else "",
                "Cohen d": f"{d:.3f}" if d is not None else "N/A",
                "Effect Size": "large" if d and abs(d) >= 0.8 else ("medium" if d and abs(d) >= 0.5 else ("small" if d and abs(d) >= 0.2 else "negligible")) if d else "N/A",
            })

    except Exception as e:
        print(f"   Error: {e}")

df = pd.DataFrame(all_results)
df = df.sort_values(["Group", "Repository", "Metric"])
df.to_csv("before_after_table.csv", index=False)

print("\n=== BEFORE/AFTER TABLE ===")
print(df.to_string(index=False))
print("\nSaved: before_after_table.csv")
