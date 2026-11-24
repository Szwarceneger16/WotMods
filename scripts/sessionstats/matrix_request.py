#!/usr/bin/env python3
"""Resolve a Session Stats matrix request from trusted GitHub metadata."""

import json
import os
from pathlib import Path
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


COMMANDS = {
    '/sessionstats-matrix': 'exhaustive',
    '/sessionstats-matrix full': 'full',
    '/sessionstats-matrix smoke': 'smoke',
}
SHARD_COUNTS = {'exhaustive': 64, 'full': 16, 'smoke': 1}
HARNESS = 'scripts/sessionstats/local-e2e/merge-report.cjs'
COMMIT = re.compile(r'[0-9a-f]{40}')
REPOSITORY = re.compile(r'[A-Za-z0-9_-]+/[A-Za-z0-9_.-]+')
LOGIN = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]*')


class MatrixRequestError(RuntimeError):
    pass


class RejectRedirects(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        return None


def github_reader(api_url, token):
    base = urlsplit(api_url)
    if base.scheme != 'https' or not base.hostname or base.username or base.query or base.fragment:
        raise MatrixRequestError('A configured HTTPS GitHub API endpoint is required.')
    if not token:
        raise MatrixRequestError('A read-only GitHub token is required.')
    opener = build_opener(RejectRedirects)

    def get(path):
        request = Request(api_url.rstrip('/') + path, headers={
            'Accept': 'application/vnd.github+json',
            'Authorization': 'Bearer ' + token,
            'User-Agent': 'wotmods-sessionstats-matrix',
        })
        try:
            with opener.open(request, timeout=20) as response:
                return json.load(response)
        except HTTPError as error:
            if error.code == 404:
                return {}
            raise MatrixRequestError('GitHub metadata request failed (HTTP %d).' % error.code) from None
        except (URLError, TimeoutError, ValueError):
            raise MatrixRequestError('GitHub metadata was unavailable.') from None

    return get


def same_repository(metadata, repository, repository_id):
    return (
        isinstance(metadata, dict)
        and type(metadata.get('id')) is int
        and metadata['id'] == repository_id
        and metadata.get('full_name', '').casefold() == repository.casefold()
    )


def requested_comment(event):
    issue = event.get('issue', {})
    comment = event.get('comment', {})
    author = comment.get('user', {})
    coverage = COMMANDS.get(comment.get('body'))
    if (
        event.get('action') != 'created'
        or not issue.get('pull_request')
        or not coverage
        or author.get('type') != 'User'
        or comment.get('author_association') not in ('OWNER', 'MEMBER', 'COLLABORATOR')
    ):
        return None
    number = issue.get('number')
    if type(number) is not int or number <= 0:
        raise MatrixRequestError('The comment event does not identify a valid pull request.')
    return coverage, number, author


def authorize_author(event, author, prefix, get):
    login = author.get('login', '')
    user_id = author.get('id')
    if not LOGIN.fullmatch(login) or type(user_id) is not int or user_id <= 0:
        raise MatrixRequestError('The comment author could not be verified.')
    owner = event['repository'].get('owner', {})
    if (
        owner.get('type') == 'User'
        and owner.get('id') == user_id
        and owner.get('login', '').casefold() == login.casefold()
    ):
        return
    collaborator = get(prefix + '/collaborators/' + login + '/permission')
    if (
        collaborator.get('user', {}).get('id') != user_id
        or collaborator.get('permission') not in ('admin', 'maintain', 'write')
    ):
        raise MatrixRequestError('Matrix comments require repository write access.')


def pull_request_sha(number, repository, repository_id, prefix, get):
    pull = get(prefix + '/pulls/' + str(number))
    base = pull.get('base', {})
    head = pull.get('head', {})
    if pull.get('number') != number or pull.get('state') != 'open':
        raise MatrixRequestError('The matrix requires an open pull request.')
    if not all(same_repository(ref.get('repo'), repository, repository_id) for ref in (base, head)):
        raise MatrixRequestError('The matrix requires a pull request branch in this repository.')
    return head.get('sha', '')


def plan(event_name, event, repository, get):
    if event_name != 'issue_comment':
        return {}
    requested = requested_comment(event)
    if requested is None:
        return {}

    coverage, number, author = requested
    metadata = event.get('repository', {})
    repository_id = metadata.get('id')
    if not REPOSITORY.fullmatch(repository) or not same_repository(metadata, repository, repository_id):
        raise MatrixRequestError('The event repository could not be verified.')
    prefix = '/repos/' + repository
    authorize_author(event, author, prefix, get)
    sha = pull_request_sha(number, repository, repository_id, prefix, get)
    if not isinstance(sha, str) or not COMMIT.fullmatch(sha):
        raise MatrixRequestError('GitHub did not return a valid commit SHA for the matrix.')
    entry = get(prefix + '/contents/' + HARNESS + '?ref=' + sha)
    if entry.get('type') != 'file' or entry.get('path') != HARNESS:
        raise MatrixRequestError('The selected commit has no Chromium matrix harness. '
                                 'Choose a pull request or branch containing the Session Stats test tools.')
    count = SHARD_COUNTS[coverage]
    return {
        'coverage': coverage,
        'target_sha': sha,
        'pr_number': str(number),
        'shard_count': str(count),
        'shards': json.dumps(list(range(1, count + 1)), separators=(',', ':')),
    }


def main():
    try:
        env = os.environ
        event = json.loads(Path(env['GITHUB_EVENT_PATH']).read_text(encoding='utf-8'))
        outputs = plan(
            env['GITHUB_EVENT_NAME'], event, env['GITHUB_REPOSITORY'],
            github_reader(env['GITHUB_API_URL'], env['GITHUB_TOKEN']),
        )
        if outputs:
            with open(env['GITHUB_OUTPUT'], 'a', encoding='utf-8') as stream:
                for key, value in outputs.items():
                    stream.write(key + '=' + value + '\n')
    except MatrixRequestError as error:
        sys.exit(str(error))
    except (AttributeError, KeyError, OSError, TypeError, ValueError):
        sys.exit('The GitHub matrix request could not be read.')


if __name__ == '__main__':
    main()
