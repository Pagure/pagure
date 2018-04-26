Changelog
=========

This document records all notable changes to `Pagure <https://pagure.io>`_.

4.0.1 (2018-04-26)
------------------

- Fix browsing projects in a namespace when logged in and the instance has only
  one contributor for every projects
- Fix commenting on a PR or an issue if the event source server is not
  configured at all (Slavek Kabrda)


4.0 (2018-04-26)
----------------

- Re-architecture the project to allow potentially extending pagure outside of
  its core
- Fix running the tests on newer pygit
- Add a space between the fork and the watch buttons
- Add a global configuration option to turn on or off fedmsg notifications for
  the entire pagure instance
- Set the default username to be 'Pagure' when sending git commit notifications
  by email
- Add project setting to show roadmap by default (Vivek Anand)
- Explain in the doc where the doc is coming from
- Expand and document the tokenization search
- Add document that multiple keys are supported
- Add a way to block non fast-forwardable commits on all branches
- Fix running pagure on docker for development (Clément Verna)
- Make the accordeon in the settings page work correctly
- Allow calling git blame on a commit instead of a branch
- Exclude the .pyc files from all folders
- Fix viewing file if the identifier provider is a commit hash
- Make pagure-ci use python-jenkins to work with newer Jenkins
- Fix the link to the pull-request shown by the default git hook
- If the tag's color is the default text, convert it to the hex value
- Include documentation on how to pull locally a pull-request on the PR page
- Properly retrieve the number of projects and forks users have
- Replace jquery.dotdotdot by jquery.expander
- Update the Preview button to display 'Edit' when previewing
- Fix supporting <link> in markdown as it is supposed to be
- Add missing authentication provider option to documentation (Michael Watters)
- Fix couple of places where fullname is required while it's not
- Let users see and access private tickets they are assigned to
- Fix allowing to add multiple tags with the same color
- Add a new API endpoint allowing to open new pull-requests
- Fix checking if the user is authenticated
- Add the possibility to mark milestones as active or inactive
- Fix making the milestones showing in the correct order on the issue page
- Fix showing the proper URLs in the repo overview
- Include the cached merge status in the JSON representation of pull-requests
- Improve the fedmsg git hook documentation
- Fix display of deleted parent on index page (Lubomír Sedlář)
- Adjust message shown to the user deleting a tag off a project
- Fix redirecting the user when they remove themselves from a project
- Add an option to notify on flags being added to a pull-request
- Add an option to notify on flags being added to a commit
- Document project intra-pagure hyperlinks
- Refresh the PR cache of the parent repo rather than always the current one
- Move the webhook service to be a celery service
- Fix dead-link due to documentation for python-markdown being moved
- Mention #pagure IRC channel in Contributing docs (Peter Oliver)
- Fix editing and deleting comments added by the EV server to PRs
- Include a count of the number of tickets shown vs recorded for each milestone
- Do not try to get the avatar if the author has no email
- Fix HTML on settings page
- Migrate the logcom service to be celery based and triggered
- Link directly to API key settings in error message about expired API key
  (Peter Oliver)
- Drop the constraint on binaryornot
- Make fork page header link consistent (Lubomír Sedlář)
- Fix the rtd hook and port it to the v2 API (Clément Verna, Pierre-Yves Chibon)
- Deduplicate list of contributors to a project (Lubomír Sedlář)
- Remove repo from gitolite cache when it gets deleted (Slavek Kabrda)
- Make the hooks use the new architecture (Clément Verna)
- Switch to comments on PR page when url fragment is reset (Lubomír Sedlář)
- Handle implicit issue link at start of line (Adam Williamson)
- Don't treat @ in the middle of words as a mention (Adam Williamson)
- Improve the CI settings docs (Clément Verna)
- Ensure the tasks has finished before checking its results
- Fix oidc logout with admin_session_timedout (Slavek Kabrda)
- Make images be lazy loaded via javascript
- Adjust activity heatmap and logs for timezone (Adam Williamson)
- Use timezone not offset for user activity, fix heat map (Adam Williamson)
- JS clean up (Lubomír Sedlář)
- Fix UnicodeEncode on entering non-ascii password (Farhaan Bukhsh)
- Add Tests and exception for non-unicode password (Farhaan Bukhsh)
- Forbid adding tags with a slash in their name to a project
- Migrate the loadjson service to be celery-based
- Specify which service is logging the action for easier debugging/reading of
  the logs
- Merge the fedmsg notifications on commit logic into the default hook
- Merge pagure-ci into the pagure's celery-based services
- When creating a new PR, allow updating the branch from
- Allow pull changes from a different repo than the parent one
- Add a new internal endpoint to get the family of a project
- Expand the API endpoint listing tags to include the hash if asked t
- List the tags of the project in the list of commits
- Fix sending notifications in the default hook
- Make it possible to use custom PR/commit flags based on instance configuration
  (Slavek Kabrda)
- Show summary of flags on page with commits list (Slavek Kabrda)
- Improve the info message when trying to setup an user with a known email
- Make badges with flag counts in commits list to links to commit details
  (Slavek Kabrda)
- Enable sending messages to stomp-compliant brokers (Slavek Kabrda)
- Update required pygit2 version (Clément Verna)
- Do not crash when getting the branches ready for PR on a fork with no parent
- Adjust tests for newer flask
- Make trigger CI build depends on project name (Clément Verna)
- Ensure the DOCS_FOLDER and TICKETS_FOLDER really are optional
- Move the `Add Milestone` button near the top and fix the layout
- Add a button to delete empty line when adding new tags
- Change submit button labels for issues and PRs (Akshay Gaikwad)
- Add changelog.rst (Akshay Gaikwad)
- Overflow heatmap automatically (Paul W. Frields)
- Large unit-tests improvement both in quality and speed (Aurélien Bompard)
- Initial support for commit CI trigger (Clément Verna)
- Added signed-off-by during web ui commit (yadneshk)
- Replace py-bcrypt by python2-bcrypt (Clément Verna)
- Fix the user's requests page
- Establish an order for readme files (Karsten Hopp)
- Include the filename when showing the diff of remote PRs
- Specify the parent repo, even when creating a remote PR
- Always use md5 to get ssh key information (Patrick Uiterwijk)
- Support showing comment submitted by ajax when the SSE is down/not set
- Add the possibility to link issues to pull-requests (in the UI)
- Rely on the list of branches rather than the ``.empty`` attribute to find out
  if a git repo is empty or not
- Add the possibility to split the tasks into multiple queues
- Fix getting the patch of a PR that no longer has a project from
- Do not update the CHECKSUMS file if the file was already uploaded
- Show the fork button on forks
- Make the web-hook field be a textarea and improve the documentation about
  web-hook
- Fix supporting branches containing multiple dots
- Do not convert to markdown commit messages in notifications
- Port pagure to use the compile-1 script from upstream gitolite (if
  configured to do so) (Slavek Kabrda)
- Add preview when editing a comment (Rahul Bajaj) and the initial comment
- Ensure that deployment keys are managed correctly (Michael Watters)
- Improve human-readable date/time display in web UI (Adam Williamson)
- Make sure we rollback session on task failures (Slavek Kabrda)
- Fix new commit notification mails with non-ASCII (#1814) (Adam Williamson)
- Don't create gitolite.conf entries for docs and tickets when they're disabled (Slavek Kabrda)
- Move source git urls above contibutors list (yadneshk)
- Fix private repo to be accessed by ACLs other than admin (Farhaan Bukhsh)
- Change the lock name based on the git repo touched (Pierre-Yves Chibon)
- Adjust the spec file, remove no longer needed lines and fix requirements (Pierre-Yves Chibon)
- Add example worker systemd service file (Pierre-Yves Chibon)
- Adjust the wsgi file for the new arch (Pierre-Yves Chibon)
- Fix turning the read-only boolean on a fork (Pierre-Yves Chibon)
- Support blaming a file is the identifier is a tag (Pierre-Yves Chibon)
- Ensure the git hooks are always executable in the rpm (Pierre-Yves Chibon)
- Do not syntax highlight 'huge' files (Patrick Uiterwijk)
- Fix exceptions caused by missing merge object (Michael Watters)
- Fix linking to a PR that was opened from a main project to a fork (Pierre-Yves
  Chibon)
- Add support for repository templates for sources and forks (Pierre-Yves
  Chibon)
- Enable usage of flask-session extension (Slavek Kabrda)
- Add a configuration key allowing to send fedmsg notifications on all commits
  (Pierre-Yves Chibon)
- Allow deleting branch when PR is merged (Lubomír Sedlář)


3.13.2 (2017-12-21)
-------------------

- Fix ordering issues by author using an alias so the User doesn't collide


3.13.1 (2017-12-19)
-------------------

- Add an alembic migration removing a constraint on the DB that not only no
  longer needed but even blocking regular use now


3.13 (2017-12-18)
-----------------

- Fix the alembic migration adjusting the pull_requests table
- Fix how is created the db in the docker development environment (Clement
  Verna)
- Ensure optional dependencies remain optional
- Ensure groups cannot be created when it is not allowed
- When listing issues, include the project as well in the user's issue API
  endpoint
- Sort forks by date of creation (descending) (Neha Kandpal)
- Ensure the pagination arguments are returned when a page is specified
- Make the milestone clickable on the issue page
- Make the celery tasks update their status so we know when they are running (vs
  pending)


3.12 (2017-12-08)
-----------------

- Adjust the API endpoint listing project to not return a 404 when not projects
  are found (Vivek Anand)
- Remove --autoreload from the docker dev deployment (Vivek Anand)
- Fix ordering issues (Patrick Uiterwijk)
- Do not log actions pertaining to private issues, PRs or projects
- Fix flagging a PR when no uid is specified
- Fix the doc about custom gitolite config
- Fix displaying the filename on the side and linking to file for remote PRs
- Add irc info in Readme (Vivek Anand)
- Make pagure compatible with newer python chardet
- Check that the identifier isn't the hash of a git tree in view_file
- Fix if the identifier provided is one of a blob instead of a commit in
  view_commit
- Include the status when flagging a PR via jenkins
- Enable OpenID Connect authentication (Slavek Kabrda)
- Use the updated timestamp in the pull-request list
- Add migration to fix the project_from_id foreign key in pull_requests
- Let the SSE server to send the notifications so they can be displayed live
- Improve the createdb script to support stamping the database in the initial
  run
- Specify a different connection and read timeout in pagure-ci
- Small CSS fix making the (un)subscribe show up on the PR page


3.11.2 (2017-11-29)
-------------------

- Fix giving a project if no user is specified
- Don't show issue stats when issues are off


3.11.1 (2017-11-28)
-------------------

- Fix showing the issue list
- Make clear in the project's settings that tags are also for PRs (Clement
  Verna)
- Remove unused jdenticon js library (Shengjing Zhu)


3.11 (2017-11-27)
-----------------

- Print out the URL to existing PR(s) or to create one on push
- Reword the repository access warning (Matt Prahl)
- Add pagure-admin admin-token update to update the expiration date
- Fix the api_view_user_activity_stats to return the expected data (post flask
  0.11)
- Add small icon showing if issues are blocked or blocking in the issue list
- Replace all print statements with print function calls (Vadim Rutkovski)
- Add a default_priority field to projects
- Bail on merge a PR that is already closed
- Add a graph of the history of the open issues on the project
- Make the pagure hook act as the person doing the push
- Clean spec file to drop deprecated lines and macros (Igor Gnatenko)
- Include selectize in the settings page to fix the autocomplete in the give
  project action
- Do not display the close_status if there isn't one
- Do not show the `Fork and edit` button all the time
- Allow project maintainer to set metadata when creating a new issue (expand the
  API as well)
- Add a timeout when trying to query jenkins
- Show the reply button even if the PR/issue is closed.
- Add a diff view for PR
- Improve the `My star` page
- Introduce repo statistics
- When a project enforce signed-off-by, clearly say so on the new PR page and
  properly block the PR from being created
- Adjust button title on the 'Fork and Edit' action
- Fix typos in the code (chocos10)
- When editing an issue, act as the person who pushed the change
- Commit using the user's fullname if there is one, otherwise its username
- Expand the group info API endpoint
- Sorting on Opened, Modified, Closed, Priority, Reporter, Assignee cols (Mohan
  Boddu and Matt Prahl)
- Fix the Vagrant setup (Ryan Lerch)
- Fix typo in the example pagure.wsgi file (Vivek Anand)
- Add API endpoints for listing pull requests for a user (Ryan Lerch)
- Ask for the post-commit hook to be run when editing files via the UI
- Fix the milter for email gpg signed
- Allow filtering the user's project by access level
- Add a modal at the bottom of the issues list to add milestones
- Add a field to store the order of the milestones
- Hide the ``+`` button on the index page when it is disabled in the UI
- Improve mimetype detection (Shengjing Zhu and Clement Verna)
- Allow assignee to drop their assignment
- Remove duplicate [Pagure] from mail subjects (Stefan Bühler)
- Fix undefined 'path' in blame.html template (Stefan Bühler)
- Warn users when a project does not support direct push
- Update gitolite's config for the project when set to PR only
- Do not report the branch differing master if PRs have been turned off
- Add a button and an API endpoint to subscribe to PR's notifications
- Fix showing the file names in PR (pre)view
- Fix number of typos in the documentation (René Genz)
- Improve the documentation about documentation hosting in pagure (René Genz)
- Allow priorities and milestones to be 0 or -1
- Return the flag UID when adding or updating a flag on a PR not in fedmsg
- Add flags on commits
- Add documentation about flags on commits and PRs
- Add status fields to flags
- Make flag's UID be unique to the commit/PR being flagged
- Add API endpoint to retrieve all issues related to an user across all repos
- Fix the new PR and delete buttons for branch name with + in them
- When merging a PR, call the post-update hook on the target repo
- Add tags to pull-request
- Fix documentation for fork API endpoint (ishcherb)
- Send fedmsg messages when deleting a project (Shaily)


3.10.1 (2017-10-13)
-------------------

- Fix providing access to some of the internal API endpoints by javascript


3.10 (2017-10-13)
-----------------

- Show the branches' head in the commit list
- Log which IP is being denied access to the internal endpoints (makes debugging
  easier)
- Link to pagure's own markdown documentation and warn that remote images are
  not supported
- Document how to run a single test file or a single test in a file
- Fix trying to decode when the encoding is None
- Include an url_path field in the JSON representation of a project
- Generalize the description of the ACLs (since we know have project-less API
  tokens)
- Drop ``--autoreload`` from the .service files as celery dropped support for it
  and it never really worked (Vivek Anand)


3.9 (2017-10-11)
----------------

- Fix the editing issue when the user does not actually edit anything
- Fix the internal API endpoint: get branches of commit to support namespace
- Consolidate the code in our custom markdown processor (fixes linking to a
  commit on a namespaced project)
- Fix deleting a project by also removing it from the gitolite config
- Warn if the user is about to just recompile the gitolite config via
  pagure-admin (Patrick Uiterwijk)
- Update .git/config example in doc/usage/pull_requests.rst (sclark)
- Include the PRs opened by the user on the 'My pull-requests' page
- Add to pagure-admin the actions: get-watch and update-watch
- Add to pagure-admin the action: read-only
- Add the user's fullname (if there is one) as title when they comment
- Fix the title of the percentage when hovering over the red bar in issues
- Make the box to edit comments bigger
- Document in the usage section where to find the API documentation
- Provide the sha256 and sha512 of the releases in a CHECKSUMS file
- Remove clear buttons (Till Maas)


3.8 (2017-09-29)
----------------

- Fix API documentation for git/branch (Matt Prahl)
- Fix giving a project to someone who already has access (Matth Prahl)
- Add some border to the tables created in README files
- Ask the user to confirm merging a pull-request
- Fix processing status and close_status updates in the SSE
- Fix the URL to the issue used by the SSE JS on tags
- Increase the logging in the milter to help figuring out issues in the future
- Fix the In-Reply-To header when sending notifications
- Fix showing the delete project button
- Fix search issues with a unicode character
- Catch exception raised when accessing the head of the repo
- Fix deleting a project when some of the folder are not used
- Allow viewing a PR when its origin (fork or branch) is gone
- Fix linking to issue or PR in namespaced projects via #<id>
- Make it more obvious that the namespace and the project are different links
- Tell fedmsg to send things with pagure certificates (Patrick Uiterwijk)
- Fix loading ticket templates on namespaced project and extracting their names
- Add a banner on the overview page when the ACLs are being refreshed on the
  backend (and thus ssh access may not be entirely functional) (Vivek Anand)
- Update the documentation on how to create pull requests (Clement Verna)
- Add button to refresh external pull requests (Patrick Uiterwijk)
- Add the possibility to get the group members when asking the project info
- Make the PROJECT_NAME_REGEX used in form be configurable
- Adjust the milter to support replying with any email addresses associated
- Allow pagure admin to give a project


3.7.1 (2017-09-05)
------------------

- Fix the UPGRADING documentation
- Add the API endpoint to edit multiple custom fields to the doc (Clement
  Verna)


3.7 (2017-09-05)
----------------

- Update link to markdown documentation, fix typo on the way (Till Hofmann)
- Add feature allowing to prevent project creation in the UI only
- Remove the front whitespace from the commit markdown regex (Clement Verna)
- New API endpoint to modify multiple custom fields (Clement Verna)
- Update the example output of the API endpoint giving project information
- Add the ability to order issues by ascending or descending (Matt Prahl)
- Consolidate around pagure.lib.git.generate_gitolite_acls
- Regenerate the gitolite ACL when changing the main admin of a project
- Change the documentation link end point (Clement Verna)
- Fixes the README.rst file (Ompragash)
- Update Docker Environment (Clement Verna)
- Add a configuration key to allow deleting forks but not projects
- Show the entire project name in the UI on the delete button
- Add support for a custom user in the SSH URL
- Do not show the SSH url when the user isn't logged in
- Update the documentation on how to work with pull requests (Clement Verna)
- Support both JSON and Form POST on APIs that accepted only JSON (Matt Prahl)
- Don't expand groups in the watchers API (Ralph Bean)
- Add a new branch API (Matt Prahl)
- Add bash function example to PR documentation (Clement Verna)
- Add the star project feature (Vivek Anand)
- Update the overview diagram
- Fix the rendering of the API version in the html page (Clement Verna)
- Fix message-id not having FQDN (Sachin Kamath)
- Mention on what the rebase was done
- Remove the line numbers coming from pygments on pull-requests
- Include the targeted branch in the list of PRs
- Separately link user/namespace/name
- Fix the pagination when listing projects via the view_projects endpoints
- Retain access when transfering ownership of the project (Matt Prahl)


3.6 (2017-08-14)
----------------

- Blacklist creating a group named 'group'
- Allow having a dedicated worker to compile the gitolite configuration file
- Fix removing groups of a project
- Make the API returns only open issues by default (as documented) (Clement
  Verna)
- Improve the README regarding the use of eventlet to run the tests (Vivek
  Anand)
- Give Pagure site admins the ability to modify projects using the API (Matt
  Prahl)
- Add the "git/generateacls" API endpoint for projects (Matt Prahl)


3.5 (2017-08-08)
----------------

- Fix login when groups are managed outside
- Fix the ordering of the issues by priority using JS and its documentation
- Indicate the issue/PR status in the title of its link
- Correct typo in waiting page template: 'You task' -> 'Your task' (Hazel Smith)
- Fix redirect in search (Carl George)
- Fix removing users of a project
- Allow customizing the HTML title globally
- Drop the new line character and the '# end of body' message when loading the
  config
- Scroll to the comment section on clicking reply. (shivani)
- only show issues on the My Issue page if the issue tracker is on for the
  project (Vivek Anand)
- Update the refresh-gitolite action of pagure-admin for the new interface
  (turns out this wasn't in fact merged in 3.4)
- Add a configuration key to make pagure case sensitive
- Add an USER_ACLS configuration key
- Document the different API token ACLs configuration keys
- Fix syncing groups from external account sources (Patrick Uiterwijk)


3.4 (2017-07-31)
----------------

- Fix layout breakage in the doc
- Stop using readlines() to drop the trailing new line character
- Fix logging by properly formatting the message
- Fix the issue count in the My Issues page (Vivek Anand)
- Add a configuration key to disable deleting branches from the UI
- Add a configuration key to disable managing user's ssh key in pagure
- Fix the vagrant environment (Clement Verna)
- Fix branch support for the git blame view
- Update the PR ref when the PR is updated
- Add a configuration key to disable the deploy keys in a pagure instance
- Fix login when groups are managed outside of pagure
- Fix setting up the git hooks when there is no DOCS_FOLDER set
- Fix installing up the pagure hooks when there is no DOCS_FOLDER set


3.3.1 (2017-07-24)
------------------

- Fix typo in the alembic migration present in 3.3


3.3 (2017-07-24)
----------------

- [SECURITY FIX] block private repo (read) access via ssh due to a bug on how we
  generated the gitolite config - CVE-2017-1002151 (Stefan Bühler)
- Add the date_modified to projects (Clement Verna)


3.2.1 (2017-07-14)
------------------

- Fix a syntax error on the JS in the wait page


3.2 (2017-07-14)
----------------

- Use a decorator to check if a project has an issue tracker (Clement Verna)
- Optimize generating the gitolite configuration for group change
- Fix the issue_keys table for mysql
- Drop the load_from_disk script
- Fix next_url URL parameter on the login page not being used (Carlos Mogas da
  Silva)
- Support configuration where there are no docs folder and no tickets folder
- Show all the projects a group has access to
- Add pagination to the projects API (Matt Prahl)
- Simplify diff calculation (Carlos Mogas da Silva)
- Show the inline comment in the PR's comments by default (Clement Verna)
- Fix the URL in the API documentation for creating a new project (Matt Prahl)


3.1 (2017-07-04)
----------------

- Allow project-less API token to create new tickets
- Tips/tricks: add info on how to validate local user account without email
  verification (Vivek Anand)
- Optimize the generation of the gitolite configuration
- Improve logging and load only the plugin of interest instead of all of them
- Show the task's status on the wait page and avoid reloading the page
- Don't show '+' sign when GROUP_MNGT is off (Vivek Anand)


3.0 (2017-06-30)
----------------

- Since 2.90 celery has become a requirement as well as one of the queueing
  system it supports (pagure defaults to using redis)
- Multiple stability and performance improvements (mainly thanks to Patrick
  Uiterwijk)
- Fix the assignee value in fedmsg when assigning a ticket (Ricky Elrod)
- Make pagure support bleach 2.0.0 (Shengjing Zhu)
- Fixes in CI support (Tim Flink)
- Update the documentation
- Fix plain readme html escape (Shengjing Zhu)
- Refactor user existence code in API and UI (Abhijeet Kasurde)
- Add an API to modify a Pagure project's owner (Matt Prahl)
- Support for uploading multiple files to an issue at once
- Introduce the external committer feature
- Add the required groups feature
- Add an API endpoint to get the git urls of a project (Matt Prahl)
- Blacklist 'wait' as project name
- Add a border to the search box on the side bar to the documentation
- Add the list-id, list-archive and X-Auto-Response-Suppress email headers
- Add ways to customize the gitolite configuration file with snippets
- Return a 404 on private ticket if the user is not authenticated
- cleanup: move static js/css to vendor dir
- Limit the requests version as it conflicts with our chardet requirement
- Rename all the services to pagure-*
- Remove 'on <project name' - watch status dropdown (Vivek Anand)
- Create references for pull-request in the git repo for local checkout
- Use the entire list of users for the assignee field completion
- Fix searching for groups
- Make the search work when searching for project with namespaces or forks
- Return a human-friendly error message when upload fails
- Let acting on the status potentially set the close_status and vice versa
- Multiple fixes to the SSE server
- When forking a project, wait until the very end to let the user go through
- Allow customizing the writing of gitolite's configuration file
- Fix diffing the branch of a project against the target branch
- Fix displaying the new PR button on the default branch
- Do not send a notification upon merge conflicts
- Do not let pagure return 500 when hit with bogus URL
- When loading comment from JSON rely on username/comment rather than comment id
- When deleting a comment, refresh the ticket git repo
- Make patch_to_diff use lists instead of string concatenation (Patrick
  Uiterwijk)


2.90.1 (2017-07-24)
-------------------

- Fix the systemd service file for the worker, needs to have the full path
  (Patrick Uiterwijk and I)
- Fix the logcom server (Patrick Uiterwijk)
- Use python-redis instead of trollius-redis to correctly clean up when client
  leaves on the EV server (Patrick Uiterwijk)


2.90.0 (2017-05-23)
-------------------

- Re-architecture the interactions with git (especially the writing part) to be
  handled by an async worker (Patrick Uiterwijk)
- Add the ability to filter projects by owner (Matt Prahl)


2.15.1 (2017-05-18)
-------------------

- Fix the requirements on straight.plugin in the requirements.txt file
  (Shengjing Zhu)
- Fix typo in the fedmsg hook so it finds the function where it actually is
- Fix and increase the logging when merging a PR
- Fix pushing a merge commit to the original repo
- Use psutil's Process() instead of looping through all processes (Patrick
  Uiterwijk)
- Don't email admins for each PR conflicting
- Fix/improve our new locking mechanism (Patrick Uiterwijk)
- Drop making the token required at the database level since pagure-ci doesn't
  use one (but do flag pull-requests)
- Fix the watch feature (Matt Prahl)


2.15 (2017-05-16)
-----------------

- Improve logic in api/issue.py to reduce code duplication (Martin Basti)
- Fix the download button for attachment (Mark Reynolds)
- Fix our markdown processor for strikethrough
- Add a spinner indicating when we are retrieving the list of branches differing
- Make add_file_to_git use a lock as we do for our other git repositories
- Add the opportunity to enforce a PR-based workflow
- Store in the DB the API token used to flag a pull-request
- Allow people with ticket access to take and drop issues
- Display the users and groups tied to the repo in the API (Matt Prahl)
- Document our markdown in rest so it shows up in our documentation
- Fix comparing the minimal version of flask-wtf required
- Allow the td and th tags to have an align attribute to allow align in html
  tables via markdown
- Avoid binaryornot 0.4.3 and chardet 3.0.0 for the time being
- Add group information API that shows group members (Matt Prahl)
- Ensure people with ticket metadata can edit the custom fields
- Add support to create private projects (Farhaan Bukhsh) - Off by default
- Link to the doc when the documentation is activated but has no content
- Enforce project wide flake8 compliance in the tests
- Enforce a linear alembic history in the tests
- Increase logging in pagure.lib.git
- Use custom logger on all module so we can configure finely the logging
- Multiple improvements to the documentation (René Genz)
- Add the ability to query projects by a namespace in the API (Matt Prahl)
- Add the /<repo>/git/branches API endpoint (Matt Prahl)
- Lock the git repo when removing elements from it
- Always remove the lockfile after using it, just check if it is still present
- Implement the `Give Repo` feature
- Allow project-less token to change the status of an issue in the API
- Make the watch feature more granular (Matt Prahl): you can now watch tickets,
  commits, both, neither or go back to the default
- Bring the pagure.lib coverage to 100% in the tests (which results to bug fixes
  in the code)
- Add locking at the project level using SQL rather than filelock at the git
  repo level


2.14.2 (2017-03-29)
-------------------

- Fix a bug in the logic around diff branches in repos


2.14.1 (2017-03-29)
-------------------

- Fix typo for walking the repo when creating a diff of a PR
- Have the web-hook use the signed content and have a content-type header
- Fix running the tests on jenkins via a couple of fixes to pagure-admin and
  skipping a couple of tests on jenkins due to the current pygit2/libgit2
  situation in epel7


2.14 (2017-03-27)
-----------------

- Update the label of the button to comment on a PR (Abhijeet Kasurde)
- Make search case insensitive (Vivek Anand)
- Improve the debugging on pagure_loadjson
- Only link the diff to the file if the PR is local and not remote
- Do not log on fedmsg edition to private comment
- When deleting a project, give the fullname in the confirmation window
- Add link to the FPCA indicating where to sign it when complaining that the
  user did not sign it (Charelle Collett)
- Fix the error: 'Project' object has no attribute 'ci_hook'
- Fix input text height to match to button (Abhijeet Kasurde)
- Fix the data model to make deleting a project straight forward
- Fix searching issues in the right project by including the namespace
- When creating the pull-request, save the commit_start and commit_stop
- Ensure there is a date before trying to humanize it
- Fixing showing tags even when some of them are not formatted as expected
- Allow repo user to Take/Drop assigment of issue (Vivek Anand)
- Add merge status column in pull requests page (Abhijeet Kasurde)
- Allow user with ticket access to edit custom fields, metadata and the privacy
  flag (Vivek Anand)
- Add number of issues in my issues page (Abhijeet Kasurde)
- Allow report to filter for a key multiple times
- Add the support to delete a report in a project
- Fix rendering the roadmap when there are tickets closed without a close date
- Fix to show tabs in pull request page on mobile (Abhijeet Kasurde)
- Document some existing API endpoints that were missing from the doc
- Make issues and pull-requests tables behave in responsive way (Abhijeet Kasurde)
- Add option to custom field for email notification (Mark Reynolds)
- When resetting the value of a custom field, indicate what the old value was
- Add instance wide API token
- Move the admin functions out of the UI and into a CLI tool pagure-admin
- Do not update the hash in the URL for every tabs on the PR page
- Fix heatmap to show current datetime not when when object was created (Smit
  Thakkar and Vivek Anand)
- Do not include watchers in the subscribers of a private issue
- Do not highlight code block unless a language is specified
- Make getting a project be case insensitive
- Do not change the privacy status of an issue unless one is specified
- Fix the logic of the `since` keyword in the API (Vivek Anand)
- Fix the logic around ticket dependencies
- Add reset watch button making it go back to the default (Vivek Anand)
- Do not show dates that are None object, instead make them empty strings
- Allow filtering tickets by milestones in the API
- Allow filtering tickets by priorities in the API
- Expand the API to support filtering issues having or not having a milestone
- Use plural form for SSH key textfield (Martin Basti)
- Support irc:// links in our markdown and adjust the regex
- Remove backticks from email subject (Martin Basti)
- Adjust the logic when filtering issues by priorities in the API
- Remove mentioning if a commit is in master on the front page
- Optimize finding out which branches are in a PR or can be
- Add required asterisk to Description on new issues (Abhijeet Kasurde)
- Fix misc typo in 404 messages (Abhijeet Kasurde)
- Add performance git repo analyzer/framework (Patrick Uiterwijk)
- Added tip_tricks in doc to document how to pre-fill issues using the url
  (Eashan)
- Document how to filter out for issues having a certain tag in the tips and
  tricks section
- Allow to manually triggering a run of pagure-ci via a list of sentences set in
  the configuration
- Add support for admin API token to pagure-admin
- Make clicking on 'Unassigned' filter the unassigned PR as it does for issues
- Add Priority column to My Issues page (Abhijeet Kasurde)
- Optimize diffing pull-requests
- Add a description to the API tokens
- Include the fullname in the API output, in the project representation
- Add the possibility to edit issue milestone in the API (Martin Basti)
- Fix some wording (Till Maas)
- Rename "request pull" to pull request (Stanislav Laznicka)
- Make tags in issue list clickable (Martin Basti)
- Include the priority name in the notification rather than its level
- Update the ticket metadata before adding the new comment (if there is one)


2.13.2 (2017-02-24)
-------------------

- Fix running the test suite due to bugs in the code:
- Fix picking which markdown extensions are available
- Fix rendering empty text files


2.13.1 (2017-02-24)
-------------------

- Add a cancel button on the edit file page (shivani)
- Fix rendering empty file (Farhan Bukhsh)
- Fix retrieving the merge status of a pull-request when there is no master
- On the diff of a pull-request, add link to see that line in the entire file
  (Pradeep CE)
- Make the pagure_hook_tickets git hook file be executable
- Be a little more selective about the markdown extensions always activated
- Do not notify the SSE server on comment added to a ticket via git
- Fix inline comment not showing on first click in PR page (Pradeep CE)


2.13 (2017-02-21)
-----------------

- Allow filtering issues for certain custom keys using <key>:<value> in the
  search input (Patric Uiterwijk)
- Make loading the JSON blob into the database its own async service
- Add ACLs to pagure (Vivek Anand)
- Fix running the tests against postgresql
- Let the doc server return the content as is when it fails to decode it
- Fix rendering a issue when one of the custom fields has not been properly
  setup (ie a custom field of type list, with no options set-up but still having
  a value for that ticket)
- Fix auto-completion when adding a tag to a ticket
- Add the possibility to filter the issues with no milestone assigned (Mark
  Reynolds)
- Fix the callback URL for jenkins for pagure-ci
- Backport the equalto test to ensure it works on old jinja2 version (fixes
  accessing the user's PR page)


2.12.1 (2017-02-13)
-------------------

- Include the build id in the flag set by pagure-ci on PR (Farhaan Bukhsh)
- Fix using the deploy keys (Patrick Uiterwijk)
- Add the possibility to ignore existing git repo on disk when creating a new
  project
- Fix checking for blacklisted projects if they have no namespace
- Link to the documentation in the footer (Rahul Bajaj)
- Fix retrieving the list of branches available for pull-request
- Order the project of a group alphabetically (case-insensitive)
- Fix listing the priorities always in their right order


2.12 (2017-02-10)
-----------------

- Fix the place of the search and tags bars in the issues page (Pradeep CE)
- Support removing all content of a custom field (Patrick Uiterwijk)
- Improve the `My Pull Requests` page (Pradeep CE)
- Fix displaying binary files in the documentation
- Add a way to easily select multiple tags in the issues list and roadmap
- Allow selecting multiple milestones easily in the UI of the roadmap
- Fix displaying namespaced docs (Igor Gnatenko)
- Fix the web-hook server
- Add a way to view patch attached to a ticket as raw
- Allow milestone to be set when creating an issue using the API (Mark Reynolds)
- Fix adding and editing tags to/of a project
- Make the usage section of the doc be at the top of it (Jeremy Cline)
- Add notifications to issues for meta-data changes (Mark Reynolds)
- Fix not updating the private status of an issue when loading it from JSON
  (Vivek Anand)
- Fix triggering web-hook notifications via the fedmsg hook
- Add a configuration key allowing to hide some projects that users have access
  to only via these groups
- Fix figuring out which branches are not merged in namespaced project
- Automatically link the commits mentionned in a ticket if their hash is 7 chars
  or more
- Allow dropping all the priorities info of an issue
- Do not edit multiple times the milestone info when updating a ticket
- Only update the custom field if there is a value to give it, otherwise remote
  it
- Make pagure compatible with flask-wtf >= 0.14.0
- Add a button to test web-hook notifications
- Fix the layout on the page listing all the closed issues (Rahul Bajaj)
- Load priorities when refreshing the DB from the ticket git repos (Mark
  Reynolds)
- Ignore `No Content-Type header in response` error raised by libgit2 on pull
  from repo hosted on github (for remote PR)
- Add deployment keys (ssh key specific for a single project can be either read
  and write or read-only) (Patrick Uiterwijk)
- Fix install the logcom service to log commits
- Fix deleting tickets that have a tag attached
- Allow pre-filling title and content of an issue via URL arguments:
  ?title=<title>&content=<issue description>
- Re-initialize the backend git repos if there are no tickets/PRs in the DB
  (Vivek Anand)
- Fix invalid pagination when listing all the tickets (regardless of their
  status) and then applying some filtering (Vibhor Verma)


2.11 (2017-01-20)
-----------------

- Fix the forked repo text on the user's PR page (Rahul Bajaj)
- Display the number of subscribers subscribed to the ticket
- Add an attachments section to tickets (Mark Reynolds)
- Small fixes around the git blame feature
- Add an `Add group` button on page listing the groups (Rahul Bajaj)
- Move the `My Issues` and `My Pull-requests` links under the user's menu
- Document the FORK_FOLDER configuration key as deprecated
- Display the subscribers to PR in the same way to display them on ticket
- Adjust the wording when showing a merge commit
- Ensure the last_updated field is always properly updated (Mark Reynolds)
- Fix decoding files when we present or blame them
- Disable the markdown extensions nl2br on README files
- Make issue reports public
- Only display modified time as the modifying user can not be determined (Mark
  Reynolds)
- Add a new API endpoint returning information about a specific project
- Add a button allowing dropping of assignments for an issue easily (Paul W.
  Frields)
- Make attachments of ticket downloadable (Mark Reynolds)
- Make patch/diff render nicely when viewed attached to a ticket (Mark Reynolds)
- Filter out the currrent ticket in the drop-down list for the blocker/depending
  fields (Eric Barbour)
- Move the logging of the commit as activity to its own service: pagure_logcom
- Add a new API endpoint to set/reset custom fields on tickets
- Introduce the USER_NAMESPACE configuration key allowing to put the project on
  the user's namespace by default
- Fix sending notifications about pull-requests to people watching a project
- Fix the list of blacklisted projects
- Inform the user when they try to create a new group using a display name
  already used (Rahul Bajaj)
- Fix importing the milestones into the project when loading from the git repo
  (Clement Verna)
- Add a button to create a default set of close status (as we have a default set
  of priorities)
- Have pagure bail with an error message if the OpenID server did not return an
  username
- Let the error email use the FROM_EMAIL address set in the configuration file
- Fix theprogress bar shown when listing issues (Gaurav Kumar)
- Replace our current tags by colored one (Mark Reynolds)
- Make the roadmap page use the colored tag (Mark Reynolds)
- Fix the tag of Open pull-request when listing all the pull-requests (Rahul
  Bajaj)
- Remove the 'pagure.lib.model.drop_tables' from test/__init__.py file (Amol
  Kahat)
- Fix the headers of the table listing all the pull-request
- Raise an exception when a PR was made against a branch that no longer exists
- Document what to do when pull-requests are not available in a troubleshooting
  section of the documentation
- Send notification upon closing tickets
- Fix re-setting the close_status to None it when re-opening a ticket
- Fix linking to the tabs in the pull-request page (cep)
- Adjust the rundocserver utility script to have the same arguments as runserver
- Ensure the filtering by author remains when changing the status filter on PR
  list (Rahul Bajaj)
- Improve the page/process to create a new API token (Pradeep CE)
- Prevent re-uploading a file with the same name
- Improve the roadmap page (Mark Reynolds)
- Improve the `My Issues` page (Mark Reynolds)
- Fix home page 'open issues' links for namespaced projects (Adam Williamson)
- Fix logging who did the action
- Return a nicer error message to the user when an error occurs with a remote
  pull-request
- Make interacting with the different git repos a locked process to avoid
  lost/orphan commits
- Update API doc for api_view_user (Clement Verna)
- Dont return 404 when viewing empty files (Pradeep CE (cep))
- Do not automatically update the last_updated or updated_on fields
- Make alembic use the DB url specified in the configuration file of pagure
- Only connect to the smtp server if we're going to send an email
- Add a type list to the custom fields (allows restricting the options) (Mark
  Reynolds)
- Fix displaying non-ascii milestones
- Add the possibility to view all the milestones vs only the active ones (Mark
  Reynolds)


2.10.1 (2016-12-04)
-------------------

- Clean up the JS code in the settings page (Lubomír Sedlář)
- Fix the URLs in the `My Issues` and `My Pull-request` pages


2.10 (2016-12-02)
-----------------

- Updating language on not found page (Brian (bex) Exelbierd)
- Add a view for open pull requests and issues (Jeremy Cline)
- Issue 1540 - New meta-data custom field type of "link" (Mark Reynolds)
- Fix overflow issue with comment preview and pre (Ryan Lerch)
- Issue 1549 - Add "updated_on" to Issues and make it queryable (Mark Reynolds)
- Drop UPLOAD_FOLDER in favor of UPLOAD_FOLDER_URL
- Make the group_name be of max 255 characters
- Bug - Update documentation to match the default EMAIL_SEND value (Michael
  Watters)
- Change - Fix grammar in UI messages around enabling/deactivating git hooks
  (Michael Watters)
- Allow resetting the priorities of a project
- Several fixes and enhancements around the activity calendarheatmap
- Add quick_replies field to project (Lubomír Sedlář)
- Fix blaming files containing non-ascii characters (Jeremy Cline and I)
- Include regular contributors when checking if user is watching a project
- List subscribers on the issue pages (Mark Renyolds and I)


2.9 (2016-11-18)
----------------

- Fix redirecting after updating an issue on a project with namespace (Vivek
  Anand)
- Remove take button from Closed Issues (Rahul Bajaj)
- Show the open date/time on issues as we do for PR (Rahul Bajaj)
- When rendering markdown file use the same code path as when rendering comments
- Add documentation for using Markdown in Pagure (Justing W. Flory)
- Fix the behavior of the Cancel button on PR page (Rahul Bajaj)
- Be tolerant to markdown processing error
- Let the notifications render correctly when added by the SSE server
- Fix the URL for pull request on the list of branches of a fork (Rahul Bajaj)
- Adjust the markdown processor to have 1 regex for all cross-project links
- Remove unsued variables (Farhaan Bukhsh)
- Hide the title of private tickets when linking to them in markdown
- Show user activity in pagure on the user's page
- Add the possibility to subscribe to issues
- Do not cache the session in pagure-ci (as we did for pagure-webhook)
- Fix rendering raw file when the sha1 provided is one of a blob
- Include project's custom fields in the JSON representation of a project
- Include the issue's custom fields values in the JSON representation of an
  issue
- Include the list of close_status and the milestones in the JSON of a project
- Improve documentation related to unit-tests (Rahul Bajaj)
- Use `project.fullname` in X-Pagure-Project header (Adam Williamson)
- Figure a way to properly support WTF_CSRF_TIME_LIMIT on older version of
  flask-wtf
- When updating an issue, if the form does not validate, say so to the user
- Fix the total number of pages when there are no PR/issues/repo (vibhcool)
- Fix forking a repo with a namespace
- Include the namespace in the message returned in pagure.lib.new_project
- Move the metadata-ery area in PR to under the comments tab (Ryan Lerch)
- Update setup instructions in the README.rst (alunux)
- Support namespaced projects when reading json data (clime)
- When uploading a file in a new issue, propagate the namespace info
- Ensure our avatar works with non-ascii email addresses
- Downgrade to emoji 1.3.1, we loose some of the newer emojis we get back
  preview and reasonable size (Clément Verna)
- Fix sending notifications email containing non-ascii characters
- Fix using the proper URL in email notifications (Adam Williamson)
- Move the Clear and Cancel buttons to the right hand side of the comment box
- Fix spelling in the PR page (Vibhor Verma)
- Support loading custom fields from JSON when loading issues from git (Vivek
  Anand)
- Fix handling namespaced project in the SSE server (Adam Williamson)
- Add a pylintrc configuration file to help with code standards (Adam
  Williamson)
- Add go-import meta tag allowing go projects to be hosted on pagure (Patrick
  Uiterwijk)
- Fix index overflow when opening remote pull-request (Mark Reynolds)
- Add SSE support for custom fields
- Add a git blame view
- Allow emptying a file when doing online editing
- Only let admins edit the dependency tree of issues
- Fix some spelling errors (Adam Williamson)
- Add SHA256 signature to webhooks notifications (Patrick Uiterwijk)
- Multiple fixes in the API documentation and output


2.8.1 (2016-10-24)
------------------

- Handle empty files in detect_encodings (Jeremy Cline)
- Fix the import of encoding_utils in the issues controller
- Fix the list of commits page
- Update docs to dnf (Rahul Bajaj)
- Add close status in the repo table if not present when updating/creating issue
  via git (Vivek Anand)
- If chardet do not return any result, default to UTF-8


2.8 (2016-10-21)
----------------

- Fix the migration adding the close_status field to remove the old status
  only at the end
- Fix the RTD and Force push hooks for the change in location of the plugins
- Fix creating new PR from the page listing the pull-requests
- Add the possibility for the user to edit their settings in their settings page
- Include the close_status in the JSON representation of an issue
- Load the close_status if there is one set in the JSON repsentation given
- Fix running the tests when EVENTSOURCE_SOURCE is defined in the
  configuration.
- Make the search case-insensitive when searching issues
- Fix the "cancel" button when editing a "regular" comment on a pull-request
- Remove the ``Content-Encoding`` headers from responses (Jeremy Cline)
- Fix creating the release folder for project with a namespace
- When sending email, make the user who made the action be in the From field
- When searching groups, search both their name and display name
- Create a Vagrantfile and Ansible role for Pagure development (Jeremy Cline)
- Made searching issue stop clearing status and tags filters (Ryan Lerch)
- Improve documentation (Bill Auger)
- Fix finding out the encoding of a file in git (Jeremy Cline)
- Fix making cross-project references using <project>#<id>
- Allow filter the list of commits for a certain user
- Ensure we disable all the submit button when clicking on one (avoid sending
  two comments)
- Do not always compute the list of diff commits
- Let's not assume PAGURE_CI_SERVICES is always there
- Allow html table to define their CSS class
- Add a link to the user on the commit list (Ryan Lerch)
- Change `Fork` button to `View Fork` on all pages of the project (tenstormavi)
- Enable some of the markdown extensions by default
- Fix mixed content blocked in the doc by not sending our user to google (Rahul
  Bajaj)


2.7.2 (2016-10-13)
------------------

- Do not show the custom field if the project has none
- Improve the documentation around SEND_EMAIL (Jeremy Cline)


2.7.1 (2016-10-12)
------------------

- Bug fix to the custom fields feature


2.7 (2016-10-11)
----------------

- Clean imports (Vivek Anand)
- Fix NoneType error when pagure-ci form is inactively updated first time
  (Farhaan Bukhsh)
- Fix minor typos in configuration documentation (Jeremy Cline)
- Use context managers to ensure files are closed (Jeremy Cline)
- Adjust update_tickets_from_git to add milestones for issues as well (Vivek
  Anand)
- Update milestone description in Settings (Lubomír Sedlář)
- Add checks for the validity of the ssh keys provided (Patrick Uiterwijk)
- Remove hardcoded hostnames in unit tests (Jeremy Cline)
- Skip clamd-dependent tests when pyclamd isn't installed (Patrick Uiterwijk)
- Fix interacting with branch containing a dot in their name (new PR button,
  delete branch button)
- Ensure only project admins can create reports
- Do not warn admins when a build in jenkins did not correspond to a
  pull-request
- Fix the progress bar on the page listing the issues (d3prof3t)
- Do not call the API when viewing a diff or a PR if issues or PRs are disabled
- Port pagure to flask 0.13+
- Fix displaying the reason when a PR cannot be merged
- Allow projects to turn on/off fedmsg notifications
- Fix the web-hook service so when a project is updated the service is as well
- Add the possibility to specify a status to close ticket (closed as upstream,
  works for me, invalid...)
- Let all the optional SelectFields in forms return None when they should
- Make each tests in the test suite run in its own temporary directory (Jeremy
  Cline)
- Use long dash in footer instead of two short ones (Lubomír Sedlář)
- Add a welcome screen to new comers (does not work with local auth)
- Ensure user are not logged in if we couldn't properly set them up in pagure
- Add the possibility to search through issues (AnjaliPardeshi)
- Add a default hook to all new projects, this hook re-set the merge status of
  all the open PR upon push to the main branch of the repo
- Add support for setting custom fields for issues per projects


2.6 (2016-09-20)
----------------

- Fix creating new PR from the page listing all the PRs
- Fix grammar error in the issues and PRs page (Jason Tibbitts)
- Fall back to the user's username if no fullname is provided (Vivek Anand)
- Fix typo in the using_docs documentation page (Aleksandra Fedorova (bookwar))
- Fix viewing plugins when the project has a namespace (and the redirection
  after that)
- Rework the milestone, so that a ticket can only be assigned to one milestone
  and things look better
- Add a project wide setting allowing to make all new tickets private by default
  (with the option to make them public)
- Allow toggling the privacy setting when editing the ticket's metadata
- Rework some of the logic of pagure-ci for when it searches the project related
  to a receive notification
- Fix the label of the button to view all close issues to be consistent with the
  PR page (Jeremy Cline)
- Add the possibility for projects to notify specific email addresses about
  issues/PRs update
- Fix loading tickets from the ticket git repository (fixes importing project to
  pagure)


2.5 (2016-09-13)
----------------

- Don't track pagure_env (venv) dir (Paul W. Frields)
- Setting Mail-Followup-To when sending message to users (Sergio Durigan Junior)
  (Fixed by Ryan Lerch and I)
- Fixed the tickets hook so that we dont ignore the files committed in the first
  commit (Clement Verna)
- Fix behavior of view of tree if default branch is not 'master' (Vivek Anand)
- Fix checking the release folder for forks
- Improve the Remote PR page
- Improve the fatal error page to display the error message is there is one
- Avoid issues attachment containing json to be considered as an issue to be
  created/updated (Clement Verna)
- Allow the <del> html tag (Clement Verna)
- Specify rel="noopener noreferrer" to link including target='_blank'
- Show in the overview page when a branch is already concerned by a PR
- Fix viewing a tree when the identifier provided is one of a blob (not a tree)
- Port all the plugins to `uselist=False` in their backref to make the code
  cleaner
- Fix pagure_ci for all sort of small issues but also simply so that it works as
  expected
- Make the private method __get_user public as get_user
- Improve the documentation (fix typos and grammar errors) (Sergio Durigan
  Junior)
- Drop the `fake` namespaces in favor of real ones
- Add the possibility to view all tickets/pull-requests of a project (regardless
  of their status)
- Paginate the pages listing the tickets and the pull-requests
- Add the possibility to save a certain filtering on issues as reports
- Add support to our local markdown processor for ~~striked~~


2.4 (2016-08-31)
----------------

- [Security] Avoid all html related mimetypes and force the download if any
  (CVE-2016-1000037) -- Fixed in 2.3.4 as well
- Redirect the URL to projects <foo>.git to <foo> (Abhishek Goswami)
- Allow creating projects with 40 chars length name on newer pagure instances
- Fix @<user> and #<id> when editing a comment (Eric Barbour)
- Display properly and nicely the ACLs of the API tokens (Lubomír Sedlář)
- Removing html5lib so bleach installation finds what version is best (Tiago M.
  Vieira)
- Remove the branchchooser from the repoheader (again) (Ryan Lerch)
- Fix hard-coded urls in the master template
- Made the interaction with the watch button clearer (Ryan Lerch)
- Introduce pagure-ci, a service allowing to integrate pagure with a jenkins
  instance (Farhaan Bukhsh and I)
- Accept Close{,s,d} in the same way as Merges and Fixes (Patrick Uiterwijk)
- Avoid showing the 'New PR' button on the overview page is a PR already exists
  for this branch, in the main project or a fork (Vivek Anand)
- Fix presenting the readme file and display the readme in the tree page if
  there is one in the folder displayed (Ryan Lerch)
- Move the new issue button to be available on every page (AnjaliPardeshi)
- Fix pagure for when an user enters a comment containing #<id> where the id
  isn't found in the db
- Make the bootstrap URLs configurable (so that they don't necessarily point to
  the Fedora infra) (Farhaan Bukhsh)
- Fix how the web-hook server determine the project and its username
- Replace the login icon with plain text (Ryan Lerch)
- Fix layout in the doc (Farhaan Bukhsh)
- Improve the load_from_disk utility script
- Fix our mardown processor to avoid crashing on #<text> (where we expect #<id>)
- Fix the search for projects with a / in their names
- Fix adding a file to a ticket when running pagure with `local` auth
- Improve the grammar around the allowed prefix in our fake-namespaces (Jason
  Tibbitts)
- Implement scanning of attached files for viruses (Patrick Uiterwijk)
- Document how to set-up multiple ssh keys per user (William Moreno Reyes)
- Add display_name and description to groups, and allow editing them
- Add the ability to run the post-receive hook after merging a PR in the UI
- Fix showing the group page even when user management is turned off (Vivek
  Anand)
- Make explicit what the separators for tags is (Farhaan Bukhsh)
- Include the word setting with icon (tenstormavi)
- Fix the requirements.txt file (Vivek Anand)
- Cleaned up the topbar a bit (Ryan Lerch)
- Fix location of bottom pagination links on user page (Ryan Lerch)
- Add user's project watch list in index page of the user (Vivek Anand)
- Fix showing the reporter when listing the closed issues (Vivek Anand)
- Fix accessing forks once the main repo has been deleted (Farhaan Bukhsh)


2.3.4 (2016-07-27)
------------------

- Security fix release blocking all html related mimetype when displaying the
  raw files in issues and forces the browser to download them instead (Thanks to
  Patrick Uiterwijk for finding this issue) - CVE: CVE-2016-1000037


2.3.3 (2016-07-15)
------------------

- Fix redering the release page when the tag message contain only spaces (Vivek
  Anand)
- Fix the search in @<username> (Eric Barbour)
- Displays link and git sub-modules in the tree with a dedicated icon


2.3.2 (2016-07-12)
------------------

- Do not mark as local only some of the internal API endpoints since they are
  called via ajax and thus with the user's IP


2.3.1 (2016-07-11)
------------------

- Fix sending notifications to users watching a project
- Fix displaying if you are watching the project or not


2.3 (2016-07-11)
----------------

- Fix typos in pr_custom_page.rst (Lubomír Sedlář)
- Improve the unit-test suite (Vivek Anand)
- Remove the branch chooser from the repoheader and rework the fork button (Ryan
  Lerch)
- Add support for non utf-8 file names (Ryan Lerch)
- Add a 'Duplicate' status for issues (Vivek Anand)
- Add title attribute for replying to comment and editing the comment in issues
  and PRs (Vivek Anand)
- Include the user when reporting error by email
- Add an API endpoint to create projects
- Add an API endpoint to assign someone to a ticket
- Add small script to be ran as cron to send reminder of expiring tokens (Vivek
  Anand)
- Do not show the PR button on branches for which a PR is already opened
- Add an API endpoint to fork projects
- Add the possibility to watch/unwatch a project (Gaurav Kumar)
- Add a 'Take' button on the issue page (Ryan Lerch and I)
- Add a dev-data script to input some test data in the DB for testing/dev
  purposes (skrzepto)
- Fix links to ticket/pull-request in the preview of a new ticket
- Add the possibility to diff two or more commits (Oliver Gutierrez)
- Fix viewing a file having a non-ascii name
- Fix viewing the diff between two commits having a file with a non-ascii name
- On the commit detail page, specify on which branch(es) the commit is
- Add the possibility to have instance-wide admins will full access to every
  projects (set in the configuration file)
- Drop the hash to the blob of the file when listing the files in the repo
- Add autocomple/suggestion on typing @<username> on a ticket or a pull-request
  (Eric Barbour)
- Fix the edit link when adding a comment to a ticket via SSE
- Add notifications to issues as we have for pull-requests
- Record in the db the date at which a ticket was closed (Vivek Anand)
- Add the possibility for pagure to rely on external groups provided by the auth
  service
- Add the possibility for pagure to use an SMTP server requiring auth
  (Vyacheslav Anzhiganov)
- Add autocomple/suggestion on typing #<id> for tickets and pull-requests (Eric
  Barbour)
- With creating a README when project's description has non-ascii characters
  (vanzhiganov)
- Add colored label for duplicate status of issues (Vivek Anand)
- Ship working wsgi files so that they can be used directly from the RPM
- Mark the wsgi files provided with the RPM as %%config(noreplace)
- Install the api_key_expire_mail.py script next to the createdb one


2.2.1 (2016-06-01)
------------------

- Fix showing the inital comment on PR having only one commit (Ryan Lerch)
- Fix diffs not showing for additions/deletions for files under 1000 lines (Ryan
  Lerch)
- Split out the commits page to a template of its own (Ryan Lerch)
- Fix hightlighting the commits tab on commit view
- Fix the fact that the no readme box show on empty repo (Ryan Lerch)


2.2 (2016-05-31)
----------------

- Fix retrieving the log level from the configuration file (Nuno Maltez)
- Rework the labels used when sorting projects (Ankush Behl)
- Fix spelling error in sample config (Bruno)
- Hide the URL to the git repo for issues if these are disabled
- Do not notify about tickets being assigned when loaded from the issue git repo
  (Clément Verna)
- Adjust get_revs_between so that if the push is in the main branch we still get
  the list of changes (Clément Verna)
- Fix display of files moved on both old and new pygit2 (Ryan Lerch)
- Fix changes summary sidebar for older versions of pygit (Ryan Lerch)
- Fix the label on the button to add a new milestone to a project (Lubomír
  Sedlář)
- Allow the roadmap feature to have multiple milestone without dates (Lubomír
  Sedlář)
- Fix the link to switch the roadmap/list views (Lubomír Sedlář)
- Render the emoji when adding a comment to a ticket or PR via SSE (Clément
  Verna)
- Always allow adming to edit/delete comments on issues
- Build Require systemd to get macros defined in the spec file (Bruno)
- Upon creating a ticket if the form already has data, show that data
- Add a readme placeholder for projects without a readme (Ryan Lerch)
- Enable markdown preview on create pull request (Ryan Lerch)
- Make bottom pagination links on project list respect the sorting filter (Ryan
  Lerch)
- Add the ability to create a README when creating a project (Ryan Lerch)
- Try to prevent pushing commits without a parent when there should be one
- Fix the configuration keys to turn off ticket or user/group management for an
  entire instance (Vivek Anand)
- Fix deleting project (propagate the deletion to the plugins tables)
- Do not render the diffs of large added and removed files (more than 1000
  lines) (Ryan Lerch)
- Adjust the UI on the template to add/remove a group or an user to a project in
  the settings page (Ryan Lerch)
- Check if a tag exists on a project before allowing to edit it (skrzepto)


2.1.1 (2016-05-13)
------------------

- Do not render the comment as markdown when importing tickets via the ticket
  git repo
- Revert get_revs_between changes made in
  https://pagure.io/pagure/pull-request/941 (Clement Verna)

2.1 (2016-05-13)
----------------

- Fix the milter to get it working (hotfixed in prod)
- Fix the fedmsg hook so that it works fine (hotfixed in prod)
- Fix the path of one of the internal API endpoint
- Pass client_encoding utf8 when connecting to the DB (Richard Marko)
- Do not use client_encoding if using sqlite (Ryan Lerch)
- Allow project names up to 255 characters (Richard Marko)
- Add a spinner showing we're working on retrieve the PR status on the PR page
  (farhaanbukhsh)
- Rework installing and removing git hooks (Clement Verna)
- Rework the summary of the changes on the PR page (Ryan Lerch)
- Improve the description of the priority system (Lubomír Sedlář)
- Fix commit url in the pagure hook (Mike McLean)
- Improve the regex when fixing/relating a commit to a ticket or a PR (Mike
  McLean)
- Improve the description of the pagure hook (Mike McLean)
- Fix the priority system to support tickets without priority
- Fix the ordering of the priority in the drop-down list of priorities
- Ensure the drop-down list of priorities defaults to the current priority
- Adjust the runserver.py script to setup PAGURE_CONFIG before importing pagure
- Remove flashed message when creating a new project
- Add markdown support for making of PR# a link to the corresponding PR
- Include the priority in the JSON representation of a ticket
- Include the priorities in the JSON representation of a project
- Do not update the assignee if the person who commented isn't an admin
- When adding a comment fails, include the comment text in the form if there was
  one
- Add support to remove a group from a project
- Add a roadmap feature with corresponding documentation
- Allow 'kbd' and 'var' html tags to render properly
- Fix deleting a project on disk as well as in the DB
- Allow setting the date_created field when importing ticket from git (Clement
  Verna)
- Strip GPG signature from the release message on the release page (Jan Pokorný)
- Make comment on PR diffs fit the parent, and not overflow horiz (Ryan Lerch)


2.0.1 (2016-04-24)
------------------

- Fixes to the UPGRADING documentation
- Fix URLs to the git repos shown in the overview page for forks
- Fix the project titles in the html to not start with `forks/`


2.0 (2016-04-22)
----------------

- Rework the initial comment of a PR, making it less a comment and more
  something that belong to the PR itself
- Fix showing or not the fork button when editing a comment on an issue or a PR
  and fix the highlighted tab when editing comment of an issue (Oliver
  Gutierrez)
- Fix the count of comments shown on the page listing all the PRs to include
  only the comments and not the notifications (farhaanbukhsh)
- In the settings page explain that API keys are personal (Lubomír Sedlář)
- Rework the fedmsg message sent upon pushing commits, one message per push
  instead of one message per commit
- Mark the page next/previous as disabled when they are (on browse pages)
- Avoid the logout/login loop when logging out
- Support rendering file with a `.markdown` extension
- Fix the layout of the password change branch
- Improve the documentation, add overview graphs, expand the usage section,
  improve the overview description
- Fix checking if the user is an admin of a project or not (which was making the
  user experience confusing as they sometime had the fork button and sometime
  not)
- Fix the pagination on the browse pages when the results are sorted
- Disable the Commit and Files tabs if a repo is new
- Update the pagure logo to look better (Ryan Lerch)
- Allow anyone to fork any project (Ryan Lerch)
- Fix searching on the browse pages by preventing submission of the 'enter' key
  (Ryan Lerch)
- Rework the issue page to be a single, large form allowing to update the
  meta-data and comment in one action and fixing updating the page via SSE
- Turn off the project's documentation by default to empty `Docs` tab leading to
  nothing
- Fill the initial comment with the body of the commit message if the PR only
  has one commit (Ryan Lerch)
- Add a plugin/git hook allowing to disable non fast-forward pushes on a branch
  basis
- Fix asynchronous inline comments in PR by fixing the URL to which the form is
  submitted
- Add a plugin/git hook allowing to trigger build on readthedocs.org upon git
  push, with the possibility to restrict the trigger to only certain branches
- Automatically scroll to the highlighted range when viewing a file with a
  selection (Lubomír Sedlář)
- Indicate the project's creation date in the overview page (Anthony Lackey)
- Clear the `preview` field after adding a comment via SSE
- Adjust the unit-tests for the change in behavior in pygments 2.1.3
- Fix listing all the request when the status is True and do not convert to text
  request.closed_at if it is in fact None
- Improved documentation
- Attempt to fix the error `too many open files` on the EventSource Server
- Add a new param to runserver.py to set the host (Ryan Lerch)
- Fix the of the Docs tab and the Fork button with rounded corners (Pedro Lima)
- Expand the information in the notifications message when a PR is updated (Ryan
  Lerch)
- Fix hidding the reply buttons when users are not authenticated (Paul W. Frields)
- Improve the description of the git hooks (Lubomír Sedlář)
- Allow reply to a notification of pagure and setting the reply email address as
  Cc
- In the fedmsg git hook, publish the username of all the users who authored the
  commits pushed
- Add an activity page/feed for each project using the information retrieved
  from datagrepper (Ryan Lerch)
- Fix showing lightweight tags in the releases page (Ryan Lerch)
- Fix showing the list of branches when viewing a file
- Add priorities to issues, with the possibility to filter or sort them by it in
  the page listing them.
- Add support for pseudo-namespace to pagure (ie: allow one '/' in project name
  with a limited set of prefix allowed)
- Add a new plugin/hook to block push containing commits missing the
  'Signed-off-by' line
- Ensure we always use the default email address when sending notification to
  avoid potentially sending twice a notification
- Add support for using the keyword Merge(s|d) to close a ticket or pull-request
  via a commit message (Patrick Uiterwijk)
- Add an UPGRADING.rst documentation file explaining how to upgrade between
  pagure releases


1.2 (2016-03-01)
----------------

- Add the possibility to create a comment when opening a pull-request (Clement
  Verna)
- Fix creating PR from a fork directly from the page listing all the PR on the
  main project (Ryan Lerch)
- Color the label showing the issues' status on the issue page and the page
  listing them (Ryan Lerch)
- Add a small padding at the bottom of the blockquote (Ryan Lerch)
- In the list of closed PR, replace the column of the assignee with the date of
  closing (Ryan Lerch)
- Drop font awesome since we no longer use it and compress the png of the
  current logo (Ryan Lerch)
- Drop the svg of the old logo from the source (Ryan Lerch)
- Add descriptions to the git hooks in the settings page (farhaanbukhsh)
- Fix the pagure git hook


1.1.1 (2016-02-24)
------------------

- Fix showing some files where decoding to UTF-8 was failing
- Avoid adding a notification to a PR for nothing
- Show notifications correctly on the PR page when received via SSE


1.1 (2016-02-23)
----------------

- Sort the release by commit time rather than name (Clerment Verna)
- Add a link to the markdown syntax we support
- Add the possibility to display custom info when creating a new PR
- Improve the title of the issue page
- Make the ssh_info page more flexible so that we can add new info more easily
- Add the possibility to resend a confirmation email when adding a new email
  address
- Encode the email in UTF-8 for domain name supporting it
- Add a button to eas
