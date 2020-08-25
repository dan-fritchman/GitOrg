"""
GitOrg

Sets up a directory-full of git-repos onto one or more remote-orgs.
Configured with a combination of YAML, directory-naming conventions, 
and `.no-git-org` ignore-files. 
"""

import git
import yaml
from pathlib import Path
from typing import List, Mapping, Optional
from pydantic.dataclasses import dataclass 


@dataclass
class GitOrgConfig:
    """ GitOrgConfig 
    Primary configuration object 
    Typically dictated via YAML """ 

    org: str
    remotes: Mapping[str, str]
    skip: List[str]
    path: Path 


def log(*args, **kwargs):
    """ Wrapper for whatever type of logging we want to do. """
    return print(*args, **kwargs)  # Thus far, the easy way!


def get_config():
    """ Look through a few levels of directory for a config YAML file. """
    config_file_name = 'git-org.yaml'
    orig_dir = this_dir = Path().absolute()
    for _ in range(3):
        config_file_path = (this_dir / config_file_name).absolute()
        if config_file_path.exists():
            config_handle = open(config_file_path, 'r')
            cfg = yaml.safe_load(config_handle)
            cfg['path'] = config_file_path.parent
            cfg = GitOrgConfig(**cfg)
            return cfg
        this_dir = this_dir.parent
    raise FileNotFoundError(f'Could not find config starting in {str(orig_dir)}')


def remote_url(*, host: str, dirname: str):
    """ Return the SSH-based git-remote URL at hostname `host`, repo-name `dirname`.
    E.g. git@gitlab.com:dan-fritchman/df.git
    Organization name is provided by our `config`.  """
    return f'git@{host}:{config.org}/{dirname}.git'


def repo_actions(repo: git.Repo):
    """ All of the actions taken on a git Repository. """
    setup_remotes(repo)
    push_all_remotes(repo)


def setup_remotes(repo: git.Repo):
    """ Set up remotes as we would like. """
    """ 
    # FIXME: do we want to remove these? Maybe just have a black-list instead.  
    for remote in repo.remotes:  # Remove any remotes we don't want
        if remote.name not in config.remotes:
            log(f'Removing Remote: {remote}')
            repo.delete_remote(remote)
    """ 
    for remote_name in config.remotes:  # Add or update remotes
        host = config.remotes[remote_name]
        dirname = Path(repo.working_dir).name
        url = remote_url(host=host, dirname=dirname)

        remote_to_update = None  # Sadly python-git's API seems to require searching through them.
        for remote in repo.remotes:
            if remote.name == remote_name:
                remote_to_update = remote
        if remote_to_update is not None:
            remote.set_url(new_url=url)
        else:
            repo.create_remote(name=remote_name, url=url)


def push_remote(*, repo: git.Repo, remote: git.Remote):
    """ Push the active branch of `repo` to `remote`. """
    try:
        remote.push(refspec=repo.active_branch.name)
    except Exception as e:
        log(f'Error Pushing to {repo}')
        raise e


def push_all_remotes(repo: git.Repo):
    """ Push to all remotes """
    if repo.is_dirty():
        log(f'Not pushing {repo} due to open changes')
        raise Exception
    for remote in repo.remotes:
        push_remote(repo=repo, remote=remote)


def is_repo(repo_dir: Path):
    """ Boolean indication of whether Path `repo_dir` is a git repository. """ 
    try:
        r = git.Repo(repo_dir)
    except git.InvalidGitRepositoryError:
        return False 
    return True 


def setup_repo_dir(repo_dir: Path):
    """ Set up the repository at `repo_dir`. 
    Raises various exceptions, including if `repo_dir` is not a repository. """
    r = git.Repo(repo_dir)
    repo_actions(r)


def setup_git_org(org_dir: Path):
    """ Setup GitOrg for local directory `org_dir`.
    Walk through sub-directories, filter some out based on rules,
    and pass them along to repo-ops. """

    filters = (
        lambda p: p.is_dir(),
        lambda p: is_repo(p),
        lambda p: p.name not in config.skip,
        lambda p: 'secret' not in p.name,
        lambda p: not (p / '.no-git-org').exists(),
    )

    passed = []
    failed = []
    skipped = []

    for p in org_dir.iterdir():
        if not all([f(p) for f in filters]):
            skipped.append(p)
            continue 
        try:
            setup_repo_dir(repo_dir=p)
        except:
            failed.append(p)
        else:
            passed.append(p)
    
    # Print some diagnosticism
    log("Pushed Repos:")
    [log(p) for p in passed]
    log("Errors Attempting to Push:")
    [log(p) for p in failed]
    log("Skipped Directories:")
    [log(p) for p in skipped]
    

config = get_config()


if __name__ == '__main__':
    log(f'GitOrg Config: {config}')
    setup_git_org(org_dir=config.path)

