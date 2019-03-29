import git
import yaml
from pathlib import Path

config_file_name = 'git-org.yaml'


def log(*args, **kwargs):
    """ Wrapper for whatever type of logging we want to do. """
    return print(*args, **kwargs)  # Thus far, the easy way!


def get_config():
    """ Look through a few levels of directory for a config YAML file. """
    orig_dir = this_dir = Path().absolute()
    for _ in range(3):
        config_file_path = (this_dir / config_file_name).absolute()
        if config_file_path.exists():
            config_handle = open(config_file_name, 'r')
            cfg = yaml.safe_load(config_handle)
            cfg['dir'] = config_file_path.parent
            return cfg
        this_dir = this_dir.parent
    raise FileNotFoundError(f'Could not find config starting in {str(orig_dir)}')


def remote_url(*, host: str, dirname: str):
    """ Return the SSH-based git-remote URL at hostname `host`, repo-name `dirname`.
    E.g. git@gitlab.com:dan-fritchman/df.git
    Organization name is provided by our `config`.  """
    return f'git@{host}:{config["org"]}/{dirname}.git'


def repo_actions(repo: git.Repo):
    """ All of the actions taken on a git Repository. """
    setup_remotes(repo)
    push_all_remotes(repo)


def setup_remotes(repo: git.Repo):
    """ Set up remotes as we would like. """
    for remote in repo.remotes:  # Remove any remotes we don't want
        if remote.name not in config['remotes']:
            log(f'Removing Remote: {remote}')
            repo.delete_remote(remote)

    for remote_name in config['remotes']:  # Add or update remotes
        host = config['remotes'][remote_name]
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
        return
    for remote in repo.remotes:
        push_remote(repo=repo, remote=remote)


def setup_repo_dir(repo_dir: Path):
    """ If `repo_dir` is a valid Git repo, set it up.
    If not, just log a message and carry on. """
    try:
        r = git.Repo(repo_dir)
    except git.InvalidGitRepositoryError:
        log(f'Not a git repo: {repo_dir}')
    else:
        log(f'Setting up git repo: {repo_dir}')
        repo_actions(r)


def setup_git_org(org_dir: Path):
    """ Setup GitOrg for local directory `org_dir`.
    Walk through sub-directories, filter some out based on rules,
    and pass them along to repo-ops. """
    filters = (
        lambda p: p.is_dir(),
        lambda p: p.name not in config['skip'],
        lambda p: 'secret' not in p.name,
        lambda p: not (p / '.no-git-org').exists(),
    )
    for p in org_dir.iterdir():
        if all([f(p) for f in filters]):
            setup_repo_dir(repo_dir=p)


config = get_config()
log(f'Config: {config}')


def main():
    """ Script main. All dictated by config. """
    setup_git_org(org_dir=config['dir'])


if __name__ == '__main__':
    main()
