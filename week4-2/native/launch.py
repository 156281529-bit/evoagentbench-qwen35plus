"""Run the native Spring adapter using the original built RSI backend dependencies."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import zipfile

HERE = Path(__file__).resolve().parent


def start(backend, build, port):
    lib = build / "lib"
    classes = build / "classes"
    lib.mkdir(parents=True, exist_ok=True)
    classes.mkdir(parents=True, exist_ok=True)
    jars = []
    with zipfile.ZipFile(backend) as archive:
        for item in archive.infolist():
            if item.filename.startswith("BOOT-INF/lib/") and item.filename.endswith(".jar"):
                target = lib / Path(item.filename).name
                with archive.open(item) as src, target.open("wb") as dst:
                    shutil.copyfileobj(src,dst)
                jars.append(str(target))
    if not jars:
        raise ValueError("Expected a built Spring Boot backend executable JAR")
    shutil.copytree(HERE / "resources", classes, dirs_exist_ok=True)
    path = os.pathsep.join([str(classes), str(lib / "*")])
    java = sorted((HERE / "src").rglob("*.java"))
    subprocess.run(["javac","-encoding","UTF-8","-g","-parameters","-cp",path,"-d",str(classes),
                    *map(str,java)],check=True)
    skill_jar = build / "week4-skill.jar"
    subprocess.run(["jar","cf",str(skill_jar),"-C",str(classes),"."],check=True)
    runtime_path = os.pathsep.join([str(skill_jar), str(lib / "*")])
    subprocess.run(["java","-Dfile.encoding=UTF-8","-Dspring.cloud.bootstrap.enabled=false",
                    "-cp",runtime_path,"week4.nativeflow.NativeApplication","--server.address=127.0.0.1",
                    f"--server.port={port}"],check=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--backend",type=Path,required=True)
    p.add_argument("--build",type=Path,required=True)
    p.add_argument("--port",type=int,default=39914)
    a = p.parse_args()
    start(a.backend,a.build.resolve(),a.port)
