from pydriller import Repository
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import re
import lizard

print("Full analysis starting... (may take 1-2 hours for 199 repos)")

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
    # Group 2: AI & ML Research
    "TestSpark": "https://github.com/JetBrains-Research/TestSpark",
    "lca-baselines": "https://github.com/JetBrains-Research/lca-baselines",
    "reflekt": "https://github.com/JetBrains-Research/reflekt",
    "docs-fine-tuning": "https://github.com/JetBrains-Research/docs-fine-tuning",
    "commit_message_generation": "https://github.com/JetBrains-Research/commit_message_generation",
    "code-summarization-dataset": "https://github.com/JetBrains-Research/code-summarization-dataset",
    "similar-python-dependencies": "https://github.com/JetBrains-Research/similar-python-dependencies",
    # Group 3: Developer Tools & Infrastructure
    "compose-multiplatform": "https://github.com/JetBrains/compose-multiplatform",
    "educational-plugin": "https://github.com/JetBrains/educational-plugin",
    "intellij-plugins": "https://github.com/JetBrains/intellij-plugins",
    "markdown": "https://github.com/JetBrains/markdown",
    "ideavim": "https://github.com/JetBrains/ideavim",
    "spbla": "https://github.com/JetBrains-Research/spbla",
    "spla": "https://github.com/JetBrains-Research/spla",
    "paddle": "https://github.com/JetBrains-Research/paddle",
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


REPOS = {
    "JPS": "https://github.com/JetBrains/JPS",
    "YouTrackSharp": "https://github.com/JetBrains/YouTrackSharp",
    "ideavim": "https://github.com/JetBrains/ideavim",
    "psiviewer": "https://github.com/JetBrains/psiviewer",
    "emacs4ij": "https://github.com/JetBrains/emacs4ij",
    "intellij-community": "https://github.com/JetBrains/intellij-community",
    "TeamCity.ServiceMessages": "https://github.com/JetBrains/TeamCity.ServiceMessages",
    "intellij-scala": "https://github.com/JetBrains/intellij-scala",
    "teamcity-messages": "https://github.com/JetBrains/teamcity-messages",
    "teamcity-cpp": "https://github.com/JetBrains/teamcity-cpp",
    "kotlin": "https://github.com/JetBrains/kotlin",
    "intellij-plugin-verifier": "https://github.com/JetBrains/intellij-plugin-verifier",
    "intellij-samples": "https://github.com/JetBrains/intellij-samples",
    "youtrack-workflows": "https://github.com/JetBrains/youtrack-workflows",
    "intellij-plugins": "https://github.com/JetBrains/intellij-plugins",
    "teamcity-shared-resources": "https://github.com/JetBrains/teamcity-shared-resources",
    "teamcity-queue-pauser": "https://github.com/JetBrains/teamcity-queue-pauser",
    "resharper-angularjs": "https://github.com/JetBrains/resharper-angularjs",
    "intellij-sbt": "https://github.com/JetBrains/intellij-sbt",
    "mapper": "https://github.com/JetBrains/mapper",
    "dotpeek-nupeek": "https://github.com/JetBrains/dotpeek-nupeek",
    "resharper-rider-samples": "https://github.com/JetBrains/resharper-rider-samples",
    "pty4j": "https://github.com/JetBrains/pty4j",
    "Exposed": "https://github.com/JetBrains/Exposed",
    "python-skeletons": "https://github.com/JetBrains/python-skeletons",
    "dotpeek-peekfx": "https://github.com/JetBrains/dotpeek-peekfx",
    "Android-Tuts-Samples": "https://github.com/JetBrains/Android-Tuts-Samples",
    "kotlin-web-site": "https://github.com/JetBrains/kotlin-web-site",
    "jetpad-projectional-open-source": "https://github.com/JetBrains/jetpad-projectional-open-source",
    "tc-sbt-runner": "https://github.com/JetBrains/tc-sbt-runner",
    "dotpeek-console": "https://github.com/JetBrains/dotpeek-console",
    "teamcity-build-agents-diff": "https://github.com/JetBrains/teamcity-build-agents-diff",
    "teamcity-sdk-maven-plugin": "https://github.com/JetBrains/teamcity-sdk-maven-plugin",
    "teamcity-investigations-auto-assigner": "https://github.com/JetBrains/teamcity-investigations-auto-assigner",
    "xodus": "https://github.com/JetBrains/xodus",
    "TeamCity.SonarQubePlugin": "https://github.com/JetBrains/TeamCity.SonarQubePlugin",
    "tc-vso-rooms": "https://github.com/JetBrains/tc-vso-rooms",
    "vijava": "https://github.com/JetBrains/vijava",
    "fernflower": "https://github.com/JetBrains/fernflower",
    "markdown": "https://github.com/JetBrains/markdown",
    "resharper-presentation-assistant": "https://github.com/JetBrains/resharper-presentation-assistant",
    "teamcity-deployer-plugin": "https://github.com/JetBrains/teamcity-deployer-plugin",
    "sbt-ide-settings": "https://github.com/JetBrains/sbt-ide-settings",
    "Arend": "https://github.com/JetBrains/Arend",
    "teamcity-azure-active-directory": "https://github.com/JetBrains/teamcity-azure-active-directory",
    "arend-lib": "https://github.com/JetBrains/arend-lib",
    "teamcity-dottrace": "https://github.com/JetBrains/teamcity-dottrace",
    "resharper-cyclomatic-complexity": "https://github.com/JetBrains/resharper-cyclomatic-complexity",
    "sbt-intellij": "https://github.com/JetBrains/sbt-intellij",
    "intellij-scala-historical": "https://github.com/JetBrains/intellij-scala-historical",
    "websandbox": "https://github.com/JetBrains/websandbox",
    "teamcity-dotnet-plugin": "https://github.com/JetBrains/teamcity-dotnet-plugin",
    "resharper-ultimate-whatsnew": "https://github.com/JetBrains/resharper-ultimate-whatsnew",
    "jdk8u_corba": "https://github.com/JetBrains/jdk8u_corba",
    "jdk8u_hotspot": "https://github.com/JetBrains/jdk8u_hotspot",
    "jdk8u_jaxws": "https://github.com/JetBrains/jdk8u_jaxws",
    "jdk8u_langtools": "https://github.com/JetBrains/jdk8u_langtools",
    "jdk8u_nashorn": "https://github.com/JetBrains/jdk8u_nashorn",
    "email-parser": "https://github.com/JetBrains/email-parser",
    "teamcity-caches-cleanup-plugin": "https://github.com/JetBrains/teamcity-caches-cleanup-plugin",
    "ExternalAnnotations": "https://github.com/JetBrains/ExternalAnnotations",
    "tfsIntegration": "https://github.com/JetBrains/tfsIntegration",
    "dotmemory-demos": "https://github.com/JetBrains/dotmemory-demos",
    "karma-gwt": "https://github.com/JetBrains/karma-gwt",
    "runAs": "https://github.com/JetBrains/runAs",
    "teamcity-s3-artifact-storage-plugin": "https://github.com/JetBrains/teamcity-s3-artifact-storage-plugin",
    "webpack-toolkit": "https://github.com/JetBrains/webpack-toolkit",
    "teamcity-commit-hooks": "https://github.com/JetBrains/teamcity-commit-hooks",
    "teamcity-github-auth": "https://github.com/JetBrains/teamcity-github-auth",
    "jdk8u_tests": "https://github.com/JetBrains/jdk8u_tests",
    "sbt-idea-plugin": "https://github.com/JetBrains/sbt-idea-plugin",
    "rsynk": "https://github.com/JetBrains/rsynk",
    "intellij-deps-trove4j": "https://github.com/JetBrains/intellij-deps-trove4j",
    "idea-php-dotenv-plugin": "https://github.com/JetBrains/idea-php-dotenv-plugin",
    "stylelint-config": "https://github.com/JetBrains/stylelint-config",
    "ruby-type-inference": "https://github.com/JetBrains/ruby-type-inference",
    "sbt-idea-shell": "https://github.com/JetBrains/sbt-idea-shell",
    "intellij-deps-ini4j": "https://github.com/JetBrains/intellij-deps-ini4j",
    "kotlin-wrappers": "https://github.com/JetBrains/kotlin-wrappers",
    "ideolog": "https://github.com/JetBrains/ideolog",
    "teamcity-vscode-extension": "https://github.com/JetBrains/teamcity-vscode-extension",
    "babel-preset": "https://github.com/JetBrains/babel-preset",
    "emoji": "https://github.com/JetBrains/emoji",
    "logos": "https://github.com/JetBrains/logos",
    "teamcity-react-demo": "https://github.com/JetBrains/teamcity-react-demo",
    "intellij-scala-bundle": "https://github.com/JetBrains/intellij-scala-bundle",
    "TeamCity.SESPlugin": "https://github.com/JetBrains/TeamCity.SESPlugin",
    "clearcase": "https://github.com/JetBrains/clearcase",
    "ring-ui-license-checker": "https://github.com/JetBrains/ring-ui-license-checker",
    "toolbox-browser-extension": "https://github.com/JetBrains/toolbox-browser-extension",
    "kotlinconf-app": "https://github.com/JetBrains/kotlinconf-app",
    "intellij-deps-jdom": "https://github.com/JetBrains/intellij-deps-jdom",
    "noria-kt": "https://github.com/JetBrains/noria-kt",
    "jdk8u_jfx": "https://github.com/JetBrains/jdk8u_jfx",
    "teamcity-termsOfService-plugin": "https://github.com/JetBrains/teamcity-termsOfService-plugin",
    "youtrack-board-status-widget": "https://github.com/JetBrains/youtrack-board-status-widget",
    "intellij-deps-asm": "https://github.com/JetBrains/intellij-deps-asm",
    "java-annotations": "https://github.com/JetBrains/java-annotations",
    "embeddedProjectJdk": "https://github.com/JetBrains/embeddedProjectJdk",
    "hub-rss-widget": "https://github.com/JetBrains/hub-rss-widget",
    "revoke-user-access-widget": "https://github.com/JetBrains/revoke-user-access-widget",
    "debugger-memory-agent": "https://github.com/JetBrains/debugger-memory-agent",
    "teamcity-bazel-plugin": "https://github.com/JetBrains/teamcity-bazel-plugin",
    "teamcity-investigations-hub-widget": "https://github.com/JetBrains/teamcity-investigations-hub-widget",
    "hub-widget-ui": "https://github.com/JetBrains/hub-widget-ui",
    "jdk-sa-jdwp": "https://github.com/JetBrains/jdk-sa-jdwp",
    "youtrack-personal-timetracking-widget": "https://github.com/JetBrains/youtrack-personal-timetracking-widget",
    "reveal.js": "https://github.com/JetBrains/reveal.js",
    "teamcity-fxcop": "https://github.com/JetBrains/teamcity-fxcop",
    "teamcity-rake": "https://github.com/JetBrains/teamcity-rake",
    "teamcity-swabra": "https://github.com/JetBrains/teamcity-swabra",
    "teamcity-xml-tests-reporting": "https://github.com/JetBrains/teamcity-xml-tests-reporting",
    "teamcity-vault-vcs": "https://github.com/JetBrains/teamcity-vault-vcs",
    "teamcity-test-metadata-demo": "https://github.com/JetBrains/teamcity-test-metadata-demo",
    "intellij-deps-proxy-vole": "https://github.com/JetBrains/intellij-deps-proxy-vole",
    "teamcity-gradle": "https://github.com/JetBrains/teamcity-gradle",
    "teamcity-pipelines-dsl": "https://github.com/JetBrains/teamcity-pipelines-dsl",
    "lets-plot-kotlin": "https://github.com/JetBrains/lets-plot-kotlin",
    "lets-plot": "https://github.com/JetBrains/lets-plot",
    "teamcity-dotcover": "https://github.com/JetBrains/teamcity-dotcover",
    "profiler-self-api": "https://github.com/JetBrains/profiler-self-api",
    "jsitter": "https://github.com/JetBrains/jsitter",
    "marketplace-makemecoffee-plugin": "https://github.com/JetBrains/marketplace-makemecoffee-plugin",
    "kotless": "https://github.com/JetBrains/kotless",
    "JetBrains.Rider.Debugger.Launcher": "https://github.com/JetBrains/JetBrains.Rider.Debugger.Launcher",
    "KotlinFinder": "https://github.com/JetBrains/KotlinFinder",
    "CMake-Tutorial-sample": "https://github.com/JetBrains/CMake-Tutorial-sample",
    "Rplugin": "https://github.com/JetBrains/Rplugin",
    "kotlin-compiler-server": "https://github.com/JetBrains/kotlin-compiler-server",
    "teamcity-webhooks": "https://github.com/JetBrains/teamcity-webhooks",
    "rider-theme-pack": "https://github.com/JetBrains/rider-theme-pack",
    "attachme": "https://github.com/JetBrains/attachme",
    "Refasmer": "https://github.com/JetBrains/Refasmer",
    "duty-manager": "https://github.com/JetBrains/duty-manager",
    "intellij-platform-plugin-template": "https://github.com/JetBrains/intellij-platform-plugin-template",
    "space-kotlin-sdk": "https://github.com/JetBrains/space-kotlin-sdk",
    "godot-support": "https://github.com/JetBrains/godot-support",
    "DPA-demo": "https://github.com/JetBrains/DPA-demo",
    "code-analytics-examples": "https://github.com/JetBrains/code-analytics-examples",
    "dl-this": "https://github.com/JetBrains/dl-this",
    "intellij-compiler-indices": "https://github.com/JetBrains/intellij-compiler-indices",
    "clion-debugger-plugin-stub": "https://github.com/JetBrains/clion-debugger-plugin-stub",
    "projector-server": "https://github.com/JetBrains/projector-server",
    "projector-client": "https://github.com/JetBrains/projector-client",
    "projector-markdown-plugin": "https://github.com/JetBrains/projector-markdown-plugin",
    "ztools": "https://github.com/JetBrains/ztools",
    "pest-intellij": "https://github.com/JetBrains/pest-intellij",
    "ij_tutorial_gradle": "https://github.com/JetBrains/ij_tutorial_gradle",
    "projector-installer": "https://github.com/JetBrains/projector-installer",
    "skiko": "https://github.com/JetBrains/skiko",
    "bazel-bsp": "https://github.com/JetBrains/bazel-bsp",
    "exposed-intellij-plugin": "https://github.com/JetBrains/exposed-intellij-plugin",
    "teamcity-ui": "https://github.com/JetBrains/teamcity-ui",
    "compose-multiplatform": "https://github.com/JetBrains/compose-multiplatform",
    "teamcity-slack-notifier": "https://github.com/JetBrains/teamcity-slack-notifier",
    "teamcity-dashboard-plugin": "https://github.com/JetBrains/teamcity-dashboard-plugin",
    "plugin-blockmap-patches": "https://github.com/JetBrains/plugin-blockmap-patches",
    "skia-build": "https://github.com/JetBrains/skia-build",
    "space-dotnet-sdk": "https://github.com/JetBrains/space-dotnet-sdk",
    "teamcity-sccache-plugin": "https://github.com/JetBrains/teamcity-sccache-plugin",
    "teamcity-kotlin-trigger": "https://github.com/JetBrains/teamcity-kotlin-trigger",
    "gradle-qodana-plugin": "https://github.com/JetBrains/gradle-qodana-plugin",
    "qodana-action": "https://github.com/JetBrains/qodana-action",
    "teamcity-rest-codegen": "https://github.com/JetBrains/teamcity-rest-codegen",
    "coverage-report": "https://github.com/JetBrains/coverage-report",
    "ap-validation": "https://github.com/JetBrains/ap-validation",
    "doclava-mirror": "https://github.com/JetBrains/doclava-mirror",
    "big": "https://github.com/JetBrains-Research/big",
    "viktor": "https://github.com/JetBrains-Research/viktor",
    "npy": "https://github.com/JetBrains-Research/npy",
    "bugs-classification": "https://github.com/JetBrains-Research/bugs-classification",
    "astminer": "https://github.com/JetBrains-Research/astminer",
    "MoveMethodGenerator": "https://github.com/JetBrains-Research/MoveMethodGenerator",
    "chipseq-smk-pipeline": "https://github.com/JetBrains-Research/chipseq-smk-pipeline",
    "sysbio-workshop": "https://github.com/JetBrains-Research/sysbio-workshop",
    "embeddings-for-trees": "https://github.com/JetBrains-Research/embeddings-for-trees",
    "anti-copy-paster": "https://github.com/JetBrains-Research/anti-copy-paster",
    "task-tracker-plugin": "https://github.com/JetBrains-Research/task-tracker-plugin",
    "feature-recommendations": "https://github.com/JetBrains-Research/feature-recommendations",
    "hldiff": "https://github.com/JetBrains-Research/hldiff",
    "task-tracker-post-processing": "https://github.com/JetBrains-Research/task-tracker-post-processing",
    "kinference": "https://github.com/JetBrains-Research/kinference",
    "psiminer": "https://github.com/JetBrains-Research/psiminer",
    "metrics-evaluation": "https://github.com/JetBrains-Research/metrics-evaluation",
    "task-tracker-server": "https://github.com/JetBrains-Research/task-tracker-server",
    "depminer": "https://github.com/JetBrains-Research/depminer",
    "RefactorInsight": "https://github.com/JetBrains-Research/RefactorInsight",
    "revizor": "https://github.com/JetBrains-Research/revizor",
    "kinference-primitives": "https://github.com/JetBrains-Research/kinference-primitives",
    "reflekt": "https://github.com/JetBrains-Research/reflekt",
    "PyNose": "https://github.com/JetBrains-Research/PyNose",
    "bumblebee": "https://github.com/JetBrains-Research/bumblebee",
    "commit_message_generation": "https://github.com/JetBrains-Research/commit_message_generation",
    "dataset-anonymizer": "https://github.com/JetBrains-Research/dataset-anonymizer",
    "contrastive-learning-framework": "https://github.com/JetBrains-Research/contrastive-learning-framework",
    "tnm": "https://github.com/JetBrains-Research/tnm",
    "optimization-methods": "https://github.com/JetBrains-Research/optimization-methods",
    "CommentUpdater": "https://github.com/JetBrains-Research/CommentUpdater",
    "louvain": "https://github.com/JetBrains-Research/louvain",
}

BUG_KEYWORDS = re.compile(r"\b(fix|bug|error|issue|crash|defect|patch|hotfix|broken|failure)\b", re.IGNORECASE)

SUPPORTED_EXTENSIONS = {".py", ".kt", ".java"}

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

def get_complexity(source_code, filename):
    if not source_code:
        return None, None
    if not filename.endswith('.py'):
        return None, None
    try:
        analysis = lizard.analyze_file.analyze_source_code(filename, source_code)
        if not analysis.function_list:
            return None, None
        cc = sum(f.cyclomatic_complexity for f in analysis.function_list) / len(analysis.function_list)
        avg_len = sum(f.length for f in analysis.function_list) / len(analysis.function_list)
        return cc, avg_len
    except Exception as e:
        return None, None

from cache_utils import cache_exists, save_cache, load_cache
import os

file_results = []
commit_results = []

if cache_exists():
    print("Cache found! Loading from cache...")
    df_files, df_commits = load_cache()
else:
    print("No cache found, scanning repos...")

for repo_name, repo_url in REPOS.items():
    print(f"\n-> Scanning {repo_name}...")
    file_count = 0
    commit_count = 0
    try:
        for commit in Repository(repo_url, since=datetime(2019, 1, 1), only_no_merge=True).traverse_commits():
            is_bugfix = 1 if BUG_KEYWORDS.search(commit.msg or "") else 0
            added = sum(f.added_lines for f in commit.modified_files)
            deleted = sum(f.deleted_lines for f in commit.modified_files)
            total_lines = added + deleted
            del_add_ratio = deleted / added if added > 0 else None
            commit_results.append({
                "repo": repo_name,
                "date": commit.committer_date,
                "is_bugfix": is_bugfix,
                "lines_changed": total_lines,
                "del_add_ratio": del_add_ratio,
            })
            commit_count += 1
            for file in commit.modified_files:
                ext = None
                for e in SUPPORTED_EXTENSIONS:
                    if file.filename.endswith(e):
                        ext = e
                        break
                if ext and file.source_code:
                    ratio = comment_ratio(file.source_code, ext)
                    cc, avg_len = get_complexity(file.source_code, file.filename)
                    if ratio is not None:
                        file_results.append({
                            "repo": repo_name,
                            "date": commit.committer_date,
                            "comment_ratio": ratio,
                            "cyclomatic_complexity": cc,
                            "cognitive_complexity": avg_len,
                        })
                        file_count += 1
        print(f"   Done: {commit_count} commits, {file_count} files")
    except Exception as e:
        print(f"   Error: {e}")

    save_cache(pd.DataFrame(file_results), pd.DataFrame(commit_results))

df_files = pd.DataFrame(file_results)
df_files["date"] = pd.to_datetime(df_files["date"], utc=True)
df_files["month"] = df_files["date"].dt.to_period("M")

df_commits = pd.DataFrame(commit_results)
df_commits["date"] = pd.to_datetime(df_commits["date"], utc=True)
df_commits["month"] = df_commits["date"].dt.to_period("M")

monthly_files = df_files.groupby(["repo", "month"]).agg(
    comment_ratio=("comment_ratio", "mean"),
    cyclomatic_complexity=("cyclomatic_complexity", "mean"),
    cognitive_complexity=("cognitive_complexity", "mean"),
).reset_index()
monthly_files["month_dt"] = monthly_files["month"].dt.to_timestamp()

monthly_commits = df_commits.groupby(["repo", "month"]).agg(
    avg_lines_changed=("lines_changed", "mean"),
    bugfix_ratio=("is_bugfix", "mean"),
    del_add_ratio=("del_add_ratio", "mean"),
).reset_index()
monthly_commits["month_dt"] = monthly_commits["month"].dt.to_timestamp()

repos = list(REPOS.keys())
colors = [
    "#2196F3","#1565C0","#42A5F5","#0D47A1","#64B5F6",
    "#4CAF50","#2E7D32","#81C784","#1B5E20","#A5D6A7",
    "#FF9800","#E65100","#FFB74D","#BF360C","#FFCC02",
    "#9C27B0","#6A1B9A","#CE93D8","#AB47BC","#7B1FA2",
]

COPILOT = pd.Timestamp("2021-06-01")
CHATGPT = pd.Timestamp("2022-11-01")

def make_chart(title, filename, df, y_col, ylabel):
    fig, axes = plt.subplots(20, 1, figsize=(14, 60), sharex=True)
    fig.suptitle(title, fontsize=13, fontweight="bold")
    for i, (repo, color) in enumerate(zip(repos, colors)):
        data = df[df["repo"] == repo].sort_values("month_dt")
        if data.empty or data[y_col].dropna().empty:
            axes[i].set_title(f"{repo} — no data", fontsize=8)
            continue
        axes[i].plot(data["month_dt"], data[y_col], color=color, linewidth=1.2, alpha=0.4)
        if len(data) > 3:
            data = data.copy()
            data["rolling"] = data[y_col].rolling(3, min_periods=1).mean()
            axes[i].plot(data["month_dt"], data["rolling"], color=color, linewidth=2.5, label="3-month avg")
        axes[i].axvline(COPILOT, color="orange", linestyle="--", linewidth=1.3, label="Copilot (Jun 2021)")
        axes[i].axvline(CHATGPT, color="red", linestyle="--", linewidth=1.3, label="ChatGPT (Nov 2022)")
        axes[i].set_title(repo, fontweight="bold", fontsize=8)
        axes[i].set_ylabel(ylabel, fontsize=7)
        axes[i].legend(fontsize=6, loc="upper right")
        axes[i].grid(True, alpha=0.3)
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    axes[-1].xaxis.set_major_locator(mdates.MonthLocator(interval=6))
    plt.setp(axes[-1].xaxis.get_majorticklabels(), rotation=45)
    plt.tight_layout()
    plt.savefig(filename, dpi=120, bbox_inches="tight")
    print(f"Saved: {filename}")

make_chart("Comment Density — 199 JetBrains Repositories", "chart1_comment_density.png", monthly_files, "comment_ratio", "Comment Ratio")
make_chart("Avg Lines Changed per Commit — 199 JetBrains Repositories", "chart2_commit_size.png", monthly_commits, "avg_lines_changed", "Lines Changed")
make_chart("Bug-Fix Commit Ratio — 199 JetBrains Repositories", "chart3_bugfix_ratio.png", monthly_commits, "bugfix_ratio", "Bug-Fix Ratio")
make_chart("Cyclomatic Complexity — 199 JetBrains Repositories", "chart4_cyclomatic.png", monthly_files, "cyclomatic_complexity", "Cyclomatic Complexity")
make_chart("Avg Function Length — 199 JetBrains Repositories", "chart5_avg_function_length.png", monthly_files, "cognitive_complexity", "Avg Lines per Function")
make_chart("Deletion/Addition Ratio — 199 JetBrains Repositories", "chart6_del_add_ratio.png", monthly_commits, "del_add_ratio", "Del/Add Ratio")

print("\nAll done! 6 charts saved.")
