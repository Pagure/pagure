# -*- coding: utf-8 -*-

"""
 (c) 2016 - Copyright Red Hat Inc

 Authors:
   Lubomír Sedlář <lubomir.sedlar@gmail.com>
   Farhaan Bukhsh <farhaan.bukhsh@gmail.com>
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

# pylint: disable=too-many-locals

import pagure.exceptions
import pagure.lib

# This import is needed as pagure.lib relies on Project.ci_hook to be
# defined and accessible and this happens in pagure.hooks.pagure_ci
from pagure.hooks import pagure_ci  # noqa: E402,F401


BUILD_STATS = {
    'SUCCESS': ('Build successful', 100),
    'FAILURE': ('Build failed', 0),
}


def process_jenkins_build(session, project, build_id, requestfolder):
    """  Gets the build info from jenkins and flags that particular
    pull-request.
    """
    import jenkins
    # Jenkins Base URL
    jenk = jenkins.Jenkins(project.ci_hook.ci_url.split('/job/')[0])
    jenkins_name = project.ci_hook.ci_url.split(
        '/job/', 1)[1].split('/', 1)[0]
    build_info = jenk.get_build_info(jenkins_name, build_id)
    result = build_info.get('result')
    url = build_info['url']

    pr_id = None
    for action in build_info['actions']:
        for cause in action.get('causes', []):
            try:
                pr_id = int(cause['note'])
            except (KeyError, ValueError):
                continue

    if not pr_id:
        raise pagure.exceptions.NoCorrespondingPR(
            'No corresponding PR found')

    if result not in BUILD_STATS:
        pagure.exceptions.PagureException(
            'Unknown build status: %s' % result)

    status = result.lower()

    request = pagure.lib.search_pull_requests(
        session, project_id=project.id, requestid=pr_id)

    if not request:
        raise pagure.exceptions.PagureException('Request not found')

    comment, percent = BUILD_STATS[result]
    # Adding build ID to the CI type
    username = project.ci_hook.ci_type + " #" + str(build_id)

    pagure.lib.add_pull_request_flag(
        session,
        request=request,
        username=username,
        percent=percent,
        comment=comment,
        url=url,
        status=status,
        uid=None,
        user=project.user.username,
        token=None,
        requestfolder=requestfolder,
    )
    session.commit()
