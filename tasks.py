from invoke.tasks import task
from invoke.collection import Collection
from invoke_config import *

import dist
import build # type: ignore



@task
def install_req(c):

    print("Installing all dependencies...")
    c.run("pip install -r requirements.txt")


@task
def dev_install(c):
    """Complete development setup - install all deps and compile assets"""
    install_req(c)
    build.compile_assets(c)
    print("\nDevelopment environment ready!")

namespace = Collection(build,  dist)
