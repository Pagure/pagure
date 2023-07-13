Changelog
=========

This document records all notable changes to `Pagure <https://pagure.io>`_.

5.13.2 (2021-01-29)
-------------------
- Fix broken pagination of group API (Lukas Brabec and František Zatloukal)
- Fixing the alias url in the examples (Mohan Boddu)
- Pull in upstream fix for apostrophes from highlightjs-rpm-specfile (David Auer)
- Improve logging when trying to interract with a git repo via http(s)


5.13.1 (2021-01-29)
-------------------
- Add the api_project_hascommit endpoint to the API doc
- Do not return a 500 error when the OpenID provider doesn't provide an email
- Fix bug in the default hook


5.13.0 (2021-01-19)
-------------------
- When failing to find a git repo, log where Pagure looked
- Get the default branch of the target repo when linking for new PR
- Add an hascommit API endpoint
- Fixing sample input and output for alias related api (Mohan Boddu)
- Add missing API endpoints related to git aliases and re-order a little
- Add support for chardet 4.0+
- Fix support for cchardet


5.12.1 (2021-01-08)
-------------------
- Block chardet 4.0, we're not compatible with it yet
- Be consistent in the messages sent and with the schemas defined in
  pagure-schemas (0.0.4+)
- Make the token_id column of the commit_flags table nullable


5.12.0 (2021-01-06)
-------------------

/!\ the PR flag API is now creating Commit flag on the commit at the top of the
pull-request.


- Display real line numbers on pull request's diff view (Julen Landa Alustiza)
- Show the assignee's avatar on the board
- Allow setting a status as closing even if the project has no close_status
- Include the assignee in the list of people notified on a ticket/PR
- Add orphaning reason on the dist-git theme (Michal Konečný)
- Adjust the way we generate humanized dates so we provide the humanized date
  as well as the actual date when hovering over (Julen Landa Alustiza)
- When a file a detected as a binary file, return the raw file
- Allow using the modifyacl API endpoint to remove groups from a project
- Add a note that repo_from* argument are mandatory in some situations when
  opening a Pull-Request from the API
- Increase the list of running Pagure instances in the documentation (Neal Gompa)
- Remove fenced code block when checking mention (Michael Scherer)
- Add support for using cchardet to detect files' encoding
- Show the default branch in the project overview page
- Send appropriate SMTP status codes and error messages in the milter. (Björn
  Persson)
- Report an error if a message ID isn't recognized by the milter. (Björn Persson)
- Add support for disabling user registration (Neal Gompa)
- Add a way to make the stats view on more than one year (if you know how to)
- Encode the data passed onto the mail hook so it is of bytes type
- Reverse out of order instructions for new repos (Jerry James)
- Split the list of branches into two lists active/inactive in dist-git
- Rework the "My PR" page so it does not pull so many info at once
- Include the date of the last mirroring process in the logs
- Forward the username when updating the pull-request
- Add pagination to group API (Michal Konečný)
- When returning the commits flags in the API, returned them by update date
- Change the PR flag API endpoints to use commit flags
- Only show the subscribers list on demand
- Improve the message showns when a new mirrored project is created
- When editing the issue's description sent the html of it to the SSE server
- Add an update-acls action to pagure-admin
- Add support for AAA system sending SSH keys encoded in base64
- Allow deleting the master branch when it is not the default branch
- Allow people with a fork to have a working drop-down for opening new PRs
- Fix handling "false" when editing project's options via the API (Bernhard M.
  Wiedemann)
- Ensure a fork project has the same default branch as its parent
- Allow to specify a default branch for all projects hosted on an instance
- Add support for pagure-messages
- Add a notification for when a group is removed from a project
- When checking if messages were sent via a rebase, do not run the git hooks
- Make the API endpoint to update project's options accept JSON
- Add a full_url to the JSON representation of our main objects
- Ensure the author in git commit notifications follow the expected format
- Add support for git branch aliases
- Update the vagrant development environment
- Allow updating the target branch when editing a PR


5.11.3 (2020-08-11)
-------------------

- Fix installability of web-apache-httpd subpackage on EL7 (Neal Gompa)
- Fix the model around the boards so it works with mariadb/mysql
- Add new endpoints to the API documentation


5.11.2 (2020-08-04)
-------------------

- Allow having a dedicated loggin configuration for the git hooks


5.11.1 (2020-08-03)
-------------------

- Increase logging to the pagure_auth logger
- Make work pagure-admin ensure-project-hooks when the target link exists but is
  broken
- Fix sorting collaborators and groups of collaborators
- Fix git push over http(s)


5.11.0 (2020-08-03)
-------------------

- Change the project icon when the project is mirrored from an external source
- Allow a theme or a blueprint to inject custom buttons in the navigation bar.
  (zPlus)
- Add API endpoint to get a pull-request comment (Lukas Holecek)
- Omit breaking original comment format in reply on pull-requests (Lukas Holecek)
- Let the milter announce when it reject an email based on its address
- Don't Let the milter process the email we send. (Björn Persson)
- Add a collaborator level to projects
- Allow collaborators to edit files in the branch that they have access to
- Add orphan button to project page (Michal Konečný)
- Allow setting the default git branch when creating projects via the API
- Allow creating mirrored project from the API
- Add the possibility to set the default branch at project creation
- Add API endpoint to set the default git branch and expose it in an existing
  endpoint
- Adjust the example configuration for logging to a file
- Allow project-less API token with the "modify_project" ACL to update watchers
- spec: Have the log directory owned by the main package (Neal Gompa)
- Add a new API endpoint to retrieve a commit's metadata/info
- Add a new API endpoint allowing to delete a project
- Add support for customizing the new issue page
- Introducing the boards feature
- Add an API endpoint to view the content of a git repo
- Port Pagure's markdown extension to the new API
- Multiple small fixes for the vagrant-based development environment
- Use WhiteNoise to serve static assets for the Pagure web
- Fix running the tests on py 3.8
- Port Pagure's test suite to pytest
- Fix the title of the graph showing the evolution of the number of open tickets
  on a project
- Do not assume there is a SMTP_STARTTLS configuration key set
- Bring back JS library used for the heatmap (Nils Philippsen)
- Show the ACL name in addition to the description when creating API tokens
- Allow editing the URL a project is mirrored from
- Add comments to the mirror service files for clarifying their purpose. (zPlus)
- Fix warning when compiling the doc
- Add a dedicated logger for everything that is auth related
- api: fix apidoc format on api_view_issues_history_detailed_stats Fixes web
  api doc view template issues (Julen Landa Alustiza)
- doc: Add a page documenting known Pagure instances (Neal Gompa)
- starttls support via SMTP_STARTTLS: provide additional documentation. (midipix)
- Add support for smtp server requiring starttls to work
- Make the stats page use the new stats API endpoint


5.10.0 (2020-05-14)
-------------------

- Allow viewing issues via the API using project-less API token (Julen Landa
  Alustiza)
- Rename Koshei to Koschei in the srcfpo theme (Fabio Valentini)
- Make Pagure work with recent sqlalchemy versions (>= 1.3.0)
- Improve the vagrant-based dev environment for Pagure developers
- Add a new API endpoint to retrieve detailed stats about the issues
- Improve the graphs displayed in the stats tab of each projects
  - Remove dependency on d3.js
  - Add dependency on chartjs
- Add a new graph tracking the number of open issues throughout the year
- Upgrade the container based development environment for Pagure developers
  (Andrew Engelbrecht)
- Improve loading tickets from git
- Support pygit2 >= 1.1.0 (Andrew Engelbrecht)
- Add missing endpoints to the API documentation (Fabio Valentini)
- Add support for wtforms >= 2.3
  - Add dependency on email_validator in such case
- Fix sorting users by their username when using python3
- Correct the API documentation for updating the watchers of a project (Fabio
  Valentini)
- Ensure the name of the headers are always of the correct type (especially when
  using python3)
- Ensure aclchecker and keyhelper can work with APP_URL having a trailing slash
- Add a new git auth backend which can manage the .ssh/authorized_keys file
  directly
- Update information about supported Git auth backends (Neal Gompa)
- Add support for arrow >= 0.15.6
- Allow repo admins to change the bugzilla overrides (srcfpo theme)
- Fix getting the milter running with python3
- Fix mirroring project hosted remotely
- Add url_path property to class User (and thus in the API) (zPlus)
- Improve email text for new user registration (zPlus)
- Set the USER environment variable when pushing over http
- Add support for git push via http using basic auth relying on API token
- If Pagure is set up for local auth, allow git push via https to use it
- Add an example nginx configuration file for Pagure (Neal Gompa)
- Create two subpackages in the Pagure for the apache and nginx configuration
  files (Neal Gompa)
- Add some documentation on how git push over http works in Pagure
- Make Pagure compatible with the latest version of flake8
- Add PAGURE_PLUGINS_CONFIG setting in Pagure configuration file (zPlus)


5.9.1 (2020-03-30)
------------------

- Add a missing </div> that broke the user's settings page
- Do not block when waiting for subprocess to finish (Michal Srb)
- Fix git blame when the identifier provided is a blob
- Fix view_commits when the identified provided is a blob
- When viewing file's history, use the default branch if needed


5.9 (2020-03-24)
----------------

- Swap "Add" and "Cancel" button ordering for access management (Ken Dreyer)
- Add API to manage plugins (ie: git hooks) (Michal Konečný)
- Fix querying mdapi from within the srcfpo theme (Karsten Hopp)
- Add support for pygit2 1.0.0 (Julen Landa Alustiza)
- Fix activity stats api tests when running the tests at the beginning of
  the year (Julen Landa Alustiza)
- Add logic to set bugzilla assignee overrides from within the srcfpo theme
  (Karsten Hopp)
- Multiple fixes and improvements to the API endpoints to retrieve the tags
  used in a project (Julen Landa Alustiza)
- Add a new API endpoint to add tags to a project (Julen Landa Alustiza)
- Add a new API endpoint to delete tags of a project (Julen Landa Alustiza)
- Add a new API endpoint to edit/update an existing issue/ticket(Julen Landa
  Alustiza)
- Add a new page to see a file's history in git (linked from the file's view page
  and the blame page)
- Only consider the 6 most recently active branch in the drop-down to create
  new PR
- Fix the view_commit endpoint when the identifier provided is a git tag
- Add an endpoint to renew user API token
- Include a link to where the token can be renewed in the email about API
  token nearing expiration
- Allow users to set their own expiration date on API token (up to 2 years)
- Fix the /groups API endpoint and order the output by group name
- Add a new API endpoint to retrieve a project's webhook token (Fabien
  Boucher)
- Expose related_prs on issue API (Lenka Segura)
- Fix the regenerate-repo actions
- Reword "Maintained by orphan" to "Package is currently unmaintained" in
  the srcfpo theme (Fabio Valentini)
- Add support for werkzeug 1.0
- Only enable the "Take" button once we know the package is active in the
  srcfpo theme
- Make the "Issue" link in the info page point to bugzilla in the srcfpo
  theme
- Provide some feedback to the user when changing monitoring worked
- Hide the SSH clone URL if the user is not in one of the group with ssh
  access
- Order pull requests based on updated_on column when we want to order based
  on last updated time (Julen Landa Alustiza)
- Update README to reference correct minimum version of pygit2 (Neal Gompa)
- Support python markdown >= 3.2.0 (Julen Landa Alustiza)
- Fix taking into account the blacklisted patterns
- Add a new API endpoint to add git tags to a project remotely
- Rework/fix the API documentation page (Julen Landa Alustiza)
- Allow deploy keys to commit to the doc git repository of a project
- Increase a lot the logging when someone asks for access to a git repo
- In the src.fp.o theme adjust the links to bugzilla to include the Fedora and
  EPEL bug reports instead of just the Fedora ones


5.8.1 (2019-12-02)
------------------

- Fix the link to the container namespace in srcfpo
- Fix checking if the user is a committer of the repo the PR originates from
- Fix showing the origin of the PR when it originates from the same project
- Do not hard-code UTF-8 when showing a file
- Fix the Vagrant setup


5.8 (2019-11-15)
----------------

- Enable the ctrl-enter keys to submit forms on tickets and PRs (Julen
  Landa Alustiza)
- Fix spelling errors on doc/. (Sergio Durigan Junior)
- Fix renewing url on invalid token error message (Julen Landa Alustiza)
- themes/srcfpo: show release-monitoring choice dropdown only on
  authenticated sessions (Julen Landa Alustiza)
- themes/srcfpo: fix error callback on release-monitoring button ajax
  (Julen Landa Alustiza)
- When not authenticated show the 'take' button but disabled
- disable smooth scrolling on initial highlight & scroll process (Julen
  Landa Alustiza)
- Accept a with_commits parameter on the branches api to resolve the HEAD
  commits (Brian Stinson)
- Fix PR view when fork was deleted (Julen Landa Alustiza)
- Return to the pr view after merging it (Julen Landa Alustiza)
- Add asciidoc syntax override (FeRD (Frank Dana))
- Fix git blame on unborn HEAD or non-master default branch repos (Julen
  Landa Alustiza)
- Drop the adopt button when the package is retired
- Add a set-default-branch action to pagure-admin (Julen Landa Alustiza)
- Allow changing allow_rebase from pull-request edit (Julen Landa Alustiza)
- Add revision along with tag/branch creation/deletion (Fabien Boucher)
- Send oldrev as old_commit for git.receive event (Fabien Boucher)
- Tag filtering support on pull requests list view (Julen Landa Alustiza)
- Tag filtering support on api pull requests endpoint (Julen Landa Alustiza)
- Send notification when a branch is created (Fabien Boucher)
- themes/srcfpo: show navigation buttons, anitya integration and orphan
  taking button only when namespace is not test (Julen Landa Alustiza)
- Add support to expire and update any API token, not just the admin ones
- theme/srcfpo: Include the package's update information in their info page
- Fix setting one's default email address (Julen Landa Alustiza)
- Fix the logic to rebase PRs (Julen Landa Alustiza)
- Add support for arrow >= 0.15
- Select full text on git|ssh url input boxes when they get focus (Julen
  Landa Alustiza)


5.7.9 (2019-09-05)
------------------

- Fix rendering badges on the PR list page
- Tweak when we show the merge and the rebase buttons
- Fix the logic around interacting with read-only databases in hooks
- Fix .diff and .patch generation for empty commits


5.7.8 (2019-08-28)
------------------

- themes/srcfpo: Fix some csp errors
- themes/srcfpo: Fix error message when interacting with the release-monitoring
  button
- themes/srcfpo: Show the release-monitoring dropdown only on authenticated
  users
- themes/srcfpo: Fix capitalization incoherency
- Fix url on the invalid token error message
- Fix typo on the pull request merge error message


5.7.7 (2019-08-21)
------------------

- Allow cross-project API token to open pull-request
- Move the button to change the anitya status to use POST requests


5.7.6 (2019-08-21)
------------------

- Allow updating PRs via the API using cross-project tokens


5.7.5 (2019-08-21)
------------------

- Fix the logic to make the merge button appear on pull-request


5.7.4 (2019-08-10)
------------------

- Fix again the alembic revision adding support for allow_rebase on PRs to
  actually work with mysql
- Relax the default CSP policy so avatars are loaded from libravatar and other
  outside resources
- Improve the support for spec file highlighting


5.7.3 (2019-08-02)
------------------

- Fix the alembic revision adding support for allow_rebase on PRs to work with
  mysql
- Make the doc build in sphinx with python3 by default


5.7.2 (2019-07-30)
------------------

- More CSP headers related fixes (Again thanks to Julen Landa Alustiza)
- Ensures @<username> doesn't overreach to email


5.7.1 (2019-07-12)
------------------

- More CSP headers fixes (Thanks again to Julen Landa Alustiza for them!)


5.7 (2019-07-05)
----------------

- Many fixes to properly support for CSP headers (Many thanks to Julen Landa
  Alustiza for his help with this)
- Fix the blame view
- Allow project-less API token to retrieve issues via the API
- Better integration work on our fork of highlightjs-line-numbers (Julen Landa
  Alustiza)
- Document the git auth backend `pagure` (mrx@mailinator.com)
- Catch ImportError before trying to catch any fedora_messaging exceptions
- Pagure markdown extension: encapsulate our markdowns on a div tag (Julen Landa
  Alustiza)
- Add styling for markdown tables (Julen Landa Alustiza)
- Always notify the person who opened the ticket/PR or are assigned to it
- Add a create-branch action to pagure-admin
- Bump jquery to latest version, fixing some CSP errors (Julen Landa Alustiza)
- Fix file view anchor link highlight & scrolling (Julen Landa Alustiza)
- Focus the comment textarea after hitting the reply button (Julen Landa Alustiza)


5.6 (2019-06-04)
----------------

.. warning:: This release contains a security fix for CVE-2019-11556

- Couple of fixes for the mirroring-in feature
- Fix linking to issues or PRs when pre-viewing a comment
- Include a search icon near the filter button on the issues list
- Include a small introduction text to email on loading files
- Move the side-bar of the repo_master into its own template for easier
  overriding by other themes
- Enforce black on all Pagure, including tests, docs and all
- Add an option to pagure-admin to delete a project
- Add an option to pagure-admin block-user to list the users blocked
- Ensure "No activity" rows get removed on subsequent updates of the calendar
  heatmap (Frank Dana)
- Send a notification upon editing the initial comment of a PR
- Send notifications on tag creation and tag and branch deletion
- Comment reply button: remove icon title (Frank Dana)
- Fix updating project options when running Pagure in python 2
- Fix the test button for webhook notifications
- Fix opening PR on forks on the page listing the PRs
- Add repo_from argument for API create pull request (Lenka Segura)
- Drop commit_flags_uid_key from commit_flags
- Add missing namespace in the link to edit inline comments in PR
- Add support for allowing the maintainers of the target project rebase
- Do not allow rebase via the API if the PR does not allow it
- Improve the install documentation (MR)
- Add CSP headers support and a mechanism to customize them
- Fix triggering a CI run on remote pull-requests
- Add a button to take maintenance of orphaned packages in dist-git
- Fix giving a project to someone who already had it
- Ensure the blame view does not render html


5.5 (2019-04-08)
----------------

- themes/srcfpo: move icons to the theme instead of linking them from other apps
  (Julen Landa Alustiza)
- Add support for !owner to the API listing projects
- Make sure that TemporaryClone.push also pushes tags (Slavek Kabrda)
- Add missing "line" in comments links (Tim Landscheidt)
- Include the target branch of the PR when triggering jenkins
- Provide more information about invalid tokens
- Fix the pagination on the fork page of the dashboard
- Fix opening/viewings PRs from the branch pages on the srcfpo theme
- Allow linking issues to PRs in the initial comment of a PR
- Allow blocking an user on a project
- Add support for username and password based authentication for pagure-ci
- Remove extra "s" character from the starred repos page (Michael Watters)
- Link to bugzilla for rpms, modules and container in the srcfpo theme
- Add a button to select/unselect all the ACLs (Lenka Segura)
- Fix the user in the notification about rebased PR
- pagure/ui/fork: fix pull request closing flash message
- Do not link on the "Star" button if the user is not authenticated
- Replace calls to pygit2.clone_repository by calls to git clone directly
- Support deployments where git hook have a read-only access to the db
- Make fork more performant by using 'git push --mirror' (Slavek Kabrda)
- Move the build ID from the title to the comment of the flag
- Fix the new PR drop-down button
- User the user's default email when rebasing
- Fix a bug that preventing properly cleaning up a project in the DB if we
  failed to create its repositories on disk
- Fix showing branches having unicode characters in their names
- Make the hook mechanism support utf-8 branch names
- Include some shortcuts to the different namespaces in the srcfpo theme


5.4 (2019-03-28)
----------------

- Allow by default the ACL "pull_request_create" on project-less API token
  (Lenka Segura)
- Implement Pagure Git Auth (Patrick Uiterwijk)
- Add a upper limit to sqlalchemy as 1.3.0 breaks our tests
- Add a new API endpoint allowing to update an existing PR
- If the user doesn't have a valid ssh key inform but let them log in
- Fix displaying diffs that contain symlinks (Slavek Kabrda)
- Add missing namespace on the link to see the user's issues when they become
  assignee of a ticket
- Add a button to take/drop a pull-request (assignee field)
- Add a new API endpoint to assign pull-request to someone
- Fix the link to view all the user's projects on the dashboard
- Allow dots and plus signs in project names
- When loading blocking or depending tickets restricts the list of tickets based
  on the user's input
- Fix seeing releases when the reference prodived returned a commit
- Allow div element to have id tags
- Include the PR tags in their JSON representation
- Inform the user when changing the assignee failed because of an ajax error
- Ensure the comment & close button shows up for the author
- Deprecate fedmsg
- Stream the repoSpanner proxy responses (Patrick Uiterwijk)
- Ensure that forking does not run the hook (Patrick Uiterwijk)


5.3 (2019-02-22)
----------------

.. warning:: This release contains a security fix for CVE-2019-762

- Change "created by" to "maintained by" in repo info (Ryan Lerch)
- Fix showing an input box if the minimum score for PR is set to 0
- Fix the output of the merge PR API endpoint when the PR conflicts
- Add some documentation on our magic keywords
- Allow filtering user's PR by time information
- Add the possibility to filter the user's issues by dates
- Add support for the `resolve` keyword among our magic words
- Allow any username to be searched in issues filters (Ryan Lerch)
- Allow using Pagure with python-redis >= 3.0.0 (Neal Gompa)
- Fix Markdown usage to work with Markdown 3.0+ (Neal Gompa)
- Decode the output from the shell commands if they are not already unicode
- Add THEME option docs to configuration documentation (Ryan Lerch)
- Fix updating the date_modified when giving the project to someone
- Don't try mirroring if we failed generating private key
- Change couple of log entries from info to warning
- Cascade deleting flags when tokens are deleted
- Ensure there are admin groups before adding them to the list of groups
- Move the create_session function into pagure.lib.model_base
- Make the button to show/hide the URL to checkout locally a PR more visible
- Fixup documentation about modifyacls (Igor Gnatenko)
- Force highlight.js to use certain highlighting schemes in file view
  (Ryan Lerch)
- Fix the total number of members on the repo info page
- Fix not showing the edit and delete buttons when they won't work
- Add project connector api endpoint (Fabien Boucher)
- Api: project connector endpoint: complete returned data (Fabien Boucher)
- Fix repoSpanner integration (Patrick Uiterwijk)
- Make sure repoSpanner tests run in CentOS CI (Patrick Uiterwijk)
- Only block new branches in hooks (Lubomír Sedlář)
- Add support for fedora-messaging in Pagure
- Fix calculation of days until API key expires in the emails (Karsten Hopp)
- Move to container-based testing on jenkins testing the following environment
  - F29 using python3 with dependencies installed as RPMs
  - F29 using python3 with dependencies installed via pip
  - CentOS7 using python2 with dependencies installed as RPMs
- Add project createapitoken endpoint (Fabien Boucher)
- CVE-2019-7628: Do not leak partial API keys. (Randy Barlow)
- Provide full repospanner reponame for aclchecker/repobridge (Slavek Kabrda)
- Allow turning on issue tracking for only some namespaces
- Do not allow `,` in tags
- Ensure we can add/edit/delete tags even when issues are off but PRs aren't
- Fix cancelling a rebase
- Add options to send notifications on all the message bus we support on all
  commits


5.2 (2019-01-07)
----------------

- Add support for the MQTT protocol (jingjing)
- Add support for mirroring in git repositories from outside sources
- Add the possibility to give a group away
- Port Pagure to markdown 3.0+ while remaining backward compatible
- Add support to merge a PR when the fork was deleted
- Indicate that the file can be either empty or a binary file in diffs
- Add the API endpoint to create new PR in the API doc
- Add the ability to generate archive from a commit or tag
- Allow searching the content of the comments on an issue tracker
- Allow filtering the issue list by the close status
- Update the version of highlightjs-line-numbers. (Clement Verna)
- Store the user who closed a ticket in the database. (Clement Verna)
- Show related PRs on the issue list if there are any
- Bypass old hooks rather than using non-existing symlinks
- Undo submitting comment via JS if the SSE is down
- Make links act like links in the commit message (Ryan Lerch)
- Add build status to pull requests page (Michael Watters)
- Bump the minimal pygit2 version to 0.26.0 (Pierre-Yves Chibon)
- Make update_pull_ref more robust by making sure fork ref is deleted
  (Slavek Kabrda)
- Provide feedback to the user if PRs are disabled in the default target
  projects
- Add a new API endpoint to update the options set for a project
- Add a new API endpoint to retrieve the options of a project
- Update the quick replies button when going into edit mode
- Hide extra GIT URLs behind a collapseable element (Ryan Lerch)
- Save metadata changes when changing status with dropdown (Ryan Lerch)
- Align markdown block of code and citation with GitHub CSS. (Jun Aruga)
- Change formatting of the issue list to make more readable (Ryan Lerch)
- Rename the fedmsg.py hook into fedmsg_hook.py as otherwise it conflicts
- Allow commenting on a PR when clicking on the merge button
- Include whether the PR passed the threshold or not in the API data
- Change the way votes are recorded on PRs
- Add support for third-party extensions to Pagure (this is very much
  work in progress and might/will fluctuate as it is polished - Do Not
  Consider This Stable)
- Enable token authentication on internal endpoints (Slavek Kabrda)
- Fix notifications and refreshing the cached merge status upon updates
- Allow specifying a branch when adding content to git
- Add support for rebasing pull-requests
- Fix viewing patch attached to ticket
- Add link to starred projects in the user menu (Michael Watters)
- Prevent double click from showing two input form
- Fix linking to specific lines in a pull-request
- Do not assume master if the default branch
- Send dedicated notifications when a PR is updated or rebased
- Show the update date/time rather than the creation one on flags
- Allow running 'git gc' explicitly after every object-adding git operation
  (Slavek Kabrda)
- Let any contributor to a project update the PR meta-data
- Rename "Cancel a PR" into "Close a PR"
- Add a Date type to the custom fields (Karsten Hopp)
- Add a new API endpoint to retrieve the flags of a pull-request
- Fix rendering comment added via JS
- Fix API task status endpoint (Slavek Kabrda)
- Make it possible to create hooks that don't have DB entries (Slavek Kabrda)
- Render status of dependent tickets differently on open/close (Akanksha)
- Implement a button to rerun CI tests on a pull request (Slavek Kabrda)
- Support disallowing remote pull requests (Karsten Hopp)
- Change button name to Save instead of Edit while editing pull request
  (anshukira)
- Make sure to also log exceptions in non-debug mode (Patrick Uiterwijk)
- Allow filtering from the milestones page (Akanksha Mishra)
- Fix multimail config with empty auth or disabled tls (Patrick Uiterwijk)
- Add an about page in the themes (Mary Kate Fain)
- Remove "Activate" from project options (jingjing)
- Add avatar_url to output of user/<username> api (Ryan Lerch)
- Fix showing a regular comment on a PR when there are none before
- Fix the UI on the release page when showing the tag message
- Update the chameleon theme (Stasiek Michalski)
- Fix filtering by status PRs retrieved by the API (Lenka Segura)


5.1.4 (2018-10-15)
------------------

- Fix the alembic migration creating the hook_mirror table
- Close the DB session in one place for all hooks
- Add more logging to the pagure_logcom service
- Configure SMTP info for git_multimail (Patrick Uiterwijk)
- Use the PR UID previously read from environment (Patrick Uiterwijk)


5.1.3 (2018-10-11)
------------------

- Don't sync up ssh keys if there are already some
- Do not notify twice when pushing commits to an open PR
- Update git-multimail to the 1.4.0 version (fixes getting it working with py3)


5.1.2 (2018-10-11)
------------------

- Add some documentation about MIRROR_SSHKEYS_FOLDER
- Make the sshkey migration more flexible (if you have not yet upgraded to 5.1)
- Fix the update date information on the pull-request page
- Fix detecting if the user is a committer via a group
- Fix writing user's ssh keys on disk
- tweak colours of the activity graph (Ryan Lerch)
- Allow a specific list of users to create a project ignoring existing repo
  (Patrick Uiterwijk)
- Implement pulling and pushing via repobridge instead of HTTPS
  (Patrick Uiterwijk)
- cache oidc user data (Karsten Hopp)


5.1.1 (2018-10-09)
------------------

- Fix adding and removing ssh keys in the user's profile


5.1 (2018-10-09)
----------------

- Fix rendering issues in chrome (Ryan Lerch)
- Fix the merge button on the PR page when the title is long (Ryan Lerch)
- Hide expired API keys by default but add a button to show them
- Allow linking to the new issue page with a specific template
- Tab order fixed on new issue (Lenka Segura)
- Fix the button to open new pull-request on the branches page
- Fix mail hook getting to mail_to (Patrick Uiterwijk)
- More distinguished Markdown blockquotes (Lenka Segura)
- Correctly exempt default hook from running on non-main (Patrick Uiterwijk)
- Add version information in static file's url to avoid caching in browser
  (Neha Kandpal)
- Update README with details on the new testing script(s) (Jingjing Shao)
- Start implementing HTTP pull/push (Patrick Uiterwijk)
- Many fixes around the documentation and onboarding setup (especially the
  Vagrant and docker dev environments) (Jingjing Shao, Alex Gleason, Lenka
  Segura, Akanksha)
- Fix citing the original comment in a ticket
- Show the comment on issues in JS if the SSE isn't responding
- Fix the From header in notification emails
- Fix loading the group list when adding a group to a project
- Rework how we display loading of the new PR dropdown (Ryan Lerch)
- Display when a PR cannot be merged because of its review score
- Check there is an user associated with the log entry
- Add a note in minimal score to merge in the doc (Fabien Boucher)
- Redirect back to branch list when deleting a branch (Ryan Lerch)
- Rework how ssh keys are stored in the database (Patrick Uiterwijk)
- Allow users to update PR's metadata when the PR is closed
- Fix adding comment on PR via the SSE
- Multiple changes and fixes around the ACL checker (Patrick Uiterwijk)
- Add a spinner when selectize is loading data. (Ryan Lerch)
- Load user async when looking up assignee (Ryan Lerch)
- When a pushed in made to a branch in a PR, update the PR
- Run all hooks in a set, and error out at the end (Patrick Uiterwijk)
- Make hooks raise exceptions instead of sys.exit (Patrick Uiterwijk)
- Fix editing comments on issues and PRs
- Add option to allow any authenticated user to edit meta-data on tickets
- Make the mirroring feature work with older git
- Fix bug in update_milestones (Akanksha)
- Allow admins to ignore existing repositories when creating a project (Patrick
  Uiterwijk)
- Adding 'list-groups' function to pagure-admin (Fabian Arrotin)
- Fix letting the user who opened the ticket close it
- Never set readonly flag if a dynamic auth backend is in use (Patrick Uiterwijk)
- Add a new API endpoint to retrieve the list of files changed in a PR


5.0.1 (2018-09-27)
------------------

.. warning:: This release contains a security fix

- Add to theme the possibility to display site-wide messages (Ryan Lerch)
- Multiple adjustments to the scripts keyhelper and aclchecker (Patrick Uiterwijk)
- Only enforce Signed-Off-By on the main git repo
- Ignore any and all action done by the Pagure user when loading JSON into the db
- Fix the last modified date on the PR list
- Updating regex for URLs and SSH urls
- Use gitolite's own mechanism to bypass the update hook
- Ensure the plugin is active when retrieving them
- Switch from GIT_SORT_TIME to GIT_SORT_NONE to preserver 'git log'-like commit
  ordering (Slavek Kabrda)
- Fix pr-dropdown (Ryan Lerch)
- Add hilightjs-line-numbers plugin (Ryan Lerch)
- Fix the reply buttons
- Fix escaping on PR diffs (Ryan Lerch)
- Fix opening/viewing PRs from the branches page
- Fix loading issue template and make the drop-down a little more obvious
- Correctly align edit button for groups in repo settings (Ryan Lerch)
- Fix all-around sidebar heading borders (Ryan Lerch)
- Remove incorrect count label on related PRs (Ryan Lerch)
- Move attachments to sidebar (Ryan Lerch)
- Add reporter and assignee to notification emails headers (Lenka Segura)
- Make sure that ticket changes don't get duplicated (Patrick Uiterwijk)
- Fix the git ssh urls in the templates
- Fix when milestones_keys and milestones get out of sync
- Sign-off the merge commits when the project enforces it
- Add missing alembic migration to create the hook_mirror table
- Don't generate API keys with random.choice (Jeremy Cline)


5.0 (2018-09-24)
----------------

.. warning:: This release contains backward incompatible changes and fixes a CVE

- Pagure supports now python2 and python3 simultaneously (Thanks to Aurélien
  Bompard and Neal Gompa for the testing)
- New UI deployed (thanks to Ryan Lerch)
- New dashboard page as index page when authenticated (Ryan Lerch)
- API listing items (projects, issues, pull-requests are now paginated (
  Karsten Hopp)
  .. warning:: Backward incompatible
- Enable private projects by default (Neal Gompa)
  .. warning:: Backward incompatible
- Change the default and sample configuration to point to localhost-friendly
  resources (Neal Gompa)
  .. warning:: Backward incompatible
- Disable sending FedMsg notifications by default (Neal Gompa)
  .. warning:: Backward incompatible
- Switch default authentication to `local` (Neal Gompa)
  .. warning:: Backward incompatible
- Drop the dependency on python-pygments
- Drop the dependency on flask-multistatic
- Drop the dependency on python-trollius (in favor of python-trololio) (Neal
  Gompa)
- Bump pygit2 requirement to 0.24.0 minimum
  .. warning:: Backward incompatible
- Add support to re-open a pull-request (Karsten Hopp)
- Fix editing a file into a fork containing a namespace
- Allow creating a new API token based on an expired one
- New API endpoint to submit a pull-request
- Add support for making the issue tracker read-only
- Add a new API endpoint allowing to update watch status on a project
- Paginate the project lists on the front pages
- Let the reply button append instead of replacing
- Add a way to list all API tokens and don't restrict the info command (
  in pagure-admin)
- Expand pagure-admin to allow using it to block an user
- Expand pagure-admin to allow adding new groups using it
- Allow viewing commits from a git tag
- Support viewing commits from a specific commit hash
- Add a hook that disables creating new branches by git push (Slavek Kabrda)
- Make API endpoint for creating new git branch have its own ACL
- Support sorting PR's by recent activity (ymdatta)
- Fix installing the API key reminder cron with systemd  integration
- Add reactions to comments (Lubomír Sedlář)
- New API endpoint allowing to retrieve pull-requests based on their UUID
  (Slavek Kabrda)
- Add an option to restrict emails sent to certain domains (Karsten Hopp)
- Integration with repospanner (Patrick Uiterwijk)
- Rework how git hooks work to rely on a single file rather than moving files
  around (Patrick Uiterwijk)
- Add themes for pagure.io, src.fedoraproject.org (Ryan Lerch)
- Add themes for OpenSUSE (hellcp)
- Ensure remote PR are opened from a remote URL (CVE-2018-1002158 - reported by
  Patrick Uiterwijk)


4.0.4 (2018-07-19)
------------------

.. note:: This release fixes CVE-2018-1002155, CVE-2018-1002156,
        CVE-2018-1002157, CVE-2018-1002153

- Ensure the project's description does not contain any javascript (Michael
  Scherer)
- Prevent the project's URL to be anything other than an URL
- Escape any html people may have injected in their author name in commits
  (Michael Scherer)
- Do not serve SVG inline (Michael Scherer)

  - The four items above constitute CVE-2018-1002155

- Catch exception raised by pagure-ci when it fails to find a build on jenkins
- Fix RELATES and FIXES regex to cover projects with a dash in their name
- Support calls from jenkins indicating the build is started
- Ensure we check the required group membership when giving a project away
- Add missing titles to the milestones table in the settings
- Properly inform the user if they are introducing a duplicated tag
- Only select the default template when creating a new ticket
- Fix the subscribe button on the PR page
- Fix updating a remote PR
- Fix showing the 'more' button on the overview page
- Multiple fixes to the pagure-milter
- Fix triggering CI checks on new comments added to a PR
- Fix logging and the SMTPHandler
- Do not notify everyone about private tickets (CVE-2018-1002157)
- Make the settings of a project private (CVE-2018-1002156)
- Ensure the git repo of private projects aren't exposed via https
  (CVE-2018-1002153)
- Do not log activity on private projects
- Drop trollius-redis requirement (Neal Gompa)


4.0.3 (2018-05-14)
------------------

- Backport utility method from the 4.1 code to fix the 4.0.2 release


4.0.2 (2018-05-14)
------------------

.. note:: This release fixes CVE-2018-1002151

- Fix showing the list of issues in a timely fashion (Patrick Uiterwijk)
- Fix stats for commits without author (Lubomír Sedlář)
- Explain how to fetch a pull request locally and some grammar fixes
  (Todd Zullinger)
- Drop the constraint on the requirement on straight.plugin but document it
- Fix the requirement on bcrypt, it's optional
- Make API endpoint for creating new git branch have its own ACL
  fixes CVE-2018-1002151


4.0.1 (2018-04-26)
------------------

- Fix browsing projects in a namespace when logged in and the instance has only
  one contributor for every projects
- Fix commenting on a PR or an issue if the event source server is not
  configured at all (Slavek Kabrda)


4.0 (2018-04-26)
----------------

- Re-architecture the project to allow potentially extending Pagure outside of
  its core
- Fix running the tests on newer pygit
- Add a space between the fork and the watch buttons
- Add a global configuration option to turn on or off fedmsg notifications for
  the entire Pagure instance
- Set the default username to be 'Pagure' when sending git commit notifications
  by email
- Add project setting to show roadmap by default (Vivek Anand)
- Explain in the doc where the doc is coming from
- Expand and document the tokenization search
- Add document that multiple keys are supported
- Add a way to block non fast-forwardable commits on all branches
- Fix running Pagure on docker for development (Clément Verna)
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
- Merge pagure-ci into the Pagure's celery-based services
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
- Port Pagure to use the compile-1 script from upstream gitolite (if
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
- Make Pagure compatible with newer python chardet
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
- Make the Pagure hook act as the person doing the push
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
- Improve the documentation about documentation hosting in Pagure (René Genz)
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
- Link to Pagure's own markdown documentation and warn that remote images are
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
- Tell fedmsg to send things with Pagure certificates (Patrick Uiterwijk)
- Fix loading ticket templates on namespaced project and extracting their names
- Add a banner on the overview page when the ACLs are being refreshed on the
  backend (and thus ssh access may not be entirely functional) (Vivek Anand)
- Update the documentation on how to create pull requests (Clement Verna)
- Add button to refresh external pull requests (Patrick Uiterwijk)
- Add the possibility to get the group members when asking the project info
- Make the PROJECT_NAME_REGEX used in form be configurable
- Adjust the milter to support replying with any email addresses associated
- Allow Pagure admin to give a project


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
- Retain access when transferring ownership of the project (Matt Prahl)


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
- Add a configuration key to make Pagure case sensitive
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
- Add a configuration key to disable managing user's ssh key in Pagure
- Fix the vagrant environment (Clement Verna)
- Fix branch support for the git blame view
- Update the PR ref when the PR is updated
- Add a configuration key to disable the deploy keys in a Pagure instance
- Fix login when groups are managed outside of Pagure
- Fix setting up the git hooks when there is no DOCS_FOLDER set
- Fix installing up the Pagure hooks when there is no DOCS_FOLDER set


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
  system it supports (Pagure defaults to using redis)
- Multiple stability and performance improvements (mainly thanks to Patrick
  Uiterwijk)
- Fix the assignee value in fedmsg when assigning a ticket (Ricky Elrod)
- Make Pagure support bleach 2.0.0 (Shengjing Zhu)
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
- Do not let Pagure return 500 when hit with bogus URL
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
- Allow repo user to Take/Drop assignment of issue (Vivek Anand)
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
- Allow one to manually triggering a run of pagure-ci via a list of sentences set in
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
- Add ACLs to Pagure (Vivek Anand)
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
- Automatically link the commits mentioned in a ticket if their hash is 7 chars
  or more
- Allow dropping all the priorities info of an issue
- Do not edit multiple times the milestone info when updating a ticket
- Only update the custom field if there is a value to give it, otherwise remote
  it
- Make Pagure compatible with flask-wtf >= 0.14.0
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
- Have Pagure bail with an error message if the OpenID server did not return an
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
- Don't return 404 when viewing empty files (Pradeep CE (cep))
- Do not automatically update the last_updated or updated_on fields
- Make alembic use the DB url specified in the configuration file of Pagure
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
- Remove unused variables (Farhaan Bukhsh)
- Hide the title of private tickets when linking to them in markdown
- Show user activity in Pagure on the user's page
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
- Add go-import meta tag allowing go projects to be hosted on Pagure (Patrick
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
- Port Pagure to flask 0.13+
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
- Ensure user are not logged in if we couldn't properly set them up in Pagure
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
  Pagure)


2.5 (2016-09-13)
----------------

- Don't track pagure_env (venv) dir (Paul W. Frields)
- Setting Mail-Followup-To when sending message to users (Sergio Durigan Junior)
  (Fixed by Ryan Lerch and I)
- Fixed the tickets hook so that we don't ignore the files committed in the first
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
- Allow creating projects with 40 chars length name on newer Pagure instances
- Fix @<user> and #<id> when editing a comment (Eric Barbour)
- Display properly and nicely the ACLs of the API tokens (Lubomír Sedlář)
- Removing html5lib so bleach installation finds what version is best (Tiago M.
  Vieira)
- Remove the branchchooser from the repoheader (again) (Ryan Lerch)
- Fix hard-coded urls in the master template
- Made the interaction with the watch button clearer (Ryan Lerch)
- Introduce pagure-ci, a service allowing to integrate Pagure with a jenkins
  instance (Farhaan Bukhsh and I)
- Accept Close{,s,d} in the same way as Merges and Fixes (Patrick Uiterwijk)
- Avoid showing the 'New PR' button on the overview page is a PR already exists
  for this branch, in the main project or a fork (Vivek Anand)
- Fix presenting the readme file and display the readme in the tree page if
  there is one in the folder displayed (Ryan Lerch)
- Move the new issue button to be available on every page (AnjaliPardeshi)
- Fix Pagure for when an user enters a comment containing #<id> where the id
  isn't found in the db
- Make the bootstrap URLs configurable (so that they don't necessarily point to
  the Fedora infra) (Farhaan Bukhsh)
- Fix how the web-hook server determine the project and its username
- Replace the login icon with plain text (Ryan Lerch)
- Fix layout in the doc (Farhaan Bukhsh)
- Improve the load_from_disk utility script
- Fix our mardown processor to avoid crashing on #<text> (where we expect #<id>)
- Fix the search for projects with a / in their names
- Fix adding a file to a ticket when running Pagure with `local` auth
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
- Add the possibility for Pagure to rely on external groups provided by the auth
  service
- Add the possibility for Pagure to use an SMTP server requiring auth
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

- Fix showing the initial comment on PR having only one commit (Ryan Lerch)
- Fix diffs not showing for additions/deletions for files under 1000 lines (Ryan
  Lerch)
- Split out the commits page to a template of its own (Ryan Lerch)
- Fix highlighting the commits tab on commit view
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
- Fix commit url in the Pagure hook (Mike McLean)
- Improve the regex when fixing/relating a commit to a ticket or a PR (Mike
  McLean)
- Improve the description of the Pagure hook (Mike McLean)
- Fix the priority system to support tickets without priority
- Fix the ordering of the priority in the drop-down list of priorities
- Ensure the drop-down list of priorities defaults to the current priority
- Adjust the runserver.py script to setup PAGURE_CONFIG before importing Pagure
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
- Update the Pagure logo to look better (Ryan Lerch)
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
- Fix hiding the reply buttons when users are not authenticated (Paul W. Frields)
- Improve the description of the git hooks (Lubomír Sedlář)
- Allow reply to a notification of Pagure and setting the reply email address as
  Cc
- In the fedmsg git hook, publish the username of all the users who authored the
  commits pushed
- Add an activity page/feed for each project using the information retrieved
  from datagrepper (Ryan Lerch)
- Fix showing lightweight tags in the releases page (Ryan Lerch)
- Fix showing the list of branches when viewing a file
- Add priorities to issues, with the possibility to filter or sort them by it in
  the page listing them.
- Add support for pseudo-namespace to Pagure (ie: allow one '/' in project name
  with a limited set of prefix allowed)
- Add a new plugin/hook to block push containing commits missing the
  'Signed-off-by' line
- Ensure we always use the default email address when sending notification to
  avoid potentially sending twice a notification
- Add support for using the keyword Merge(s|d) to close a ticket or pull-request
  via a commit message (Patrick Uiterwijk)
- Add an UPGRADING.rst documentation file explaining how to upgrade between
  Pagure releases


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
- Fix the Pagure git hook


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
