set -x

yum install -y podman

set -e

echo $BRANCH $REPO

if [ -n "$REPO" -a -n "$BRANCH" ]; then
git remote rm proposed || true
git gc --auto
git remote add proposed "$REPO"
git fetch proposed
git checkout origin/master
git config --global user.email "you@example.com"
git config --global user.name "Your Name"
git merge --no-ff "proposed/$BRANCH" -m "Merge PR"

echo "Running tests for branch $BRANCH of repo $REPO"
echo "Last commits:"
git log -2
fi

podman build --rm -t pagure-f29-rpms-py3 \
    -f dev/containers/f29-rpms-py3 \
    dev/containers

if [ ! -d `pwd`/results_f29-rpms-py3 ]; then
  mkdir `pwd`/results_f29-rpms-py3;
fi

podman run --rm -it --name pagure-f29-rpms-py3 \
    -v `pwd`/results_f29-rpms-py3:/pagure/results:z \
    -e BRANCH=$BRANCH \
    -e REPO=$REPO \
    pagure-f29-rpms-py3


podman build --rm -t pagure-c7-rpms-py2 \
    -f dev/containers/centos7-rpms-py2 \
    dev/containers

if [ ! -d `pwd`/results_centos7-rpms-py2 ]; then
  mkdir `pwd`/results_centos7-rpms-py2;
fi

podman run --rm -it --name pagure-c7-rpms-py2 \
    -v `pwd`/results_centos7-rpms-py2:/pagure/results:z \
    -e BRANCH=$BRANCH \
    -e REPO=$REPO \
    pagure-c7-rpms-py2


podman build --rm -t pagure-fedora-pip-py3 \
    -f dev/containers/fedora-pip-py3 \
    dev/containers

if [ ! -d `pwd`/results_fedora-pip-py3 ]; then
  mkdir `pwd`/results_fedora-pip-py3;
fi

podman run --rm -it --name pagure-fedora-pip-py3 \
    -v `pwd`/results_fedora-pip-py3:/pagure/results:z \
    -e BRANCH=$BRANCH \
    -e REPO=$REPO \
    pagure-fedora-pip-py3
