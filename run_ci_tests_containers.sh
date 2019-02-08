set -x

yum install -y podman

sysctl -w fs.file-max=2048

set -e

echo $BRANCH $REPO

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
