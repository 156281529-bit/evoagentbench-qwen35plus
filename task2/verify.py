"""Prepare an isolated checkout for synchronous RSI-Flow tests without the private jars."""

import argparse
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

TASK_ROOT = Path(__file__).resolve().parent.parent
TESTS = (
    "FlowLoopTest,FlowSingleNodeTest,FlowMultiNodeTest,FlowConditionTest,FlowNestTest,"
    "FlowAsyncAllTest,FlowAsyncAnyTest,FlowAsyncVoidTest"
)
CORE = Path("flow-core/src/main/java/cc/eamon/open/flow/core/stereotype/execute/holder")
CONFIG = Path("flow-config/src/main/java/cc/eamon/open/flow/config/flow/FlowConfig.java")
PACKAGE = "package cc.eamon.open.flow.core.stereotype.execute.holder;\n"


def prepare(source, destination):
    shutil.copytree(
        source, destination, ignore=shutil.ignore_patterns(".git", "target", "FLOW_SCHEDULE")
    )
    # The private auto-config type is only used in the unused inline models field.
    config = destination / CONFIG
    config.write_text(
        config.read_text(encoding="utf-8").replace(
            "cc.eamon.open.auto.config.code.detail.ModelConfig",
            "cc.eamon.open.flow.config.model.ModelConfig",
        ),
        encoding="utf-8",
    )
    for pom in destination.glob("*/pom.xml"):
        content = pom.read_text(encoding="utf-8")
        updated = re.sub(
            r"(?m)^[ \t]*<dependency>\s*<groupId>[^<]+</groupId>\s*"
            r"<artifactId>(?:auto-config|scheduler-core)</artifactId>\s*"
            r"(?:<version>[^<]+</version>\s*)?</dependency>[ \t]*\n",
            "",
            content,
        )
        if updated != content:
            pom.write_text(updated, encoding="utf-8")
    holder = destination / CORE
    (holder / "FlowScheduleHolder.java").write_text(
        PACKAGE + """
final class FlowScheduleHolder {
    FlowScheduleHolder(FlowHolder flow) { }
    void execute() { throw new UnsupportedOperationException("Scheduler unavailable in test copy"); }
}
""",
        encoding="utf-8",
    )
    (holder / "FlowScheduleNodeHolder.java").write_text(
        PACKAGE + """
import cc.eamon.open.flow.config.flow.FlowNodeConfig;
final class FlowScheduleNodeHolder extends FlowNodeHolder {
    FlowScheduleNodeHolder(FlowNodeConfig config) throws Exception { super(config); }
    @Override public void execute() {
        throw new UnsupportedOperationException("Scheduler unavailable in test copy");
    }
}
""",
        encoding="utf-8",
    )
    print(destination)


def execute(source, easyfile, cache, work, skill_fixture=None, offline=False):
    source, easyfile, cache, work = (p.resolve() for p in (source, easyfile, cache, work))
    if work == source or source in work.parents or work == easyfile or easyfile in work.parents:
        raise SystemExit("Use a verification work directory outside the source checkouts.")
    if not (source / "flow-core/pom.xml").is_file():
        raise SystemExit(f"RSI-Flow source directory not found: {source}")
    if not (source / "flow-test/src/test/resources/flow/FLOW_LOOP").is_dir():
        raise SystemExit("Apply rsi-flow-while.patch in the source checkout before running this verifier.")
    if not (easyfile / "pom.xml").is_file():
        raise SystemExit(f"Clone https://github.com/ymxiong/easyfile at abb8ecd into {easyfile} first.")
    commit = subprocess.check_output(["git", "-C", str(easyfile), "rev-parse", "HEAD"], text=True).strip()
    if commit != "abb8ecd37f53868ae84b9f46bbfaf6aec335fa74":
        raise SystemExit("The easyfile checkout must be at abb8ecd37f53868ae84b9f46bbfaf6aec335fa74.")
    docker = shutil.which("docker")
    if not docker:
        fallback = Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Docker/Docker/resources/bin/docker.exe"
        if fallback.is_file():
            docker = str(fallback)
    if not docker:
        raise SystemExit("Install or start Docker Desktop, then run this verifier again.")
    cache.mkdir(parents=True, exist_ok=True)
    work.mkdir(parents=True, exist_ok=True)
    build = Path(tempfile.mkdtemp(prefix="rsi-flow-test-", dir=work))
    verify = build / "rsi-flow"
    dependency = build / "easyfile"
    prepare(source, verify)
    # Keep Docker's compile outputs outside both source checkouts.
    shutil.copytree(easyfile, dependency, ignore=shutil.ignore_patterns(".git", "target"))
    mounts = []
    test_options = f"-Dtest={TESTS} -Dsurefire.failIfNoSpecifiedTests=false"
    if skill_fixture is not None:
        skill_fixture = skill_fixture.resolve(strict=True)
        mounts.extend(["--mount", f"type=bind,source={skill_fixture},target=/skill-input.json,readonly"])
        test_options = (
            f"-Dtest={TESTS},SkillReplayTest -Dsurefire.failIfNoSpecifiedTests=false "
            "-Drsi.skills.fixture=/skill-input.json -Drsi.skills.output=/workspace/skill-replay-results.json"
        )
    maven = "mvn -B -ntp -o -Dmaven.repo.local=/root/.m2/repository" if offline else "mvn -B -ntp"
    command = [
        docker, "run", "--rm",
        *(["--network", "none"] if offline else []),
        *mounts,
        "--mount", f"type=bind,source={verify},target=/workspace",
        "--mount", f"type=bind,source={dependency},target=/easyfile",
        "--mount", f"type=bind,source={cache},target=/root/.m2",
        "--workdir", "/workspace", "maven:3.9-eclipse-temurin-8", "sh", "-c",
        f"{maven} -f /easyfile/pom.xml -Dmaven.javadoc.skip=true install && "
        f"{maven} -pl flow-test -am {test_options} test",
    ]
    print("Running loop and regression tests in Docker with Java 8.", flush=True)
    subprocess.run(command, check=True)
    print(f"Test reports: {verify / 'flow-test/target/surefire-reports'}")
    if skill_fixture is not None:
        print(f"Skill replay evidence: {verify / 'skill-replay-results.json'}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=TASK_ROOT / "work/rsi-flow")
    parser.add_argument("--easyfile", type=Path, default=TASK_ROOT / "work/rsi-easyfile")
    parser.add_argument("--cache", type=Path, default=TASK_ROOT / "work/maven-cache")
    parser.add_argument("--work", type=Path, default=TASK_ROOT / "work")
    parser.add_argument("--skill-fixture", type=Path, help="Also verify the locally generated skill replay fixture")
    parser.add_argument("--offline", action="store_true", help="Use a populated Maven cache and disable container networking")
    args = parser.parse_args()
    try:
        execute(args.source, args.easyfile, args.cache, args.work, args.skill_fixture, args.offline)
    except subprocess.CalledProcessError as error:
        raise SystemExit(error.returncode) from None
